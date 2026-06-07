from typing import List, Optional
from app.repositories.flight_repository import flight_repo
from app.repositories.database import async_session
from sqlalchemy.ext.asyncio import AsyncSession

class FlightService:
    # CHANGE THIS NAME from get_live_flights to get_filtered_flights
    async def get_filtered_flights(
        self, 
        status: Optional[str] = None, 
        min_speed: Optional[float] = None, 
        country: Optional[str] = None
    ) -> List[dict]:
        """Fetches from Redis hot storage and applies quick in-memory filters."""
        flights = await flight_repo.get_cached_flights()
        
        # Fallback if cache is expired or worker hasn't run yet
        if not flights:
            async with async_session() as session:
                flights = await flight_repo.refresh_and_store_pipeline(session)

        # Apply filtering matrix
        filtered = []
        for f in flights:
            if status == "air" and f["onGround"]: continue
            if status == "ground" and not f["onGround"]: continue
            if min_speed and f["speed"] < min_speed: continue
            if country and country.lower() != "all" and country.lower() != f["country"].lower(): continue
            filtered.append(f)
            
        return filtered

    async def trigger_background_sync(self):
        """Method executed by background cron scheduler managers."""
        async with async_session() as session:
            await flight_repo.refresh_and_store_pipeline(session)
            
    @staticmethod
    def _parse_state(s: list) -> dict:
        return {
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
            "vertRate": round(s[11]) if s[11] is not None else 0,
            "category": s[17] if len(s) > 17 else 0  # <-- ADD THIS LINE HERE
        }
        
    async def get_history_from_db(
        self,
        db_session: AsyncSession,
        icao: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Fetches raw rows from repository and normalizes them for API consumption."""
        db_records = await flight_repo.get_historical_records(
            db_session=db_session, 
            icao=icao, 
            country=country, 
            limit=limit
        )
        
        return [
            {
                # "id": record.id,
                "icao": record.icao24,
                "callsign": record.callsign,
                "country": record.origin_country,
                "lon": record.longitude,
                "lat": record.latitude,
                "altitude": record.altitude,
                "onGround": record.on_ground,
                "speed": record.velocity_kmh,
                "rawSpeedMs":0.0,
                "heading": record.heading,
                "vertRate": record.vertical_rate,
                # "recordedAt": record.recorded_at.isoformat()
            }
            for record in db_records
        ]