import asyncio
from datetime import datetime, timezone

from colmi_r02_client.client import Client


RING_ADDRESS = "31:30:45:32:E9:06"


async def main():
    async with Client(RING_ADDRESS) as ring:
        print("Connected to ring")

        battery = await ring.get_battery()
        print("Battery:", battery)

        device_info = await ring.get_device_info()
        print("Device Info:", device_info)

        steps = await ring.get_steps(datetime.now(timezone.utc))
        print("Steps:", steps)


if __name__ == "__main__":
    asyncio.run(main())