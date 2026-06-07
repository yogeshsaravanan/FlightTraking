from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from app.repositories.database import Base

class FlightHistoricalState(Base):
    __tablename__ = "flight_historical_states"

    id = Column(Integer, primary_key=True, index=True)
    icao24 = Column(String(10), nullable=False, index=True)
    callsign = Column(String(10))
    origin_country = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Integer)
    on_ground = Column(Boolean)
    velocity_kmh = Column(Float)
    raw_speed_ms = Column(Float)
    heading = Column(Integer)
    vertical_rate = Column(Integer)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)