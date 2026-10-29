# skill_sql_catalog（月度经营分析 · 数据能力登记表）

> 用途：登记月度经营分析 Skill 的只读原始脚本与派生脚本，供下次同类需求直接复用。
> 硬约束：原始脚本 readonly=true，禁止任何修改；派生逻辑一律写入新文件。

## 原始脚本（readonly=true）

| 代号 | 文件 | 用途 | 参数 |
|------|------|------|------|
| S1 | monthly-ops-analysis/skills/monthly-ops-analysis/data/skill数据集1-目标达成情况数据.txt | 目标 vs 实际、达成率（月度口径，12 部门宽表） | ${输入月份格式为yyyy-mm} |
| S2 | monthly-ops-analysis/skills/monthly-ops-analysis/data/skill数据集2-品类拆解数据.txt | 品类拆解（是否当年新品×是否当月新品×大类×二级品类；三级维度被注释） | ${输入start_date，格式为yyyy-mm-dd}、${输入end_date，格式为yyyy-mm-dd}（各 2 处） |
| S3 | monthly-ops-analysis/skills/monthly-ops-analysis/data/skill数据集3-新老品业务部门.txt | 新老品 × 业务部门（仅保留泳衣两部 + 成衣两部） | 同 S2（各 2 处） |

## 派生脚本（generated=true）

| id | file | based_on | purpose | params | covers_report_slots | status |
|----|------|----------|---------|--------|---------------------|--------|
| G001 | generated_sql/S2__l3__generated.sql | S2 | 三级品类拆解（恢复被注释的 third_category 维度，其余口径/过滤/指标与 S2 完全一致） | start_date,end_date | §4表B, §5图4 | stable |

## 执行记录

- 2026-10-21：G001 首次跑通（参数 2026-10-01 ~ 2026-10-20，242 行，结果自检 exit=0），用于报告《经营分析报告2026-10-21》（out/ops_20261021/）。参数代入副本与查询产物存于 generated_sql/run_20261021_20261020/ 与 out/ops_20261021/。
- 下次运行：G001 与 S1/S2/S3 一并纳入标准执行清单；同一 purpose 已有 stable 文件，禁止重复生成。
