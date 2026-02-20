# Day 3: Database Design Thinking

## 核心思考：从 Excel 到 数据库
如果不使用数据库设计思维，所有数据都在一张大表里（类似 Excel），会导致：
1. **数据冗余**：张三来了 10 次，名字、生日、手机号就要存 10 次。
2. **修改困难**：张三改名了，要改 10 行数据，一旦漏改就会数据不一致。

## 数据库设计五大要点

### 1. 唯一性（Primary Key - PK）
每行数据必须有一个**独一无二的身份证号**。
- **原则**：不要用自然语言（如同名同姓）做主键，要用系统 ID。
- **例子**：
  - 病人 → `MRN` (Medical Record Number)
  - 医生 → `NPI` (National Provider Identifier)
  - 订单 → `Order ID` (系统生成的流水号)

### 2. 消除冗余（Normalization - 范式化）
同一类信息只在一个地方存储。
- **原则**：**Entity Separation（实体分离）**。
- **方法**：拆表。
  - **错误**：在每个订单里重复写病人的姓名、生日、手机号。
  - **正确**：建立 `Patient` 表，只存一遍。订单表里只存 `Patient ID`。

### 3. 连接与引用（Foreign Key - FK）
用 ID 把不同的表关联起来，而不是复制数据。
- **原则**：**Reference by ID（通过 ID 引用）**。
- **类型**：
  - **1:N (一对多)**：一个病人有多个订单 (`Order` 表里有一个 `patient_id` 字段)。
  - **N:N (多对多)**：一个处方里有多个药，一个药可以被开给很多人 (需要中间表 `OrderMedication`)。

### 4. 历史快照（Snapshot vs. Reference）
**特例**：有时候为了保留历史现场，**适当的冗余是必要的**。
- **原则**：**Immutable History（不可变历史）**。
- **场景**：
  - **医疗/电商**：病人改名了，或者商品涨价了。
  - **决策**：虽然有 Patient 表，但在 Order 表里可能仍需要**复制**一份当时的 `patient_name`。因为两年前的处方单上应该是旧名字，不能因为现在改名了，历史记录也跟着变。
  - **结论**：我们的 MVP 目前使用这种“快照”模式（所有信息存 Order 表），在医疗场景下是有一定合理性的。

### 5. 扩展性（Scalability）
- **原则**：**Type Safety（类型安全）**。
- **例子**：
  - `medication` 字段：现在是字符串 "Aspirin"。未来如果是 ID `1001` 指向 `Medication` 表，就能做库存扣减、药物相互作用检查。

---

## Django + Docker 数据库开发流程 (4步走)

1.  **Docker (Infra)**: 给房子打地基，接水电 (创建数据库服务 `careplan_db`)。
2.  **Settings (Connection)**: 给房子把钥匙拿来 (告诉 Django 用什么账号密码去连这个库)。
3.  **Models (Design)**: 你的设计图纸 (决定要有几个房间，每个房间多大，放什么家具)。
4.  **Migrations (Build)**: 施工队进场 (把你的设计图纸变成真正的砖墙，也就是 `CREATE TABLE`)。

---

## 调试 (Debug) 技巧小结
- **F10 (Step Over)**: 跳过细节，执行下一行。
- **F11 (Step Into)**: 不仅下一行，还要进到函数里面去。
- **Shift+F11 (Step Out)**: 误入框架源码时，赶紧跳出来，回到上一层。
- **F5 (Continue)**: 直接飞奔到下一个断点。