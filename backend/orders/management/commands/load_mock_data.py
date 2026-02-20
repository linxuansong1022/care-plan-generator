# backend/orders/management/commands/load_mock_data.py
#
# Django Management Command：自定义的命令行工具
# 运行方式：python manage.py load_mock_data
#
# 这个脚本会往 4 张表里插入测试数据
# 注意看：同一个 Patient 被多个 Order 引用，不再重复存储了！

from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.models import Patient, Provider, Order, CarePlan
from datetime import date


class Command(BaseCommand):
    help = 'Load mock data into Patient, Provider, Order, and CarePlan tables'

    def handle(self, *args, **options):
        # 先清空旧数据（方便你反复运行这个脚本测试）
        self.stdout.write('Clearing existing data...')
        CarePlan.objects.all().delete()
        Order.objects.all().delete()
        Patient.objects.all().delete()
        Provider.objects.all().delete()

        # ============================================================
        # 1. 创建 Patients（5 个患者）
        # ============================================================
        self.stdout.write('Creating patients...')
        patients = [
            Patient.objects.create(
                first_name='Jane', last_name='Doe',
                mrn='123456', dob=date(1979, 6, 8)
            ),
            Patient.objects.create(
                first_name='John', last_name='Smith',
                mrn='234567', dob=date(1985, 3, 15)
            ),
            Patient.objects.create(
                first_name='Maria', last_name='Garcia',
                mrn='345678', dob=date(1992, 11, 22)
            ),
            Patient.objects.create(
                first_name='James', last_name='Wilson',
                mrn='456789', dob=date(1968, 7, 30)
            ),
            Patient.objects.create(
                first_name='Emily', last_name='Chen',
                mrn='567890', dob=date(2001, 1, 5)
            ),
        ]

        # ============================================================
        # 2. 创建 Providers（3 个医生）
        # ============================================================
        self.stdout.write('Creating providers...')
        providers = [
            Provider.objects.create(
                name='Dr. Sarah Johnson', npi='1234567890'
            ),
            Provider.objects.create(
                name='Dr. Michael Lee', npi='2345678901'
            ),
            Provider.objects.create(
                name='Dr. Rachel Kim', npi='3456789012'
            ),
        ]

        # ============================================================
        # 3. 创建 Orders（8 个订单）
        #    注意：Jane Doe 有 3 个订单，但 Patient 表里只有 1 条记录！
        # ============================================================
        self.stdout.write('Creating orders...')
        orders_data = [
            # Jane Doe - 3 个订单（同一个 patient 对象被引用了 3 次）
            {
                'patient': patients[0], 'provider': providers[0],
                'medication_name': 'IVIG',
                'primary_diagnosis': 'G70.01',
                'additional_diagnoses': ['I10', 'K21.0'],
                'medication_history': ['Pyridostigmine 60mg', 'Prednisone 10mg'],
                'patient_records': 'Progressive proximal muscle weakness over 6 months.',
                'status': 'completed',
            },
            {
                'patient': patients[0], 'provider': providers[1],
                'medication_name': 'Rituximab',
                'primary_diagnosis': 'G70.01',
                'additional_diagnoses': ['I10'],
                'medication_history': ['IVIG', 'Pyridostigmine 60mg'],
                'patient_records': 'Inadequate response to IVIG therapy.',
                'status': 'completed',
            },
            {
                'patient': patients[0], 'provider': providers[0],
                'medication_name': 'Eculizumab',
                'primary_diagnosis': 'G70.01',
                'additional_diagnoses': [],
                'medication_history': ['IVIG', 'Rituximab'],
                'patient_records': 'Refractory generalized myasthenia gravis.',
                'status': 'pending',
            },
            # John Smith - 2 个订单
            {
                'patient': patients[1], 'provider': providers[0],
                'medication_name': 'Humira',
                'primary_diagnosis': 'K50.90',
                'additional_diagnoses': ['K21.0'],
                'medication_history': ['Mesalamine 800mg'],
                'patient_records': 'Moderate Crohn\'s disease, failed conventional therapy.',
                'status': 'completed',
            },
            {
                'patient': patients[1], 'provider': providers[2],
                'medication_name': 'Stelara',
                'primary_diagnosis': 'K50.90',
                'additional_diagnoses': [],
                'medication_history': ['Humira', 'Mesalamine 800mg'],
                'patient_records': 'Loss of response to Humira after 18 months.',
                'status': 'failed',
            },
            # Maria Garcia - 1 个订单
            {
                'patient': patients[2], 'provider': providers[1],
                'medication_name': 'Ocrevus',
                'primary_diagnosis': 'G35',
                'additional_diagnoses': ['G89.29'],
                'medication_history': ['Copaxone'],
                'patient_records': 'Relapsing multiple sclerosis with 2 relapses in past year.',
                'status': 'completed',
            },
            # James Wilson - 1 个订单
            {
                'patient': patients[3], 'provider': providers[2],
                'medication_name': 'Keytruda',
                'primary_diagnosis': 'C34.90',
                'additional_diagnoses': ['I10', 'E11.9'],
                'medication_history': ['Carboplatin', 'Paclitaxel'],
                'patient_records': 'Stage IIIB non-small cell lung cancer, PD-L1 positive.',
                'status': 'processing',
            },
            # Emily Chen - 1 个订单
            {
                'patient': patients[4], 'provider': providers[0],
                'medication_name': 'Dupixent',
                'primary_diagnosis': 'L20.9',
                'additional_diagnoses': ['J45.20'],
                'medication_history': ['Topical corticosteroids', 'Cyclosporine'],
                'patient_records': 'Severe atopic dermatitis uncontrolled with topicals.',
                'status': 'completed',
            },
        ]

        orders = []
        for data in orders_data:
            order = Order.objects.create(**data)
            orders.append(order)

        # ============================================================
        # 4. 创建 CarePlans（只给 completed 状态的订单创建）
        # ============================================================
        self.stdout.write('Creating care plans...')

        care_plans = {
            0: """1. Problem List / Drug Therapy Problems (DTPs)
- Risk of infusion-related reactions (headache, flushing, chills) with IVIG
- Potential for thromboembolic events given IVIG therapy and hypertension (I10)
- Drug interaction consideration: IVIG may reduce effectiveness of live vaccines
- GERD (K21.0) may be exacerbated by IVIG-related GI side effects

2. Goals (SMART format)
- Achieve ≥50% improvement in Quantitative Myasthenia Gravis (QMG) score within 12 weeks
- Maintain IgG trough levels between 800-1200 mg/dL, measured monthly
- Zero infusion-related adverse events requiring treatment discontinuation over 6 months
- Blood pressure maintained <140/90 mmHg at all clinic visits

3. Pharmacist Interventions / Plan
- Pre-medicate with acetaminophen 650mg and diphenhydramine 25mg 30 min before each infusion
- Start infusion at 0.5 mL/kg/hr, increase by 0.5 mL/kg/hr every 30 min as tolerated (max 4 mL/kg/hr)
- Educate patient on signs of thromboembolic events: sudden chest pain, leg swelling, shortness of breath
- Coordinate with Dr. Johnson regarding concurrent prednisone taper schedule
- Verify patient is adequately hydrated before each infusion

4. Monitoring Plan & Lab Schedule
- Baseline: CBC, CMP, IgG level, LFTs — before first infusion
- Monthly: IgG trough levels (draw before next infusion)
- Every 3 months: CBC, CMP, renal function (BUN/Cr)
- Every infusion: vital signs q15min during first hour, then q30min
- QMG score assessment at baseline, 6 weeks, and 12 weeks
- Follow-up phone call 48 hours after each infusion""",

            1: """1. Problem List / Drug Therapy Problems (DTPs)
- Risk of progressive multifocal leukoencephalopathy (PML) with rituximab
- Increased infection risk due to B-cell depletion
- Prior IVIG use suggests refractory disease requiring close monitoring
- Hypertension (I10) requires monitoring during infusion

2. Goals (SMART format)
- Achieve complete B-cell depletion (CD20 <1%) within 4 weeks of first cycle
- Reduce MG exacerbation rate by ≥50% over 12 months
- No grade 3-4 infusion reactions during treatment course
- Maintain adequate immunoglobulin levels (IgG >400 mg/dL)

3. Pharmacist Interventions / Plan
- Pre-medicate with methylprednisolone 100mg IV, acetaminophen 650mg, diphenhydramine 50mg
- Administer rituximab 375 mg/m² IV weekly x4 for induction
- Screen for hepatitis B (HBsAg, anti-HBc) before initiating therapy
- Educate patient: report any new neurological symptoms immediately (PML risk)
- Coordinate with Dr. Lee for pneumocystis prophylaxis with TMP-SMX

4. Monitoring Plan & Lab Schedule
- Baseline: CBC with differential, CD20 count, hepatitis B panel, quantitative immunoglobulins
- Every 2 weeks x8: CBC with differential
- Monthly x6: quantitative immunoglobulins, CD20 B-cell count
- Every infusion: vital signs q15min first hour, then q30min
- 6-month reassessment: MG-ADL score, QMG score, anti-AChR antibody titers""",

            3: """1. Problem List / Drug Therapy Problems (DTPs)
- Risk of serious infections including tuberculosis reactivation with Humira
- Injection site reactions common (erythema, itching, pain)
- GERD (K21.0) may complicate GI assessment in Crohn's disease monitoring
- Potential for hepatotoxicity requiring liver function monitoring

2. Goals (SMART format)
- Achieve clinical remission (CDAI <150) within 12 weeks of initiation
- Reduce CRP to <5 mg/L and normalize ESR within 8 weeks
- Complete TB screening and hepatitis panel before first dose
- Zero hospitalizations or ER visits for Crohn's flares over 12 months

3. Pharmacist Interventions / Plan
- Verify negative TB test (QuantiFERON-Gold or PPD) before initiation
- Instruct patient on proper subcutaneous injection technique and rotation sites
- Loading dose: 160mg SC at week 0, 80mg at week 2, then 40mg every other week
- Educate: avoid live vaccines; report signs of infection (fever, persistent cough)
- Coordinate with GI regarding concurrent mesalamine continuation vs taper

4. Monitoring Plan & Lab Schedule
- Baseline: CBC, CMP, LFTs, CRP, ESR, TB test, hepatitis B/C panel, lipid panel
- Every 4 weeks x12: CRP, ESR
- Every 3 months: CBC, CMP, LFTs
- Every 6 months: fecal calprotectin, adalimumab drug levels and anti-drug antibodies
- Colonoscopy per GI schedule (typically 6-12 months after initiation)
- Annual: TB screening, dermatologic exam (skin cancer screening)""",

            5: """1. Problem List / Drug Therapy Problems (DTPs)
- Risk of infusion-related reactions with Ocrevus (most common in first infusion)
- Progressive multifocal leukoencephalopathy (PML) risk with anti-CD20 therapy
- Chronic pain (G89.29) may require separate pain management coordination
- Risk of increased infections due to immunosuppression

2. Goals (SMART format)
- Complete first split-dose infusion (300mg x2, 14 days apart) with no grade 3+ reactions
- No new T2/FLAIR lesions on MRI at 6-month follow-up
- Annualized relapse rate <0.2 over 12 months
- Maintain IgG levels >400 mg/dL throughout treatment

3. Pharmacist Interventions / Plan
- Pre-medicate: methylprednisolone 100mg IV + acetaminophen + antihistamine 30 min prior
- First dose split: 300mg IV day 1, 300mg IV day 15; subsequent doses 600mg IV q6 months
- Screen for hepatitis B before initiation
- Educate: report any signs of infection or new neurological symptoms
- Coordinate with neurologist regarding Copaxone washout period

4. Monitoring Plan & Lab Schedule
- Baseline: CBC, immunoglobulins, hepatitis B panel, JCV antibody, MRI brain/spine
- Before each infusion (q6 months): CBC with differential, immunoglobulin levels
- 6-month MRI: brain with and without contrast
- Annual: JCV antibody, comprehensive metabolic panel
- Every infusion: vital signs monitoring per protocol""",

            7: """1. Problem List / Drug Therapy Problems (DTPs)
- Risk of immune-mediated dermatitis requiring topical management
- Potential for immunosuppression and increased infection risk with Dupixent
- Asthma (J45.20) may be positively impacted by dupilumab (dual indication)
- Prior cyclosporine use: monitor for residual nephrotoxicity

2. Goals (SMART format)
- Achieve EASI-75 (75% improvement in Eczema Area Severity Index) within 16 weeks
- Reduce pruritus NRS score by ≥4 points within 4 weeks
- Taper topical corticosteroids to PRN use within 8 weeks
- Maintain adequate asthma control (ACT score ≥20)

3. Pharmacist Interventions / Plan
- Loading dose: 600mg SC (two 300mg injections), then 300mg SC every other week
- Train patient on autoinjector use; rotate injection sites (thigh, abdomen, upper arm)
- Educate: conjunctivitis is most common side effect — use preservative-free artificial tears
- Coordinate with dermatologist for concurrent emollient therapy plan
- Assess asthma medication regimen for potential step-down given dual benefit

4. Monitoring Plan & Lab Schedule
- Baseline: CBC with eosinophils, total IgE, BMP (renal function post-cyclosporine)
- Week 4: phone follow-up — pruritus NRS, injection technique assessment
- Week 8: in-person visit — EASI score, topical steroid taper assessment
- Week 16: EASI score, IGA assessment, eosinophil count
- Every 3 months ongoing: dermatology visit, EASI score
- Every 6 months: CBC, BMP, ophthalmologic exam if conjunctivitis symptoms""",
        }

        for order_idx, content in care_plans.items():
            CarePlan.objects.create(
                order=orders[order_idx],
                content=content,
            )

        # ============================================================
        # 打印总结
        # ============================================================
        self.stdout.write(self.style.SUCCESS(f"""
✅ Mock data loaded successfully!

Summary:
  Patients:   {Patient.objects.count()}
  Providers:  {Provider.objects.count()}
  Orders:     {Order.objects.count()}
  CarePlans:  {CarePlan.objects.count()}

Key point to observe:
  Jane Doe (MRN: 123456) has {patients[0].orders.count()} orders
  → but Patient table only has 1 record for her!
  → This is normalization in action 🎉

Try these queries:
  docker compose exec backend python manage.py shell
  >>> from orders.models import *
  >>> Patient.objects.get(mrn='123456').orders.all()
  >>> Order.objects.filter(status='completed').count()
  >>> Order.objects.get(id=1).care_plan.content[:100]
"""))
