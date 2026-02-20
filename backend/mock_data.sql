-- mock_data.sql
-- 直接在 TablePlus 或 psql 里运行这个文件来插入测试数据
--
-- 使用方法：
--   方式 1（TablePlus）：打开 TablePlus → 连接数据库 → 打开这个文件 → 点 Run
--   方式 2（命令行）：docker compose exec db psql -U postgres -d careplan -f /tmp/mock_data.sql
--   方式 3（命令行）：cat mock_data.sql | docker compose exec -T db psql -U postgres -d careplan
--
-- ⚠️ 注意：要先运行 migration 建表，再运行这个 SQL
--   docker compose exec backend python manage.py migrate

-- 清空旧数据（注意顺序：先删有外键的表）
DELETE FROM orders_careplan;
DELETE FROM orders_order;
DELETE FROM orders_patient;
DELETE FROM orders_provider;

-- 重置自增 ID（从 1 开始）
ALTER SEQUENCE orders_patient_id_seq RESTART WITH 1;
ALTER SEQUENCE orders_provider_id_seq RESTART WITH 1;
ALTER SEQUENCE orders_order_id_seq RESTART WITH 1;
ALTER SEQUENCE orders_careplan_id_seq RESTART WITH 1;

-- ============================================================
-- Patients（5 个患者）
-- ============================================================
INSERT INTO orders_patient (first_name, last_name, mrn, dob, created_at) VALUES
('Jane',  'Doe',    '123456', '1979-06-08', NOW()),
('John',  'Smith',  '234567', '1985-03-15', NOW()),
('Maria', 'Garcia', '345678', '1992-11-22', NOW()),
('James', 'Wilson', '456789', '1968-07-30', NOW()),
('Emily', 'Chen',   '567890', '2001-01-05', NOW());

-- ============================================================
-- Providers（3 个医生）
-- ============================================================
INSERT INTO orders_provider (name, npi, created_at) VALUES
('Dr. Sarah Johnson', '1234567890', NOW()),
('Dr. Michael Lee',   '2345678901', NOW()),
('Dr. Rachel Kim',    '3456789012', NOW());

-- ============================================================
-- Orders（8 个订单）
-- 注意 patient_id 和 provider_id 是外键，指向上面的表
-- Jane Doe (patient_id=1) 有 3 个订单 → 但 Patient 表只有 1 条记录
-- ============================================================
INSERT INTO orders_order (patient_id, provider_id, medication_name, primary_diagnosis, additional_diagnoses, medication_history, patient_records, status, order_date, created_at) VALUES
-- Jane Doe 的 3 个订单
(1, 1, 'IVIG',       'G70.01', '["I10","K21.0"]',  '["Pyridostigmine 60mg","Prednisone 10mg"]',  'Progressive proximal muscle weakness over 6 months.',       'completed',  CURRENT_DATE, NOW()),
(1, 2, 'Rituximab',  'G70.01', '["I10"]',           '["IVIG","Pyridostigmine 60mg"]',             'Inadequate response to IVIG therapy.',                      'completed',  CURRENT_DATE, NOW()),
(1, 1, 'Eculizumab', 'G70.01', '[]',                '["IVIG","Rituximab"]',                       'Refractory generalized myasthenia gravis.',                 'pending',    CURRENT_DATE, NOW()),
-- John Smith 的 2 个订单
(2, 1, 'Humira',     'K50.90', '["K21.0"]',         '["Mesalamine 800mg"]',                       'Moderate Crohn''s disease, failed conventional therapy.',    'completed',  CURRENT_DATE, NOW()),
(2, 3, 'Stelara',    'K50.90', '[]',                '["Humira","Mesalamine 800mg"]',              'Loss of response to Humira after 18 months.',               'failed',     CURRENT_DATE, NOW()),
-- Maria Garcia
(3, 2, 'Ocrevus',    'G35',    '["G89.29"]',        '["Copaxone"]',                               'Relapsing MS with 2 relapses in past year.',                'completed',  CURRENT_DATE, NOW()),
-- James Wilson
(4, 3, 'Keytruda',   'C34.90', '["I10","E11.9"]',   '["Carboplatin","Paclitaxel"]',               'Stage IIIB NSCLC, PD-L1 positive.',                         'processing', CURRENT_DATE, NOW()),
-- Emily Chen
(5, 1, 'Dupixent',   'L20.9',  '["J45.20"]',        '["Topical corticosteroids","Cyclosporine"]', 'Severe atopic dermatitis uncontrolled with topicals.',       'completed',  CURRENT_DATE, NOW());

-- ============================================================
-- CarePlans（只给 completed 的订单创建）
-- 注意：pending/processing/failed 的订单没有 CarePlan 记录
-- ============================================================
INSERT INTO orders_careplan (order_id, content, created_at) VALUES
(1, '1. Problem List / Drug Therapy Problems (DTPs)
- Risk of infusion-related reactions with IVIG
- Potential for thromboembolic events given hypertension (I10)
- GERD (K21.0) may be exacerbated by IVIG-related GI side effects

2. Goals (SMART format)
- Achieve ≥50% improvement in QMG score within 12 weeks
- Maintain IgG trough levels 800-1200 mg/dL monthly
- Zero infusion reactions requiring discontinuation over 6 months

3. Pharmacist Interventions / Plan
- Pre-medicate with acetaminophen 650mg and diphenhydramine 25mg
- Start infusion at 0.5 mL/kg/hr, titrate up as tolerated
- Educate on thromboembolic event signs
- Coordinate with Dr. Johnson on prednisone taper

4. Monitoring Plan & Lab Schedule
- Baseline: CBC, CMP, IgG level, LFTs
- Monthly: IgG trough levels
- Every 3 months: CBC, CMP, renal function
- QMG score at baseline, 6 weeks, 12 weeks', NOW()),

(2, '1. Problem List / Drug Therapy Problems (DTPs)
- PML risk with rituximab
- Increased infection risk due to B-cell depletion
- Prior IVIG use suggests refractory disease

2. Goals (SMART format)
- Achieve complete B-cell depletion (CD20 <1%) within 4 weeks
- Reduce MG exacerbation rate by ≥50% over 12 months
- Maintain IgG >400 mg/dL throughout treatment

3. Pharmacist Interventions / Plan
- Pre-medicate with methylprednisolone, acetaminophen, diphenhydramine
- Screen for hepatitis B before initiating
- Educate on PML symptoms
- Coordinate pneumocystis prophylaxis with Dr. Lee

4. Monitoring Plan & Lab Schedule
- Baseline: CBC, CD20, hepatitis B panel, immunoglobulins
- Every 2 weeks x8: CBC with differential
- Monthly x6: immunoglobulins, CD20 count
- 6-month: MG-ADL score, anti-AChR antibodies', NOW()),

(4, '1. Problem List / Drug Therapy Problems (DTPs)
- TB reactivation risk with Humira
- Injection site reactions
- GERD may complicate GI assessment

2. Goals (SMART format)
- Achieve clinical remission (CDAI <150) within 12 weeks
- Reduce CRP to <5 mg/L within 8 weeks
- Zero Crohn''s flare hospitalizations over 12 months

3. Pharmacist Interventions / Plan
- Verify negative TB test before initiation
- Loading: 160mg week 0, 80mg week 2, then 40mg q2w
- Train on SC injection technique
- Coordinate with GI on mesalamine plan

4. Monitoring Plan & Lab Schedule
- Baseline: CBC, CMP, LFTs, CRP, ESR, TB test, hepatitis panel
- Every 4 weeks: CRP, ESR
- Every 3 months: CBC, CMP, LFTs
- Every 6 months: drug levels, anti-drug antibodies', NOW()),

(6, '1. Problem List / Drug Therapy Problems (DTPs)
- Infusion-related reactions (most common first dose)
- PML risk with anti-CD20 therapy
- Chronic pain requires separate management

2. Goals (SMART format)
- Complete first split-dose with no grade 3+ reactions
- No new MRI lesions at 6-month follow-up
- Annualized relapse rate <0.2 over 12 months

3. Pharmacist Interventions / Plan
- Pre-medicate with methylprednisolone, acetaminophen, antihistamine
- First dose split: 300mg day 1, 300mg day 15; then 600mg q6mo
- Screen for hepatitis B
- Educate on infection signs and neurological symptoms

4. Monitoring Plan & Lab Schedule
- Baseline: CBC, immunoglobulins, hepatitis B, JCV antibody, MRI
- Before each infusion: CBC, immunoglobulin levels
- 6-month: MRI brain with/without contrast
- Annual: JCV antibody, CMP', NOW()),

(8, '1. Problem List / Drug Therapy Problems (DTPs)
- Risk of immune-mediated dermatitis
- Asthma (J45.20) may benefit from dupilumab dual indication
- Monitor for residual nephrotoxicity from prior cyclosporine

2. Goals (SMART format)
- Achieve EASI-75 within 16 weeks
- Reduce pruritus NRS by ≥4 points within 4 weeks
- Taper topical corticosteroids to PRN within 8 weeks

3. Pharmacist Interventions / Plan
- Loading: 600mg SC, then 300mg SC every other week
- Train on autoinjector use and site rotation
- Educate: conjunctivitis is most common side effect
- Assess asthma meds for potential step-down

4. Monitoring Plan & Lab Schedule
- Baseline: CBC with eosinophils, total IgE, BMP
- Week 4: phone follow-up, pruritus NRS
- Week 8: EASI score, steroid taper assessment
- Week 16: EASI, IGA, eosinophil count
- Every 6 months: CBC, BMP, ophthalmologic exam if needed', NOW());

-- ============================================================
-- 验证数据
-- ============================================================
-- 运行完后你可以用这些查询验证：

-- 查看所有患者
-- SELECT * FROM orders_patient;

-- 查看 Jane Doe 的所有订单（注意只有 1 条 patient 记录，但 3 个 order）
-- SELECT p.first_name, p.last_name, o.medication_name, o.status
-- FROM orders_order o
-- JOIN orders_patient p ON o.patient_id = p.id
-- WHERE p.mrn = '123456';

-- 查看有 care plan 的订单
-- SELECT o.id, p.first_name, p.last_name, o.medication_name, o.status, 
--        CASE WHEN cp.id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_careplan
-- FROM orders_order o
-- JOIN orders_patient p ON o.patient_id = p.id
-- LEFT JOIN orders_careplan cp ON cp.order_id = o.id;
