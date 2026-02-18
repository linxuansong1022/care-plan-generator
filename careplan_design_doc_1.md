# CarePlan System — Design Document

**Project:** Automated Care Plan Generation System  
**Customer:** CVS Specialty Pharmacy  
**Author:** [你的名字]  
**Date:** 2026-02-18  
**Status:** Draft v1.0

---

## 1. 背景与目标

### 问题
CVS 药剂师每位患者需要手动生成 Care Plan，耗时 20-40 分钟，且因合规和 Medicare 报销要求无法省略。当前人手严重不足，已形成积压。

### 目标
构建一个 Web 系统，让 CVS 医疗工作者能够：
1. 输入患者和药物信息
2. 系统自动调用 LLM 生成 Care Plan
3. 下载 Care Plan 文件打印后交给患者
4. 导出数据用于 pharma 报告

### 用户
- **使用者：** CVS 内部医疗工作者（医疗助理、药剂师）
- **非用户：** 患者不直接使用本系统

---

## 2. 功能需求

### 2.1 必须实现（MVP）

| 功能 | 说明 |
|------|------|
| 患者信息录入 Web 表单 | 填写所有必填字段并验证格式 |
| 重复患者检测 | 防止同一患者被重复录入 |
| 重复订单检测 | 防止同一天重复下单 |
| Provider 去重 | 同 NPI 只能录入一次 |
| LLM 生成 Care Plan | 调用 Claude/OpenAI API，输出结构化文本 |
| Care Plan 下载 | 生成可下载的文件（.txt 或 .pdf） |
| 数据导出 | 支持导出用于 pharma 报告（格式待定：CSV/Excel） |

### 2.2 Care Plan 输出格式（固定结构）

每份 Care Plan **必须包含以下四个部分**：

```
1. Problem List / Drug Therapy Problems (DTPs)
2. Goals (SMART 格式)
3. Pharmacist Interventions / Plan
4. Monitoring Plan & Lab Schedule
```

> 一个 Care Plan 对应一个订单（一种药物）。

---

## 3. 输入字段与验证规则

| 字段 | 类型 | 验证规则 |
|------|------|---------|
| Patient First Name | string | 必填，非空 |
| Patient Last Name | string | 必填，非空 |
| Patient MRN | string | 必填，唯一，**恰好 6 位数字** |
| Patient DOB | date | 必填（用于重复检测） |
| Referring Provider | string | 必填，非空 |
| Referring Provider NPI | string | 必填，**恰好 10 位数字** |
| Primary Diagnosis | string | 必填，**ICD-10 格式**（如 G70.01） |
| Medication Name | string | 必填，非空 |
| Additional Diagnoses | list[string] | 可选，每项须为有效 ICD-10 格式 |
| Medication History | list[string] | 可选，自由文本列表 |
| Patient Records | string 或 PDF | 可选，文本或上传 PDF 文件 |

### ICD-10 格式规则
- 格式：1 个字母 + 2 位数字 + 可选小数点 + 1-4 位字母数字
- 示例：`G70.01`、`I10`、`K21.0`

---

## 4. 重复检测规则

### 4.1 订单重复检测

| 场景 | 处理方式 | HTTP 状态码 |
|------|---------|------------|
| 同患者 + 同药物 + **同一天** | ❌ **ERROR** — 阻止提交，必须修正 | 409 Conflict |
| 同患者 + 同药物 + **不同天** | ⚠️ **WARNING** — 提示用户，可确认继续 | 409 Conflict（含 `warnings` 字段） |

### 4.2 患者重复检测

| 场景 | 处理方式 | HTTP 状态码 |
|------|---------|------------|
| MRN 相同 + 姓名或 DOB 不同 | ⚠️ **WARNING** — 可能录入错误，提示确认 | 409 Conflict（含 `warnings` 字段） |
| 姓名 + DOB 相同 + MRN 不同 | ⚠️ **WARNING** — 可能是同一人，提示确认 | 409 Conflict（含 `warnings` 字段） |

### 4.3 Provider 重复检测

| 场景 | 处理方式 | HTTP 状态码 |
|------|---------|------------|
| NPI 相同 + Provider 名字不同 | ❌ **ERROR** — 阻止提交，NPI 是唯一标识 | 409 Conflict |

### ERROR vs WARNING 的核心区别

- **ERROR**：数据存在确定性冲突，系统**拒绝**处理，用户必须先修正。
- **WARNING**：数据存在疑似问题，但**允许用户确认后继续**提交。

---

## 5. 系统架构（MVP）

```
[Web 前端 (React)]
        |
        | HTTP POST /orders
        v
[Django REST API]
        |
   ┌────┴────┐
   |  验证   |  → 格式验证 + 重复检测
   └────┬────┘
        |
   ┌────┴────┐
   |  存数据  |  → 写入 PostgreSQL
   └────┬────┘
        |
   ┌────┴────┐
   | 调 LLM  |  → Claude / OpenAI API
   └────┬────┘
        |
   ┌────┴────┐
   | 返回结果 |  → Care Plan 文件可下载
   └─────────┘
```

> **Day 1 MVP 架构**：同步调用 LLM（LLM 调用放在请求链路里，后续 Day 4 会改为异步队列）。

---

## 6. 数据库设计（初版）

### 表结构

**Provider**
```
id, npi (唯一), name, created_at
```

**Patient**
```
id, mrn (唯一), first_name, last_name, dob, created_at
```

**Order**
```
id, patient_id (FK), provider_id (FK),
medication_name, primary_diagnosis,
additional_diagnoses (JSON), medication_history (JSON),
patient_records (text), order_date,
status (pending / completed / failed),
created_at
```

**CarePlan**
```
id, order_id (FK, 唯一),
content (text), file_path,
created_at
```

---

## 7. API 设计（初版）

### POST /api/orders
提交新订单，触发 Care Plan 生成。

**Request Body:**
```json
{
  "patient": {
    "first_name": "Jane",
    "last_name": "Doe",
    "mrn": "123456",
    "dob": "1979-06-08"
  },
  "provider": {
    "name": "Dr. Smith",
    "npi": "1234567890"
  },
  "medication_name": "IVIG",
  "primary_diagnosis": "G70.01",
  "additional_diagnoses": ["I10", "K21.0"],
  "medication_history": ["Pyridostigmine 60mg", "Prednisone 10mg"],
  "patient_records": "Progressive proximal muscle weakness..."
}
```

**Response — 成功 (201):**
```json
{
  "order_id": 42,
  "status": "completed",
  "care_plan_url": "/api/orders/42/careplan/download"
}
```

**Response — WARNING (409):**
```json
{
  "type": "warning",
  "warnings": ["Same patient + same medication was ordered on 2026-01-15"],
  "order_id": null
}
```

**Response — ERROR (409):**
```json
{
  "type": "error",
  "errors": ["Duplicate order: same patient + same medication + same day"]
}
```

### GET /api/orders/{id}/careplan/download
下载 Care Plan 文件。

### GET /api/orders?export=true
导出订单数据（用于 pharma 报告）。

---

## 8. 技术栈

| 层 | 技术 | 原因 |
|----|------|------|
| 后端 | Python + Django + DRF | 你已熟悉 |
| 前端 | React | 课程统一技术栈 |
| 数据库 | PostgreSQL | 关系型，适合业务逻辑约束 |
| LLM | Claude API / OpenAI API | Care Plan 生成 |
| 容器化 | Docker + Docker Compose | 本地开发一键启动 |
| 异步（后期） | Celery + Redis → SQS + Lambda | Day 4 之后引入 |

---

## 9. 待确认问题（需客户回复）

以下是需求中尚未明确的部分，需在开发前确认：

1. **Care Plan 下载格式：** `.txt` 还是 `.pdf`？还是两种都要？
2. **导出报告格式：** pharma 报告的导出格式是 CSV、Excel，还是其他系统的接口？
3. **Medication Name 的来源：** 是自由输入还是从药品库下拉选择？
4. **WARNING 确认方式：** 用户点击"确认继续"后，系统是否需要记录"用户已知晓此警告"？
5. **Care Plan 的存储期限：** 生成的文件需要保留多久？是否需要历史查询？
6. **并发量：** 系统同时有多少医疗工作者在用？（影响架构选型）
7. **PDF 上传大小限制：** Patient Records 上传 PDF 最大允许多大？

---

## 10. 不在 MVP 范围内

- 患者/医疗工作者登录认证（暂不做）
- Care Plan 审批流程
- 与 CVS 内部 EHR 系统集成
- 移动端

---

*文档将随开发进度持续更新。*
