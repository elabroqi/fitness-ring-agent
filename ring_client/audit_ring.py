import asyncio
from datetime import datetime, timezone, timedelta

from bleak import BleakClient

from colmi_r02_client.client import Client
from colmi_r02_client.steps import NoData
from colmi_r02_client import real_time

RING_ADDRESS = "31:30:45:32:E9:06"


async def print_gatt_services(address):
    print("\n=== BLE Services / Characteristics ===")

    async with BleakClient(address) as client:
        for service in client.services:
            print(f"\nService: {service.uuid}")
            for char in service.characteristics:
                print(f"  Char: {char.uuid}")
                print(f"    Properties: {char.properties}")


async def print_ring_data():
    print("\n=== Ring Data ===")

    async with Client(RING_ADDRESS) as ring:
        battery = await ring.get_battery()
        print("Battery:", battery)

        device_info = await ring.get_device_info()
        print("Device Info:", device_info)

        print("\n=== Step History: Last 7 Days ===")
        for days_back in range(0, 7):
            target = datetime.now(timezone.utc) - timedelta(days=days_back)

            try:
                details = await ring.get_steps(target)

                if isinstance(details, NoData):
                    print(f"{target.date()}: No step data")
                    continue

                print(f"\n{target.date()} — {len(details)} buckets")
                for d in details:
                    print(
                        f"  {d.timestamp.isoformat()} | "
                        f"steps={d.steps} | "
                        f"distance={d.distance}m | "
                        f"calories={d.calories}"
                    )

            except Exception as e:
                print(f"{target.date()}: Failed to read steps: {e}")

        print("\n=== Real-Time Sensor Checks ===")

        for reading_type in [
            real_time.RealTimeReading.HEART_RATE,
            real_time.RealTimeReading.SPO2,
            real_time.RealTimeReading.FATIGUE,
            real_time.RealTimeReading.HRV,
        ]:
            try:
                values = await ring.get_realtime_reading(reading_type)
                print(f"{reading_type.name}: {values}")
            except Exception as e:
                print(f"{reading_type.name}: Failed: {e}")


async def main():
    await print_gatt_services(RING_ADDRESS)
    await print_ring_data()


if __name__ == "__main__":
    asyncio.run(main())