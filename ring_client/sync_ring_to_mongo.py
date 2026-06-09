import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
import os
import argparse
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

from ring_client.colmi_ring import ColmiRing

from backend.storage import (
    connect,
    upsert_sport_details,
    recompute_daily_summary,
)

load_dotenv()


def _get_args():
    p = argparse.ArgumentParser(description="Sync ring data to MongoDB for a given user")
    p.add_argument("--user-id", dest="user_id", help="Target user id to sync for")
    p.add_argument("--ring-address", dest="ring_address", help="Fallback ring bluetooth address (MAC)")
    return p.parse_args()


ARGS = _get_args()

USER_ID = ARGS.user_id or os.getenv("USER_ID")
FALLBACK_RING_ADDRESS = ARGS.ring_address or os.getenv("RING_ADDRESS")


async def sync_day(ring, db, target_date):
    details = await ring.sync_steps(target_date)

    if not details:
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
    global USER_ID

    if not USER_ID:
        USER_ID = input("Enter user id to sync for: ").strip()

    db = connect(os.getenv("MONGO_URI"))

    # Try to resolve the ring address from the registration collections
    device_doc = db.registered_devices.find_one({"user_id": USER_ID}) or db.devices.find_one({"user_id": USER_ID})
    ring_address = None
    if device_doc:
        ring_address = device_doc.get("address") or device_doc.get("ios_peripheral_uuid")

    if not ring_address:
        if FALLBACK_RING_ADDRESS:
            ring_address = FALLBACK_RING_ADDRESS
            print(f"Using fallback ring address from env/arg: {ring_address}")
        else:
            ring_address = input("Could not find registered ring address for user; enter ring address (MAC) to use: ").strip()

    # If the stored id is an iOS peripheral UUID (not a MAC), warn the user
    if ring_address and len(ring_address) == 36 and '-' in ring_address:
        print("Warning: resolved address looks like an iOS peripheral UUID. Desktop sync requires a MAC address. If you only have an iOS UUID, run sync from a machine that knows the device MAC or provide --ring-address.")

    ring = ColmiRing(ring_address)

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