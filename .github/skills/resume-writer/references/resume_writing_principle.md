# 简历编写原则（全栈 / 后端工程师方向）

## 1. 项目描述四段式结构

遵循"背景 → 目标 → 过程 → 结果"逻辑：

- **背景**：项目所属业务场景、用户痛点、系统定位。例：*本项目为 CVS 药房构建自动化 Care Plan 生成系统，药剂师手动编写一份 Care Plan 需 20-40 分钟，系统通过 LLM 集成将其自动化，服务于药房日常运营流程。*
- **目标**：技术目标或架构改进方向（解耦、可扩展、高可用、部署自动化等）。例：*设计事件驱动的异步架构解决 LLM 调用阻塞问题，实现多数据源适配和一键云部署。*
- **过程**：关键技术方案和工程实现细节，明确候选人负责部分、架构决策、面临挑战。例：*独立设计分层架构，实现消息队列异步处理、3 层输入验证管道、Adapter Pattern 多源适配，并完成从本地 Docker 到 AWS Serverless 的完整迁移。*
- **结果**：量化数据展示最终效果。例：*用户提交响应时间从 30s 降至 <1s，支持 50+ 并发提交，83 个测试用例覆盖 81% 代码，Terraform 一键管理 10+ AWS 资源。*

## 2. 技术标签维度

简历需显式体现与岗位匹配度较高的技术要素，覆盖以下维度：

| 维度            | 关键词示例                                                               |
| --------------- | ------------------------------------------------------------------------ |
| 后端框架        | Python, Django, Django REST Framework, Flask, FastAPI, Spring Boot       |
| 前端框架        | React, JavaScript, Axios, Polling, Component State Management            |
| 数据库          | PostgreSQL, MySQL, ORM, Migration, Foreign Key, Normalization, Index     |
| 异步 / 消息队列 | Redis, Celery, SQS, RabbitMQ, Kafka, Async Worker, Event-Driven          |
| API 设计        | RESTful API, HTTP Status Codes (201/202/409), Serializer, Validation     |
| 设计模式        | Adapter Pattern, Template Method, Factory, Layered Architecture, SOLID   |
| 云服务          | AWS Lambda, API Gateway, SQS, RDS, IAM, VPC, Security Groups, CloudWatch |
| 基础设施        | Terraform, Docker, Docker Compose, Infrastructure as Code                |
| 监控            | Prometheus, Grafana, Metrics, Alerting                                   |
| 测试            | Unit Test, Integration Test, Test Coverage, Mock, Fixture                |
| LLM 集成        | Gemini API, Prompt Engineering, Error Handling, Retry Logic              |

这些关键词既可作为项目描述中的术语，也可在"技术栈"部分单独列出，便于 ATS 系统和招聘者快速识别。

## 3. 亮点挖掘与差异化策略

面试官关注候选人主导了什么、有哪些独到之处、是否体现技术判断力：

1. **介绍决策过程**：说明选择某方案的原因，对比过哪些方案，最终决策背后的技术判断。例：*为什么选 Polling 而不是 WebSocket？因为项目规模下 Polling 实现简单且满足需求，WebSocket 引入连接管理复杂度不值得。*
2. **展示问题解决能力**：描述遇到的技术难点与解决方法。例：*Mac ARM 打包的 psycopg2 在 Lambda x86 环境报错，通过 Docker --platform linux/amd64 交叉编译解决。*
3. **强调可复用性 / 通用性**：项目中具有通用价值的架构设计作为重点亮点。例：*Platform-agnostic service layer 让同一份业务逻辑同时服务 Django 和 Lambda，新增部署目标只需写入口层适配。*
4. **突出结果与影响力**：用量化指标体现项目价值。例：*83 个测试用例，81% 覆盖率；4 种数据源零代码修改接入；Terraform 管理 10+ AWS 资源一键部署/销毁。*

## 4. 常见误区

| 误区               | 说明                                       | 本项目中的反面教材                                                                          |
| ------------------ | ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| 大而空             | 不要用"负责后端开发""参与云部署"等泛化描述 | ❌ "负责系统后端开发和 AWS 部署"                                                             |
| 工具堆砌           | 仅列工具名而不解释实际作用与价值           | ❌ "使用了 Redis, Celery, SQS, Lambda, Terraform"                                            |
| 缺乏结果           | 没有量化指标的项目难以评估价值             | ❌ "实现了异步处理，提升了性能"                                                              |
| 逻辑混乱           | 过程描述过长但缺乏主线                     | ❌ 一条 bullet 里同时讲验证、部署、监控                                                      |
| 只讲 What 不讲 Why | 面试官更关心你为什么这么选                 | ❌ "使用了 Adapter Pattern" → ✅ "为适配 4 种异构数据源，应用 Adapter Pattern 实现零修改扩展" |

## 5. 改进建议

- 多用"**Designed**""**Built**""**Implemented**""**Migrated**""**Achieved**"等主动动词开头，少用 "participated""assisted"
- 按"问题/背景 → 技术方案 → 量化结果"结构描述每条 bullet
- 每条 bullet 聚焦一个主题：架构、验证、扩展性、部署各占一条
- 量化一切可量化的内容（并发数、响应时间、测试数、覆盖率、资源数、数据源数...）
- 技术栈集中放在项目标题下方一行，bullet points 里不重复罗列工具名

## 6. 本项目可量化指标速查

| 指标                     | 数值                                                    | 来源                    |
| ------------------------ | ------------------------------------------------------- | ----------------------- |
| LLM 单次调用耗时         | 10-30s                                                  | Gemini API 实测         |
| 异步化后用户感知响应时间 | <1s (202 Accepted)                                      | 架构设计                |
| 预估并发支持             | 50+ simultaneous requests                               | 50 users × ~17 QPS 推算 |
| 输入验证层数             | 3 层 (serializer → service → exception handler)         | Day 8 实现              |
| 重复检测规则数           | 6 条 (Provider 1 + Patient 2 + Order 3)                 | Day 8 实现              |
| 支持数据源数             | 4 种 (web form, JSON, XML, pipe-delimited)              | Day 9-10 实现           |
| 新数据源接入成本         | 1 个 adapter class, 0 行已有代码修改                    | Open-Closed Principle   |
| 测试用例总数             | 83 (unit + integration)                                 | Day 8-9 实现            |
| 代码覆盖率               | 81%                                                     | Django test coverage    |
| Adapter 专项测试数       | 45                                                      | Day 9 实现              |
| AWS 资源数               | 10+ (Lambda ×3, API Gateway, SQS ×2, RDS, IAM, VPC, SG) | Day 13-15               |
| DLQ 重试次数             | 3 次后转移                                              | Day 14 配置             |
| Terraform 管理资源       | 一键 apply / destroy                                    | Day 15 实现             |
| DB 表数                  | 4 (Patient, Provider, Order, CarePlan)                  | Day 3 设计              |

## 7. 按目标岗位调整侧重点

| 目标岗位    | 重点突出                                        | 可弱化             |
| ----------- | ----------------------------------------------- | ------------------ |
| 后端 SWE    | 分层架构、异步处理、验证管道、测试覆盖          | 前端 React         |
| 全栈 SWE    | 端到端数据流（前端→API→队列→Worker→DB→Polling） | Terraform 细节     |
| 云 / DevOps | AWS 架构、Terraform IaC、DLQ、监控              | 设计模式、验证逻辑 |
| 大模型应用  | LLM 集成、Prompt 工程、异步调用、错误处理       | Adapter Pattern    |

## 8. 面试官高频追问方向（提前准备）

| Bullet Point    | 可能追问                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------- |
| 异步架构        | 为什么选 Polling 不选 WebSocket？Redis vs RabbitMQ vs Kafka 怎么选？202 vs 200 的语义区别？ |
| 验证管道        | 为什么验证拆两层？为什么自定义异常而不用 DRF 内置的？ERROR vs WARNING 的业务含义？          |
| Adapter Pattern | 为什么用 dataclass 不用 dict？base class validate vs 子类各自验证的取舍？何时算过度设计？   |
| 云部署          | Lambda vs EC2 的决策依据？Mac ARM → Lambda x86 的打包问题？Terraform 销毁顺序为什么重要？   |
