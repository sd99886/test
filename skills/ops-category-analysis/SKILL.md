---
name: ops-category-analysis
description: 品类拆解与业绩归因章节分析 skill（经营分析报告第 4 章品类拆解 + 第 5 章业绩原因分析）：含取数查询流程、品类聚合口径、L2→L3 下钻、日趋势、增长-份额矩阵、三因子分解，产出飞书章节内容与交互式 HTML 分析报告。当用户要求「做品类分析/品类下钻/二级三级品类拆解/业绩归因/出第4章第5章」时使用。
---

# 品类拆解与业绩归因分析（ops-category-analysis）

撰写经营分析报告的**第 4 章（品类拆解）与第 5 章（业绩原因分析）**：
从 MaxCompute 取数 → 品类聚合 → 归因分析 → 图表 → 飞书章节内容 + 交互式 HTML 报告。

**与其他 skill 的分工**：本 skill 专做**品类与归因维度**（第 4/5 章）；
第 1/2/3/7 章（目标达成、新老品结构、口径附录）归 ops-weekly-report；
端到端全流程（含发布）归 ops-report-full。

---

## 0. 开工确认（每次都必须问，不许跳过）

**必须先问用户分析时间窗口，让用户自己给 start_date / end_date**：

> 「本次品类分析的窗口是哪两天？（例如 2026-10-01 ~ 2026-10-20）」

窗口语义与全流程一致：环比期=起止各回拨 1 个月（自动派生），同比期=回拨 1 年（自动派生）。
若用户只要单独看品类（不进报告），也建议确认是否输出 HTML 交互版。

---

## 1. 取数流程（依赖 odps-query skill，三步验收）

### 1.1 数据清单（本 skill 需要 4 个查询）

| SQL 模板 | 产出 CSV | 用途 | 规模 |
|---|---|---|---|
| `S2_品类拆解L2.sql.tpl` | S2_品类拆解L2.csv | 二级品类全指标（第 4 章主体） | 70 行 × 115 列 |
| `S2_品类拆解L3.sql.tpl` | S2_品类拆解L3.csv | 三级品类全指标（4.2 下钻） | 242 行 × 116 列 |
| `S2D_品类日趋势.sql.tpl` | S2D_品类日趋势.csv | 按日粒度销售/UV（4.3 趋势折线） | ≈1479 行 |
| `S3_新老品业务部门.sql.tpl` | S3_新老品业务部门.csv | 部门×新老品（5.2 结构分析） | 按部门 |

全部查询的口径锚点：**在线调整口径（is_online_adjustment=1），排除无库存测试款与赠品**。

### 1.2 生成日期已填充的 SQL

```bash
py -3 <skill>/scripts/render_sql.py --start <start_date> --end <end_date> \
    --sql-dir <skill>/sql --out-dir <workspace>/out/ops_<end_date去掉横线>
```

> 脱敏版模板的表 schema 是占位符，需额外传：`--schema <主数仓项目>`（{{PROJECT_SCHEMA}}）、
> `--cdm-schema <CDM 项目>`（{{CDM_SCHEMA}}，S2/S3 的 variant_combination 表用到）。

环比/同比/周边界全部自动派生（日号回拨自动夹到目标月最大天数），**不要手工算日期**。

### 1.3 执行（odps-query 正式取数）

每个 SQL 走 odps-query：`lint --sql-file` → `--sql-file ... --output xxx.csv` → `verify`，
三步退出码全 0 才算取数完成。行数校验：L2=70、L3=242（不含表头），漂移先核对口径。

**关键坑**：S2D 的 periods 非等值 JOIN 必须保留 `/* +MAPJOIN(b)*/` hint，否则跑不出来。

---

## 2. 品类聚合口径（写分析文字前的必读）

### 2.1 新老品过滤

品类聚合一律先过滤：`是否当月新品 ∈ {当月新品, 当月老品}`，**排除「当月未上架」行**
（S2/S2D 原始数据含未上架行，不过滤会虚低款效与均价）。

### 2.2 对比期还原

明细行的环比增长率列给出的是比率，对比期原始值由 `本期值 ÷ (1+增长率)` 还原；
增长率缺失或 ≤ -100% 按对比期=0。聚合层（大类/二级/三级）的环比 = 加总后重算，不是行环比的平均。

### 2.3 大类与二级品类的关系（易错）

泳衣/内睡/ACC 是**大类**，不在二级品类表里（AGG_SEC 查「泳衣」会 KeyError）——
取它们的环比要用降级函数 `sec_mom('泳衣')`（先查 AGG_SEC 再回落 AGG_BIG，脚本已内置）。

### 2.4 三因子分解（5.3 / 图5-4 的核心方法）

销售额 = 流量(UV) × 转化(CVR) × 价格(P)，**序贯替代法**拆贡献：

```
c_uv  = (UV₁ - UV₀) × CVR₀ × P₀      # UV 变化的贡献
c_cvr = UV₁ × (CVR₁ - CVR₀) × P₀     # CVR 变化的贡献
c_p   = UV₁ × CVR₁ × (P₁ - P₀)       # 价格变化的贡献
c_uv + c_cvr + c_p = 销售额₁ - 销售额₀ （可验证）
```

比率类指标（CVR/CTR/均价）在聚合层由基础量重算，不用比率平均。

---

## 3. 分析产出（两条线）

### 3.1 交互式 HTML 报告（gen_l2l3_analysis.py，预览/深挖用）

```bash
cd <workspace>/feishu_api
py -3 gen_l2l3_analysis.py --start <start_date> --end <end_date> --out out/ops_<...>
```

单文件 HTML + Chart.js（CDN），11 张交互图，覆盖六类分析：
整体概览（大类结构）、下钻（L1→L2→L3）、趋势（按日折线，本期 vs 环比期）、
对比、同环比（增长-份额矩阵：x=销售额占比、y=环比增速）、交叉（品类×新老品、三因子分解）。
产出 `l2l3_analysis_report.html`，本地 `python -m http.server` 起服务给用户预览。

### 3.2 飞书章节内容（gen_report_json.py 的第 4/5 章）

```bash
py -3 gen_report_json.py --start <start_date> --end <end_date> \
    --out out/ops_<...> --sections 45
```

`--sections 45` 只输出第 4/5 章（其余章节数据计算照常执行，仅不进内容序列），
用于把品类章节并入完整报告前的单独预览。第 4 章结构：

| 小节 | 内容 | 图 |
|---|---|---|
| 4.1 品类结构总览 | 大类占比/环比/同比、正负贡献、结构迁移 | 图4-1 环形、图4-2 分组柱状 |
| 4.2 品类下钻 L2→L3 | Top12（环比着色）、增量 Top8、缩减 Top8 | 图4-3/4-4/4-5 水平柱状 |
| 4.3 品类按日趋势 | 日均对比、单日峰值 | 图4-6 双折线 |
| 4.4 增长-份额矩阵 | 明星/现金牛/风险/疑问四象限解读 | 图4-7 散点 |

第 5 章结构：5.1 总览结论 → 5.2 部门与新老品结构（用 S3）→ 5.3 效率因素（三因子+转化链路+库存退货）→
5.4 可视化（图5-1 部门达成率、图5-2 新老品结构、图5-3 新老品同比、图5-4 三因子按大类）。

**章节分工红线**：第 4 章=纯品类维度；第 5 章=部门及部门×品类。跨章引用（如 5.1 引「详见第 4 章」）时
注意目标章节是否存在（--sections 裁剪后引用可能落空）。

### 3.3 叙述性数字的边界（重要）

窗口派生文字自动更新，但**分析结论里的数据性叙述数字**（如「比基尼套装缺口约 70 万美元」）
与 2026-10 窗口绑定——换窗口必须先跑脚本拿新聚合，再逐段重写结论文字与第 6 章依赖的依据。

---

## 4. 图表规范

- matplotlib 静态图（飞书只能放图片），dpi=150，中文字体 Microsoft YaHei，负值红色 / 正值蓝色；
- 水平柱状图：数值标注在柱端，figsize=(10, 0.42×条数+1.8)；
- 增长-份额矩阵标注策略：仅 `x≥3%` 或 `|y|≥30%` 的点标品类名，避免过密；
- 表格超飞书上限（约 100 列）一律转图片（render_table_image 已内置）。

## 已知限制与陷阱

| 陷阱 | 规避 |
|---|---|
| AGG_SEC['泳衣'] KeyError | 泳衣是大类，用 sec_mom() |
| 未上架款虚低指标 | 聚合前过滤「是否当月新品」 |
| S2D 无 MAPJOIN hint 跑不出 | 保留 `/* +MAPJOIN(b)*/` |
| 增长率缺失行的对比期 | 按 0 处理（口径声明已注明涉及行数） |
| Windows GBK 终端打印 | sys.stdout 包 TextIOWrapper(encoding='gbk') |
| HTML 中文/emoji 打印失败 | 同上，errors='replace' |

## 部署（首次使用）

1. `scripts/*.py` 拷到 `<workspace>/feishu_api/`；
2. `pip install matplotlib`（HTML 版只需标准库+模板）；
3. workspace 根非 `<workspace根目录>` 时改脚本头部 BASE；
4. odps-query skill 已初始化。

## 文件清单

```
ops-category-analysis/
├── SKILL.md                  # 本文件
├── requirements.txt
├── scripts/
│   ├── render_sql.py         # SQL 模板日期填充
│   ├── gen_report_json.py    # 飞书章节内容生成（--sections 45 取第4/5章）
│   └── gen_l2l3_analysis.py  # 交互式 HTML 品类分析报告
└── sql/
    ├── S2_品类拆解L2.sql.tpl
    ├── S2_品类拆解L3.sql.tpl
    ├── S2D_品类日趋势.sql.tpl
    └── S3_新老品业务部门.sql.tpl
```
