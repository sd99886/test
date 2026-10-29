# monthly-ops-analysis（月度经营分析）

Qoder 原生插件：把本地 Skill 包「LLM生成报告Skill」转换为可安装、可分发的 Qoder 插件。用户触发「月度经营分析」后，助手自学 3 个只读 MaxCompute SQL 脚本，经 `odps-query` 取数，按**固定 7 章大纲**产出含图表的经营分析报告（Markdown）；缺数时新建派生 SQL 并自动固化进 `skill_sql_catalog.md`，下次直接复用。

## 来源（Provenance）

- 源：本地压缩包 `c:\Users\Cupshe\Desktop\LLM生成报告Skill.zip`（解压目录 `c:\Users\Cupshe\Desktop\test\llm_report_skill_extract\LLM生成报告Skill\`）
- 源文件：
  - `monthly_ops_analysis_skill_prompt.md` —— 主提示词，已适配为 `skills/monthly-ops-analysis/SKILL.md`
  - `skill数据集1-目标达成情况数据.txt`（S1）、`skill数据集2-品类拆解数据.txt`（S2）、`skill数据集3-新老品业务部门.txt`（S3）—— 只读原始 SQL 脚本
  - `经营分析报告skill.xmind` —— 原始思维导图
- Logo：本插件自带生成的 `assets/avatar.svg`，非源文件内容。

## 包含内容

| 文件 | 说明 |
|------|------|
| `skills/monthly-ops-analysis/SKILL.md` | 主技能（由源提示词适配：数据脚本路径改为插件内 `data/` 相对路径；派生 SQL/catalog 明确存放在当前工作目录；其余流程、约束、大纲、句式逐字保留） |
| `skills/monthly-ops-analysis/data/skill数据集1-目标达成情况数据.txt` | S1 原始脚本（MD5 校验与源一致，未做任何修改） |
| `skills/monthly-ops-analysis/data/skill数据集2-品类拆解数据.txt` | S2 原始脚本（MD5 校验与源一致，未做任何修改） |
| `skills/monthly-ops-analysis/data/skill数据集3-新老品业务部门.txt` | S3 原始脚本（MD5 校验与源一致，未做任何修改） |
| `assets/avatar.svg` | 插件 Logo |
| `.qoder-plugin/plugin.json` | Qoder 插件清单 |

## 省略文件及原因

- `经营分析报告skill.xmind`：源提示词 §8 已对其结构做了 6 条明确「纠偏」（基础是 3 个脚本而非「两个结果」、禁止改原始查询、策略章不得复述原因等），保留旧思维导图可能误导模型按旧结构生成报告。如需查阅，请从原始 zip 获取。

## 使用前提（Setup Notes）

1. **odps-query**：报告取数依赖环境中可用的 `odps-query` 技能（MaxCompute/ODPS 只读查询）。缺少它时本 Skill 只能出框架、无法填数。
2. **参数**：运行时需提供 `start_date`、`end_date`（`yyyy-mm-dd`，参数值不带引号）；若原始脚本另有必填参数会逐项询问。
3. **运行时产物**：派生 SQL（`./generated_sql/*__generated.sql`）与登记表 `skill_sql_catalog.md` 在**当前工作目录**创建，属运行时状态，不随插件分发；原始脚本永不被修改。
4. **飞书写入**：源流程中「写入飞书云文档」暂不执行（权限未就绪），先产出完整 Markdown 报告。

## 校验

- 离线校验：`validate_qoder_plugin.py` 通过（见插件根目录验证记录）。
- 数据脚本完整性：三个 `.txt` 与源文件 MD5 逐一比对一致。
