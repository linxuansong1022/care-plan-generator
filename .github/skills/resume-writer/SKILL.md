---
name: resume-writer
description: "基于 CarePlan Generator 全栈项目生成定制化简历项目经历。突出事件驱动异步架构、3 层验证管道、Adapter Pattern 多数据源适配、AWS Serverless 迁移与 Terraform IaC 等硬核亮点。Use when user says '写简历', 'resume', '简历', '项目经历', 'bullet points', or asks to generate resume content based on CarePlan Generator project."
---

# Resume Writer (CarePlan Generator Edition)

## Phase 1: 加载知识库

1. 读取 `references/resume_principles.md` — 简历编写原则（四段式结构、技术标签维度、亮点策略、常见误区、量化指标速查）
2. 读取 `references/project_highlights.md` — 项目亮点库（系统架构、4 条 bullet points、技术栈分类、面试 talking points）

## Phase 2: 采集用户画像

向用户抛出以下 2 个问题，**等待用户回答后再进入下一步**：

**问题 1：目前你想主投什么方向的岗位？**（单选）
- A. **Backend SWE** — 侧重分层架构设计、异步消息队列、输入验证管道、测试覆盖
- B. **Full-Stack SWE** — 侧重端到端数据流（React → Django → Redis/Celery → PostgreSQL → Polling）、前后端联调
- C. **Cloud / DevOps** — 侧重 AWS Serverless 架构、SQS + DLQ 失败恢复、Terraform IaC、Prometheus + Grafana 监控
- D. **AI Application Engineer** — 侧重 LLM 集成（Gemini API）、Prompt Engineering、异步生成兜底、Adapter Pattern 切换 LLM Provider

**问题 2：希望在这个项目经历下面放几个 bullet points？**（通常建议 3-4 个）

## Phase 3: 路由与生成逻辑

根据问题 1 的回答，从 `project_highlights.md` 中提取匹配亮点，并参照 `resume_principles.md` 中的"按目标岗位调整侧重点"表格：

### A. Backend SWE
- **必选**：亮点 1（事件驱动异步架构）+ 亮点 2（3 层验证管道 + 测试）
- **推荐**：亮点 3（Adapter Pattern + Open-Closed Principle）
- **可选**：亮点 4（云部署）— 简化为一句话收尾
- **弱化**：前端 React 细节

### B. Full-Stack SWE
- **必选**：亮点 1（异步架构 + 前端 Polling 联调）+ 亮点 2（验证管道）
- **推荐**：亮点 4（本地 Docker → AWS 迁移，强调 platform-agnostic service layer）
- **可选**：亮点 3（Adapter Pattern）
- **弱化**：Terraform 细节、监控细节

### C. Cloud / DevOps
- **必选**：亮点 4（AWS Lambda ×3 + SQS + RDS + API Gateway + Terraform）+ 亮点 1（SQS + DLQ 异步处理）
- **推荐**：新增 Prometheus + Grafana 监控描述
- **可选**：亮点 2（验证管道）— 简化
- **弱化**：设计模式、前端 React

### D. AI Application Engineer
- **必选**：以 LLM 集成为主线 — Gemini API 调用 → 10-30s 延迟问题 → 引出亮点 1（异步队列兜底）
- **推荐**：亮点 3 中的 LLM Adapter（Template Method + Factory，切换 Provider 只改环境变量）
- **可选**：亮点 2（验证管道保证输入数据质量）
- **弱化**：Terraform、Prometheus

## Phase 4: 输出简历草稿

### 格式要求

严格按照 `resume_principles.md` 中的规则输出：

1. **项目标题行**：项目名 + 一句话定位
2. **技术栈行**：根据目标岗位从 `project_highlights.md` 的 "Tech Stack Line by Target Role" 中选取对应版本，10-12 个关键词
3. **Bullet Points**：每条遵循以下规则——
   - 动词开头（Designed / Built / Implemented / Migrated / Achieved）
   - 结构：问题或背景 → 技术方案 → 量化结果
   - 量化数据从 `resume_principles.md` 第 6 节"可量化指标速查"中提取
   - 每条聚焦一个主题，不混搭
   - 技术栈不在 bullet 里重复（已在标题行列出）

### 输出模板

```
**CarePlan Generator — Automated Pharmaceutical Care Plan System**
[技术栈行，根据岗位方向选取]

• [Bullet 1: 动词开头 → 问题/背景 → 技术方案 → 量化结果]
• [Bullet 2: ...]
• [Bullet 3: ...]
• [Bullet 4（可选）: ...]
```

### 质量自检清单

输出前逐条检查：
- [ ] 每条是否以动词开头？
- [ ] 每条是否有至少一个量化数字？
- [ ] 是否避免了工具堆砌（技术名已在标题行）？
- [ ] 是否避免了"参与""协助"等被动表达？
- [ ] 4 条之间是否主题不重叠？
- [ ] 是否匹配用户选择的岗位方向？

## Phase 5: 面试深度预测与模拟（Bonus）

简历生成完毕后，根据用户选择的岗位方向，从 `resume_principles.md` 第 8 节"面试官高频追问方向"中提取对应问题，主动提醒用户：

---

> **面试官一看这段项目经历，为了验证是你本人做的，大概率会追问这些问题：**
>
> 1. [根据 Bullet 1 对应的追问]
> 2. [根据 Bullet 2 对应的追问]
> 3. [根据最硬核的那条 Bullet 追问一个 deep dive 问题]
>
> **👉 需要我扮演面试官模拟盘问你一下吗？（回答"是"开启追问模式）**

---

### 追问模式规则

如果用户回答"是"：
1. 每次只问一个问题，等用户回答后再追问
2. 追问深度逐层递进：What → Why → What if（如果换一种方案呢？）→ Trade-off
3. 用户回答不完整时，给出补充提示而不是直接给答案
4. 每轮追问结束后给出评分（Strong / Good / Needs Work）和改进建议
5. 支持中英文切换练习（用户可以说"英文模式"或"中文模式"）
