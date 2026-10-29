---
name: data-analysis-skill-builder
description: 基于 L0-L4 分层架构创建数据分析类 skill 的标准化脚手架与工作流。当用户要"固化"某个业务域的数据分析能力、新建数据查询/归因/建议类 skill、把重复的取数分析流程做成可复用技能，或提到 L0-L4 分层、原子方法编排、指标口径文档、数仓表结构文档、HTML+Chart.js 报告输出时使用。
version: 1.1.0
---

# 数据分析技能脚手架（data-analysis-skill-builder）

基于 L0-L4 分层架构，为任意业务域快速创建"数据查询 → 归因分析 → 可执行建议"类 skill 的标准化脚手架。

**核心方法论**：把业务问题翻译成「正确的表 + 正确的指标口径 + 正确的分析方法」，用确定性脚本执行，杜绝手写 SQL 的口径错误与数据幻觉。

## L0-L4 分层架构总览

| 层       | 产物文件                     | 作用                                | 变化频率 |
| ------- | ------------------------ | --------------------------------- | ---- |
| L0 数据层  | warehouse_schema.md      | 表清单、字段、枚举、关联键、查询前自检               | 低    |
| L1 指标层  | metrics_definitions.md   | 指标 ID、公式、口径、陷阱                    | 低    |
| L2 原子方法 | attribution_logic.md §L2 | 可复用分析模式 + 伪 SQL + 解读规则            | 中    |
| L3 场景配置 | attribution_logic.md §L3 | 场景 ID → 方法链映射                     | 高    |
| L4 决策树  | attribution_logic.md §L4 | 用户意图 → 场景路由                       | 中    |
| 输出层     | output_standards.md      | HTML 报告结构 + Chart.js + CSS + 表述铁律 | 低    |
| 主入口     | SKILL.md                 | 工作流、铁律、资源索引                       | 低    |

**设计原则**：稳定的东西沉到底层（表 L0、指标 L1、原子方法 L2），场景（L3）退化为「方法组合 + 参数」配置。新增业务场景时，优先复用 L2 原子方法、只在 L3 加一行配置。

详细编写规范见 [references/architecture-guide.md](references/architecture-guide.md)。填写示例见 [references/example-snippet.md](references/example-snippet.md)。旧版技能升级见 [references/migration-guide-v1.md](references/migration-guide-v1.md)。已有技能改造见 [references/refactor-strategy.md](references/refactor-strategy.md)。

## 五步创建工作流

### 第一步：需求澄清

用 AskUserQuestion 收敛范围，必问：

1. **业务域**：这个技能分析什么？（如换货、流量转化、库存周转）
2. **数据源**：用哪些库表？（项目名 + 表名，如果不确定先用 DISTINCT 探查）
3. **目标用户**：谁用？（运营/产品/分析师）
4. **分析场景**：要支持几种分析？（列出来，每个一句话）
5. **核心指标**：每个场景的核心指标是什么？
6. **建议类型**：最终给什么建议？（运营动作 / 产品优化 / 尺码表调整 …）

### 第二步：L0 数据层 + L1 指标层

1. **探查数仓**：用 `DESC`、`SHOW PARTITIONS`、`SELECT DISTINCT ... LIMIT` 探查真实表结构。
2. **产出 warehouse_schema.md**：从 [templates/warehouse\_schema.template.md](templates/warehouse_schema.template.md) 复制，填入：
   - 表总览（项目/层/粒度/规模/分区/更新时效/用途）
   - 每张表的字段说明 + 枚举值（含占比）
   - 表间关系（关联键 + 是否唯一）
   - 查询前自检清单（3-7 条硬规则）
3. **产出 metrics_definitions.md**：从 [templates/metrics\_definitions.template.md](templates/metrics_definitions.template.md) 复制，填入：
   - 指标速查表（ID/名称/公式/说明）
   - 按场景分节的核心维度 + 计算示例 SQL
   - 常见计算陷阱（≥ 3 条）

### 第三步：L2-L4 方法层 + 场景层 + 决策树

产出 attribution_logic.md：从 [templates/attribution\_logic.template.md](templates/attribution_logic.template.md) 复制，填入：

1. **L0 表清单 + 选表规则**：从 warehouse_schema.md 提炼表 ID 别名。
2. **L1 指标层**：指向 metrics_definitions.md，列出各场景核心指标 ID。
3. **L2 原子方法库**：通用方法（MTD-01~08）已在模板中，追加业务特有方法（MTD-09+）。每个方法必须包含 8 要素结构化格式：触发、适用表、参数、步骤、伪 SQL（用 T_ID 别名 + `${参数}` 占位）、输出、陷阱、特别提示。简单方法（如探查枚举）可省略部分要素，但复杂方法必须写全。
4. **L3 场景配置**：一张表格，每行一个场景，9 列覆盖完整配置（场景 ID / 名称 / 触发词 / 方法链 / 维度 / 指标 / 必需输入 / 固化查询 / 备注）。必需输入列声明该场景启动前必须从用户获取的数据（目标值/文件等），空 = 无需额外输入。固化查询列填写 FQ-XX 编号（指向 fixed_queries.md），未固化填 "—"。备注列为补充说明性质，非执行依赖。参数由 L2 方法定义，agent 执行时动态绑定，不在 L3 重复维护。新增场景可用 YAML 模板。
5. **L4 决策树**：前置校验步骤首先检查"必需输入"列，未提供则向用户索取；包含固化查询快捷路径（有 FQ-XX → 注入参数直接执行；无 → 走方法链编排），附带全局 Checklist（窗口等长、体量门槛、比率聚合规则、数据不足声明、建议可执行）。
6. **执行规则**：方法链执行时每步必过全局 Checklist，结论区分"统计显著"与"业务显著"，小样本不下强结论。

### 第四步：输出层标准

产出 output_standards.md：从 [templates/output\_standards.template.md](templates/output_standards.template.md) 复制，填入：

1. 交付五原则
2. HTML 报告结构（标题 → KPI → 数据说明 → 核心诊断 → 数据展示 → 建议 → 自查项 → 固化查询提示（条件显示）→ 免责声明）
3. CSS 样式规范（直接复用模板）
4. 图表选型与 Chart.js 配置（按本业务域常见场景）
5. 图表选型速查表
6. 配色方案
7. 表述铁律（禁止 vs 替代）
8. 优先级标签

### 第五步：组装与校验

1. **生成 SKILL.md**：从 [templates/SKILL.template.md](templates/SKILL.template.md) 复制，替换所有 `{{占位符}}`：
   - frontmatter（name / description / version）
   - 核心工作流（五步，与 L4 决策树对齐：解析意图 → 前置校验 → 执行路径选择 → 固化建议 → 证据校验）
   - 数据铁律（≥ 3 条，每条「怎么做」+「为什么」）
   - 表速查（精简，完整字段指向 warehouse_schema.md）
   - 资源索引（五个资源文件链接，含 fixed_queries.md）
   - 查询执行（引用 odps-query 技能）
   - 输出格式（七段式结构，含固化查询提示）
   - 严格约束
2. **确认外部依赖**：
   - 确保目标环境已安装 `odps-query` 技能（查询执行的外部依赖）
3. **结构完整性校验**：运行 `bash scripts/validate.sh <技能目录>` 或逐项核对 [references/architecture-guide.md](references/architecture-guide.md) 末尾的检查清单。
4. **回顾迭代**：校验发现问题时，按以下路径回溯修正，无需从头重来：
   - 占位符残留 → 回到对应层补充真实内容
   - L2 方法要素不全 → 回到第三步补全 8 要素
   - L3 场景缺列 → 回到第三步扩展表格
   - 指标口径重复 → 回到第二步统一收口到 metrics_definitions.md
   - 资源链接失效 → 检查文件路径和目录结构
   - 校验通过后，建议用一个真实业务问题做一次端到端试跑，验证 agent 能否正确走完 L4 决策路径

## 目录结构约定

```
<skill-name>/
├── SKILL.md                          # 主入口
└── resources/
    ├── warehouse_schema.md           # L0 数据层
    ├── metrics_definitions.md        # L1 指标层
    ├── attribution_logic.md          # L2-L4 方法+场景+决策树
    ├── fixed_queries.md              # 固化查询库（可选，已验证场景的参数化 SQL）
    └── output_standards.md           # 输出层
```

> **注意**：本架构不内置查询脚本，统一依赖公司提供的 `odps-query` 技能执行 SQL。凭证由 odps-query 管理，本技能无需配置。

## 质量校验清单

每次创建或大改技能后，逐项核对：

- [ ] SKILL.md frontmatter 完整（name/description/version）
- [ ] 数据铁律 ≥ 3 条，每条说清「怎么做」+「为什么」
- [ ] warehouse_schema.md 含查询前自检清单
- [ ] metrics_definitions.md 含常见计算陷阱
- [ ] attribution_logic.md 含 L0-L4 四层，L2 通用方法 ≥ 8 个（MTD-01~08，含漏斗转化模式）
- [ ] L2 每个复杂方法包含 8 要素（触发/适用表/参数/步骤/伪SQL/输出/陷阱/特别提示）
- [ ] L3 场景配置覆盖所有业务场景，9 列完整（ID/名称/触发词/方法链/维度/指标/必需输入/固化查询/备注），触发词含口语化表达
- [ ] 需要用户提供数据的场景已填写"必需输入"列（含格式要求）
- [ ] L4 决策树前置校验包含必需输入检查，包含固化查询快捷路径，附带全局 Checklist
- [ ] fixed_queries.md 中每个固化查询含验证日期、场景名称、参数说明表、${param} 占位（若已创建）
- [ ] fixed_queries.md 中的参数名与 L2 方法参数命名一致（若已创建）
- [ ] output_standards.md 含 HTML 骨架 + CSS + 图表选型 + 表述铁律
- [ ] SKILL.md 查询执行章节引用 odps-query 技能（非内置脚本，无硬编码路径）
- [ ] 所有 `{{占位符}}` 已替换为真实内容
- [ ] 口径唯一权威：同一指标只在 metrics_definitions.md 定义一次

## 从实战中总结的常见陷阱

这些是在真实迭代中踩过的坑，创建新技能时务必避免：

1. **口径漂移**：同一指标在 SKILL.md 和 metrics_definitions.md 各写一遍且公式不同 → 查询结果对不上。
2. **报告数据与查询不一致**：在旧报告上改数字，没重新跑查询 → KPI 卡片和图表数字矛盾。必须每次全量重建报告。
3. **时间范围 T-1 算错**：今天是 N 号，"近一周"应为 N-7 ~ N-1，不要写成 N-6 ~ N。用 `date` 命令取当前日期。
4. **全表扫描未开开关**：非分区表查询前未 `set odps.sql.allow.fullscan=true;` → 查询直接报错。
5. **关联键混淆**：如 `subsite_comm`（渠道表）vs `subsite_id`（埋点表），JOIN 时用了错误的键。
6. **组合品 NULL 值干扰**：分析某字段分布时，该字段仅子集有值（如组合品），未先过滤导致 NULL 占比失真。
7. **去重口径混用**：`COUNT(1)` 冒充 `COUNT(DISTINCT)`，或 order_no 和 service_order_no 混淆。
8. **比率分母未用 NULLIF**：分母为零时 SQL 报错或返回 NULL 被吞掉。
9. **凭假设写枚举值**：字段取值靠猜 → SQL 过滤条件错误。必须先用 MTD-07 探查。
10. **Chart.js 数据硬编码**：把上次查询结果写死在 JS 里，下次忘了更新 → 图表显示旧数据。
11. **报告未全量重建**：在旧 HTML 上改数字，KPI 卡片、图表、表格三处数据不一致。必须每次全量重建报告，用 `renderChart()` 包装函数，canvas 和 JS 调用配对。
12. **分区表与快照表混淆**：分区表用 `pt` 过滤、快照表用业务时间 SUBSTR 截取，搞混了要么报错要么扫全表。
13. **漏斗数据覆盖范围不明**：漏斗/埋点表可能仅部分版本/渠道有数据，与全量售后表直接对比会得出错误结论。必须在报告中标注数据覆盖范围。

## 参考现有范例

本架构来源于两个已验证的数据分析 skill，可直接参考其实现：

- **exchange-analysis-advisor**：换货分析，3 张表（2 快照 + 1 分区）/ 10 个场景 / 12 个原子方法
- **data-decision-advisor**：冷暖区数据分析，6 张表 / 11 个场景 / 8+ 个原子方法

## 严格约束

- **禁止幻觉**：模板中的字段名、表名、枚举值必须来自真实数仓探查结果，不可凭记忆填写。
- **口径唯一权威**：指标公式只在 metrics_definitions.md 定义一次。
- **只读查询**：所有 SQL 通过外部 `odps-query` 技能执行，该技能仅放行只读查询。
- **人在环路**：绝不建议自动执行任何写操作。
