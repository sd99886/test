# 指标口径与计算逻辑

> 聚焦 4 大分析场景：趋势归因（GMV 涨跌拆因子）、维度对比归因（品类/部门/新老品结构）、转化漏斗归因（流量→转化→客单）、异常诊断（单维度下滑下钻）。所有口径与 monthly-ops-analysis 技能源脚本（S1/S2/S3）对齐，**同一指标只在本文件定义一次**。

## 指标速查

| 指标 ID | 名称 | 公式 | 说明 |
| ------------- | --------------- | ----------- | -------- |
| M01 | 销售额（GMV） | `SUM(sale_amount_usd)` | USD，核心口径；目标达成口径额外要求 `is_gift_cart='否'` |
| M02 | 销量 | `SUM(sale_quantity)` | 件 |
| M03 | 平均售价 | `SUM(sale_amount_usd) / NULLIF(SUM(sale_quantity),0)` | 量价拆分的"价"因子 |
| M04 | 退货率 | `SUM(total_refund_amount_usd) / NULLIF(SUM(sale_amount_usd),0)` | 金额口径 |
| M05 | 退件率 | `SUM(return_quantity) / NULLIF(SUM(sale_quantity),0)` | 数量口径 |
| M06 | 在架 SKC | `COUNT(DISTINCT 组合品归一skc)` | 供给规模，见 warehouse_schema §一 归一 CASE |
| M07 | 款效 | `SUM(sale_amount_usd) / NULLIF(在架SKC,0)` | 单款产出 |
| M08 | 款均销量 | `SUM(sale_quantity) / NULLIF(在架SKC,0)` | |
| M09 | 款均 UV | `SUM(pdp_view_user) / NULLIF(在架SKC,0)` | 单款流量 |
| M10 | 商列浏览 UV | `SUM(collection_view_user)` | 漏斗第 1 层 |
| M11 | 商列点击 UV | `SUM(collection_click_user)` | 漏斗第 2 层 |
| M12 | CTR | `SUM(collection_click_user) / NULLIF(SUM(collection_view_user),0)` | 商列点击率 |
| M13 | 详情页 UV | `SUM(pdp_view_user)` | 漏斗第 3 层 |
| M14 | 详情页加购 UV | `SUM(pdp_add_to_cart_user)` | 漏斗第 4 层 |
| M15 | 加车率 | `SUM(pdp_add_to_cart_user) / NULLIF(SUM(pdp_view_user),0)` | UV 口径 |
| M16 | CVR | `SUM(sale_quantity) / NULLIF(SUM(pdp_view_user),0)` | 量纲为件/人（销量÷UV），非人头转化率，解读时注意 |
| M17 | UV 价值 | `SUM(sale_amount_usd) / NULLIF(SUM(pdp_view_user),0)` | GMV = UV × UV价值 |
| M18 | 成功款占比 | `成功款SKC数 / NULLIF(在架SKC,0)` | 成功款 = popular_type ∈ 畅销/爆款/大爆款/超爆款 |
| M19 | 爆款以上占比 | `爆款以上SKC数 / NULLIF(在架SKC,0)` | 爆款以上 = 爆款/大爆款/超爆款 |
| M20 | 达成率 | `实际 / NULLIF(目标,0)` | 目标=0 时记 0（与源脚本一致） |
| M21 | 环比 | `(本期 - 环比期) / NULLIF(环比期,0)` | 环比期 = 起止日各回拨 1 个月（等长窗口） |
| M22 | 同比 | `(本期 - 同比期) / NULLIF(同比期,0)` | 同比期 = 起止日各回拨 1 年 |
| M23 | 占比 | `该维度值 / NULLIF(SUM(该维度值) OVER (),0)` | 分母按各自周期合计 |
| M24 | 占比环比（比差） | `本期占比 - 环比期占比` | 单位：百分点（pp）——趋势/品类对比场景统一用比差 |
| M25 | 投入产出比 | `(销量占比) / NULLIF(在架SKC占比,0)` | 该维度以多少供给份额换多少销量份额 |

---

## 场景①：趋势归因（GMV 涨跌拆因子）

### 核心维度

| 维度字段 | 含义 | 分析用途 |
| ------------- | --------------- | ----------- |
| `date_type`（本期/环比上一周期/同比上一周期） | periods 构造 | 所有同环比对比的骨架 |
| `是否当年新品` / `是否当月新品` | 新老品结构 | 增长来源拆分（新品驱动 vs 老品基本盘） |
| `big_category` + `second_category` | 品类结构 | 结构迁移定位 |

### 量价拆解框架（GMV = 销量 × 平均售价）

```sql
SELECT  是否当年新品, big_category, second_category,
        SUM(sale_amount_usd)                                        AS 销售额,
        SUM(sale_quantity)                                          AS 销量,
        SUM(sale_amount_usd) / NULLIF(SUM(sale_quantity), 0)        AS 平均售价
FROM    cupshe_bigdata_ads.ads_prod_skc_product_info_di a
JOIN    periods b ON a.date_str >= b.start_date AND a.date_str <= b.end_date
LEFT JOIN (SELECT DISTINCT skc, combination_skc
           FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df) c
       ON a.skc = c.skc
WHERE   a.is_online_adjustment = 1
  AND   a.pt >= '20240101'
  AND   a.style_position != '无库存测试款'
  AND   a.big_category != '赠品'
GROUP BY 是否当年新品, big_category, second_category
```

> 涨跌贡献归因：对每个维度值算 `(本期值 - 环比值)`，按绝对差额降序排列即为贡献度排名；差额合计应等于整体差额（交叉验证）。量价拆分：`ΔGMV ≈ Δ销量 × 环比均价 + 环比销量 × Δ均价 + Δ销量 × Δ均价`。

---

## 场景②：维度对比归因（品类/部门/新老品）

### 核心维度

| 维度字段 | 含义 | 分析用途 |
| ------------- | --------------- | ----------- |
| `业务部门`（business_group_name 补全后） | 组织维度 | 部门贡献与投入产出对比 |
| `big_category` / `second_category` / `third_category` | 品类层级 | 结构占比与占比环比（pp） |
| `popular_type` | 商品效率分层 | 成功款/爆款结构 |
| `是否当月新品` | 新老品（当月口径，**不跨月查询**） | 新品占比与贡献 |

### 计算示例（占比 + 占比环比比差 + 投入产出比）

```sql
SELECT  业务部门,
        本期_销售额,
        (本期_销售额 - 环比_销售额) / NULLIF(环比_销售额, 0)          AS 销售额_环比,
        本期_销售额 / NULLIF(SUM(本期_销售额) OVER (), 0)             AS 本期_销售额占比,
        本期_销售额 / NULLIF(SUM(本期_销售额) OVER (), 0)
            - 环比_销售额 / NULLIF(SUM(环比_销售额) OVER (), 0)       AS 销售额占比_环比_比差,
        (本期_销量 / NULLIF(SUM(本期_销量) OVER (), 0))
            / NULLIF(本期_在架skc / NULLIF(SUM(本期_在架skc) OVER (), 0), 0) AS 本期_投入产出比
FROM    pivoted   -- periods + agg + pivot 结构见 attribution_logic.md MTD-01
ORDER BY 本期_销售额 DESC
```

---

## 场景③：转化漏斗归因（流量 → 转化 → 客单）

### 漏斗结构（同表自含，无需跨表）

```
商列浏览UV (M10) → 商列点击UV (M11) → 详情页UV (M13) → 详情页加购UV (M14) → 销量 (M02) → 销售额 (M01)
        └─ CTR (M12) ─┘                    └─ 加车率 (M15) ─┘   └─ CVR (M16) ─┘  └─ 平均售价 (M03) ─┘
```

### GMV 流量模型（归因主方程）

`GMV = 详情页UV × CVR × 平均售价`（因 CVR = 销量/UV、均价 = GMV/销量，恒等式成立）。漏斗归因即对每个维度算三因子的环比变化，定位主降/主升因子。

### 计算示例

```sql
SELECT  big_category,
        SUM(pdp_view_user)                                            AS 详情页uv,
        SUM(sale_quantity)  / NULLIF(SUM(pdp_view_user), 0)           AS cvr,
        SUM(sale_amount_usd) / NULLIF(SUM(sale_quantity), 0)          AS 平均售价,
        SUM(sale_amount_usd) / NULLIF(SUM(pdp_view_user), 0)          AS uv价值
FROM    cupshe_bigdata_ads.ads_prod_skc_product_info_di a
JOIN    periods b ON a.date_str >= b.start_date AND a.date_str <= b.end_date
WHERE   a.is_online_adjustment = 1 AND a.pt >= '20240101'
  AND   a.style_position != '无库存测试款' AND a.big_category != '赠品'
GROUP BY big_category, b.date_type
```

> ⚠️ 埋点 UV 字段（collection_*/pdp_*）的覆盖范围与售后/交易字段不完全对齐（可能仅部分渠道/版本有埋点），报告中必须标注"漏斗指标基于埋点 UV 口径"。

---

## 场景④：异常诊断（单维度下滑下钻）

### 专项指标

| 指标 | 公式 | 业务含义 |
| ------------------ | ----------- | -------------------- |
| 下滑贡献额 | `(维度本期GMV - 维度环比GMV)`，负值取绝对值排序 | 定位拖累最大的维度值 |
| 供给缺口 | `在架SKC环比变化`、`款均在架天数环比变化` | 判断是"没货卖"还是"卖不动" |
| 库存制约度 | `日均可售库存 = SUM(sale_available_inventory)/天数` | 库存环比大跌 + 销量跌 → 供给问题 |
| 退货侵蚀 | `退货率环比变化` | 退货恶化吞噬 GMV 增长 |
| 商品分层恶化 | `成功款占比环比差`（pp） | 畅销款占比下滑 → 选品/运营问题 |

### 三因子诊断顺序（异常诊断标准动作）

1. **供给因子**：在架 SKC ↓？款均在架天数 ↓？日均可售库存 ↓？→ 是：供给问题（断货/下架）。
2. **流量因子**：商列浏览 UV ↓？详情页 UV ↓？→ 是：流量问题（投放/陈列）。
3. **效率因子**：CTR ↓？加车率 ↓？CVR ↓？平均售价 ↓？→ 是：转化问题（定价/详情/竞品）。
4. **侵蚀因子**：退货率 ↑ 退件率 ↑ → 售后侵蚀。

---

## 常见计算陷阱

1. **当月新品不可跨月**：`is_new_this_month` 含当月语义，跨月查询会把"上架满 2 个月"的款仍判为当月新品。跨月分析一律用 `是否当年新品`；仅当分析窗口在同一个月内才用 `是否当月新品`。
2. **组合品重复计数**：在架 SKC 不用组合品归一 CASE 会把组合品子品重复计入；款效/款均销量等所有"分母含 SKC 数"的指标全部失真。
3. **占比环比口径二义**：源脚本存在两种写法——S2 用**比差**（`本期占比 - 环比占比`，单位 pp），S3 用**相对比**（`本期占比/环比占比 - 1`）。本技能统一采用**比差（pp）**（M24），报告表述用"个百分点"；若引用 S3 产出需换算。
4. **cvr 量纲混淆**：CVR = 销量/UV（件/人），不是人头转化率；解读时不要说"xx% 的用户下了单"。
5. **`_mi` 与 `_di` 字段名差异**：在架标志在月表叫 `is_online_adjust`、日表叫 `is_online_adjustment`；月表分区是数值型（`PT>0`），日表是字符串型（`pt>='20240101'`）。
6. **NULL 处理**：`business_group_name` NULL 必须补全；`popular_type` NULL 归'不动销'；`channels` NULL 视为独立站；度量字段聚合前 `NVL`。
7. **分母除零**：所有比率必须 `NULLIF(x,0)`，结果为 NULL 时报告写 `N/A`，不得报错中断。
8. **新老品渠道限定**：`is_new_this_year='新品'` 还必须 `NVL(channels,'独立站') REGEXP '独立站'` 才算新品，漏掉渠道条件会把渠道专供款误判为新品。
9. **达成率目标为 0**：源脚本约定目标为 0 时达成率记 0（不是 NULL/报错）。
10. **环比窗口非自然月**：环比 = 起止日各回拨 1 个月（如 10-01~10-18 环比 09-01~09-18），不是上月整月；报告数据说明必须写明窗口。
