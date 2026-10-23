---
name: ops-weekly-report
description: 经营周报 skill（经营分析报告第 1/2/3/7 章：分析说明、目标达成总览、新老品与业务部门结构、口径附录）：含取数查询流程与发布，不含归因分析与策略建议。当用户要求「出周报/经营周报/目标达成报告（不要归因分析）」或明确只要第一二三七章时使用。
---

# 经营周报（ops-weekly-report）

产出经营分析报告的**第 1 章（分析说明）、第 2 章（目标达成总览）、第 3 章（新老品与业务部门结构）、
第 7 章（口径附录）**，即「无归因分析」版本——不含第 4/5/6 章（品类拆解、业绩原因、改善策略），
发布时也**不创建/复用电子表格**。

**与其他 skill 的分工**：需要归因分析及策略建议（第 4/5/6 章）时用 ops-category-analysis 或
ops-report-full（全流程含归因）；本 skill 只做周报主体。

---

## 0. 开工确认（每次都必须问，不许跳过、不许自己默认）

**必须先问用户时间窗口，让用户自己给 start_date / end_date**：

> 「本期周报的统计窗口是哪两天？（例如 2026-10-13 ~ 2026-10-20）」

并**复述窗口语义**让用户确认：

| 参数 | 含义 |
|---|---|
| start_date / end_date | 分析窗口起止；环比期=起止各回拨 1 个月（自动派生），同比期=回拨 1 年 |
| 第 2 章月度口径 | end_date 所在月（YYYY-MM）当月 1 日累计；时间进度 = end_day / 当月天数 |

再确认一次范围（本 skill 默认无归因）：

> 「本次只出第 1/2/3/7 章（不含品类拆解与策略建议），对吗？如需要归因请告知。」

用户如临时要归因，转 ops-report-full 流程（--sections 1234567）。

---

## 1. 取数流程（依赖 odps-query skill，三步验收）

### 1.1 数据清单（本 skill 需要 3 个查询 + 1 个可选）

| SQL 模板 | 产出 CSV | 服务内容 | 何时执行 |
|---|---|---|---|
| `S1_目标达成.sql.tpl` | S1_目标达成.csv | 2.1~2.8 全部指标 + 表2-1 | 总是 |
| `S1W_周度上新.sql.tpl` | S1W_周度上新.csv | 2.4 上新数（本周/上周/本月累计/上月同期/去年同期） | 总是 |
| `S3_新老品业务部门.sql.tpl` | S3_新老品业务部门.csv | 第 3 章新老品销售/流量 + 表3-1/3-2 | 总是 |
| `S1V_上新口径验证.sql.tpl` | —（stdout 核对） | 2.4 上新数口径核对 | 数字存疑时 |

口径锚点：在线调整口径（is_online_adjustment=1）、排除赠品与无库存测试款、
目标=「正常目标」类型、第 3 章对照《经营情况模板》采用同比口径。

### 1.2 生成日期已填充的 SQL

```bash
py -3 <skill>/scripts/render_sql.py --start <start_date> --end <end_date> \
    --sql-dir <skill>/sql --out-dir <workspace>/out/ops_<end_date去掉横线>
```

> 脱敏版模板的表 schema 是占位符，需额外传：`--schema <主数仓项目>`（{{PROJECT_SCHEMA}}）、
> `--cdm-schema <CDM 项目>`（{{CDM_SCHEMA}}）、`--ads-dev-schema <ADS 开发项目>`（{{ADS_DEV_SCHEMA}}，仅 S1 用到）。

S1W 的周界（本周=END 所在自然周周一~周日、上周=前一周）由 render_sql.py 自动计算，**不要手工算**。

### 1.3 执行（odps-query 正式取数）

每个 SQL 走 odps-query：lint → 执行（--output 落盘）→ verify，三步退出码全 0 才算完成。
行数校验：S1W=5 行（五个周期）；S1/S3 行数与上次运行对比，漂移先核对口径再继续。

---

## 2. 生成报告（gen_report_json.py，无归因模式）

```bash
cd <workspace>/feishu_api
py -3 gen_report_json.py --start <start_date> --end <end_date> \
    --out out/ops_<end_date去掉横线> \
    --sections 1237 \
    --title "经营周报<发布日期>"
```

`--sections 1237` 是本 skill 的核心参数：
- 只输出第 1/2/3/7 章；第 4/5/6 章整体剔除（含图表与电子表格链接）；
- 第 1 章口径声明自动改为「第 3 章为窗口口径」（不再出现「第 3~6 章」「电子表格」字样）；
- `feishu_report.json` 的 `include_sheets=false` → 发布时自动跳过电子表格。

产出：`feishu_report.json` + `feishu_report_preview.txt`（预览文本）+ `charts/*.png`
（含表2-1、表3-1/3-2 表格图片——飞书原生表格卡顿/超列，一律转图片）。

### 章节内容速览

| 章 | 小节 | 数据源 |
|---|---|---|
| 1 分析说明 | 时间窗、双口径声明、数据范围、汇总口径 | 窗口参数自动派生 |
| 2 目标达成 | 2.1 GMV ~ 2.8 全指标表（表2-1 图片） | S1 + S1W |
| 3 新老品与部门结构 | 3.1 销售 / 3.2 流量（图3-1/3-2） / 3.3 结构与达成结合（表3-1/3-2 图片） | S3 |
| 7 附录 | 全部指标口径定义 | 窗口参数自动派生 |

### 叙述性数字的边界（重要）

窗口派生文字（时间窗、环比/同比区间、时间进度、口径声明）自动更新；但第 2/3 章段落里
写死的数据性叙述（如「新品销售额 46.67 万元、占比 10.13%」「成衣一部老品 +15.32%」）与 2026-10
窗口绑定——换窗口必须先跑脚本拿新数据，再逐段更新这些数字与结论。

---

## 3. 本地预览与用户确认（发布前必经）

把 `feishu_report_preview.txt` 的章节结构与关键段落呈给用户确认；用户提意见则改
gen_report_json.py 对应段落，重新生成，再次预览。**确认后才发布。**

## 4. 发布（publish_report.py）

```bash
cd <workspace>/feishu_api
py -3 publish_report.py --report-json out/ops_<...>/feishu_report.json
```

- `include_sheets=false` 时自动跳过电子表格，只建飞书文档；
- 首次运行或 token 过期会弹浏览器 OAuth 授权（回调 `http://localhost:8899/callback`），请用户点击授权；
- 产出 `publish_result.json`（doc_url / doc_id）。

## 5. 发布后校验

```bash
cd <workspace>/feishu_api
py -3 verify_and_cleanup.py
```

核对块数量（预期 ≈139 块：h2×4 + h3×11 + 文本 + 图片）与关键字抽查
（应含「1. 分析说明」「2. 目标达成总览」「3. 新老品与业务部门结构」「7. 附录」，
**不应含**「4. 品类拆解」「6. 改善策略」「电子表格」）。
校验通过后把 verify_and_cleanup.py 头部默认 DOC 改为新文档 id。

---

## 口径速查（写周报文字必须遵守）

- **双口径**：第 2 章=月度口径（当月 1 日累计，进度基准=时间进度）；第 3 章=窗口口径。不可混用。
- **达成率** = 实际/目标；时间进度 = 截止日/当月天数；落后/超时间进度 = 达成率 − 时间进度；
  差额数值 = 时间进度差 × 目标值。
- **环比** =（本期 − 上月同期）/上月同期（起止各回拨 1 个月）；**同比**同理回拨 1 年。
- **汇总** = 明细行加总；对比期原始值由 `本期值 ÷ (1+增长率)` 还原，缺失或 ≤ -100% 按对比期=0。
- **CTR** = 商列点击UV/商列浏览UV；**CVR** = 销量/详情页UV；**款效** = 销售额/在架SKC；
  **退件率** = 退货数量/销量；**退货率** = 退款总额/销售额。
- 金额单位美元，段落中「万元」=美元/10000。

## 已知限制与陷阱

| 陷阱 | 规避 |
|---|---|
| 误带第 4/5/6 章 | 必须 --sections 1237；发布后校验关键字「4. 品类拆解」不应存在 |
| S1W 周界手算错 | 用 render_sql.py 自动派生（周一为一周之始） |
| 飞书原生表格卡顿/超列 | 表2-1/3-1/3-2 已内置 render_table_image 转图片 |
| 上新数口径分歧 | 2.4 用「当月上架款数」月度口径；对不上时跑 S1V 验证 |
| Windows GBK 终端打印 | sys.stdout 包 TextIOWrapper(encoding='gbk', errors='replace') |
| OAuth token 过期 | publish_report.py 自动走浏览器重授权，提示用户点击即可 |

## 部署（首次使用）

1. `scripts/*.py` 拷到 `<workspace>/feishu_api/`（config.py 含应用凭证，勿提交版本库）；
2. `pip install requests matplotlib`；
3. workspace 根非 `<workspace根目录>` 时改脚本头部 BASE 常量；
4. odps-query skill 已初始化。

## 文件清单

```
ops-weekly-report/
├── SKILL.md                  # 本文件
├── requirements.txt
├── scripts/
│   ├── render_sql.py         # SQL 模板日期填充（含 S1W 周界自动派生）
│   ├── gen_report_json.py    # 报告内容生成（--sections 1237 无归因模式）
│   ├── publish_report.py     # 发布（include_sheets=false 时跳过电子表格）
│   ├── verify_and_cleanup.py # 发布后校验
│   ├── feishu_chat_reader.py # OAuth2 user_access_token（被 publish 复用）
│   └── config.py             # 飞书应用凭证（脱敏版为 config.py.example）
└── sql/
    ├── S1_目标达成.sql.tpl
    ├── S1W_周度上新.sql.tpl
    ├── S1V_上新口径验证.sql.tpl
    └── S3_新老品业务部门.sql.tpl
```
