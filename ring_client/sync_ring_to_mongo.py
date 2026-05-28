import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
import os

from datetime import datetime, timezone, timedelta

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


async def sync_day(ring, db, target_date):
    details = await ring.get_steps(target_date)

    if isinstance(details, NoData):
        print(f"No data for {target_date.date()}")
        return

    print(f"\n=== {target_date.date()} ===")
    print(f"Retrieved {len(details)} sport buckets")

    for d in details:
        print(
            f"  {d.timestamp.isoformat()} | "
            f"steps={d.steps} | "
            f"distance={d.distance}m | "
            f"calories={d.calories} | "
            f"raw_calories={getattr(d, 'ring_calories_raw', None)}"
        )

    inserted = upsert_sport_details(
        db,
        USER_ID,
        details,
    )

    print(f"Stored {inserted} ring samples")

    recompute_daily_summary(
        db,
        USER_ID,
        target_date.date(),
    )


async def main():
    db = connect(os.getenv("MONGO_URI"))

    ring = Client(RING_ADDRESS)

    await ring.connect()
    print("Connected to ring")

    try:

        # HISTORY SYNC
        for days_back in range(1, 7):
            target = datetime.now(timezone.utc) - timedelta(days=days_back)

            try:
                await sync_day(ring, db, target)
            except Exception as e:
                print(f"Failed historical sync for {target.date()}: {e}")

        # TODAY SYNC
        today = datetime.now(timezone.utc)

        try:
            await sync_day(ring, db, today)
        except Exception as e:
            print(f"Failed today sync: {e}")

    finally:
        await ring.disconnect()
        print("Disconnected from ring")


if __name__ == "__main__":
    asyncio.run(main())