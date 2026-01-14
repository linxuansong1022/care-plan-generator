# Care Plan Generator

A production-ready web application for specialty pharmacies to automatically generate care plans using LLM technology.


<img width="1172" height="751" alt="Screenshot 2026-01-06 at 9 16 40 PM" src="https://github.com/user-attachments/assets/eec3a5cd-d318-4b50-9f9b-3bf44aa5364f" />

## Features

- ✅ Web form for patient/provider/order data entry
- ✅ Real-time validation (NPI Luhn checksum, ICD-10 format, MRN)
- ✅ Duplicate detection with user confirmation workflow
- ✅ LLM-powered care plan generation (Claude/OpenAI)
- ✅ Async processing with Celery
- ✅ HIPAA-compliant error handling
- ✅ Django REST Framework API
- ✅ PostgreSQL database

## Tech Stack

- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **LLM**: Anthropic Claude / OpenAI
- **Infrastructure**: Docker, Terraform, AWS

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Docker (Recommended)

```bash
# 1. Clone repository
git clone <repo-url>
cd larmar-care

# 2. Copy environment file and configure API keys
cp backend/.env.example backend/.env
# Edit backend/.env with your ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Start all services (db, redis, backend, worker, frontend)
docker-compose up -d

# 4. (Optional) Create admin user
docker-compose exec backend python manage.py createsuperuser

# 5. (Optional) Import mock data for testing
docker-compose exec backend python manage.py seed_data
```

That's it! Both backend and frontend will be running via Docker.

### Access the App

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| Admin | http://localhost:8000/admin/ |

## API Endpoints

### Orders

```bash
# Create order
POST /api/v1/orders/
{
    "patient_mrn": "123456",
    "patient_first_name": "John",
    "patient_last_name": "Doe",
    "primary_diagnosis_code": "G70.00",
    "provider_npi": "1234567893",
    "provider_name": "Dr. Smith",
    "medication_name": "IVIG",
    "patient_records": "Clinical notes..."
}

# List orders
GET /api/v1/orders/

# Get order
GET /api/v1/orders/{id}/

# Regenerate care plan
POST /api/v1/orders/{id}/regenerate/
```

### Care Plans

```bash
# Get care plan
GET /api/v1/care-plans/by-order/{order_id}/

# Get status
GET /api/v1/care-plans/status/{order_id}/

# Download care plan
GET /api/v1/care-plans/download/{order_id}/
```

### Providers

```bash
GET /api/v1/providers/
GET /api/v1/providers/{id}/
GET /api/v1/providers/by-npi/{npi}/
```

### Patients

```bash
GET /api/v1/patients/
GET /api/v1/patients/{id}/
GET /api/v1/patients/by-mrn/{mrn}/
GET /api/v1/patients/{id}/history/
```

## Running Tests

```bash
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=apps --cov-report=html

# Run specific test file
docker-compose exec backend pytest tests/unit/test_validators.py

# Run only unit tests
docker-compose exec backend pytest tests/unit/

# Run only integration tests
docker-compose exec backend pytest tests/integration/
```

## Validation Rules

| Field | Rule |
|-------|------|
| NPI | 10 digits, Luhn checksum with 80840 prefix |
| MRN | Exactly 6 digits |
| ICD-10 | Format: Letter + 2 digits + optional decimal (e.g., G70.00) |

## Duplicate Detection

| Entity | Detection Method |
|--------|------------------|
| Provider | Same NPI → reuse; Same NPI different name → block |
| Patient | Same MRN → reuse; Same name+DOB different MRN → warn |
| Order | Same hash within 30 days → warn, require confirmation |

## Environment Variables

See `.env.example` for all available settings.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `CELERY_BROKER_URL`: Redis URL for Celery
- `ANTHROPIC_API_KEY`: API key for Claude LLM
- `LLM_PROVIDER`: `claude` or `openai`

## Common Commands

### Stop Services

```bash
# Stop all containers (keeps data)
docker-compose down

# Stop all containers and remove volumes (full cleanup, deletes database data)
docker-compose down -v
```

### View Running Containers

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Force stop a specific container
docker stop <container_id>
```

### Port Conflicts

If you get a "port already in use" error:

```bash
# Check what's using port 5432 (PostgreSQL)
lsof -i :5432

# Check what's using port 6379 (Redis)
lsof -i :6379

# Check what's using port 8000 (Backend)
lsof -i :8000

# Kill the process using the port
kill -9 <pid>
```

### Database Management

```bash
# Access PostgreSQL shell
docker-compose exec db psql -U careplan -d careplan

# View logs
docker-compose logs -f db      # Database logs
docker-compose logs -f backend # Backend logs
docker-compose logs -f worker  # Celery worker logs

# Restart a specific service
docker-compose restart backend
```

### Local PostgreSQL vs Docker PostgreSQL

If you have both local PostgreSQL and Docker PostgreSQL running, they may conflict on port 5432. Choose one approach:

**Recommended: Use Docker only (cleaner, easier to manage)**

```bash
# 1. Stop local PostgreSQL
brew services stop postgresql
# Or kill the process directly
kill <pid>

# 2. Verify Docker PostgreSQL is running
docker ps

# 3. Restart Docker services if needed
docker-compose down
docker-compose up -d
```

**Quick fix: Kill all processes on port 5432**

```bash
lsof -ti :5432 | xargs kill -9
```

## Project Structure

```
backend/
├── config/                 # Django settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/
│   ├── core/              # Common utilities
│   │   ├── validators.py  # NPI, MRN, ICD-10
│   │   └── exceptions.py  # Custom exceptions
│   ├── providers/         # Provider management
│   ├── patients/          # Patient management
│   ├── orders/            # Order management
│   │   └── services.py    # Duplicate detection
│   └── care_plans/        # Care plan generation
│       ├── tasks.py       # Celery tasks
│       ├── llm_service.py # LLM integration
│       └── prompts.py     # LLM prompts
├── tests/
│   ├── unit/
│   └── integration/
└── manage.py
```
