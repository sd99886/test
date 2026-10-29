---
name: return-reason-analysis
description: 从 MaxCompute 取数或接收用户上传的 Excel，分析产品退货原因分布与月度趋势，生成深层诊断与改善建议，交付 4 Sheet 格式 Excel 或飞书电子表格。触发词：退货分析、退货原因、退件率、return reason、return analysis。
---

# 退货原因分析

## 使用流程

### Step 1：确认数据来源

向用户确认两种输入方式之一：

| 方式 | 说明 |
|------|------|
| **A. 自动取数** | 调用 `odps-query` skill 执行 `sql/return_reason_query.sql`，需先确认筛选条件 |
| **B. 上传文件** | 用户直接提供 Excel/CSV，跳过取数直接进入分析 |

### Step 2：确认筛选条件（仅自动取数时需要）

**必须**向用户逐项确认以下条件：

> ⚠️ **数据范围说明**：本技能仅获取 `channel = '独立站'` 的数据，不含 Amazon / Zalando 等渠道。

| # | 确认项 | 对应字段 | 示例 | 默认值 |
|---|--------|---------|------|--------|
| 1 | 销售时间范围 | `date_str` | `>= '2026-08-01' AND <= '2026-10-31'` | 全量（不限） |
| 2 | 上新时间范围 | `首次上架时间` | `>= '2026-01'` | 全量（不限） |
| 3 | SKC | `rid.skc` | `'CAB03C6H001JK'` 或 `IN (...)` | 全量（不限） |
| 4 | 业务部门 | `cud.业务部门` | `'ACC'` | 全量（不限） |
| 5 | 大类别 | `cud.大类别` | `'鞋品'` | 全量（不限） |

**如无明确指出，则默认全量（不加该条件）。**

### Step 3：取数 → 分析

1. 将确认的条件填入 `sql/return_reason_query.sql` 模板（替换占位符）
2. 调用 `odps-query` 执行查询，导出为 CSV
3. 运行 `scripts/analysis.py` 执行 7 大板块分析，输出 `analysis_result.json`

### Step 4：确认交付方式

分析完成后，**必须**询问用户：

```
分析已完成，请选择交付方式：
A. Excel 文件（.xlsx）— 含 4 个 Sheet
B. 飞书电子表格 — 在线协作，自动设权限
```

| 选项 | 执行动作 |
|------|----------|
| **A. Excel 文件** | 运行 `scripts/write_excel.py`，生成含 4 Sheet 的 `.xlsx` 文件 |
| **B. 飞书电子表格** | 运行 `scripts/create_feishu.py`，创建飞书在线表格并返回链接 |

---

## 交付格式标准（4 Sheet）

无论 Excel 还是飞书，**必须**包含以下 4 个 Sheet：

| Sheet | 内容 | 格式要求 |
|-------|------|----------|
| **汇总透视** | 按 SKC × 一级原因 × 二级原因 层级展开 | 黄色小计行、蓝色总计行 |
| **分月透视** | 月 × SKC × 原因 层级展开 | 黄色小计行、蓝色月汇总行 |
| **数据明细** | 原始查询结果（21列） | 蓝色表头 |
| **分析结论** | 7 大板块分析结论 | 深蓝标题、浅蓝板块标题、蓝色表头、红/黄/绿条件着色 |

### 颜色规范

| 颜色 | 色值 | 含义 | 使用场景 |
|------|------|------|----------|
| 深蓝 | `FF2F5496` | 大标题 | 文档标题行、Sheet 标题行 |
| 浅蓝 | `FFD6E4F0` | 板块标题 | 一、二、三… 各板块标题 |
| 蓝色 | `FF4472C4` | 表头 | 表格列标题行 |
| 红色 | `FFFFC7CE` | 高风险 | 占比 > 30% / 退件率 > 50% / 峰值月 / P0 |
| 黄色 | `FFFFEB9C` | 需关注 | 占比 15-30% / 退件率 25-50% / 恶化月 / P1 |
| 绿色 | `FFC6EFCE` | 已改善 | 环比下降 / 低风险 |
| 纯黄 | `FFFFFF00` | 小计行 | 透视表中各层级汇总行 |
| 浅蓝底 | `FFD9E2F3` | 总计行 | 透视表中 SKC 总计 /  grand total |

### 原因中文映射

分析结论中退货原因需附带中文注释，格式：`英文名（中文名）`

| 英文名 | 中文名 |
|--------|--------|
| Item Doesn't Fit | 尺码问题 |
| Dislike the Fabric | 面料问题 |
| Arrived Different From Description/Photo | 描述不符 |
| I Don't Like the Product | 不喜欢 |
| Order not shipped, cancelled | 订单取消 |
| Other | 其他 |

二级原因同理：Too big（偏大）、Too small（偏小）、Fabric is thin/transparent（面料太薄/透）、Cheap material（材质廉价）等。

---

## SQL 取数模板

查询模板位于 `sql/return_reason_query.sql`，核心结构：

- **主表**：`cupshe_bigdata_ads.ads_scm_cp_refund_info_df`（退货明细）
- **维表**：`cupshe_bigdata_cdm.dws_prod_skc_label_di` + `dws_prod_skc_with_combination_label_di`（SKC 维度）
- **固定条件**：`rid.channel = '独立站'`
- **聚合粒度**：销售月 × cp × skc × 首次上架时间 × 一/二/三级退货原因 × 品类

输出字段：销售月、cp、skc、品类（一/二/三级）、图片链接、首次上架时间、sku级别一/二/三级原因、销量、GMV、退款数量、退款金额、退券金额、退款总额、退件率、退款率、退券率、退货率

---

## 分析框架（7 个板块）

### 一、整体退货概况

| 指标 | 计算方式 |
|------|---------|
| 总销量 | SUM(销量) |
| 总退款数量 | SUM(退款数量) |
| 总 GMV | SUM(GMV) |
| 总退款金额 | SUM(退款金额) |
| 退件率 | 总退款数量 / 总销量 |
| 退货率 | 总退款总额 / 总 GMV |

### 二、退货原因分布

按一级原因聚合，退款数量降序。核心原因（占比 > 20%）下钻二级原因 TOP 3。

### 三、分月退货趋势

按月份聚合，自动标注：
- 退件率最高月 → 🔴 峰值
- 环比下降的最低月 → 🟢 改善
- 环比上升月 → 🟡 恶化

### 四、分月退货原因明细

每月 × 每原因。退件率 > 50% 标红；首次出现标注"新问题"。

### 五、深层问题诊断

对占比 TOP 2 原因做深层诊断（数据支撑 + 趋势 + 严重度 + 结论）。

严重度：占比 > 30% 或退件率 > 50% → 🔴 高；15-30% → 🟡 中；< 15% → 🟢 低

### 六、改善建议

| 优先级 | 含义 | 底色 |
|--------|------|------|
| P0 | 立即行动（影响大 + 可快速落地） | 红色 |
| P1 | 短期跟进（需一定周期） | 黄色 |

自动匹配建议类型：
- 尺码类 → 调整鞋楦 / 更新尺码表 / 增加尺码说明
- 面料类 → 面料升级 / 加衬里 / 改善面料手感
- 描述类 → 更新产品图 / 增加实物说明 / 改善详情页描述

### 七、改善目标

现状 vs 目标对比 + TOP 3 行动项。目标退件率按现状降低 30% 计算。

---

## 飞书电子表格交付流程

使用 `scripts/create_feishu.py`，流程如下：

1. 获取 tenant_access_token（飞书应用身份）
2. 创建电子表格（`POST /sheets/v3/spreadsheets`）
3. 依次创建 4 个 Sheet 并写入数据：
   - 汇总透视（默认 Sheet 重命名）
   - 分月透视（`POST /sheets/v3/spreadsheets/{token}/sheets`）
   - 数据明细
   - 分析结论
4. 对关键行应用样式（标题/表头/小计/条件着色）
5. 设置组织内访问权限（`PATCH /drive/v1/permissions/{token}/public`）
6. 返回链接：`https://mycupshe.feishu.cn/sheets/{token}`

### 飞书 API 注意事项

- **权限必设**：创建后必须调用权限 API 设置 `link_share_entity: tenant_editable`，否则用户无法访问
- **写入列数**：每批写入的 range 列数必须 >= 该批所有行的最大列数，不能只看首行
- **添加 Sheet**：使用 v3 端点 `POST /sheets/v3/spreadsheets/{token}/sheets`，body 为 `{"title": "xxx"}`
- **get_sheets 返回**：`data["data"]["sheets"]` 直接是列表，不需再索引

---

## 脚本清单

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `scripts/analysis.py` | 7 大板块分析，输出 JSON | pandas |
| `scripts/write_excel.py` | 生成 4 Sheet Excel 文件 | openpyxl, pandas |
| `scripts/create_feishu.py` | 创建飞书在线表格（需配置凭证） | requests, pandas |
| `sql/return_reason_query.sql` | MaxCompute 取数模板 | — |
