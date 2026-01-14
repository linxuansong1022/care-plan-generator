# Care Plan Generator

A production-ready web application for specialty pharmacies to automatically generate care plans using LLM technology.

<img width="1172" height="751" alt="Screenshot 2026-01-06 at 9 16 40 PM" src="https://github.com/user-attachments/assets/eec3a5cd-d318-4b50-9f9b-3bf44aa5364f" />

## Background

**Customer:** A specialty pharmacy

**Problem:** Pharmacists spend 20-40 minutes per patient manually creating care plans. These are required for compliance and Medicare/pharma reimbursement. The pharmacy is short-staffed and backlogged.

**Solution:** A web application that allows medical assistants to input patient/order information and automatically generate care plans using LLM.

## Features

- ✅ Web form for patient/provider/order data entry
- ✅ Real-time input validation (NPI, MRN, ICD-10, etc.)
- ✅ Duplicate detection for patients and orders
- ✅ LLM-powered care plan generation
- ✅ Async processing with Celery
- ✅ Care plan download
- ✅ Export all data for pharma reporting

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.0, Django REST Framework |
| Database | PostgreSQL |
| Task Queue | Celery + Redis |
| LLM | Anthropic Claude / OpenAI (configurable) |
| Frontend | React + Vite |
| Infrastructure | Docker, Terraform, AWS |

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd larmar-careplan

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

That's it! All services will be running via Docker.

### Access the App

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| Admin | http://localhost:8000/admin/ |

## Input Fields

### Patient Information

| Field | Type | Validation |
|-------|------|------------|
| patient_first_name | string | Required |
| patient_last_name | string | Required |
| patient_mrn | string | Exactly 6 digits |
| patient_date_of_birth | date | Valid date |
| patient_sex | string | Required |
| patient_weight | number | Required |
| patient_allergies | string | Required |

### Provider Information

| Field | Type | Validation |
|-------|------|------------|
| provider_name | string | Required |
| provider_npi | string | Exactly 10 digits |

### Order Information

| Field | Type | Validation |
|-------|------|------------|
| medication_name | string | Required |
| primary_diagnosis_code | string | ICD-10 format (e.g., G70.00) |
| additional_diagnosis_codes | list | ICD-10 format |
| medication_history | list | List of strings |
| patient_records | string | Free text (clinical notes) |

## Duplicate Detection Logic

### Patient Duplicates

| Scenario | Condition | Result |
|----------|-----------|--------|
| Exact match | MRN same + first_name + last_name + date_of_birth all same | ✅ Reuse existing patient |
| MRN conflict | MRN same + first_name/last_name/date_of_birth different | ⚠️ WARNING (can acknowledge & continue) |
| Name/DOB conflict | first_name + last_name + date_of_birth same + MRN different | ⚠️ WARNING (can acknowledge & continue) |
| No match | All different | ✅ Create new patient |

### Order Duplicates

| Scenario | Condition | Result |
|----------|-----------|--------|
| Exact duplicate | Same patient + same medication + same day | ❌ ERROR (blocked, cannot proceed) |
| Possible duplicate | Same patient + same medication + different day | ⚠️ WARNING (can acknowledge & continue) |

### Provider Duplicates

| Scenario | Condition | Result |
|----------|-----------|--------|
| Exact match | NPI same + provider_name same | ✅ Reuse existing provider |
| NPI conflict | NPI same + provider_name different | ❌ ERROR (blocked, must correct name) |
| No match | NPI different | ✅ Create new provider |

## Care Plan Generation

### Input to LLM

Patient records text that may include:
- Patient demographics (Name, MRN, DOB, Sex, Weight, Allergies)
- Medication
- Primary/Secondary diagnoses
- Home meds
- Recent history
- Clinical notes (e.g., Baseline clinic note, Infusion visit note, Follow-up notes)

### Output Required Headers

The generated care plan MUST include these sections:
1. Problem list / Drug therapy problems (DTPs)
2. Goals (SMART)
3. Pharmacist interventions / plan
4. Monitoring plan & lab schedule

## API Endpoints

### Orders

```bash
# Create order (triggers care plan generation)
POST /api/v1/orders/

# List all orders
GET /api/v1/orders/

# Get order details
GET /api/v1/orders/{id}/

# Regenerate care plan
POST /api/v1/orders/{id}/regenerate/
```

### Create Order Request Body

```json
{
    "patient_mrn": "123456",
    "patient_first_name": "John",
    "patient_last_name": "Doe",
    "patient_date_of_birth": "1979-06-08",
    "patient_sex": "Female",
    "patient_weight": 72,
    "patient_allergies": "None known",
    "provider_npi": "1234567893",
    "provider_name": "Dr. Smith",
    "medication_name": "IVIG",
    "primary_diagnosis_code": "G70.00",
    "additional_diagnosis_codes": ["I10", "K21.0"],
    "medication_history": ["Pyridostigmine 60mg", "Prednisone 10mg"],
    "patient_records": "Name: A.B.\nMRN: 123456\nDOB: 1979-06-08..."
}
```

### Care Plans

```bash
# Get care plan content
GET /api/v1/care-plans/by-order/{order_id}/

# Get generation status
GET /api/v1/care-plans/status/{order_id}/

# Download care plan as file
GET /api/v1/care-plans/download/{order_id}/
```

### Export

```bash
# Export all orders and care plans as CSV
GET /api/v1/export/
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

# Quick fix: Kill all processes on port 5432
lsof -ti :5432 | xargs kill -9
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

## Environment Variables

See `.env.example` for all available settings.

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| CELERY_BROKER_URL | Redis URL for Celery |
| ANTHROPIC_API_KEY | API key for Claude LLM |
| OPENAI_API_KEY | API key for OpenAI (alternative) |
| LLM_PROVIDER | `claude` or `openai` |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Django    │────▶│ PostgreSQL  │
│   (React)   │     │   REST API  │     │             │
└─────────────┘     └──────┬──────┘     └──────▲──────┘
                           │                   │
                           │ queue task        │ read order /
                           ▼                   │ write care plan
                    ┌─────────────┐     ┌──────┴──────┐     ┌─────────────┐
                    │    Redis    │────▶│   Celery    │◀───▶│    LLM      │
                    │   (Queue)   │     │   Worker    │     │  (Claude/   │
                    └─────────────┘     └─────────────┘     │   OpenAI)   │
                                                            └─────────────┘
```

**Data Flow:**
1. Django API saves order to PostgreSQL, then queues task ID to Redis
2. Celery Worker picks up task ID from Redis
3. Worker reads order data from PostgreSQL
4. Worker sends prompt to LLM, receives generated care plan
5. Worker writes care plan back to PostgreSQL

## Workflow

1. Medical assistant fills out web form with patient/order data
2. Frontend validates input (MRN 6 digits, NPI 10 digits, etc.)
3. API checks for duplicate patients and orders
   - If warning → user can acknowledge and continue
   - If error → user must fix the issue
4. Order is saved to database
5. Celery task is triggered asynchronously
6. Worker fetches order from database
7. Worker calls LLM to generate care plan
8. Care plan is saved to database
9. User can download care plan as text file

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

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── package.json

terraform/
└── ... (AWS infrastructure)
```

## Intentionally Out of Scope (Phase 2)

The following features were intentionally excluded from the MVP to focus on the core value proposition (LLM-powered care plan generation). These are planned for Phase 2:

| Feature | What's Missing | Why Deferred |
|---------|----------------|--------------|
| **Authentication** | No user login, no role-based access control (RBAC) | MVP focuses on core functionality; auth can be quickly added via Django auth or Auth0 |
| **HIPAA Compliance** | No PHI encryption at rest, no access audit trails, no BAA with cloud providers | Requires significant infrastructure investment; would use AWS HIPAA-eligible services in production |
| **Care Plan Editing** | Users cannot edit generated care plans, only download or regenerate | Need to first validate LLM output quality before building editing UI |
| **Version History** | Regenerating overwrites the previous care plan | Current design stores only the latest version; versioning adds complexity |
| **Real-time Updates** | Frontend polls for status instead of WebSocket push | Polling is sufficient for MVP; WebSocket is a Phase 2 optimization |
| **Audit Logging** | No comprehensive audit trail (who did what, when) | Required for healthcare compliance but deferred for MVP |
| **Rate Limiting** | No API throttling or rate limits | Needed for production but acceptable for internal tool MVP |
| **Multi-tenancy** | Single-tenant design | Would need redesign if serving multiple pharmacy organizations |

### HIPAA Compliance Roadmap (Phase 2)

For production deployment with real PHI (Protected Health Information):

1. **Encryption** - Enable encryption at rest (AWS RDS, S3) and in transit (TLS)
2. **Access Controls** - Implement RBAC with minimum necessary access
3. **Audit Trails** - Log all PHI access with immutable audit logs
4. **BAA** - Sign Business Associate Agreements with AWS, Anthropic/OpenAI
5. **Data Retention** - Implement compliant data retention and deletion policies
6. **Incident Response** - Establish breach notification procedures
