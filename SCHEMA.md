# Fitness Ring — MongoDB Schema

This database stores activity data synced from a Colmi R02 fitness ring.
You (the agent) have access to it via the MongoDB MCP. Use this doc to write
correct, efficient queries.

**Database:** `fitness_agent`
**Time zone:** All timestamps are stored as UTC `Date` values. When the user
asks about "today" or "this week," interpret in their local time zone if
known, otherwise UTC.

---

## Collections

### `ring_samples` — raw 15-minute activity buckets

One document per 15-minute window. This is the finest-grained data available.

| Field               | Type    | Notes                                                       |
|---------------------|---------|-------------------------------------------------------------|
| `_id`               | string  | SHA1 of `user_id + timestamp`; deterministic across syncs   |
| `user_id`           | string  | Stable per-user identifier                                  |
| `timestamp`         | Date    | Start of the 15-min bucket, UTC                             |
| `year`              | int     | UTC year                                                    |
| `month`             | int     | UTC month (1–12)                                            |
| `day`               | int     | UTC day of month (1–31)                                     |
| `time_index`        | int     | Bucket index within the day (0–95). 0 = 00:00, 4 = 01:00    |
| `steps`             | int     | Steps taken in this 15-min window                           |
| `distance_meters`   | int     | Distance covered, in meters                                 |
| `calories`          | number  | Calories burned (kcal). May be int or float                 |
| `ring_calories_raw` | int     | Pre-conversion value from the ring; ignore for analytics    |
| `source`            | string  | Always `"colmi_r02"` for now                                |
| `synced_at`         | Date    | Last time this doc was written                              |

**Indexes:**
- `{ user_id: 1, timestamp: -1 }` — use for recent-activity queries
- `{ user_id: 1, year: 1, month: 1, day: 1 }` — use for day-bucketed rollups

### `heart_rate_samples` — individual heart-rate readings

One document per non-zero heart-rate sample. The ring writes `0` when it
couldn't get a reading; those are filtered out and not stored.

| Field        | Type    | Notes                                |
|--------------|---------|--------------------------------------|
| `_id`        | string  | SHA1 of `user_id + timestamp`        |
| `user_id`    | string  |                                      |
| `timestamp`  | Date    | When the sample was taken, UTC       |
| `bpm`        | int     | Heart rate in beats per minute       |
| `source`     | string  | `"colmi_r02"`                        |
| `synced_at`  | Date    | Last write time                      |

**Indexes:**
- `{ user_id: 1, timestamp: -1 }`

### `daily_summaries` — pre-aggregated per-day totals

Materialized after each sync. **Prefer this collection for any "total X per
day" or "average X this week" question** — it's faster and the numbers are
already correct.

| Field              | Type   | Notes                                              |
|--------------------|--------|----------------------------------------------------|
| `_id`              | string | SHA1 of `user_id + date`                           |
| `user_id`          | string |                                                    |
| `date`             | Date   | Midnight UTC of the day                            |
| `year`/`month`/`day` | int  | Convenience fields                                 |
| `steps`            | int    | Total steps for the day                            |
| `distance_meters`  | int    | Total distance for the day                         |
| `calories`         | number | Total calories for the day                         |
| `active_minutes`   | int    | Minutes with any step activity (rounded to 15)     |
| `first_sample_at`  | Date   | Timestamp of first non-empty bucket                |
| `last_sample_at`   | Date   | Timestamp of last non-empty bucket                 |
| `source`           | string | `"colmi_r02"`                                      |
| `computed_at`      | Date   | When the rollup was last computed                  |

**Indexes:**
- `{ user_id: 1, date: -1 }`

---

## Query recipes

### Today's totals
```js
db.daily_summaries.findOne(
  { user_id: "<id>", date: ISODate("<today-midnight-UTC>") }
)
```

### Last 7 days of step totals
```js
db.daily_summaries.find(
  { user_id: "<id>", date: { $gte: ISODate("<7-days-ago>") } },
  { date: 1, steps: 1, calories: 1, _id: 0 }
).sort({ date: -1 })
```

### Hour-by-hour steps for a given day (from raw buckets)
```js
db.ring_samples.aggregate([
  { $match: { user_id: "<id>", year: 2026, month: 5, day: 26 } },
  { $group: {
      _id: { $floor: { $divide: ["$time_index", 4] } },  // 4 buckets per hour
      steps: { $sum: "$steps" }
  }},
  { $sort: { _id: 1 } }
])
```

### Average resting heart rate over the last week
```js
db.heart_rate_samples.aggregate([
  { $match: {
      user_id: "<id>",
      timestamp: { $gte: ISODate("<7-days-ago>") },
      bpm: { $lt: 80 }    // crude resting filter
  }},
  { $group: { _id: null, avg_bpm: { $avg: "$bpm" } } }
])
```

### Most active 15-minute window today
```js
db.ring_samples.find(
  { user_id: "<id>", year: 2026, month: 5, day: 26 }
).sort({ steps: -1 }).limit(1)
```

---

## Conventions and gotchas

- **Always filter by `user_id` first.** Every index is `user_id`-prefixed; un-prefixed queries do a collection scan.
- **Use `daily_summaries` for any aggregate spanning more than a day or two.** Don't `$group` over `ring_samples` for week/month rollups unless the daily doc is missing.
- **`calories` may be a float** in `ring_samples` (the ring reports tenths of a kcal). Treat as a number; don't compare to integers strictly.
- **`time_index` semantics:** `time_index // 4` is the hour, `(time_index % 4) * 15` is the minute within that hour.
- **Zero-step buckets are still stored.** They're real data (the user was inactive), not missing data. Filter with `{ steps: { $gt: 0 } }` if you want activity only.
- **Heart-rate zeros are NOT stored.** Absence of a sample at time T means the ring couldn't read it, not that the user's heart stopped.
- **Re-syncs overwrite, not duplicate.** If the same time window appears again, the `_id` collides and the doc updates in place. Counts are stable across re-syncs.
- **No multi-user joins.** Each user's data is isolated by `user_id`; don't try to compare across users unless the question explicitly asks for it.
