---
name: ops-report-full
description: 经营分析报告全流程 skill：从确认时间窗口与归因需求，到 MaxCompute 取数、生成七章飞书文档报告、发布与校验的端到端流程。当用户要求「出经营分析报告/月报/经营周报（含归因与策略）」「把经营数据整理成飞书报告并发布」时使用。
---

# 经营分析报告全流程（ops-report-full）

把「问窗口 → 问归因 → 取数 → 生成 → 预览确认 → 发布 → 校验」固化为可复跑的端到端流程。
产出：飞书文档《经营分析报告<日期>》+（含第 4 章时）随附电子表格《品类拆解全量明细》。

**读者是 agent**：所有命令由 agent 执行，不要指挥用户敲命令；只在必须由人决策的点提问（见第 0 步）。

---

## 0. 两个必做的开工确认（每次都必须问，不许跳过、不许自己默认）

### 0.1 确认分析时间窗口（start_date / end_date）

**流程一开始就必须问用户**，让用户自己给出起止日期，agent 不得擅自决定。

> 示例提问：「本期报告的分析窗口是哪两天？（例如 2026-10-01 ~ 2026-10-20）」

窗口语义（后续所有步骤共用，务必向用户复述确认）：

| 参数 | 含义 |
|---|---|
| start_date | 分析窗口起始日（如 2026-10-01） |
| end_date | 分析窗口截止日（如 2026-10-20），也是「时间进度」的分母分子来源 |
| 环比期 | start/end 起止各回拨 1 个月（如 2026-09-01~09-20），由脚本自动派生 |
| 同比期 | start/end 起止各回拨 1 年（如 2025-10-01~10-20），由脚本自动派生 |
| 第 2 章月度口径 | end_date 所在月（YYYY-MM，如 2026-10），当月 1 日累计 |

### 0.2 确认是否需要归因分析及策略建议

**问完窗口后必须问的第二个问题**：

> 示例提问：「报告是否需要归因分析与策略建议（第 4 章品类拆解、第 5 章业绩原因分析、第 6 章改善策略）？」
> - **需要** → 输出全文七章（1 分析说明 / 2 目标达成 / 3 新老品结构 / 4 品类拆解 / 5 业绩原因 / 6 改善策略 / 7 口径附录），并发布随附电子表格
> - **不需要** → 仅输出第 1/2/3/7 章（`--sections 1237`），跳过电子表格

用户的回答直接决定后面取数范围（第 1 步）与生成参数（第 2 步），两个答案在开工前都要拿到。

---

## 1. 取数（依赖 odps-query skill）

取数一律通过 **odps-query** skill 执行（lint → 执行 → verify 三步验收），本 skill 不直连数仓。
数据源表：`{{PROJECT_SCHEMA}}.ads_prod_skc_product_info_di`（在线调整口径）等。

### 1.1 生成日期已填充的 SQL

SQL 模板在本 skill 的 `sql/` 目录（占位符说明见模板头注释）。用 render_sql.py 填充：

```bash
py -3 <skill>/scripts/render_sql.py --start <start_date> --end <end_date> \
    --sql-dir <skill>/sql --out-dir <workspace>/out/ops_<end_date去掉横线>
```

> 脱敏版模板的表 schema 是占位符，需额外传：`--schema <主数仓项目>`（{{PROJECT_SCHEMA}}，ADS 层）、
> `--cdm-schema <CDM 项目>`（{{CDM_SCHEMA}}）、`--ads-dev-schema <ADS 开发项目>`（{{ADS_DEV_SCHEMA}}，仅 S1 用到）。

render_sql.py 自动派生：环比期（回拨 1 个月）、同比期（回拨 1 年）、月串（YYYY-MM）、
END 所在自然周与上一周（供 S1W 周度上新）。日号回拨自动夹到目标月最大天数（如 03-31→02-28）。

### 1.2 按报告范围执行查询

| SQL（模板） | 产出 CSV | 服务章节 | 何时执行 |
|---|---|---|---|
| S1_目标达成.sql | S1_目标达成.csv | 第 2 章表2-1 | 总是 |
| S1W_周度上新.sql | S1W_周度上新.csv | 2.4 上新数 | 总是 |
| S3_新老品业务部门.sql | S3_新老品业务部门.csv | 第 3 章表3-1/3-2 | 总是 |
| S2_品类拆解L2.sql | S2_品类拆解L2.csv | 第 4 章（70 行 × 115 列） | 仅需归因时 |
| S2_品类拆解L3.sql | S2_品类拆解L3.csv | 第 4 章（242 行 × 116 列） | 仅需归因时 |
| S2D_品类日趋势.sql | S2D_品类日趋势.csv | 4.3 日趋势折线 | 仅需归因时 |

（S1V_上线口径验证.sql 为 2.4 口径核对辅助，数字对不上时才需要。）

每个 SQL 走 odps-query 正式取数（`--sql-file ... --output <out>/Xxx.csv`），verify 退出码 0 才算完成。

**已知坑**：S2D 的 periods 非等值 JOIN 必须保留 `/* +MAPJOIN(b)*/` hint，删掉会跑不出来。

### 1.3 数据行数校验（生成前的硬门槛）

CSV 落盘后核对行数（不含表头）：S1W=5 行（本周/上周/本月累计/上月同期/去年同期）、
S2_L2=70、S2_L3=242、S3 按部门数。行数漂移说明口径变化，先停下核对再继续。

---

## 2. 生成报告（gen_report_json.py）

```bash
cd <workspace>/feishu_api
py -3 gen_report_json.py --start <start_date> --end <end_date> \
    --out out/ops_<end_date去掉横线> \
    --sections <1234567 或 1237> \
    --title "经营分析报告<发布日期>"
```

参数与行为：

| 参数 | 说明 |
|---|---|
| `--start/--end` | 分析窗口（与取数一致） |
| `--out` | 数据目录（CSV 所在），相对路径相对 workspace 根 |
| `--sections` | **归因开关**：`1234567`=全文七章；`1237`=无归因（仅 1/2/3/7 章，第 4/5/6 章连同电子表格链接整体剔除） |
| `--title` | 报告标题（默认「经营分析报告<今天>」） |

产出：
- `feishu_report.json`（content 块序列 + detail_sheets + include_sheets 标志 + meta）
- `feishu_report_preview.txt`（**给用户预览用的全文文本**）
- `charts/*.png`（matplotlib 静态图，dpi=150，中文字体 Microsoft YaHei）

### 叙述性数字的边界（重要）

窗口派生文字（时间窗、环比/同比期区间、时间进度、月度口径声明）会**自动**随 --start/--end 更新；
但第 3~6 章段落里写死的数据性叙述数字（如「新品销售额 46.67 万元」「环比 -44.62%」「比基尼套装缺口约 70 万美元」）
与 **2026-10 窗口的数据绑定**。换窗口运行时必须：
1. 先跑一遍拿到新数据（gen_report_json.py 会打印关键聚合）；
2. 对照新 CSV/聚合结果**逐段更新**这些叙述数字与结论文字；
3. 第 6 章策略表（P0/P1/P2）的业务结论同样要按新数据重写。

这是本 skill 当前最重要的手工环节，跳过会产出旧数据的新报告。

---

## 3. 本地预览与用户确认（发布前必经）

1. 把 `feishu_report_preview.txt` 的关键内容（章节结构 + 每章首段 + 图表清单）呈给用户；
2. 需要图形预览时用 `python -m http.server` 起本地服务展示 `l2l3_analysis_report.html`（第 4/5 章交互版）；
3. **用户确认后才进入第 4 步发布**。用户提修改意见时改 gen_report_json.py 对应段落再重新生成，重新预览。

## 4. 发布（publish_report.py）

```bash
cd <workspace>/feishu_api
py -3 publish_report.py --report-json out/ops_<...>/feishu_report.json [--reuse-sheet <token>]
```

行为（按报告内容自动分支）：
- **含第 4 章**：处理电子表格（复用 `--reuse-sheet` 指定的表，或传空串用应用身份新建：
  应用即 owner（等价自动「添加文档应用」），再把授权用户加为协作者，并把链接分享设为
  「组织内获得链接的人可阅读」），文档第 4 章末尾的电子表格链接自动指向它；
- **不含第 4 章**（--sections 1237）：完全跳过电子表格；
- 文档块写入：标题/文本/图片（三步法上传）/链接分批追加，descendant API 建表格图片。

首次运行（或 token 过期）会弹浏览器 OAuth 授权（回调 `http://localhost:8899/callback`），让用户点击授权即可。

## 5. 发布后校验（verify_and_cleanup.py）

```bash
cd <workspace>/feishu_api
py -3 verify_and_cleanup.py  # 默认校验脚本头部 DOC 指向的文档
```

核对：块数量与预期一致（标题/文本/图片/链接计数）、关键内容关键字抽查。
**校验通过后**把 verify_and_cleanup.py 与 read_doc_comments.py 头部的默认 DOC 改为新文档 id（脚本里各有一处）。

## 6. 评论修订循环（可选）

用户在飞书文档上打评论后：`py -3 read_doc_comments.py` 拉取全部评论及回复 →
逐条落实 → 修改 gen_report_json.py → 重新生成 → 重新发布（新文档）→ 删除旧文档。

---

## 口径速查（写报告文字时必须遵守）

- **双口径**：第 2 章=月度口径（当月 1 日累计，进度基准=时间进度=end_day/当月天数）；
  第 3~6 章=窗口口径（start~end），环比=起止各回拨 1 个月，同比=回拨 1 年。两套数字不可混用。
- **汇总**：整体/大类/品类/新老品汇总=明细行加总；对比期原始值=`本期值 ÷ (1+增长率)` 还原，
  增长率缺失或 ≤ -100% 按对比期=0。
- **品类聚合**（第 4 章）：过滤「是否当月新品 ∈ {当月新品, 当月老品}」（排除未上架款）。
- **三因子分解**（5.3/图5-4）：销售额=UV×CVR×价格，序贯替代法：
  `c_uv=(UV₁-UV₀)×CVR₀×P₀；c_cvr=UV₁×(CVR₁-CVR₀)×P₀；c_p=UV₁×CVR₁×(P₁-P₀)`。
- **单位**：金额美元，段落中「万元」=美元/10000。

## 已知限制与陷阱

| 陷阱 | 说明 / 规避 |
|---|---|
| 飞书文档原生表格上限 | 约 100 列/表、descendant 单次约 1000 块；大表一律 render_table_image 转图片（脚本已内置） |
| 图片三步法 | 建空 image block → medias/upload_all → PATCH replace_image（脚本已内置，勿改） |
| Windows GBK 终端 | 打印中文/emoji 前包 `io.TextIOWrapper(sys.stdout.buffer, encoding='gbk', errors='replace')` |
| 泳衣是大类不是二级品类 | 取二级品类环比用 `sec_mom('泳衣')`（脚本已处理），直接查 AGG_SEC 会 KeyError |
| OAuth scope | user token 缺 drive 系 scope 时，权限设置走应用身份降级（publish_report.py 已内置双通道） |
| 电子表格 owner | 用户身份建的表，应用非协作者改不了权限；新建表用应用身份建（owner=应用）即可全自动 |

## 部署（首次使用）

1. 把 `scripts/` 下所有 .py 拷到 `<workspace>/feishu_api/`（config.py 含应用凭证，勿提交版本库）；
2. `pip install requests matplotlib`（见 requirements.txt）；
3. 若 workspace 根不是 `<workspace根目录>`，改各脚本头部的 `BASE` 常量；
4. odps-query skill 已初始化（凭据可用）。

## 文件清单

```
ops-report-full/
├── SKILL.md                  # 本文件
├── requirements.txt
├── scripts/
│   ├── render_sql.py         # SQL 模板日期填充
│   ├── gen_report_json.py    # 报告内容生成（--sections 归因开关）
│   ├── gen_l2l3_analysis.py  # 第4/5章交互式 HTML 分析报告（预览用）
│   ├── publish_report.py     # 发布（文档+电子表格+权限）
│   ├── verify_and_cleanup.py # 发布后块完整性校验
│   ├── read_doc_comments.py  # 读取文档评论（修订循环）
│   ├── feishu_chat_reader.py # OAuth2 user_access_token（被 publish 复用）
│   └── config.py             # 飞书应用凭证（脱敏版为 config.py.example）
└── sql/                      # 6 个取数 SQL 模板（*.sql.tpl）
```
