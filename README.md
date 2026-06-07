# ✈️ SkyRadar — Real-Time Flight Ingestion & Visualization

> A full-stack, production-grade flight tracking application that ingests live ADS-B transponder data from the [OpenSky Network](https://opensky-network.org/), persists it across a polyglot data layer, and renders it on an interactive map at 60 FPS — complete with dynamic aircraft icons, heading-aware rotation, and historical flight path trails.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA INGESTION PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

  [ OpenSky Network REST API ]
           │
           │  HTTP Poll every 30s
           │  (Rate-limited: 400 req/day budget)
           ▼
  ┌─────────────────────┐
  │  Background Worker  │  ← FastAPI Lifespan asyncio task loop
  │  (lifespan event)   │     Runs inside the backend process
  └──────────┬──────────┘
             │
     ┌───────┴────────┐
     │                │
     ▼                ▼
┌─────────┐    ┌──────────────┐
│  Redis  │    │  PostgreSQL  │
│  Cache  │    │  Historical  │
│  TTL:   │    │  Log Store   │
│   45s   │    │  (permanent) │
└────┬────┘    └──────┬───────┘
     │                │
     └───────┬────────┘
             │
             ▼
  ┌─────────────────────┐
  │   FastAPI Backend   │  ← Python 3.10+, fully async
  │   REST API Layer    │     Uvicorn ASGI server
  └──────────┬──────────┘
             │
             │  JSON over HTTP
             ▼
  ┌─────────────────────┐
  │   React Frontend    │  ← Vite build environment
  │   Leaflet.js Map    │     Canvas renderer @ 60 FPS
  │   SVG Aircraft Icons│     Dynamic heading rotation
  └─────────────────────┘
             │
             ▼
      [ Browser / User ]
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PORT ALLOCATION SUMMARY                             │
├───────────────────┬──────────────────┬──────────────────────────────────────┤
│ Service           │ Internal Port    │ Host-Exposed Port                    │
├───────────────────┼──────────────────┼──────────────────────────────────────┤
│ FastAPI Backend   │ 8000             │ 8000                                 │
│ React Frontend    │ 5173             │ 5173                                 │
│ PostgreSQL        │ 5432             │ 5433 (conflict-free)                 │
│ Redis             │ 6379             │ 6379                                 │
│ pgAdmin           │ 80               │ 8080                                 │
└───────────────────┴──────────────────┴──────────────────────────────────────┘
```

---

## 📁 Project Structure

```
skyradar/
│
├── Backend/                        # FastAPI application root
│   ├── main.py                     # App entrypoint — lifespan scheduler & background worker
│   ├── docker-compose.yml          # Container orchestration (Postgres, Redis, pgAdmin)
│   │
│   └── app/
│       ├── controllers/            # API Router endpoint handlers (route definitions)
│       ├── services/               # Data normalization & business logic layer
│       └── repositories/           # Database engines & SQLAlchemy configurations
│
└── frontend/                       # React + Vite application root
    ├── package.json                 # React dependency manifest
    │
    └── src/
        ├── App.jsx                  # Root state coordinator — manages global flight state
        │
        └── components/             # Leaflet map layers & panel layout components
```

---

## 🚀 Local Setup & Installation

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24.x
- Python 3.10+
- Node.js ≥ 18.x & npm ≥ 9.x

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-org/skyradar.git
cd skyradar
```

---

### Step 2 — Spin Up the Database Cluster (Docker)

Navigate to the `Backend/` directory where `docker-compose.yml` lives and execute a clean detached initialization to spin up all three infrastructure services concurrently:

```bash
cd Backend
docker compose up -d
```

Verify all containers are running:

```bash
docker ps
```

Expected output:

```
CONTAINER NAME                STATUS          PORTS
my-postgres                   Up              0.0.0.0:5433->5432/tcp
flight_redis_container        Up              0.0.0.0:6379->6379/tcp
flight_pgadmin_container      Up              0.0.0.0:8080->80/tcp
```

| Service | URL / Connection |
|---------|-----------------|
| pgAdmin UI | http://localhost:8080 |
| pgAdmin login | `admin@tracker.com` / `adminpassword` |
| PostgreSQL (direct) | `localhost:5433` — db: `flight_tracker`, user: `postgres` |
| Redis | `localhost:6379` |

---

### Step 3 — Run the FastAPI Backend Server

In your `Backend/` directory, create and activate a Python virtual environment:

```bash
# Create the virtual environment
python -m venv env

# Activate — Windows
.\env\Scripts\activate

# Activate — macOS / Linux
source env/bin/activate
```

Install all asynchronous dependencies:

```bash
pip install fastapi uvicorn sqlalchemy redis "psycopg[binary]"
```

Start the backend engine:

```bash
python main.py
```

On launch, SQLAlchemy analyzes your schema mappings, mounts connection channels to PostgreSQL on port `5433`, automatically initializes the `flight_historical_states` table, and starts the background 30-second data ingestion loop.

The API will be live at **http://localhost:8000**
Interactive Swagger docs at **http://localhost:8000/docs**

---

### Step 4 — Run the React Frontend Application

Open a new terminal tab and navigate to the frontend:

```bash
cd frontend
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The React application will be live at **http://localhost:5173**

---

## 🔌 API Endpoint Matrix

| Method | Endpoint | Data Source | Cache | Description |
|--------|----------|-------------|-------|-------------|
| `GET` | `/api/v1/flights` | **Redis** | TTL 45s | Returns the full current airspace snapshot. Serves the latest ingested state vector set from the in-memory cache. Falls back to PostgreSQL on cache miss. |
| `GET` | `/api/v1/flights/history` | **PostgreSQL** | None | Returns a paginated log of all historical flight states ever recorded. Supports `?icao=`, `?limit=`, and `?offset=` query parameters for filtering. |
| `GET` | `/api/v1/flights/{icao}/path` | **PostgreSQL** | None | Returns an ordered array of `[latitude, longitude, timestamp]` coordinates for a single aircraft identified by its ICAO24 transponder code. Used to render click-triggered trail overlays. |

### Request & Response Examples

**`GET /api/v1/flights`**
```json
{
  "source": "redis_cache",
  "cached_at": "2024-11-15T14:32:10Z",
  "count": 342,
  "flights": [
    {
      "icao24": "a3f2b1",
      "callsign": "UAL123",
      "latitude": 37.6213,
      "longitude": -122.379,
      "altitude_m": 10972.8,
      "velocity_ms": 248.5,
      "heading": 274.3,
      "vertical_rate": -1.2,
      "category": "jet",
      "on_ground": false,
      "last_seen": "2024-11-15T14:32:05Z"
    }
  ]
}
```

**`GET /api/v1/flights/a3f2b1/path`**
```json
{
  "icao24": "a3f2b1",
  "callsign": "UAL123",
  "point_count": 47,
  "path": [
    { "lat": 37.3382, "lon": -121.8863, "ts": "2024-11-15T13:01:00Z" },
    { "lat": 37.4100, "lon": -121.9700, "ts": "2024-11-15T13:01:30Z" },
    { "lat": 37.4950, "lon": -122.0600, "ts": "2024-11-15T13:02:00Z" }
  ]
}
```

---

## ⚡ Key Technical Implementations

### 🖼️ HTML5 Canvas Rendering @ 60 FPS

Standard Leaflet marker DOM elements collapse under load with hundreds of simultaneous aircraft. SkyRadar bypasses this by using a **Leaflet Canvas renderer layer**, painting all aircraft markers directly onto a single `<canvas>` element. This eliminates DOM reflow entirely, reduces memory pressure, and maintains smooth 60 FPS animation even with 400+ simultaneous state vectors updating every 30 seconds.

```javascript
// RadarMap.jsx — Canvas renderer initialization
const renderer = L.canvas({ padding: 0.5, tolerance: 10 });
const flightLayer = L.geoJSON(null, { renderer, pointToLayer: renderAircraftMarker });
```

---

### 🧭 Dynamic SVG Heading Rotation via CSS Injection

Each aircraft icon must rotate to face its real-world heading in degrees. Rather than pre-generating 360 rotated icon variants or using canvas `transform`, SkyRadar uses **raw CSS injection** — dynamically writing a `<style>` block per aircraft keyed to its ICAO24 identifier. This keeps the SVG markup static and offloads the transform entirely to the GPU compositor.

```javascript
// utils/cssRotation.js
export function injectHeadingStyle(icao24, heading) {
  const styleId = `heading-${icao24}`;
  let tag = document.getElementById(styleId);
  if (!tag) {
    tag = document.createElement('style');
    tag.id = styleId;
    document.head.appendChild(tag);
  }
  tag.textContent = `
    .aircraft-icon-${icao24} {
      transform: rotate(${heading}deg);
      transform-origin: center center;
      transition: transform 0.8s ease-out;
    }
  `;
}
```

---

### 🗃️ Polyglot Data Architecture (Redis + PostgreSQL)

The application deliberately separates concerns across two storage layers with different performance and durability characteristics:

| Concern | Engine | Rationale |
|---------|--------|-----------|
| Live airspace state (read-heavy, ephemeral) | **Redis** (TTL 45s) | Sub-millisecond key lookup; auto-expiry keeps memory bounded; tolerates data loss on restart |
| Historical flight log (write-once, permanent) | **PostgreSQL** | ACID guarantees; indexed by `icao24` + `timestamp` for efficient path queries; survives restarts |
| Background ingestor write path | **Both simultaneously** | A single worker write atomically updates Redis (via `SET ... EX 45`) and appends a row to Postgres in the same async task cycle |

This architecture completely shields the OpenSky 400 req/day API budget: the frontend never calls OpenSky directly, polling frequency is controlled entirely server-side, and the Redis cache absorbs any number of concurrent frontend clients with zero additional API cost.

---

### 🛩️ Aircraft Category Icon Selection

SkyRadar maps OpenSky's ADS-B `category` integer codes to distinct visual icon variants at render time, providing immediate visual disambiguation between aircraft types on the map.

| Category Code | Aircraft Type | Icon |
|---------------|---------------|------|
| 1–3 | No info / Glider | Default circle |
| 4–7 | **Fixed-wing (Jet/GA)** | ✈ Swept-wing SVG |
| 10–12 | **Rotorcraft / Helicopter** | 🚁 Rotor SVG |
| 14 | **UAV / Drone** | ⬡ Hexagon SVG |
| 19–20 | Space / Ultralight | Minimal ring |

---

## 🐳 Docker Services Reference

```yaml
# Backend/docker-compose.yml — annotated topology
services:
  flight-redis:                         # High-speed volatile cache
    image: redis:7-alpine
    container_name: flight_redis_container
    ports: ["6379:6379"]

  flight-postgres:                      # Relational historical store
    image: postgres:15-alpine
    container_name: my-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: mysecretpassword
      POSTGRES_DB: flight_tracker
    ports: ["5433:5432"]               # Host 5433 → avoids conflicts with local PG
    volumes:
      - postgres_data:/var/lib/postgresql/data

  flight-pgadmin:                       # Database management GUI
    image: dpage/pgadmin4
    container_name: flight_pgadmin_container
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@tracker.com
      PGADMIN_DEFAULT_PASSWORD: adminpassword
    ports: ["8080:80"]
    depends_on: [flight-postgres]
```

---

## 🔧 Development Scripts

```bash
# Start all infrastructure (detached) — run from Backend/
cd Backend && docker compose up -d

# Tail logs from all containers
docker compose logs -f

# Stop and remove containers (preserve volumes)
docker compose down

# Nuclear reset — wipe volumes and re-initialize
docker compose down -v && docker compose up -d

# Start backend (from Backend/ with venv active)
python main.py

# Start frontend dev server (from frontend/)
cd frontend && npm run dev

# Production build
cd frontend && npm run build
```

---

## 📊 Performance Characteristics

| Metric | Value |
|--------|-------|
| Frontend render target | 60 FPS (Canvas) |
| Backend poll interval | 30 seconds |
| Redis cache TTL | 45 seconds |
| OpenSky API budget | 400 requests/day |
| Estimated daily API usage | ~2,880 requests/day at 30s interval |

> **Note:** Authenticated OpenSky accounts receive a significantly higher rate limit. Pass credentials to the ingestor worker via environment variables or a config module for production deployments.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Built with FastAPI · React · Leaflet.js · Redis · PostgreSQL · Docker
</p>