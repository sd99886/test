# 数据仓库表结构与字段映射

> Cupshe BigData（MaxCompute，阿里云 eu-central-1）。共 3 张表：1 张日粒度 SKC 快照表（分析主力）+ 1 张月粒度 SKC 快照表（目标达成）+ 1 张组合品映射表（SKC 归一）。所有销售额归因场景的表结构与枚举值均来自 2026-10-22 真实探查（`DESC` + `SELECT DISTINCT`），禁止凭记忆修改。

## 表总览与关系

| 表 | 项目 | 层 | 粒度 | 数据规模 | 分区 | 更新时效 | 用途 |
| -------------- | ------- | --- | --------- | -------- | ------------- | ------- | ------- |
| `cupshe_bigdata_ads.ads_prod_skc_product_info_di` | cupshe_bigdata_ads | ADS | SKC × 日 | ~3500 在架 SKC/日，全品类 | `pt`（STRING，yyyymmdd） | T+1 | 趋势归因 / 维度对比 / 漏斗 / 异常诊断的主力事实表 |
| `cupshe_bigdata_ads.ads_prod_skc_product_info_mi` | cupshe_bigdata_ads | ADS | SKC × 月 | 同上按月 | `pt`（数值分区，`PT>0`） | T+1 | 目标达成（部门目标 vs 实际 GMV），仅月度场景 |
| `cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df` | cupshe_bigdata_cdm | DWD | SKC × 组合品 | 全量 | 无分区（快照表） | 每日 | 组合品 SKC 归一映射（`skc → combination_skc`） |

> **⚠️ 混合表类型注意**：`_di` 与 `_mi` 为分区表（用 `pt` 过滤，注意 `_mi` 的 pt 为数值型写 `PT>0`，`_di` 的 pt 为字符串型写 `pt >= '20240101'` 或 `pt = '${pt}'`）；`_combination_df` 为**无分区全量快照表**，查询前需 `set odps.sql.allow.fullscan=true;` 或搭配其他表 JOIN 使用（子查询中 `SELECT DISTINCT skc, combination_skc` 数据量小，实践中随主表 JOIN 不触发全扫报错）。

**表间关系：** `di.skc = cdm.skc`（LEFT JOIN，`_combination_df` 已 DISTINCT，`skc` 侧唯一，不膨胀）。组合品归一规则：`COUNT(DISTINCT CASE WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc END)`——组合品按 `combination_skc` 计数，避免组合品+子品重复计数。

---

## 一、`cupshe_bigdata_ads.ads_prod_skc_product_info_di` — 全品类信息 SKC 日表

### 基础过滤（所有查询必须继承）

```sql
WHERE a.is_online_adjustment = 1      -- 当日在架（调整后口径）
  AND a.pt >= '20240101'              -- 分区下限（历史数据从 2024 起）
  AND a.style_position != '无库存测试款' -- 排除测试款
  AND a.big_category != '赠品'         -- 排除赠品
```

> 目标达成场景（`_mi` 表）用等价过滤：`PT > 0 AND is_online_adjust = 1 AND big_category != '赠品'`（注意 `_mi` 表字段名为 `is_online_adjust`，与 `_di` 的 `is_online_adjustment` 不同）。目标口径额外要求 `is_gift_cart = '否'` 排除赠品卡。

### 字段说明（按用途分组）

**时间与主键：**

| 字段 | 类型 | 含义 |
| --------- | -------- | ----------- |
| `date_str` | STRING | 业务日期（yyyy-mm-dd），时间窗过滤用此字段 |
| `skc` | STRING | SKC 编码（商品款色），主键之一 |
| `pt` | STRING | 分区字段（yyyymmdd） |

**品类与组织维度：**

| 字段 | 类型 | 含义 |
| --------- | -------- | ----------- |
| `first_category` | STRING | 一级品类 |
| `big_category` | STRING | 大类 |
| `second_category` | STRING | 二级品类 |
| `third_category` | STRING | 三级品类 |
| `business_group_name` | STRING | 业务部门（有 NULL，需按映射规则补全，见下） |
| `channels` | STRING | 渠道（原渠道字段：定泳为下单渠道、成衣为开发渠道；NULL 视为独立站） |
| `business_channels` | STRING | 企划设计渠道（开发渠道） |
| `style_position` | STRING | 款式定位（含 '无库存测试款'，须排除） |
| `popular_type` | STRING | 畅滞销类型 |
| `is_new_this_month` | STRING | 是否当月上新（'新品'/'未上架'/其他=老品） |
| `is_new_this_year` | STRING | 是否当年上新（'新品'/'未上架'/其他=老品） |
| `first_published_at` | STRING | 首次上架时间 |
| `nation_line_name` | STRING | 国家线 |
| `series` | STRING | 人群线 |

**交易度量（销售额归因核心）：**

| 字段 | 类型 | 含义 |
| --------- | -------- | ----------- |
| `sale_amount_usd` | DECIMAL | 销售额（USD）——GMV 核心指标 |
| `sale_quantity` | BIGINT | 销量 |
| `return_quantity` | BIGINT | 退货数量 |
| `total_refund_amount_usd` | DECIMAL | 退款额（含退 store credit） |
| `order_num` / `order_user` / `order_quantity` / `order_amount_us` | BIGINT/DECIMAL | 订单数 / 下单用户 / 订单商品量 / 订单金额 |
| `checkout_cnt` / `checkout_user` / `checkout_quantity` | BIGINT | 结算次数 / 用户 / 商品量 |
| `add_to_cart_cnt` / `add_to_cart_user` | BIGINT | 总加购次数 / 用户 |

**流量与转化度量（漏斗归因）：**

| 字段 | 类型 | 含义 |
| --------- | -------- | ----------- |
| `collection_view_user` / `collection_view_cnt` | BIGINT | 商列（列表页）浏览 UV/PV |
| `collection_click_user` / `collection_click_cnt` | BIGINT | 商列点击 UV/PV |
| `collection_add_to_cart_user` / `collection_add_to_cart_cnt` | BIGINT | 商列加购 UV/次数 |
| `pdp_view_user` / `pdp_view_cnt` | BIGINT | 详情页浏览 UV/PV |
| `pdp_add_to_cart_user` / `pdp_add_to_cart_cnt` | BIGINT | 详情页加购 UV/次数 |

**库存与供给度量：**

| 字段 | 类型 | 含义 |
| --------- | -------- | ----------- |
| `sale_available_inventory` | BIGINT | 可售库存 |
| `transit_inventory` | BIGINT | 采购在途库存 |
| `is_online` / `is_online_adjustment` | BIGINT | 是否在架 / 当日在架（调整口径） |

### 枚举值（2026-10-21 分区实查）

**big_category（大类，在架 SKC 占比）：**

| 值 | 含义 | 在架 SKC 数 |
| --------- | ----------------- | ------- |
| 成衣 | 最大品类 | 2153 |
| 泳衣 | 第二品类 | 1215 |
| 内睡 | 内衣睡衣家居服 | 83 |
| ACC | 配饰鞋品 | 43 |
| 赠品 | 赠品（**须过滤**） | 4 |

**business_group_name（业务部门）：** 成衣一部(1706)、泳衣产品部(862)、成衣二部(438)、泳衣买手部(354)、NULL(101)、塑身衣项目部(57)、ACC(43)、内睡(37)、品牌设计部(1)。
**NULL 补全规则（必用，与 monthly-ops-analysis 技能同源）：**

```sql
CASE
    WHEN business_group_name IS NULL AND second_category = '泳衣' THEN '泳衣产品部'
    WHEN business_group_name IS NULL AND second_category IN ('下装','运动服','连体装','针织服装','外套','罩衫','上衣','两件套','连衣裙','上装') THEN '成衣一部'
    WHEN business_group_name IS NULL AND second_category IN ('内衣','睡衣','家居服','塑身衣') THEN '内睡'
    WHEN business_group_name IS NULL AND first_category IN ('女士配饰','女士鞋品') THEN 'ACC'
    ELSE business_group_name
END AS 业务部门
```

**popular_type（畅滞销类型，在架 SKC 数）：** 畅销(1318)、平销(594)、滞销(573)、爆款(435)、不动销(333)、大爆款(162)、NULL(127)、超爆款(57)。成功款 = 畅销+爆款+大爆款+超爆款；爆款以上 = 爆款+大爆款+超爆款。

**is_new_this_month / is_new_this_year：** 取值 '新品'/'未上架'/其他。判定规则（注意渠道限定）：`is_new_this_year = '新品' AND NVL(channels,'独立站') REGEXP '独立站'` 才算当年新品；`'未上架'` 单独归类；其余为老品。**当月新品维度不可跨月查询**（字段含当月语义）。

**style_position：** 含 '无库存测试款'（须排除）与其他正常定位值。

### 新老品判定口径（与源脚本一致）

```sql
CASE
    WHEN is_new_this_year = '新品' AND NVL(channels, '独立站') REGEXP '独立站' THEN '当年新品'
    WHEN is_new_this_year = '未上架' THEN '当年未上架'
    ELSE '当年老品'
END AS 是否当年新品
-- 是否当月新品同构：is_new_this_month → '当月新品'/'当月未上架'/'当月老品'
```

---

## 二、`cupshe_bigdata_ads.ads_prod_skc_product_info_mi` — 全品类信息 SKC 月表

用于目标达成场景：`month_str`（月份）× `style_position_adjust`（正常目标/无库存测试款）× 部门，输出目标值与实际值（部门清单：成衣一部、成衣二部、品牌设计部、新渠道产品部、泳衣产品部、泳衣买手部、内睡、ACC、塑身衣项目部；成衣口径限定 `big_category = '成衣'`；全部实际值要求 `is_gift_cart = '否'`）。字段与 `_di` 基本同构，差异字段：`month_str`（月份）、`is_gift_cart`（是否赠品卡）、`is_online_adjust`（注意与 `_di` 的 `is_online_adjustment` 命名不同）。新品 GMV 判定：`month_str = SUBSTR(first_published_at,1,7) AND (channels REGEXP '独立站' OR channels IS NULL)`。

---

## 三、`cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df` — 组合品映射

### 字段说明

| 字段 | 类型 | 含义 | 示例 |
| --------- | -------- | ----------- | ----------- |
| `skc` | STRING | 子品 SKC | （内部编码） |
| `combination_skc` | STRING | 所属组合品 SKC | （内部编码） |

> 使用方式：`LEFT JOIN (SELECT DISTINCT skc, combination_skc FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df) c ON a.skc = c.skc`。组合品子品的销售额/销量会同时挂在子品与组合品上，**在架 SKC 计数必须走组合品归一 CASE 表达式**，否则重复计数。

---

## 四、查询前自检清单

构造任何 SQL 前必过以下检查：

1. **时间过滤**：`_di` 表双过滤——分区用 `pt >= '20240101'`（字符串比较），业务时间窗用 `a.date_str >= '${start_date}' AND a.date_str <= '${end_date}'`（与 periods JOIN 实现同环比窗口）；`_mi` 表用 `PT > 0` + `month_str` 过滤。**periods 非等值 JOIN（>=/<=）必须加 `/* +MAPJOIN(b) */` hint**，否则报 `ODPS-0130071: expect equality expression`。
2. **关联键确认**：`a.skc = c.skc`（组合品映射）。不要与 `subsite_comm`/`subsite_id` 等其他业务域键混淆。
3. **NULL 处理**：`business_group_name` 有 ~3% NULL，必须走补全 CASE；`channels` NULL 视为独立站（`NVL(channels,'独立站')`）；`popular_type` NULL 在源脚本中归为 '不动销'（`IF(popular_type IS NULL,'不动销',popular_type)`）。
4. **时间字段语义**：`date_str` 为业务日（快照日），`first_published_at` 为首次上架时间（跨月新品判定用）；环比窗口 = 起止日各回拨 1 个月，同比 = 各回拨 1 年（等长窗口）。
5. **全表扫描开关**：`_combination_df` 为无分区快照表，单独查询需 `set odps.sql.allow.fullscan=true;`（实践中作为 JOIN 子查询即可）。
6. **去重口径**：在架 SKC 一律用组合品归一 CASE 表达式去重；禁止 `COUNT(1)` 冒充 `COUNT(DISTINCT ...)`。
7. **比率分母**：所有比率分母 `NULLIF(x, 0)`；`cvr = 销量/详情页UV`（量纲：件/人，非严格转化率）、`ctr = 商列点击UV/商列浏览UV`（同为人头口径）。
8. **基础过滤继承**：`is_online_adjustment = 1` + `style_position != '无库存测试款'` + `big_category != '赠品'` 三条件必须原样继承，不得增删（与 monthly-ops-analysis 技能口径对齐）。
