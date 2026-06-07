import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers import flight_controller
from app.services.flight_service import FlightService
from app.repositories.database import engine, Base

flight_service = FlightService()

async def scheduler_worker():
    """Background worker loop executing the ingestion sequence safely."""
    while True:
        try:
            await flight_service.trigger_background_sync()
        except Exception as e:
            print(f"Background Sync Error Shielded: {e}")
        await asyncio.sleep(240)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Engine Tasks: Create database tables automatically if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Spin up background ingestion worker task loop
    worker_task = asyncio.create_task(scheduler_worker())
    yield
    # Shutdown Tasks
    worker_task.cancel()
    await engine.dispose()

app = FastAPI(title="Clean Flight Tracker Engine", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flight_controller.router)