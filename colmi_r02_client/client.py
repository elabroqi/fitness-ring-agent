import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from dataclasses import dataclass
import logging
from pathlib import Path
from types import TracebackType
from typing import Any, BinaryIO

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

from colmi_r02_client import battery, date_utils, steps, set_time, blink_twice, hr, hr_settings, packet, reboot, real_time

UART_SERVICE_UUID = "6E40FFF0-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

DEVICE_INFO_UUID = "0000180A-0000-1000-8000-00805F9B34FB"
DEVICE_HW_UUID = "00002A27-0000-1000-8000-00805F9B34FB"
DEVICE_FW_UUID = "00002A26-0000-1000-8000-00805F9B34FB"

logger = logging.getLogger(__name__)


class ParseError:
    """Sentinel pushed onto a queue when a parser raises, so awaiters fail fast instead of hanging."""

    def __init__(self, exc: BaseException):
        self.exc = exc


def empty_parse(_packet: bytearray) -> None:
    """Used for commands that we expect a response, but there's nothing in the response"""
    return None


# TODO move this maybe?
@dataclass
class FullDataError:
    """Returned in place of a log when fetching that day's data failed."""

    target: datetime
    error: str


@dataclass
class FullData:
    address: str
    heart_rates: list[hr.HeartRateLog | hr.NoData | FullDataError]
    sport_details: list[list[steps.SportDetail] | steps.NoData | FullDataError]


def _build_command_handlers() -> dict[int, Callable[[bytearray], Any]]:
    """
    Build a fresh set of command handlers per Client.

    Parsers like SportDetailParser and HeartRateLogParser are stateful (they
    accumulate across multi-packet responses), so they must NOT be shared
    across Client instances or the state will corrupt between concurrent users.
    """
    return {
        battery.CMD_BATTERY: battery.parse_battery,
        real_time.CMD_START_REAL_TIME: real_time.parse_real_time_reading,
        real_time.CMD_STOP_REAL_TIME: empty_parse,
        steps.CMD_GET_STEP_SOMEDAY: steps.SportDetailParser().parse,
        hr.CMD_READ_HEART_RATE: hr.HeartRateLogParser().parse,
        set_time.CMD_SET_TIME: empty_parse,
        hr_settings.CMD_HEART_RATE_LOG_SETTINGS: hr_settings.parse_heart_rate_log_settings,
    }


class Client:
    def __init__(self, address: str, record_to: Path | None = None):
        self.address = address
        self.bleak_client = BleakClient(self.address)
        self.command_handlers = _build_command_handlers()
        self.queues: dict[int, asyncio.Queue] = {cmd: asyncio.Queue() for cmd in self.command_handlers}
        self.record_to = record_to
        self._record_fh: BinaryIO | None = None

    async def __aenter__(self) -> "Client":
        logger.info(f"Connecting to {self.address}")
        await self.connect()
        logger.info("Connected!")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        logger.info("Disconnecting")
        if exc_val is not None:
            logger.error("Error inside Client context", exc_info=(exc_type, exc_val, exc_tb))
        await self.disconnect()

    async def connect(self):
        await self.bleak_client.connect()

        nrf_uart_service = self.bleak_client.services.get_service(UART_SERVICE_UUID)
        if not nrf_uart_service:
            raise RuntimeError(
                "UART service not found. Ring may be asleep, charging, or connected elsewhere."
            )
        rx_char = nrf_uart_service.get_characteristic(UART_RX_CHAR_UUID)
        if not rx_char:
            raise RuntimeError("RX characteristic not found.")
        self.rx_char = rx_char

        if self.record_to is not None:
            self._record_fh = self.record_to.open("ab")

        await self.bleak_client.start_notify(UART_TX_CHAR_UUID, self._handle_tx)

    async def disconnect(self):
        try:
            await self.bleak_client.disconnect()
        finally:
            if self._record_fh is not None:
                try:
                    self._record_fh.close()
                finally:
                    self._record_fh = None

    def _drain_queue(self, cmd: int) -> None:
        """Drain any stale items from a command's queue before sending a new request."""
        q = self.queues[cmd]
        while not q.empty():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                break

    def _handle_tx(self, _: BleakGATTCharacteristic, packet: bytearray) -> None:
        """Bleak callback that handles new packets from the ring."""

        logger.info(f"Received packet {packet}")

        # Defensive checks. Don't use bare `assert` here: under `python -O`
        # asserts are stripped, and raising inside a Bleak notification
        # callback would just be swallowed and hang any awaiter.
        if len(packet) != 16:
            logger.warning(f"Packet is the wrong length, dropping: {packet!r}")
            return
        packet_type = packet[0]
        if packet_type >= 127:
            logger.warning(f"Packet has error bit set, dropping: {packet!r}")
            return

        if packet_type in self.command_handlers:
            try:
                result = self.command_handlers[packet_type](packet)
            except Exception as e:
                logger.exception(f"Parser for command {packet_type} raised")
                # Push a sentinel so any awaiter wakes up immediately instead of timing out.
                self.queues[packet_type].put_nowait(ParseError(e))
                result = None

            if result is not None:
                self.queues[packet_type].put_nowait(result)
            else:
                logger.debug(f"No result returned from parser for {packet_type}")
        else:
            logger.warning(f"Did not expect this packet: {packet}")

        if self._record_fh is not None:
            # Length-prefix each packet (1 byte for length) since binary data can contain
            # any byte value including newlines, so '\n' is not a safe separator.
            try:
                self._record_fh.write(bytes([len(packet)]))
                self._record_fh.write(packet)
                self._record_fh.flush()
            except Exception:
                logger.exception("Failed to record packet")

    async def send_packet(self, packet: bytearray) -> None:
        logger.debug(f"Sending packet: {packet}")
        await self.bleak_client.write_gatt_char(self.rx_char, packet, response=False)

    async def _await_response(self, cmd: int, timeout: float = 5.0) -> Any:
        """Wait on a command's queue and re-raise if the parser pushed a ParseError sentinel."""
        result = await asyncio.wait_for(self.queues[cmd].get(), timeout=timeout)
        if isinstance(result, ParseError):
            raise RuntimeError(f"Parser failed for command {cmd}") from result.exc
        return result

    async def get_battery(self) -> battery.BatteryInfo:
        self._drain_queue(battery.CMD_BATTERY)
        await self.send_packet(battery.BATTERY_PACKET)
        result = await self._await_response(battery.CMD_BATTERY)
        assert isinstance(result, battery.BatteryInfo)
        return result

    async def _poll_real_time_reading(self, reading_type: real_time.RealTimeReading) -> list[int] | None:
        start_packet = real_time.get_start_packet(reading_type)
        stop_packet = real_time.get_stop_packet(reading_type)

        self._drain_queue(real_time.CMD_START_REAL_TIME)
        await self.send_packet(start_packet)

        valid_readings: list[int] = []
        error = False
        tries = 0
        while len(valid_readings) < 6 and tries < 20:
            try:
                data: real_time.Reading | real_time.ReadingError = await asyncio.wait_for(
                    self.queues[real_time.CMD_START_REAL_TIME].get(),
                    timeout=5,
                )
                if isinstance(data, ParseError):
                    logger.error("Parser error while reading real-time data", exc_info=data.exc)
                    error = True
                    break
                if isinstance(data, real_time.ReadingError):
                    error = True
                    break
                if data.value != 0:
                    valid_readings.append(data.value)
            except TimeoutError:
                tries += 1

        await self.send_packet(stop_packet)
        if error:
            return None
        return valid_readings

    async def get_realtime_reading(self, reading_type: real_time.RealTimeReading) -> list[int] | None:
        return await self._poll_real_time_reading(reading_type)

    async def set_time(self, ts: datetime) -> None:
        await self.send_packet(set_time.set_time_packet(ts))

    async def blink_twice(self) -> None:
        await self.send_packet(blink_twice.BLINK_TWICE_PACKET)

    async def get_device_info(self) -> dict[str, str]:
        client = self.bleak_client
        data = {}
        device_info_service = client.services.get_service(DEVICE_INFO_UUID)
        assert device_info_service

        hw_info_char = device_info_service.get_characteristic(DEVICE_HW_UUID)
        assert hw_info_char
        hw_version = await client.read_gatt_char(hw_info_char)
        data["hw_version"] = hw_version.decode("utf-8")

        fw_info_char = device_info_service.get_characteristic(DEVICE_FW_UUID)
        assert fw_info_char
        fw_version = await client.read_gatt_char(fw_info_char)
        data["fw_version"] = fw_version.decode("utf-8")

        return data

    async def get_heart_rate_log(self, target: datetime | None = None) -> hr.HeartRateLog | hr.NoData:
        if target is None:
            target = date_utils.start_of_day(date_utils.now())
        self._drain_queue(hr.CMD_READ_HEART_RATE)
        await self.send_packet(hr.read_heart_rate_packet(target))
        return await self._await_response(hr.CMD_READ_HEART_RATE)

    async def get_heart_rate_log_settings(self) -> hr_settings.HeartRateLogSettings:
        self._drain_queue(hr_settings.CMD_HEART_RATE_LOG_SETTINGS)
        await self.send_packet(hr_settings.READ_HEART_RATE_LOG_SETTINGS_PACKET)
        return await self._await_response(hr_settings.CMD_HEART_RATE_LOG_SETTINGS)

    async def set_heart_rate_log_settings(self, enabled: bool, interval: int) -> None:
        self._drain_queue(hr_settings.CMD_HEART_RATE_LOG_SETTINGS)
        await self.send_packet(hr_settings.hr_log_settings_packet(hr_settings.HeartRateLogSettings(enabled, interval)))

        # The ring acks the write on the same command code as the read response,
        # but the payload doesn't reflect the new settings — it appears to echo
        # back stale/garbage data. We drain it here so the next read isn't
        # confused by a leftover packet. TODO: investigate the actual ack format
        # so we can confirm the write succeeded instead of blindly discarding.
        await self._await_response(hr_settings.CMD_HEART_RATE_LOG_SETTINGS)

    async def get_steps(self, target: datetime, today: datetime | None = None) -> list[steps.SportDetail] | steps.NoData:
        if today is None:
            today = datetime.now(timezone.utc)

        if target.tzinfo != timezone.utc:
            logger.info("Converting target time to utc")
            target = target.astimezone(tz=timezone.utc)

        days = (today.date() - target.date()).days
        if days < 0:
            raise ValueError(
                f"target ({target.date()}) is in the future relative to today ({today.date()}); "
                "the ring can only return past data"
            )
        logger.debug(f"Looking back {days} days")

        self._drain_queue(steps.CMD_GET_STEP_SOMEDAY)
        await self.send_packet(steps.read_steps_packet(days))
        return await self._await_response(steps.CMD_GET_STEP_SOMEDAY)

    async def reboot(self) -> None:
        await self.send_packet(reboot.REBOOT_PACKET)

    async def raw(self, command: int, subdata: bytearray, replies: int = 0) -> list[bytearray]:
        if command not in self.queues:
            raise ValueError(
                f"Command {command} has no registered handler/queue; cannot collect replies for it"
            )
        p = packet.make_packet(command, subdata)
        self._drain_queue(command)
        await self.send_packet(p)

        results: list[bytearray] = []
        while replies > 0:
            try:
                data: bytearray = await self._await_response(command)
                results.append(data)
            except TimeoutError:
                logger.warning(
                    f"Timed out waiting for reply {len(results) + 1}/{len(results) + replies} "
                    f"to command {command}; returning partial results"
                )
                break
            replies -= 1

        return results

    async def get_full_data(self, start: datetime, end: datetime) -> FullData:
        """
        Fetches all data from the ring between start and end. Useful for syncing.

        Note: this is sequential — BLE only allows one in-flight request per
        connection — so runtime scales linearly with (end - start). Errors on
        individual days are captured as FullDataError entries rather than
        aborting the whole sync.
        """
        heart_rate_logs: list[hr.HeartRateLog | hr.NoData | FullDataError] = []
        sport_detail_logs: list[list[steps.SportDetail] | steps.NoData | FullDataError] = []
        for d in date_utils.dates_between(start, end):
            try:
                heart_rate_logs.append(await self.get_heart_rate_log(d))
            except Exception as e:
                logger.exception(f"Failed to fetch heart rate log for {d}")
                heart_rate_logs.append(FullDataError(target=d, error=str(e)))

            try:
                sport_detail_logs.append(await self.get_steps(d))
            except Exception as e:
                logger.exception(f"Failed to fetch sport detail log for {d}")
                sport_detail_logs.append(FullDataError(target=d, error=str(e)))

        return FullData(self.address, heart_rates=heart_rate_logs, sport_details=sport_detail_logs)