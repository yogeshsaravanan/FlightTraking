Markdown
# 🗺️ Real-Time Flight Ingestion & Visualization Radar

A high-performance, asynchronous full-stack flight tracking application. The system processes live spatial telemetry matrices, implements a polyglot storage layer to handle rapid data streams safely, and visualizes moving aircraft on a hardware-accelerated React map canvas at 60 FPS using Dead Reckoning physics algorithms.

---

## 🏛️ System Architecture View

The engine divides execution traffic across decoupled operational runtimes to prevent API rate-limiting while maintaining a permanent logging footprint.

                ┌────────────────────────┐
                │  OpenSky Network API   │
                └───────────┬────────────┘
                            │ 
                            │ (30-Sec Ingestion Stream)
                            ▼
                ┌────────────────────────┐
                │ Background Sync Worker │ <── [Lifespan Event Loop]
                └───────────┬────────────┘
                            │
     ┌──────────────────────┴──────────────────────┐
     ▼ (Stringified JSON Payload)                  ▼ (SQL Relational Snapshots)

┌────────────────────────┐                    ┌────────────────────────┐│   Redis Hot Storage    │                    │ PostgreSQL DB (Port 5435)││    - Volatile Memory   │                    │  - Permanent Logging   ││    - TTL: 45 Seconds   │                    │  - Flight History Rows │└───────────▲────────────┘                    └────────────────────────┘││ (Fast Read in Microseconds)▼┌────────────────────────┐│  FastAPI Router Engine │ <── [Controller / Service / Repo Architecture]└───────────▲────────────┘││ (Filtered JSON Response Arrays)▼┌────────────────────────┐│  React (Vite) Frontend │ <── [HTML5 Leaflet Canvas Layer]└────────────────────────┘
### 🔁 Core Data Flow Architecture

1. **Ingest Engine Engine:** A native background task runner spins up on server launch, pulling aggregate aircraft metadata packets globally every 30 seconds to strictly honor the 400 requests/day target cap.
2. **Caching Shield Layer:** Ingested streams are structured and cached instantly inside **Redis Memory**. When client browsers hit the standard map endpoint, the API reads purely out of Redis memory, neutralizing expensive disk query overloads.
3. **Cold Storage Logging:** Simultaneously, incoming track updates are dumped directly into **PostgreSQL** (`flight_tracker` schema), creating historical tracking telemetry used to generate flight path polylines when users click markers.

---

## 🛠️ Project Structure

```text
├── Backend/
│   ├── app/
│   │   ├── controllers/   # API Router endpoints
│   │   ├── services/      # Data normalization and business logic
│   │   └── repositories/  # Database engines & SQLAlchemy configurations
│   ├── main.py            # Application entrypoint & background scheduler
│   └── docker-compose.yml # Container orchestrations (Postgres, Redis, pgAdmin)
└── frontend/
    ├── src/
    │   ├── components/    # Leaflet Map & Panel Layouts
    │   └── App.jsx        # State coordinator
    └── package.json       # React dependencies Matrix
📦 Infrastructure PrerequisitesEnsure you have the following frameworks installed natively on your machine:Python 3.10+ (Asynchronous loop optimized)Node.js LTS (For compiling the user interface)Docker Desktop (Container environment management)🚀 Installation & Setup1. Launch the Database Cluster (Docker)Navigate to your Backend/ directory and execute a clean detached initialization sequence to spin up the required databases:Bashcd Backend
# Spin up Postgres, Redis, and pgAdmin containers concurrently
docker compose up -d
Verification Check: Run docker ps to verify that your system is actively hosting my-postgres running on port 5435, flight_redis_container on port 6379, and pgAdmin running on web port 8080.2. Run the FastAPI Backend ServerOpen your terminal in the Backend/ directory and set up your virtual Python environment:Bash# Create and activate the virtual environment
python -m venv env
.\env\Scripts\activate   # On Windows (Use 'source env/bin/activate' on Linux/Mac)

# Install asynchronous requirements
pip install fastapi uvicorn sqlalchemy redis "psycopg[binary]"

# Fire up the backend engine
python main.py
Upon launching, SQLAlchemy analyzes your schema mappings, mounts connection channels to PostgreSQL over port 5435, automatically initializes the flight_historical_states table structure, and starts the background data loop.3. Run the React Frontend ApplicationOpen a separate terminal window, navigate into the frontend/ directory, install the node modules, and start Vite's modern build pipeline:Bashcd frontend
# Install strict peer-dependency modules
npm install

# Start the local development web server
npm run dev
Open your browser and navigate to http://localhost:5173 to see your running real-time radar system!🧪 Core API Endpoint MatrixHTTP MethodAPI URL Endpoint Routing PathDestination Target IntentData Source EngineGET/api/v1/flightsFetch live flights with active parameters filtering (status, minSpeed, country).Redis MemoryGET/api/v1/flights/historyQuery database cold arrays directly to trace historical logging records.PostgreSQL DiskGET/api/v1/flights/{icao}/pathExtract chronological track vectors matching a single tail address to paint past flight trails.PostgreSQL Disk✨ Key Technical ImplementationsVector Nose Rotations: Standard dots are replaced with dynamically rendered inline SVG markers. Using raw CSS injections inside Leaflet DivIcon nodes, the airplane noses are rotated instantly to match their current tracking heading degree orientation.Category Classifiers: Aircraft models change visualization layouts based on transponder data arrays—rendering commercial jets as aircraft silhouettes (Neon Blue), helicopters as rotorcraft (Neon Yellow), and UAVs as quadcopter outlines (Neon Green).HTML5 Map Canvas Layer: Bypasses DOM element limitations by painting thousands of real-time coordinate transformations on an accelerated single Canvas layer, maintaining 60 FPS performance.