"""
xAPI statement projections.

This module is intentionally pure: it converts domain objects (SportDetail,
HeartRateLog, etc.) into xAPI statement dicts. It does NOT talk to an LRS,
does not do I/O, and does not depend on Mongo. That keeps it usable whether
we end up shipping statements to a real LRS later or just exporting them as
JSON for analytics.

Spec reference: https://github.com/adlnet/xAPI-Spec
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from colmi_r02_client import steps, hr


# --- IRI constants -----------------------------------------------------------
# xAPI requires extension keys, verb IDs, and activity IDs to be IRIs.
# Keep them centralized so they're easy to change and easy to audit.

HOMEPAGE = "https://fitness-ring-agent.local"
VERBS = f"{HOMEPAGE}/verbs"
ACTIVITIES = f"{HOMEPAGE}/activities"
EXT = f"{HOMEPAGE}/extensions"

# Registered activity type from the Activity Streams 1.0 schema — a reasonable
# fit for "physical exercise activity". Not learning-specific, which is fine
# for fitness telemetry.
ACTIVITY_TYPE_EXERCISE = "http://activitystrea.ms/schema/1.0/exercise"


# --- Helpers -----------------------------------------------------------------

def _iso_z(ts: datetime) -> str:
    """Format a datetime as ISO-8601 with a 'Z' suffix for UTC.

    xAPI accepts any valid ISO-8601 with offset, but `Z` is the most widely
    interpreted form across LRS implementations.
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return ts.isoformat().replace("+00:00", "Z")


def _actor(user_id: str) -> dict[str, Any]:
    return {
        "objectType": "Agent",
        "account": {
            "name": user_id,
            "homePage": HOMEPAGE,
        },
    }


def _deterministic_id(*parts: str) -> str:
    """Build a stable UUID5 from the given parts so re-syncs are idempotent.

    Two calls with the same parts produce the same statement ID, which means
    if you POST the same statement to an LRS twice, the second one is
    rejected as a duplicate rather than stored twice.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "/".join(parts)))


# --- Projections -------------------------------------------------------------

def sport_detail_to_statement(user_id: str, detail: steps.SportDetail) -> dict[str, Any]:
    """Project a single 15-minute SportDetail bucket into an xAPI statement."""
    ts_iso = _iso_z(detail.timestamp)
    return {
        "id": _deterministic_id("sport_detail", user_id, ts_iso),
        "actor": _actor(user_id),
        "verb": {
            "id": f"{VERBS}/recorded",
            "display": {"en-US": "recorded"},
        },
        "object": {
            "objectType": "Activity",
            "id": f"{ACTIVITIES}/walking",
            "definition": {
                "name": {"en-US": "Walking Activity"},
                "description": {
                    "en-US": "A 15-minute walking activity segment recorded by the ring."
                },
                "type": ACTIVITY_TYPE_EXERCISE,
            },
        },
        "result": {
            "extensions": {
                f"{EXT}/steps": detail.steps,
                f"{EXT}/distance-meters": detail.distance,
                f"{EXT}/calories": detail.calories,
                f"{EXT}/ring-calories-raw": getattr(detail, "ring_calories_raw", None),
                f"{EXT}/time-index": detail.time_index,
            },
        },
        "timestamp": ts_iso,
    }


def sport_details_to_statements(
    user_id: str, details: list[steps.SportDetail]
) -> list[dict[str, Any]]:
    """Project a list of SportDetail buckets (e.g. one day's worth) into statements."""
    return [sport_detail_to_statement(user_id, d) for d in details]


def heart_rate_log_to_statement(
    user_id: str, log: hr.HeartRateLog
) -> dict[str, Any]:
    """Project a HeartRateLog into a single xAPI statement.

    The series of samples is carried in an extension as an array. If you'd
    rather have one statement per sample (better for some analytics), build
    that variant in a separate function — don't overload this one.
    """
    # HeartRateLog is assumed to expose `.timestamp` (start of the log window)
    # and `.heart_rates` (list[int]). Adjust attribute names if your dataclass
    # differs.
    ts_iso = _iso_z(log.timestamp)
    return {
        "id": _deterministic_id("heart_rate_log", user_id, ts_iso),
        "actor": _actor(user_id),
        "verb": {
            "id": f"{VERBS}/recorded",
            "display": {"en-US": "recorded"},
        },
        "object": {
            "objectType": "Activity",
            "id": f"{ACTIVITIES}/heart-rate",
            "definition": {
                "name": {"en-US": "Heart Rate Log"},
                "description": {
                    "en-US": "A series of heart rate samples recorded by the ring."
                },
                "type": ACTIVITY_TYPE_EXERCISE,
            },
        },
        "result": {
            "extensions": {
                f"{EXT}/heart-rate-samples": list(log.heart_rates),
                f"{EXT}/sample-count": len(log.heart_rates),
            },
        },
        "timestamp": ts_iso,
    }


# --- Mongo interop -----------------------------------------------------------

def statement_from_mongo_sport_detail(doc: dict[str, Any]) -> dict[str, Any]:
    """Project a Mongo `ring_samples` document directly into an xAPI statement.

    Useful when you're exporting historical data from Mongo to an LRS without
    re-hydrating SportDetail objects. Expects the document shape produced by
    the ingest layer:

        {
            "user_id": str,
            "timestamp": datetime,
            "steps": int,
            "distance_meters": int,
            "calories": float,
            "ring_calories_raw": float,
            "time_index": int,
            ...
        }
    """
    user_id = doc["user_id"]
    ts_iso = _iso_z(doc["timestamp"])
    return {
        "id": _deterministic_id("sport_detail", user_id, ts_iso),
        "actor": _actor(user_id),
        "verb": {
            "id": f"{VERBS}/recorded",
            "display": {"en-US": "recorded"},
        },
        "object": {
            "objectType": "Activity",
            "id": f"{ACTIVITIES}/walking",
            "definition": {
                "name": {"en-US": "Walking Activity"},
                "type": ACTIVITY_TYPE_EXERCISE,
            },
        },
        "result": {
            "extensions": {
                f"{EXT}/steps": doc.get("steps"),
                f"{EXT}/distance-meters": doc.get("distance_meters"),
                f"{EXT}/calories": doc.get("calories"),
                f"{EXT}/ring-calories-raw": doc.get("ring_calories_raw"),
                f"{EXT}/time-index": doc.get("time_index"),
            },
        },
        "timestamp": ts_iso,
    }