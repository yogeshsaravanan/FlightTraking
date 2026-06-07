from fastapi import APIRouter,Query,Depends
from typing import Optional,List
from app.services.flight_service import FlightService
from sqlalchemy import select
from app.repositories.database import get_db
from app.repositories.models import FlightHistoricalState
from sqlalchemy.ext.asyncio import AsyncSession


router=APIRouter(prefix="/api/v1/flights",tags=["Flights"])
flight_services =FlightService()

@router.get("",response_model=List[dict])
async def get_flights(
    status: Optional[str] = Query(None, description="Filter: 'air' or 'ground'"),
    minSpeed: Optional[float] = Query(None, description="Minimum speed filtering threshold in km/h"),
    country: Optional[str] = Query(None, description="Filter by flight's country of origin")
):
    return await flight_services.get_filtered_flights(
        status=status, 
        min_speed=minSpeed, 
        country=country
    )
    
@router.get("/{icao}/path", response_model=List[dict])
async def get_flight_path(icao: str, db: AsyncSession = Depends(get_db)):
    """Fetches the last 50 recorded positions of a specific aircraft to draw its path."""
    stmt = (
        select(FlightHistoricalState.latitude, FlightHistoricalState.longitude)
        .where(FlightHistoricalState.icao24 == icao)
        .order_by(FlightHistoricalState.recorded_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    # Reverse so the oldest point is first, ending at the current location
    return [{"lat": r[0], "lng": r[1]} for r in reversed(rows)]

@router.get("/history", response_model=List[dict])
async def get_database_history(
    icao: Optional[str] = Query(None, description="Search by unique 24-bit ICAO transponder address"),
    country: Optional[str] = Query(None, description="Search records by country name context matching"),
    limit: int = Query(100, ge=1, le=1000, description="Control maximum return payload limits"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exposes historical logging tracks directly from the persistent 
    PostgreSQL database layer. Bypasses the volatile Redis hot cache cache.
    """
    return await flight_services.get_history_from_db(
        db_session=db,
        icao=icao,
        country=country,
        limit=limit
    )

