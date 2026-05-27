import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from colmi_r02_client.client import Client
from colmi_r02_client.steps import NoData

from backend.storage import (
    connect,
    upsert_sport_details,
    recompute_daily_summary,
)

load_dotenv()

RING_ADDRESS = "31:30:45:32:E9:06"
USER_ID = "aurela"


async def main():
    db = connect(os.getenv("MONGO_URI"))

    async with Client(RING_ADDRESS) as ring:
        print("Connected to ring")

        details = await ring.get_steps(datetime.now(timezone.utc))

        if isinstance(details, NoData):
            print("No step data")
            return

        print(f"Retrieved {len(details)} sport buckets")

        inserted = upsert_sport_details(
            db,
            USER_ID,
            details,
        )

        print(f"Stored {inserted} ring samples")

        today = datetime.now(timezone.utc).date()

        summary = recompute_daily_summary(
            db,
            USER_ID,
            today,
        )

        print("Daily Summary:")
        print(summary)


if __name__ == "__main__":
    asyncio.run(main())