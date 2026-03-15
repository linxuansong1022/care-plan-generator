# CarePlan Generator — Project Highlights

## Project Title (Resume)

**CarePlan Generator — Automated Pharmaceutical Care Plan System**
Python, Django REST Framework, React, PostgreSQL, Redis, Celery, AWS (Lambda, API Gateway, SQS, RDS), Terraform, Docker, Prometheus, Grafana

---

## System Architecture Overview

### 5-Layer Architecture

```
┌─────────────────────────────────────┐
│  Presentation Layer (React)         │  ← User interaction + Polling
├─────────────────────────────────────┤
│  API Layer (Django REST / Lambda)   │  ← HTTP routing + request parsing
├─────────────────────────────────────┤
│  Business Logic Layer (services.py) │  ← Validation, duplicate detection, order creation
├─────────────────────────────────────┤
│  Async Processing Layer             │  ← Redis+Celery (local) / SQS+Lambda (AWS)
│  (Message Queue + Worker)           │  ← LLM calls, care plan generation
├─────────────────────────────────────┤
│  Data Layer (PostgreSQL / RDS)      │  ← 4-table normalized storage
└─────────────────────────────────────┘
```

### Core Data Flow

```
User submits form → API receives request → Input validation (format + duplicate detection)
→ Write to DB (Patient/Provider/Order) → Send message to queue → Return 202 Accepted
→ Worker consumes async → Call LLM API → Generate CarePlan and write to DB
→ Frontend polls for result → Download Care Plan file
```

### Local vs AWS Architecture Mapping

| Local (Docker)    | AWS (Serverless)          | Role                            |
| ----------------- | ------------------------- | ------------------------------- |
| Django views.py   | post_orders Lambda        | Receive HTTP, validate, persist |
| Redis             | SQS order-queue           | Message queue, decouple writes  |
| Celery Worker     | generate_care_plan Lambda | Consume queue, call LLM, save   |
| Docker PostgreSQL | RDS PostgreSQL            | Persistent data storage         |
| Django StatusView | get_orders Lambda         | Query order status + CarePlan   |
| localhost:8000    | API Gateway               | HTTP entry point, routing       |
| —                 | order-queue-dlq           | Dead Letter Queue for failures  |

---

## Resume Bullet Points (4 Points)

### 1. Architecture + Async Processing

> Designed an event-driven asynchronous architecture that decouples LLM API calls (10-30s latency) into message queue processing with immediate 202 responses, enabling concurrent handling of 50+ simultaneous requests without blocking the user interface.

### 2. Input Validation + Data Integrity + Testing

> Built a 3-layer validation pipeline — field-level format checks in serializers, business-rule duplicate detection with ERROR vs WARNING semantics in services, and a custom exception hierarchy with centralized error handling — achieving 81% test coverage across 83 unit and integration tests.

### 3. Design Patterns + Extensibility

> Applied Adapter Pattern with Template Method to support 4 heterogeneous data sources (web form, JSON, XML, pipe-delimited) through a unified internal data model, enabling new source integration with a single adapter class and zero modification to existing business logic.

### 4. Cloud Deployment + IaC

> Migrated the full system to a serverless cloud architecture with a platform-agnostic service layer sharing identical business logic between local and cloud environments, and automated infrastructure provisioning for reproducible one-command deployment and teardown.

---

## Tech Stack by Category

| Category         | Technologies                                  |
| ---------------- | --------------------------------------------- |
| Backend          | Python, Django REST Framework                 |
| Frontend         | React, JavaScript                             |
| Database         | PostgreSQL                                    |
| Async Processing | Redis (Message Queue), Celery (Worker)        |
| Cloud Services   | AWS Lambda, API Gateway, SQS, RDS, CloudWatch |
| Infrastructure   | Terraform (IaC), Docker, Docker Compose       |
| Monitoring       | Prometheus, Grafana                           |
| AI/LLM           | Google Gemini API                             |
| Testing          | Django TestCase, 83 tests, 81% coverage       |

---

## Tech Stack Line by Target Role

- **Backend SWE:** Python, Django REST Framework, PostgreSQL, Redis, Celery, AWS Lambda, SQS, Terraform, Docker
- **Full-Stack SWE:** Python, Django REST Framework, React, PostgreSQL, Redis, Celery, AWS Lambda, SQS, Docker
- **Cloud / DevOps:** Python, AWS (Lambda, API Gateway, SQS, RDS, CloudWatch), Terraform, Docker, Prometheus, Grafana

---

## Key Design Decisions (Interview Talking Points)

### Why async? (Bullet 1)
- LLM calls take 10-30s → synchronous = blocked UI
- Solution: 202 Accepted + message queue + worker pattern
- Same pattern locally (Redis+Celery) and on AWS (SQS+Lambda)

### Why 3-layer validation? (Bullet 2)
- Layer 1 (serializers): format checks — NPI 10-digit, MRN 6-digit, ICD-10 regex
- Layer 2 (services): business rules — duplicate patient/provider/order detection
- Layer 3 (exception handler): centralized error formatting for frontend
- ERROR = definitive conflict, block submission; WARNING = suspected issue, allow user confirmation

### Why Adapter Pattern? (Bullet 3)
- CVS receives orders from multiple sources with different formats
- Each adapter transforms source-specific data into a unified InternalOrder dataclass
- Factory function selects adapter by source type
- Adding a new source = one new class, zero changes to services/views/tests (Open-Closed Principle)

### Why platform-agnostic service layer? (Bullet 4)
- Business logic lives in services.py, shared by Django and Lambda
- Django views parse Django request → call service; Lambda handlers parse AWS event → call same service
- One codebase, two deployment targets
- Terraform automates all AWS resource creation/destruction with a single command
