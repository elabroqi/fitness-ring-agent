import asyncio
from datetime import datetime, timezone

from colmi_r02_client.client import Client
from colmi_r02_client import real_time

RING_ADDRESS = "31:30:45:32:E9:06"


async def main():
    async with Client(RING_ADDRESS) as ring:
        print("Connected to ring")

        await ring.set_time(datetime.now(timezone.utc))
        print("Ring time synced")

        # BEFORE ACTIVITY
        start_steps_data = await ring.get_steps(datetime.now(timezone.utc))
        print("Starting Steps:", start_steps_data)

        input("Walk around, then press ENTER to continue...")

        # AFTER ACTIVITY
        end_steps_data = await ring.get_steps(datetime.now(timezone.utc))
        print("Ending Steps:", end_steps_data)

        # REAL-TIME HEART RATE
        hr_values = await ring.get_realtime_reading(
            real_time.RealTimeReading.HEART_RATE
        )
        print("Heart rate:", hr_values)

        # EXAMPLE STEP DELTA CALCULATION
        if (
            isinstance(start_steps_data, list)
            and isinstance(end_steps_data, list)
            and len(start_steps_data) > 0
            and len(end_steps_data) > 0
        ):
            start_steps = start_steps_data[-1].steps
            end_steps = end_steps_data[-1].steps

            session_steps = end_steps - start_steps

            print("Session Steps:", session_steps)


if __name__ == "__main__":
    asyncio.run(main())