# Care Plan Generator

A production-ready web application for specialty pharmacies to automatically generate care plans using LLM technology.

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
- Node.js 18+ (for frontend)

### Docker (Recommended)

```bash
# 1. Clone repository
git clone <repo-url>
cd larmar-care

# 2. Copy environment file and configure API keys
cp backend/.env.example backend/.env
# Edit backend/.env with your ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Start all backend services (database migration runs automatically)
docker-compose up -d

# 4. (Optional) Create admin user
docker-compose exec backend python manage.py createsuperuser

# 5. (Optional) Import mock data for testing
docker-compose exec backend python manage.py seed_data

# 6. Start frontend
cd frontend
npm install
npm run dev
```

### Access the App

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| Admin | http://localhost:8000/admin/ |

### Manual Setup (Alternative)

```bash
# Clone repository
cd care-plan-generator/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install poetry
poetry install

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver

# In another terminal, start Celery worker
celery -A config worker -l info
```

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
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test file
pytest tests/unit/test_validators.py

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
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