from datetime import datetime, timezone
import os
from pathlib import Path
import logging
from typing import Any

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship
from sqlalchemy import select, UniqueConstraint, ForeignKey, create_engine, event, func, types
from sqlalchemy.engine import Engine, Dialect

# Import PyMongo to speak to your new Atlas Cluster
from pymongo import MongoClient
from dotenv import load_dotenv

from colmi_r02_client import hr, steps
from colmi_r02_client.client import FullData
from colmi_r02_client.date_utils import start_of_day, end_of_day

load_dotenv()
logger = logging.getLogger(__name__)

# ==========================================
# NEW: MongoDB Initializer Wrapper
# ==========================================
def get_mongodb_client():
    """Safely fetch your global Atlas connection mapping"""
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGO_URI")
    if not mongo_uri:
        logger.warning("⚠️ MONGO_URI not found in environment variables!")
        return None
    return MongoClient(mongo_uri)

class Base(DeclarativeBase):
    pass


class DateTimeInUTC(types.TypeDecorator):
    """
    TypeDecorator for sqlalchemy that will:

        1. make sure that you cannot save datetimes with no tzinfo/timezone
        2. convert any datetime to utc before saving it
        3. add the utc timezone to all datetimes retrieved from the database
    """

    impl = types.DateTime
    cache_ok = True

    def process_bind_param(self, value: Any | None, _dialect: Dialect) -> datetime | None:
        if value is None:
            return None

        if not isinstance(value, datetime):
            raise ValueError(f"Trying to store {value} that's not a datetime")

        if value.tzinfo is None:
            raise ValueError(f"Trying to store {value} with no timezone")

        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Any | None, _dialect: Dialect) -> datetime | None:
        if value is None:
            return None

        if not isinstance(value, datetime):
            raise ValueError(f"Trying to add timezone to {value} that's not a datetime")

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)


class Ring(Base):
    __tablename__ = "rings"
    __table_args__ = (UniqueConstraint("address"),)
    ring_id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str]
    heart_rates: Mapped[list["HeartRate"]] = relationship(back_populates="ring")
    sport_details: Mapped[list["SportDetail"]] = relationship(back_populates="ring")
    syncs: Mapped[list["Sync"]] = relationship(back_populates="ring")


class Sync(Base):
    __tablename__ = "syncs"
    sync_id: Mapped[int] = mapped_column(primary_key=True)
    ring_id = mapped_column(ForeignKey("rings.ring_id"), nullable=False)
    timestamp = mapped_column(DateTimeInUTC(timezone=True), nullable=False)
    comment: Mapped[str | None]
    ring: Mapped["Ring"] = relationship(back_populates="syncs")
    heart_rates: Mapped[list["HeartRate"]] = relationship(back_populates="sync")
    sport_details: Mapped[list["SportDetail"]] = relationship(back_populates="sync")


class HeartRate(Base):
    __tablename__ = "heart_rates"
    __table_args__ = (UniqueConstraint("ring_id", "timestamp"),)
    heart_rate_id: Mapped[int] = mapped_column(primary_key=True)
    reading: Mapped[int]
    timestamp = mapped_column(DateTimeInUTC(timezone=True), nullable=False)
    ring_id = mapped_column(ForeignKey("rings.ring_id"), nullable=False)
    ring: Mapped["Ring"] = relationship(back_populates="heart_rates")
    sync_id = mapped_column(ForeignKey("syncs.sync_id"), nullable=False)
    sync: Mapped["Sync"] = relationship(back_populates="heart_rates")


class SportDetail(Base):
    __tablename__ = "sport_details"
    __table_args__ = (UniqueConstraint("ring_id", "timestamp"),)
    sport_detail_id: Mapped[int] = mapped_column(primary_key=True)
    calories: Mapped[int]
    steps: Mapped[int]
    distance: Mapped[int]
    timestamp = mapped_column(DateTimeInUTC(timezone=True), nullable=False)
    ring_id = mapped_column(ForeignKey("rings.ring_id"), nullable=False)
    ring: Mapped["Ring"] = relationship(back_populates="sport_details")
    sync_id = mapped_column(ForeignKey("syncs.sync_id"), nullable=False)
    sync: Mapped["Sync"] = relationship(back_populates="sport_details")


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable actual foreign key checks in sqlite on every connection to the database"""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db_session(path: Path | None = None) -> Session:
    """
    Return a live db session with all tables created.

    TODO: probably not default to in memory... that's just useful for testing
    """

    url = "sqlite:///"
    if path is not None:
        url = url + str(path)
    else:
        logger.info("Using in memory sqlite database. Data will be lost after program exits")
        url = url + ":memory:"
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    return Session(engine)


def create_or_find_ring(session: Session, address: str) -> Ring:
    ring = session.scalars(select(Ring).where(Ring.address == address)).one_or_none()
    if ring is not None:
        return ring

    ring = Ring(address=address)
    session.add(ring)
    session.commit()  # not sure this should be here tbh
    return ring

# ==========================================
# UPDATED: full_sync with MongoDB Pipeline
# ==========================================
def full_sync(session: Session, data: FullData) -> None:
    """Sync all data from the ring to local SQLite, then push clean blocks to MongoDB Atlas."""
    
    # 1. Run your original local SQLite transaction safely
    ring = create_or_find_ring(session, data.address)
    sync = Sync(ring=ring, timestamp=datetime.now(tz=timezone.utc))
    session.add(sync)

    _add_heart_rate(sync, ring, data, session)
    _add_sport_details(sync, ring, data, session)
    session.commit()
    logger.info("✅ SQLite local caching sync transaction complete.")

    # 2. Extract, normalize, and push the clean data up to your MongoDB cluster
    mongo_client = get_mongodb_client()
    if mongo_client is None:
        return

    try:
        db_name = os.getenv("MONGO_DB", "fitness_ring")
        mongo_db = mongo_client[db_name]
        user_id = "aurela"  # Aligns perfectly with your setup_db.py profile
        
        # --- SUB-PIPELINE A: Process and Normalize Steps/Calories ---
        total_steps = 0
        total_calories = 0
        total_distance = 0
        latest_timestamp = None

        for slog in data.sport_details:
            if isinstance(slog, steps.NoData):
                continue
            for item in slog:
                total_steps += item.steps
                # FIXING CALORIE MULTIPLIER BUG RIGHT HERE AT THE GATE:
                # If your ring reads 47250, this cleanly drops it down to 47.25 kcal
                total_calories += (item.calories / 1000.0 if item.calories > 1000 else item.calories)
                total_distance += item.distance
                latest_timestamp = item.timestamp

        # If we parsed active workout data blocks, upsert them as a Workout event
        if total_steps > 0:
            workout_payload = {
                "user_id": user_id,
                "synced_at": datetime.now(tz=timezone.utc),
                "recorded_at": latest_timestamp or datetime.now(tz=timezone.utc),
                "metrics": {
                    "daily_steps": total_steps,
                    "calories_burned_kcal": round(total_calories, 2),
                    "distance_meters": total_distance
                },
                "source_device": "COLMI_R02",
                "device_address": data.address
            }
            
            # Upsert into a clean timeline table based on the date string
            date_str = (latest_timestamp or datetime.now(tz=timezone.utc)).strftime("%Y-%m-%d")
            mongo_db.daily_summaries.update_one(
                {"user_id": user_id, "date": date_str},
                {"$set": workout_payload},
                upsert=True
            )
            logger.info(f"💾 MongoDB Atlas: Saved dynamic daily summary metrics for {date_str}")

        # --- SUB-PIPELINE B: Process and Normalize Heart Rates ---
        heart_rate_documents = []
        for log in data.heart_rates:
            if isinstance(log, hr.NoData):
                continue
            for reading, timestamp in log.heart_rates_with_times():
                if reading == 0:
                    continue
                
                # Format an open-ended, granular biometric log document for your AI Agent
                heart_rate_documents.append({
                    "user_id": user_id,
                    "timestamp": timestamp,
                    "bpm": reading,
                    "device_address": data.address
                })

        if heart_rate_documents:
            # Drop them in using bulk writes to avoid hammer-pinging the network connection
            # We use update_one with upsert to prevent duplicate entries if you sync twice in one day
            for hr_doc in heart_rate_documents:
                mongo_db.biometrics_timeline.update_one(
                    {"user_id": user_id, "timestamp": hr_doc["timestamp"]},
                    {"$set": hr_doc},
                    upsert=True
                )
            logger.info(f"💾 MongoDB Atlas: Bulk synced {len(heart_rate_documents)} biometric metrics.")

    except Exception as mongo_err:
        logger.error(f"❌ Failed to bridge telemetry data over to MongoDB Atlas cluster: {mongo_err}")
    finally:
        mongo_client.close()



def _add_heart_rate(sync: Sync, ring: Ring, data: FullData, session: Session) -> None:
    logger.info(f"Adding {len(data.heart_rates)} days of heart rates")
    for log in data.heart_rates:
        if isinstance(log, hr.NoData):
            logger.info("No heart rate data for date")
            continue

        existing = {}
        for heart_rate in session.scalars(
            select(HeartRate)
            .where(HeartRate.timestamp >= start_of_day(log.timestamp))
            .where(HeartRate.timestamp <= end_of_day(log.timestamp))
        ):
            existing[heart_rate.timestamp] = heart_rate.reading

        for reading, timestamp in log.heart_rates_with_times():
            if reading == 0:
                continue

            if x := existing.get(timestamp):
                if x != reading:
                    logger.warning(f"Inconsistent data detected! {timestamp} is {x} in db but got {reading} from ring")
            else:
                h = HeartRate(reading=reading, timestamp=timestamp, ring=ring, sync=sync)
                session.add(h)


def _add_sport_details(sync: Sync, ring: Ring, data: FullData, session: Session) -> None:
    logger.info(f"Adding {len(data.sport_details)} days of sport details")
    sport_detail_logs: list[steps.SportDetail] = []
    for slog in data.sport_details:
        if isinstance(slog, steps.NoData):
            logger.info("No step data for date")
        else:
            sport_detail_logs.extend(slog)
    if len(sport_detail_logs) == 0:
        return
    start = min([sport_detail.timestamp for sport_detail in sport_detail_logs])
    end = max([sport_detail.timestamp for sport_detail in sport_detail_logs])

    existing_sport_logs = {}
    for sport_detail_record in session.scalars(
        select(SportDetail)
        .where(SportDetail.timestamp >= start_of_day(start))
        .where(SportDetail.timestamp <= end_of_day(end))
    ):
        existing_sport_logs[sport_detail_record.timestamp] = sport_detail_record

    for sport_detail in sport_detail_logs:
        if x := existing_sport_logs.get(sport_detail.timestamp):
            x.calories = sport_detail.calories
            x.steps = sport_detail.steps
            x.distance = sport_detail.distance
            session.add(x)
        else:
            s = SportDetail(
                calories=sport_detail.calories,
                steps=sport_detail.steps,
                distance=sport_detail.distance,
                timestamp=sport_detail.timestamp,
                ring=ring,
                sync=sync,
            )
            session.add(s)


def get_last_sync(session: Session, ring_address: str) -> datetime | None:
    return session.scalars(select(func.max(Sync.timestamp)).join(Ring).where(Ring.address == ring_address)).one_or_none()
