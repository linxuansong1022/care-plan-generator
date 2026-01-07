"""
Seed test data for development.
Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.providers.models import Provider
from apps.patients.models import Patient, PatientDiagnosis, MedicationHistory
from apps.orders.models import Order
from apps.care_plans.models import CarePlan


class Command(BaseCommand):
    help = "Seed database with test data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        # Create Providers
        providers = [
            Provider.objects.get_or_create(
                npi="1234567893",
                defaults={"name": "Dr. Jane Smith", "phone": "555-0101"}
            )[0],
            Provider.objects.get_or_create(
                npi="1234567810",
                defaults={"name": "Dr. Michael Chen", "phone": "555-0102"}
            )[0],
            Provider.objects.get_or_create(
                npi="1234567828",
                defaults={"name": "Dr. Sarah Johnson", "phone": "555-0103"}
            )[0],
        ]
        self.stdout.write(f"  Created {len(providers)} providers")

        # Create Patients
        patients_data = [
            {
                "mrn": "000001",
                "first_name": "Alice",
                "last_name": "Williams",
                "date_of_birth": "1979-06-08",
                "sex": "Female",
                "weight_kg": 72.0,
                "allergies": "None known",
                "primary_diagnosis_code": "G70.00",
                "primary_diagnosis_description": "Myasthenia gravis without (acute) exacerbation",
            },
            {
                "mrn": "000002",
                "first_name": "Bob",
                "last_name": "Martinez",
                "date_of_birth": "1965-03-15",
                "sex": "Male",
                "weight_kg": 85.5,
                "allergies": "Penicillin",
                "primary_diagnosis_code": "D83.9",
                "primary_diagnosis_description": "Common variable immunodeficiency",
            },
            {
                "mrn": "000003",
                "first_name": "Carol",
                "last_name": "Thompson",
                "date_of_birth": "1982-11-22",
                "sex": "Female",
                "weight_kg": 68.0,
                "allergies": "Sulfa drugs",
                "primary_diagnosis_code": "G61.0",
                "primary_diagnosis_description": "Guillain-Barre syndrome",
            },
            {
                "mrn": "000004",
                "first_name": "David",
                "last_name": "Kim",
                "date_of_birth": "1958-07-30",
                "sex": "Male",
                "weight_kg": 78.0,
                "allergies": "None known",
                "primary_diagnosis_code": "M32.10",
                "primary_diagnosis_description": "Systemic lupus erythematosus",
            },
            {
                "mrn": "000005",
                "first_name": "Emma",
                "last_name": "Davis",
                "date_of_birth": "1990-01-05",
                "sex": "Female",
                "weight_kg": 62.0,
                "allergies": "Latex",
                "primary_diagnosis_code": "D80.0",
                "primary_diagnosis_description": "Hereditary hypogammaglobulinemia",
            },
        ]

        patients = []
        for data in patients_data:
            patient, created = Patient.objects.get_or_create(
                mrn=data["mrn"],
                defaults=data
            )
            patients.append(patient)
        self.stdout.write(f"  Created {len(patients)} patients")

        # Add medication history for first patient
        if patients:
            MedicationHistory.objects.get_or_create(
                patient=patients[0],
                medication_name="Pyridostigmine",
                defaults={"dosage": "60 mg", "frequency": "PO q6h PRN", "is_current": True}
            )
            MedicationHistory.objects.get_or_create(
                patient=patients[0],
                medication_name="Prednisone",
                defaults={"dosage": "10 mg", "frequency": "PO daily", "is_current": True}
            )
            MedicationHistory.objects.get_or_create(
                patient=patients[0],
                medication_name="Lisinopril",
                defaults={"dosage": "10 mg", "frequency": "PO daily", "is_current": True}
            )

            # Add secondary diagnoses
            PatientDiagnosis.objects.get_or_create(
                patient=patients[0],
                icd10_code="I10",
                defaults={"description": "Essential hypertension", "is_primary": False}
            )
            PatientDiagnosis.objects.get_or_create(
                patient=patients[0],
                icd10_code="K21.0",
                defaults={"description": "GERD with esophagitis", "is_primary": False}
            )

        # Create sample orders
        sample_records = """
Name: A.W. (Fictional)
MRN: 000001 (fictional)
DOB: 1979-06-08 (Age 46)
Sex: Female
Weight: 72 kg
Allergies: None known to medications (no IgA deficiency)
Medication: IVIG

Primary diagnosis: Generalized myasthenia gravis (AChR antibody positive), MGFA class IIb
Secondary diagnoses: Hypertension (well controlled), GERD

Home meds:
- Pyridostigmine 60 mg PO q6h PRN (current avg 3–4 doses/day)
- Prednisone 10 mg PO daily
- Lisinopril 10 mg PO daily
- Omeprazole 20 mg PO daily

Recent history:
Progressive proximal muscle weakness and ptosis over 2 weeks with worsening speech and swallowing fatigue.
Neurology recommends IVIG for rapid symptomatic control (planned course prior to planned thymectomy).
Baseline respiratory status: no stridor; baseline FVC 2.8 L (predicted 4.0 L; ~70% predicted).

Baseline clinic note (pre-infusion)
Date: 2025-10-15
Vitals: BP 128/78, HR 78, RR 16, SpO2 98% RA, Temp 36.7°C
Exam: Ptosis bilateral, fatigable proximal weakness (4/5), speech slurred after repeated counting.
Labs: CBC WNL; BMP: Na 138, K 4.1, Cl 101, HCO3 24, BUN 12, SCr 0.78, eGFR >90 mL/min/1.73m².
Plan: IVIG 2 g/kg total (144 g for 72 kg) given as 0.4 g/kg/day x 5 days.
"""

        orders_data = [
            {
                "patient": patients[0],
                "provider": providers[0],
                "medication_name": "IVIG (Privigen)",
                "patient_records": sample_records,
                "status": "completed",
            },
            {
                "patient": patients[1],
                "provider": providers[1],
                "medication_name": "IVIG (Gammagard)",
                "patient_records": "Patient with CVID requiring monthly IVIG replacement therapy.\nCurrent IgG level: 450 mg/dL (low).\nNo recent infections.",
                "status": "pending",
            },
            {
                "patient": patients[2],
                "provider": providers[0],
                "medication_name": "IVIG (Privigen)",
                "patient_records": "Acute GBS presentation. Ascending weakness over 3 days.\nCSF: albuminocytologic dissociation. EMG consistent with demyelinating polyneuropathy.",
                "status": "processing",
            },
            {
                "patient": patients[3],
                "provider": providers[2],
                "medication_name": "Rituximab",
                "patient_records": "SLE with refractory lupus nephritis class IV.\nFailing mycophenolate + hydroxychloroquine.",
                "status": "pending",
            },
            {
                "patient": patients[4],
                "provider": providers[1],
                "medication_name": "SCIG (Hizentra)",
                "patient_records": "Hereditary hypogammaglobulinemia. Transitioning from IVIG to SCIG for home therapy.",
                "status": "completed",
            },
        ]

        orders = []
        for data in orders_data:
            order, created = Order.objects.get_or_create(
                patient=data["patient"],
                provider=data["provider"],
                medication_name=data["medication_name"],
                defaults={
                    "patient_records": data["patient_records"],
                    "status": data["status"],
                }
            )
            orders.append(order)
        self.stdout.write(f"  Created {len(orders)} orders")

        # Create sample care plan for completed orders
        sample_care_plan = """# PHARMACIST CARE PLAN - IVIG FOR MYASTHENIA GRAVIS

## 1. PROBLEM LIST / DRUG THERAPY PROBLEMS (DTPs)

1. **Need for rapid immunomodulation** - Patient requires IVIG to reduce myasthenic symptoms prior to thymectomy
2. **Risk of infusion-related reactions** - Headache, chills, fever, rare anaphylaxis possible
3. **Risk of renal dysfunction** - Monitor in patients with risk factors
4. **Risk of thromboembolic events** - Rare but serious; assess baseline risk
5. **Drug interactions** - Timing with pyridostigmine; steroid management

## 2. GOALS (SMART Format)

### Primary Goal
- Achieve clinically meaningful improvement in muscle strength within 2 weeks of completing IVIG course
- Measurable: Improved MG-ADL score, reduced ptosis, improved FVC

### Safety Goals
- No severe infusion reactions during therapy
- No acute kidney injury (SCr increase <0.3 mg/dL within 7 days)
- No thromboembolic events

### Process Goal
- Complete full 2 g/kg course (0.4 g/kg/day × 5 days) with documented monitoring

## 3. PHARMACIST INTERVENTIONS / PLAN

### Dosing & Administration
- Total dose: 2.0 g/kg = 144 g for 72 kg patient
- Daily dose: 28.8 g/day × 5 days
- Product: Privigen 10% IVIG
- Document lot number and expiration

### Premedication
- Acetaminophen 650 mg PO 30-60 min pre-infusion
- Diphenhydramine 25-50 mg PO 30-60 min pre-infusion
- Consider low-dose methylprednisolone if prior reactions

### Infusion Protocol
- Start: 0.5 mL/kg/hr for first 30 minutes
- Titrate: Increase by 0.5 mL/kg/hr every 30 min as tolerated
- Maximum: Per manufacturer guidelines (typically 8 mL/kg/hr for Privigen)

### Hydration & Renal Protection
- Ensure adequate hydration pre-infusion (250-500 mL NS if not fluid-overloaded)
- Monitor SCr at baseline and 3-7 days post-course

## 4. MONITORING PLAN & LAB SCHEDULE

| Timepoint | Parameters |
|-----------|------------|
| Baseline | CBC, BMP, FVC, vital signs |
| During infusion | VS q15min × 1hr, then q30min |
| Daily | FVC, symptom assessment |
| Post-course (Day 7) | BMP, clinical response |
| Follow-up (2 weeks) | Neurology assessment |

## 5. PATIENT EDUCATION POINTS

1. Purpose of IVIG therapy and expected timeline for improvement
2. Common side effects (headache, fatigue) and how to manage
3. Warning signs requiring immediate attention (chest pain, SOB, severe headache)
4. Importance of staying hydrated
5. Continue home medications as prescribed
"""

        for order in orders:
            if order.status == "completed":
                CarePlan.objects.get_or_create(
                    order=order,
                    defaults={
                        "content": sample_care_plan,
                        "llm_model": "claude-3-sonnet-20240229",
                        "llm_prompt_tokens": 1500,
                        "llm_completion_tokens": 800,
                        "generation_time_ms": 3500,
                        "generated_at": timezone.now(),
                    }
                )

        self.stdout.write(self.style.SUCCESS("✓ Database seeded successfully!"))
        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(f"  - Providers: {Provider.objects.count()}")
        self.stdout.write(f"  - Patients: {Patient.objects.count()}")
        self.stdout.write(f"  - Orders: {Order.objects.count()}")
        self.stdout.write(f"  - Care Plans: {CarePlan.objects.count()}")
