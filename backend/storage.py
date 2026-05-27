"""
MongoDB write path for ring data.

Pure storage layer: takes parsed domain objects (SportDetail, HeartRateLog)
and upserts them into Mongo. Idempotent by design — re-syncing the same day
overwrites in place rather than duplicating.

Collections:
    ring_samples       — one doc per 15-minute SportDetail bucket
    heart_rate_samples — one doc per heart-rate reading
    daily_summaries    — one doc per (user, day), aggregated from ring_samples

Run `ensure_indexes()` once at startup.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone, date
from typing import Iterable

from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from colmi_r02_client import steps, hr

logger = logging.getLogger(__name__)

SOURCE = "colmi_r02"


# --- ID helpers --------------------------------------------------------------

def _bucket_id(user_id: str, ts: datetime) -> str:
    """Deterministic _id for a 15-min sport bucket. Re-syncs overwrite cleanly."""
    return hashlib.sha1(f"sport|{user_id}|{ts.isoformat()}".encode()).hexdigest()


def _hr_sample_id(user_id: str, ts: datetime) -> str:
    return hashlib.sha1(f"hr|{user_id}|{ts.isoformat()}".encode()).hexdigest()


def _daily_id(user_id: str, d: date) -> str:
    return hashlib.sha1(f"daily|{user_id}|{d.isoformat()}".encode()).hexdigest()


# --- Index setup -------------------------------------------------------------

def ensure_indexes(db: Database) -> None:
    """Create the indexes the app relies on. Safe to call repeatedly."""
    db.ring_samples.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    db.ring_samples.create_index(
        [("user_id", ASCENDING), ("year", ASCENDING), ("month", ASCENDING), ("day", ASCENDING)]
    )

    db.heart_rate_samples.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])

    db.daily_summaries.create_index([("user_id", ASCENDING), ("date", DESCENDING)])


# --- SportDetail writes ------------------------------------------------------

def _sport_detail_doc(user_id: str, detail: steps.SportDetail) -> dict:
    ts = detail.timestamp
    return {
        "user_id": user_id,
        "timestamp": ts,                       # stored as native BSON date
        "year": ts.year,
        "month": ts.month,
        "day": ts.day,
        "time_index": detail.time_index,       # 15-min bucket within the day (0..95)
        "steps": detail.steps,
        "distance_meters": detail.distance,
        "calories": detail.calories,
        "ring_calories_raw": getattr(detail, "ring_calories_raw", None),
        "source": SOURCE,
    }


def upsert_sport_details(
    db: Database, user_id: str, details: Iterable[steps.SportDetail]
) -> int:
    """Upsert a batch of SportDetail buckets. Returns the number of ops issued."""
    ops = []
    now = datetime.now(timezone.utc)
    for d in details:
        doc = _sport_detail_doc(user_id, d)
        ops.append(
            UpdateOne(
                {"_id": _bucket_id(user_id, d.timestamp)},
                {
                    "$set": {**doc, "synced_at": now},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        )
    if not ops:
        return 0
    result = db.ring_samples.bulk_write(ops, ordered=False)
    logger.info(
        "ring_samples upsert: matched=%d modified=%d upserted=%d",
        result.matched_count, result.modified_count, len(result.upserted_ids),
    )
    return len(ops)


# --- Heart rate writes -------------------------------------------------------

def upsert_heart_rate_log(db: Database, user_id: str, log: hr.HeartRateLog) -> int:
    """
    Fan out a HeartRateLog into one doc per non-zero sample.

    Assumes `log.heart_rates` is a list of ints and the timestamp of sample i
    is `log.timestamp + i * log.interval` (minutes). Adjust if your HeartRateLog
    exposes the per-sample times directly.
    """
    interval_minutes = getattr(log, "interval", 5)  # most rings default to 5
    start = log.timestamp
    now = datetime.now(timezone.utc)

    ops = []
    for i, bpm in enumerate(log.heart_rates):
        if bpm == 0:
            continue  # ring writes 0 when it didn't get a reading
        sample_ts = start.replace() + _minutes(i * interval_minutes)
        ops.append(
            UpdateOne(
                {"_id": _hr_sample_id(user_id, sample_ts)},
                {
                    "$set": {
                        "user_id": user_id,
                        "timestamp": sample_ts,
                        "bpm": bpm,
                        "source": SOURCE,
                        "synced_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        )
    if not ops:
        return 0
    db.heart_rate_samples.bulk_write(ops, ordered=False)
    return len(ops)


def _minutes(n: int):
    from datetime import timedelta
    return timedelta(minutes=n)


# --- Daily rollups -----------------------------------------------------------

def recompute_daily_summary(db: Database, user_id: str, d: date) -> dict | None:
    """
    Aggregate one day's ring_samples into a daily_summaries doc.

    Call this after each sync (or nightly) so MCP-driven agent queries hit a
    pre-aggregated doc instead of asking the LLM to write a $group pipeline.
    """
    pipeline = [
        {"$match": {"user_id": user_id, "year": d.year, "month": d.month, "day": d.day}},
        {
            "$group": {
                "_id": None,
                "steps": {"$sum": "$steps"},
                "distance_meters": {"$sum": "$distance_meters"},
                "calories": {"$sum": "$calories"},
                "active_buckets": {
                    "$sum": {"$cond": [{"$gt": ["$steps", 0]}, 1, 0]}
                },
                "first_sample": {"$min": "$timestamp"},
                "last_sample": {"$max": "$timestamp"},
            }
        },
    ]
    agg = list(db.ring_samples.aggregate(pipeline))
    if not agg:
        return None
    row = agg[0]
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "date": datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
        "year": d.year,
        "month": d.month,
        "day": d.day,
        "steps": row["steps"],
        "distance_meters": row["distance_meters"],
        "calories": row["calories"],
        "active_minutes": row["active_buckets"] * 15,
        "first_sample_at": row["first_sample"],
        "last_sample_at": row["last_sample"],
        "source": SOURCE,
        "computed_at": now,
    }
    db.daily_summaries.update_one(
        {"_id": _daily_id(user_id, d)},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return doc


# --- Convenience -------------------------------------------------------------

def connect(uri: str, db_name: str = "fitness_ring") -> Database:
    """Tiny helper so callers don't have to import pymongo directly."""
    client = MongoClient(uri, tz_aware=True)
    db = client[db_name]
    ensure_indexes(db)
    return db
