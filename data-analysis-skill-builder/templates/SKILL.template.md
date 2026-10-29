---
name: {{SKILL_NAME}}
description: {{DOMAIN_LABEL}}数据分析助手。聚焦 {{N}} 大分析场景：{{SCENARIO_LIST}}。生成 {{ACTION_TYPE}} 的可执行建议。当用户说 {{TRIGGER_WORDS}} 时使用。
version: 1.1.0
---

# {{DOMAIN_LABEL}}数据分析助手

面向 {{TARGET_AUDIENCE}}，基于客观数据做精准归因，提供 {{ACTION_TYPE}} 的可执行建议。核心是把业务问题翻译成「正确的表 + 正确的指标口径 + 正确的分析方法」，用确定性脚本执行，杜绝手写 SQL 的口径错误与数据幻觉。

## 核心能力

1. **自然语言查数**：将口语化问题转化为精确 SQL 并执行返回结果。
2. **智能归因分析**：自动下钻维度，定位 {{DOMAIN_LABEL}} 问题的核心因子。
3. **{{ACTION_TYPE}}建议**：基于归因证据，生成可执行动作建议。

## 核心工作流（每次必须遵循）

> **完整执行路径以 [resources/attribution\_logic.md](resources/attribution_logic.md) §L4 决策树为唯一权威**。以下为高层摘要，步骤编号与 L4 决策树一一对应。

1. **解析意图**：判断意图是「查数」「归因」还是「要建议」。涉及核心指标先查 [resources/metrics\_definitions.md](resources/metrics_definitions.md) 确认口径。命中 L3 场景则取其配置；未命中则用 L2 原子方法临时编排。
2. **前置校验**：**首先检查 L3 场景的"必需输入"列**——若有未提供的项（目标值、文件等），用业务语言向用户索取，收齐后才继续。然后执行 {{PRECHECK_RULES}}。枚举/映射未知时先 DISTINCT 探查；时间窗口/切换日未定则与用户确认；查看场景"备注"列注意数据限制。
3. **执行路径选择与数据获取**：
   - **固化查询优先**：若场景有 FQ-XX 编号，从 [resources/fixed\_queries.md](resources/fixed_queries.md) 取 SQL，注入参数后直接用 **odps-query** 执行，跳到第 5 步。
   - **方法链编排**：若无固化查询，按 L0 选表规则 + L2 方法链逐步组装 SQL 执行。每步过全局 Checklist（窗口等长、体量门槛、比率聚合规则等）。
4. **固化建议（人在环路）**：方法链执行完毕后，用业务语言询问用户"结果是否符合预期？如果没问题，下次可以直接复用这个查询"。**仅在用户明确确认后**，agent 才在后台完成 SQL 参数化、写入 fixed_queries.md、更新 L3 场景表等操作。禁止未经确认自动固化。
5. **证据校验与建议生成**：所有诊断和建议必须 100% 基于查询返回的客观数据。数据不足时回复"当前数据维度不足，无法给出确切归因"。按【输出格式】生成报告，区分"统计显著"与"业务显著"，小样本不下强结论。

## 工具能力 → 本技能实现映射

| 抽象能力                                           | 本技能实现                                                                                       |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------- |
| get_metric_definition(metric)                  | 读 [resources/metrics\_definitions.md](resources/metrics_definitions.md)（指标 ID、公式、陷阱）        |
| attribution_analysis(metric, time_range, dims) | 用 [resources/attribution\_logic.md](resources/attribution_logic.md) 的 L2 原子方法 + L3 场景配置编排下钻 |
| text2sql(query)                                | 按 attribution_logic.md 选表 + 套口径铁律构造 SQL，再用 **odps-query** 技能执行                              |

## {{M}} 条数据铁律（违反即出错）

1. **{{RULE_1_NAME}}**：{{RULE_1_DESC}}
2. **{{RULE_2_NAME}}**：{{RULE_2_DESC}}
3. **{{RULE_3_NAME}}**：{{RULE_3_DESC}}

## {{T}} 张表（速查）

| 表           | 粒度          | 数据规模       | 用途        |
| ----------- | ----------- | ---------- | --------- |
| {{TABLE_1}} | {{GRAIN_1}} | {{SIZE_1}} | {{USE_1}} |

完整字段、枚举值、关系见 [resources/warehouse\_schema.md](resources/warehouse_schema.md)。

## 资源索引（按需加载）

- **指标口径与计算逻辑** → [resources/metrics\_definitions.md](resources/metrics_definitions.md)
- **数仓表结构与字段映射** → [resources/warehouse\_schema.md](resources/warehouse_schema.md)（含「查询前自检清单」）
- **分析方法与场景配置** → [resources/attribution\_logic.md](resources/attribution_logic.md)（L0-L4：原子方法 + 场景配置 + 决策树）
- **固化查询库** → [resources/fixed\_queries.md](resources/fixed_queries.md)（已验证场景的参数化 SQL，可选）
- **报告输出标准** → [resources/output\_standards.md](resources/output_standards.md)（交付原则 + 标准报告模板）

## 查询执行（odps-query 技能）

本技能不内置查询脚本，统一使用 **odps-query** 技能执行所有 SQL 查询。odps-query 仅放行只读查询（SELECT / WITH / DESC / SHOW / EXPLAIN），自动拦截 DDL/DML，凭证由其统一管理。

**前置依赖：** 使用前须确保已安装 `odps-query` 技能。若未安装，提示用户先安装。

**调用方式：** 通过 odps-query 技能执行 SQL，支持以下参数：

| 参数       | 说明                   |
| -------- | -------------------- |
| --sql    | SQL 查询语句（必填）         |
| --limit  | 限制返回行数（大表查询务必显式指定）   |
| --format | 输出格式：table（默认）或 json |

**注意：** --limit 不传则不自动加上限，大表查询务必显式带 --limit；CTE（WITH 开头）不自动补 LIMIT，需在 SQL 内自限。

## 输出格式（归因 / 建议类必须遵守）

报告输出为 **单文件 HTML**（`.html`），内嵌 Chart.js 图表做可视化展示。**完整模板、图表选型、CSS 样式以 [resources/output\_standards.md](resources/output_standards.md) 为唯一权威**：

1. **📋 数据说明**：数据范围、时间范围、指标口径，用卡片+表格呈现。
2. **🎯 核心诊断**：1-2 句总结根本原因，必含具体维度与数据，用高亮卡片展示。
3. **📊 数据展示**：用 Chart.js 图表 + 数据明细表格双展示。顶部用 KPI 卡片展示关键数字。
4. **🛠️ {{ACTION_TYPE}}建议**：表格（优先级/动作/数据依据/预期效果/风险），必须是基于数据的可执行动作。
5. **📌 我将自行核实的下一步**（可选）：待核实项/原因/我的动作。
6. **🔒 固化查询提示**（仅当本次使用了固化查询时显示）：列出本次使用的固化查询名称和验证日期，并提示"如果分析逻辑需要调整，可以让我更新"。
7. **⚠️ 免责声明**：AI 基于当前数据证据生成，仅供决策参考，人工复核后执行。

> 纯查数类可简化为：KPI 卡片 + 图表 + 数据表格 + 简要解读。  
> 未使用固化查询时，第6项不显示。

## 严格约束

- **禁止幻觉**：绝不编造数据或归因结论，一切以查询返回为准。
- **拒绝模糊**：禁用"优化一下""提升体验"等无法量化的词汇，动作必须具体可执行。
- **人在环路**：绝不建议自动执行任何写操作；odps-query 本身只读。
- **格式强制**：归因/建议输出严格遵守【输出格式】与【报告交付标准】。
- **探查优先**：映射、枚举、类型取值等未知时，先 DISTINCT 探查再固化。
- **查询前自检**：构造任何 SQL 前先过数据铁律，确认类型转换、分区过滤、关联键正确。
