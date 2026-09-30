# CropSure — AI crop health demo

CropSure is a full-stack academic demonstration for crop image triage, field risk signals, sensor readings, and extension-worker review. It runs locally without an API key, trained model, or physical sensor.

> **Demo limitations:** the current disease result is a deterministic simulated estimate based on the farm's selected crop, and weather/risk/sensor data are sample values. They are not trained-model predictions, live weather, validated agronomic forecasts, or confirmed diagnoses. The UI and API mark these outputs as demo data. Use local extension services and laboratory confirmation for real crop decisions. Chemical advice intentionally gives label and authority guidance without product/dose instructions.

## Features

- Responsive React/Vite farmer dashboard with English, Kannada, and Hindi navigation.
- FastAPI REST API with bearer JWT authentication, bcrypt password hashes, roles, farm ownership checks, validated image uploads, case history, and sensor data.
- Demo accounts for farmer, expert, and admin; a farmer registration endpoint is included.
- Expert review workflow and role-gated approximate map data endpoint.
- Sample weather forecast, risk signal, sensor history, and seeded cases.
- MobileNetV2 training/evaluation script for folder-per-class image datasets.
- SQLite default, PostgreSQL conceptual schema, and Docker Compose.

## Architecture and structure

React/Vite browser → FastAPI REST API → SQLAlchemy → SQLite (local demo)
FastAPI also serves demo image triage, risk, and sensor services.
ML training script → MobileNetV2 artifact (separate; not wired into demo inference)

- backend/app/main.py: API, entities, seed data and routes
- backend/tests/: API smoke tests
- frontend/src/: React screens and responsive styling
- ml/train.py: MobileNetV2 training pipeline
- ml/predict.py: saved model command-line inference
- database/schema.sql: PostgreSQL reference schema
- docker-compose.yml: local containers

## Run locally

Requirements: Python 3.11+, Node.js 20+, npm.

1. In a terminal, install and start the backend:

   cd backend
   py -3.11 -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   uvicorn app.main:app --reload

   API docs: http://localhost:8000/docs. SQLite is created as backend/crop_health.db and sample records are seeded on first startup.

2. In a second terminal, start the frontend:

   cd frontend
   npm install
   npm run dev

   Open http://localhost:5173. Demo farmer credentials are prefilled.

3. Optional container launch from the project root: docker compose up --build. Compose runs the Vite development server.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Farmer | farmer@cropsure.demo | demo1234 |
| Expert | expert@cropsure.demo | demo1234 |
| Admin | admin@cropsure.demo | demo1234 |

New public registrations can only create farmer accounts; assign staff roles through an administrator process before any real deployment.

## API overview

All paths are prefixed with /api. Sign in with JSON containing email and password; pass the returned token as Authorization: Bearer token.

| Method | Path | Access / purpose |
| --- | --- | --- |
| POST | /auth/register, /auth/login | Register farmer / obtain JWT |
| GET | /auth/me | Signed-in profile |
| POST, GET | /farms | Create / list accessible farms |
| GET | /farms/{id} | Read accessible farm |
| POST | /disease/predict | Multipart image and farm_id, simulated estimate |
| GET | /disease/cases, /disease/cases/{id} | Case history/detail |
| GET, POST | /expert/cases, /expert/review | Expert/admin review queue and decision |
| GET | /weather, /risk-forecast | Simulated weather and risk |
| GET, POST | /sensors/data | Readings history / add reading |
| GET, POST | /pest-traps | Trap records (shares sensor table) |
| GET | /recommendations/{disease} | Cautious IPM guidance |
| GET | /dashboard/overview | Role-aware dashboard |
| GET | /dashboard/statistics | Expert/admin aggregate stats |
| GET | /map/cases | Expert/admin coarse location data |

Interactive Swagger documentation is served at /docs.

## Model training

Install TensorFlow in its supported Python environment (the current development runtime here is Python 3.14; TensorFlow's supported versions are listed in its install guide). The project includes a downloader for PlantVillage, an openly licensed labeled leaf dataset:

    py -3.11 -m venv .venv-ml
    .\.venv-ml\Scripts\Activate.ps1
    python -m pip install -r backend/requirements.txt
    python -m pip install -r ml/requirements.txt
    cd ml
    python download_dataset.py

This prepares class folders such as Tomato___Early_blight and Tomato___healthy. The dataset is a research benchmark; its labels and image conditions are not a substitute for locally expert-confirmed field data.

Install ml/requirements.txt, then run from the ml directory:

    pip install -r requirements.txt
    python train.py --data dataset --output saved_models/crop_health.keras --epochs 8
    python predict.py image.jpg --model saved_models/crop_health.keras

Training uses a seeded 80/20 training/validation split, augmentation, and MobileNetV2 transfer learning. It saves the model, class names, validation report, confusion matrix, and accuracy/loss charts. A separate field test set can be passed with --test-data. See ml/README.md for setup and setting MODEL_PATH so the API uses your trained model. PlantVillage-style Crop___Disease folder labels are filtered to the selected farm crop.

## Configuration and production integration

Copy backend/.env.example and configure SECRET_KEY, DATABASE_URL, CORS_ORIGINS, UPLOAD_DIR, and DEMO_MODE. SQLite is the zero-setup default. For PostgreSQL, install a psycopg driver and set a PostgreSQL SQLAlchemy URL; add and maintain migrations before deployment.

Replace the weather and risk endpoints with a trusted provider adapter, keep provider keys server-side, include timestamps, and validate crop-specific risk logic with local agronomists. IoT devices can POST readings to /api/sensors/data; production hardware should use device credentials rather than a browser user's token. Use HTTPS, managed secrets, rate limits, malware scanning, retention controls, and model monitoring before public use.

Map access is role-gated and case coordinates are rounded to two decimal places; farmer endpoints do not return coordinates. Production maps should aggregate further to a suitable minimum case count and obtain consent for location processing.

## Tests and next steps

From backend, install dependencies and run pytest. Smoke tests cover seeded sign-in, role boundaries, sensor validation, and recommendation shape.

Next: wire evaluated model inference, use migrations and PostgreSQL in deployment, integrate trusted weather feeds, verify translations and advisories, add notification delivery, enrich review/audit workflows, and aggregate map clusters with consent safeguards.
