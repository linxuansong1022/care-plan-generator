# CarePlan Generator

**Automated Pharmaceutical Care Plan System** designed to streamline the workflow for pharmacists. By integrating large language models (LLMs), this system autonomously generates comprehensive patient care plans from medical orders, reducing the manual drafting time from 20-40 minutes per plan down to a 10-30 second background task.

## 🌟 Project Highlights

- **Event-Driven Asynchronous Architecture**: Orchestrated an asynchronous queue system (Redis/Celery locally, AWS SQS/Lambda in production) to decouple the 10-30 second LLM invocation from the main thread. Utilizes polling and HTTP `202 Accepted` to confidently support 50+ concurrent requests without blocking the UI.
- **Robust REST API Design**: Built a comprehensive and standard-compliant RESTful API. Strictly utilizes HTTP status codes (e.g., `409 Conflict` for business rule violations like duplicate patients, `202 Accepted` for async processing, `204 No Content` for clean deletions).
- **Quality Assurance & Data Integrity**: Implemented a rigorous 3-layer validation pipeline filtering out format errors via Serializers, catching duplicates at the Service layer, and handling global exceptions cleanly. Accompanied by **83 Unit and Integration tests** achieving **81% code coverage**.
- **Adapter Design Pattern for Multi-Source Ingestion**: Developed an extensible Intake Webhook capable of assimilating data from 4 heterogeneous sources (Web, JSON, XML, pipe-delimited) using the Adapter pattern. Adding new external clients requires zero changes to core business logic (Open-Closed Principle).
- **Cloud Migration & Infrastructure-as-Code (IaC)**: Seamlessly migrated the local Dockerized application to an AWS Serverless environment (API Gateway, Lambda, SQS, RDS). Managed the entire cloud footprint through **Terraform**, empowering one-click declarative deployments and teardowns.

## 🏗️ Architecture Overview

The system strictly adheres to a **5-Layer Architecture**, maintaining a platform-agnostic business logic layer shared between local and cloud environments:

1. **Presentation Layer**: React frontend handling user interaction and order status polling.
2. **API Layer**: Django REST Framework (Local) / AWS API Gateway (Cloud) routing HTTP requests.
3. **Business Logic Layer**: Reusable `services.py` that handles validation, deduplication, and database operations.
4. **Async Processing Layer**: Redis & Celery (Local) / SQS & Lambda (Cloud) driving background tasks.
5. **Data Layer**: 4-table normalized PostgreSQL database (Patient, Provider, Order, CarePlan).

### Deployment Mapping

| Component | Local (Docker) | Production AWS (Serverless) |
| :--- | :--- | :--- |
| **API Entry** | localhost:8000 | API Gateway |
| **HTTP Routing & Logic** | Django `views.py` | `post_orders` Lambda |
| **Message Queue** | Redis | SQS `order-queue` |
| **Async Worker (LLM)**| Celery Worker | `generate_care_plan` Lambda |
| **Database** | Docker PostgreSQL | AWS RDS (PostgreSQL) |
| **Failure Handling** | Celery Retries | SQS Dead Letter Queue (DLQ) |

## 💻 Tech Stack

- **Backend core**: Python, Django REST Framework
- **Databases & Queue**: PostgreSQL, Redis, Celery
- **Cloud (AWS)**: Lambda, API Gateway, SQS, RDS, CloudWatch
- **Infrastructure & Monitoring**: Terraform (IaC), Docker, Docker Compose, Prometheus, Grafana
- **AI Integration**: Google Cloud Vertex AI (Gemini Pro) via API

## 🚀 Getting Started (Local Development)

### Prerequisites
- Docker & Docker Compose
- API Key (e.g., Gemini Pro)

### 1. Environment Setup
```bash
cp .env.example .env
# Edit .env and insert your database credentials and API Key
```

### 2. Launch Local Environment (Docker)
```bash
docker compose up --build
```
This single command spins up the Frontend (Port 3000), API Server (Port 8000), PostgreSQL Database, Redis, Celery Worker, and local Monitoring stack.

- Frontend App: `http://localhost:3000`
- API Endpoint: `http://localhost:8000/api/orders/`

### 3. Run Tests
```bash
docker compose exec web python manage.py test
```

## ☁️ AWS Deployment (Terraform)

Ensure you have the AWS CLI configured and Terraform installed.

```bash
cd careplan-terraform

# Initialize Terraform plugins
terraform init

# Review the infrastructure plan
terraform plan

# Deploy the entire stack to AWS
terraform apply
```

To tear down all resources and stop incurring charges:
```bash
terraform destroy
```

## 📄 License
This MVP is an exploratory educational project detailing best-practices in software engineering, backend architecture, and cloud deployment.
