from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as aioredis

# Connect via localhost ports exposed by Docker
DATABASE_URL = "postgresql+psycopg://postgres:mysecretpassword@127.0.0.1:5433/flight_tracker"
REDIS_URL = "redis://127.0.0.1:6379/0"

engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    pool_size=20, 
    max_overflow=10,
    connect_args={"options": "-c password_encryption=md5"}
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

async def get_db():
    async with async_session() as session:
        yield session