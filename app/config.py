import pydantic_settings

class Settings(pydantic_settings.BaseSettings):
    OPENSKY_URL: str = "https://opensky-network.org/api/states/all"
    LAMIN: float = 6.5546079
    LOMIN: float = 68.1113787
    LAMAX: float = 35.6745457
    LOMAX: float = 97.3955610
    CACHE_TTL_SECONDS: int = 30
    
settings = Settings()