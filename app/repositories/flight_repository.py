import json
import httpx
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.config import settings
from app.repositories.database import redis_client
from app.repositories.models import FlightHistoricalState

from sqlalchemy import select, desc

class FlightRepository:
    def __init__(self):
        self.cache_key = "flights:active_stream"

    async def get_cached_flights(self) -> List[dict]:
        """Reads instantly from Redis cache to shield OpenSky and PostgreSQL."""
        data = await redis_client.get(self.cache_key)
        if data:
            return json.loads(data)
        return []
    
    async def get_historical_records(
        self, 
        db_session: AsyncSession,
        icao: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 100
    ) -> List[FlightHistoricalState]:
        """Queries the PostgreSQL cold database for logged flight snapshots."""
        stmt = select(FlightHistoricalState).order_by(desc(FlightHistoricalState.recorded_at))

        # Apply database filtering clauses if parameters are provided
        if icao:
            stmt = stmt.where(FlightHistoricalState.icao24 == icao.lower().strip())
        if country:
            stmt = stmt.where(FlightHistoricalState.origin_country.ilike(f"%{country.strip()}%"))

        # Enforce a limit cap to prevent heavy queries from crashing memory
        stmt = stmt.limit(limit)
        
        result = await db_session.execute(stmt)
        return result.scalars().all()

    async def refresh_and_store_pipeline(self, db_session: AsyncSession) -> List[dict]:
        """
        The Core Engine Worker Target: Fetches OpenSky data, pushes to Redis cache,
        and logs snapshots straight into PostgreSQL.
        """
        params = {
            "lamin": settings.LAMIN, "lomin": settings.LOMIN,
            "lamax": settings.LAMAX, "lomax": settings.LOMAX
        }
        
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(settings.OPENSKY_URL, params=params)
            if response.status_code != 200:
                return await self.get_cached_flights() # Fallback to existing cache on error

            states = response.json().get("states") or []
            processed_list = []
            db_insert_mappings = []

            for s in states:
                if s[5] is None or s[6] is None:
                    continue
                
                # Transform telemetry mapping structures
                flight_obj = {
                    "icao": s[0],
                    "callsign": (s[1] or "").strip() or s[0],
                    "country": s[2] or "Unknown",
                    "lon": s[5],
                    "lat": s[6],
                    "altitude": round(s[7]) if s[7] is not None else 0,
                    "onGround": bool(s[8]),
                    "speed": round(s[9] * 3.6) if s[9] is not None else 0,
                    "rawSpeedMs": s[9] or 0.0,
                    "heading": round(s[10]) if s[10] is not None else 0,
                    "vertRate": round(s[11]) if s[11] is not None else 0
                }
                processed_list.append(flight_obj)

                # Prepare relational record maps
                db_insert_mappings.append({
                    "icao24": flight_obj["icao"],
                    "callsign": flight_obj["callsign"],
                    "origin_country": flight_obj["country"],
                    "latitude": flight_obj["lat"],
                    "longitude": flight_obj["lon"],
                    "altitude": flight_obj["altitude"],
                    "on_ground": flight_obj["onGround"],
                    "velocity_kmh": flight_obj["speed"],
                    "raw_speed_ms": flight_obj["rawSpeedMs"],
                    "heading": flight_obj["heading"],
                    "vertical_rate": flight_obj["vertRate"]
                })

            if processed_list:
                # 1. Store Hot Data in Redis (TTL: 45 seconds to keep it fresh)
                await redis_client.setex(
                    self.cache_key, 
                    settings.CACHE_TTL_SECONDS + 15, 
                    json.dumps(processed_list)
                )

                # 2. Perform Bulk Insert into PostgreSQL asynchronously for performance
                await db_session.execute(insert(FlightHistoricalState), db_insert_mappings)
                await db_session.commit()

            return processed_list

flight_repo = FlightRepository()