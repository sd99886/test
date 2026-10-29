# 归因分析方法与场景配置（L0-L4 分层框架）

> 设计原则：稳定的东西沉到底层（表、指标、原子方法），场景退化为「方法组合 + 参数」配置。销售额归因主方程：**GMV = 详情页UV × CVR × 平均售价 = 销量 × 平均售价 = Σ维度贡献**。

---

## L0 数据层

### 表清单

| 表 ID | 全名 | 粒度 | 数据规模 | 适用 |
| -------- | --------------------------------------------- | --------- | -------- | -------------- |
| T1 | `cupshe_bigdata_ads.ads_prod_skc_product_info_di` | SKC × 日 | ~3500 在架 SKC/日 | 趋势/对比/漏斗/异常诊断主力表 |
| T2 | `cupshe_bigdata_ads.ads_prod_skc_product_info_mi` | SKC × 月 | 同上按月 | 目标达成（含部门目标） |
| T3 | `cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df` | SKC × 组合品 | 全量快照 | 组合品归一映射（随 T1 JOIN） |

### 选表规则

| 需求特征 | 选表 |
| -------- | -------- |
| 任意时间窗（日/周/月）、趋势、对比、漏斗、下钻 | T1（+T3 JOIN） |
| 月度目标 vs 实际、达成率、缺口 | T2 |
| 涉及在架 SKC 计数 / 款效 / 款均指标 | T1 + T3（必须） |
| 当月新品维度 | T1，且分析窗口必须在同一自然月内 |

> 所有 T1 查询必须继承基础过滤（见 [warehouse_schema.md](warehouse_schema.md) §一）：`is_online_adjustment=1 AND pt>='20240101' AND style_position!='无库存测试款' AND big_category!='赠品'`。

---

## L1 指标层

见 [metrics_definitions.md](metrics_definitions.md)，核心指标：

| 场景 | 核心指标 |
| ------------ | -------------- |
| 趋势归因 | M01 GMV, M02 销量, M03 均价, M21 环比, M22 同比, M23/M24 占比与占比环比 |
| 维度对比归因 | M01, M06 在架SKC, M07 款效, M17 UV价值, M23/M24, M25 投入产出比, M18/M19 成功款/爆款占比 |
| 转化漏斗归因 | M10-M15 漏斗层与转化率, M16 CVR, M17 UV价值, M03 均价 |
| 异常诊断 | M01, M06, M04/M05 退货退件率, M18/M19, 库存与在架天数指标 |
| 目标达成 | M01, M20 达成率（T2 口径，`is_gift_cart='否'`） |

---

## L2 原子方法（可复用的分析模式）

### MTD-01 整体概览基线

- **触发：** "整体""概览""这个月卖得怎么样""GMV 多少"
- **适用表：** T1
- **参数：** 时间窗（${start_date}, ${end_date}）、分组维度（${dim}：big_category / 业务部门 / second_category / 是否当年新品…）
- **步骤：**
  1. periods 构造本期/环比/同比窗口（环比起止各回拨 1 个月，同比各回拨 1 年）
  2. 按维度 × date_type 聚合核心度量
  3. 窗口函数算占比
- **伪 SQL：**

```sql
JOIN periods b ON a.date_str >= b.start_date AND a.date_str <= b.end_date
-- ⚠️ periods 非等值 JOIN 必须加 MAPJOIN hint（写在 SELECT 后）：SELECT /* +MAPJOIN(b) */ ...
-- periods: 本期 / 环比(DATEADD(start_dt,-1,'mm')~DATEADD(end_dt,-1,'mm')) / 同比(-1,'yyyy')
SELECT
    /* +MAPJOIN(b) */
    b.date_type, ${dim}, SUM(sale_amount_usd) AS 销售额, SUM(sale_quantity) AS 销量,
    SUM(sale_amount_usd) / NULLIF(SUM(sale_quantity),0) AS 平均售价,
    COUNT(DISTINCT 组合品归一skc) AS 在架skc
FROM    T1 a JOIN periods b ON ... LEFT JOIN T3 c ON a.skc = c.skc
WHERE   基础过滤
GROUP BY b.date_type, ${dim}
ORDER BY b.date_sort, ...   -- date_sort 需在 GROUP BY 中或改用其他排序方式
```

- **输出：** 维度 × 周期 × 度量基线表
- **陷阱：** 忘记继承基础过滤会混入测试款与赠品
- **特别提示：** 任何归因分析先跑此方法取基线，再按方法链下钻

### MTD-02 排行下钻

- **触发：** "Top""排行""哪些品类卖得最好/最差""拖累最大"
- **适用表：** T1
- **参数：** 排序指标（默认 M01）、维度、Top N（默认 10）、体量门槛（默认 GMV 占比 ≥ 2%）
- **步骤：**
  1. 按维度聚合排序指标
  2. HAVING 过体量门槛（`占比 >= 0.02`）
  3. 排序取 Top/Bottom N
- **伪 SQL：**

```sql
SELECT  ${dim}, SUM(sale_amount_usd) AS gmv
FROM    T1 a（JOIN periods 取本期窗口）
WHERE   基础过滤
GROUP BY ${dim}
HAVING  SUM(sale_amount_usd) / NULLIF(SUM(SUM(sale_amount_usd)) OVER (),0) >= 0.02
ORDER BY gmv DESC LIMIT ${N};
```

- **输出：** 排序清单表
- **陷阱：** 小体量噪声——占比 < 2% 的品类环比翻倍也无业务意义，必须先过门槛
- **特别提示：** ——

### MTD-03 时间趋势

- **触发：** "趋势""走势""拐点""近 N 天"
- **适用表：** T1
- **参数：** 时间粒度（日/周）、维度、指标
- **步骤：**
  1. 按时间粒度聚合（日粒度 `date_str`；周粒度用 `week_start_day` 字段）
  2. 识别拐点或连续下滑（连续 ≥3 期同向）
- **伪 SQL：**

```sql
SELECT  date_str, SUM(sale_amount_usd) AS gmv
FROM    T1 a
WHERE   基础过滤 AND a.date_str BETWEEN '${start_date}' AND '${end_date}'
GROUP BY date_str ORDER BY date_str;
```

- **输出：** 趋势数据表 + 折线图
- **陷阱：** 日粒度噪声大，≥2 周窗口建议周粒度（表内自带 `week_start_day`）；单维度日 GMV 小时提示"波动大，不宜过度解读"
- **特别提示：** 注意 T+1 时效——最新可得数据为昨天

### MTD-04 前后对比

- **触发：** "上架前后""改版前后""活动前后"
- **适用表：** T1
- **参数：** 事件日期（${event_date}）、前窗口、后窗口（**必须等长**）、分组维度
- **步骤：**
  1. 校验前后窗口等长，剔除大促/异常日
  2. 按维度分组算两窗口指标
  3. 算变化量与变化率
- **伪 SQL：**

```sql
SELECT  CASE WHEN date_str < '${event_date}' THEN '前' ELSE '后' END AS period,
        ${dim}, SUM(sale_amount_usd) AS gmv
FROM    T1 a WHERE 基础过滤 AND date_str BETWEEN '${start_date}' AND '${end_date}'
GROUP BY CASE WHEN date_str < '${event_date}' THEN '前' ELSE '后' END, ${dim};
```

- **输出：** 维度 × 前后对比表 + 变化率
- **陷阱：** 窗口不等长；跨大促日；比率指标对率值求平均（必须分子分母分别聚合后再除）
- **特别提示：** 若几乎所有维度同向变化，多半是季节性/大促共同因素，**不要直接归因于策略变更**；补充同比差分剥离季节性

### MTD-05 环比/同比

- **触发：** "环比""同比""比上个月""比去年"
- **适用表：** T1
- **参数：** 对比方式、指标
- **步骤：**
  1. 环比 = (本期 − 环比期)/环比期，环比期 = 起止日各回拨 1 个月（等长窗口）
  2. 同比 = 起止日各回拨 1 年（**本业务域约定：日历日回拨**，与 monthly-ops-analysis 源脚本 S2/S3 一致；不用 T−364 周对齐）
- **伪 SQL：**

```sql
,periods AS (
    SELECT '本期' AS date_type, TO_CHAR(start_dt,'yyyy-mm-dd') AS start_date, ... FROM params
    UNION ALL SELECT '环比上一周期', TO_CHAR(DATEADD(start_dt,-1,'mm'),'yyyy-mm-dd'), ... FROM params
    UNION ALL SELECT '同比上一周期', TO_CHAR(DATEADD(start_dt,-1,'yyyy'),'yyyy-mm-dd'), ... FROM params
)
```

- **输出：** 环比% / 同比% 变化表
- **陷阱：** 环比窗口是"上月同期"非上月整月（10-01~10-18 的环比是 09-01~09-18）；跨月时环比窗口天数可能不等（如 3-31 vs 2-28），需检查 DATEDIFF
- **特别提示：** 占比类指标的环比用比差（pp，M24），不用相对比

### MTD-06 交叉分析

- **触发：** "XX 和 YY 交叉""分部门看品类""新老品 × 大类"
- **适用表：** T1
- **参数：** 维度 A、维度 B、度量
- **步骤：**
  1. 按两维度分组聚合
  2. 发现结构性差异（如某部门某品类异常低）
- **伪 SQL：**

```sql
SELECT  ${dim_a}, ${dim_b}, SUM(sale_amount_usd) AS gmv, COUNT(DISTINCT 组合品归一skc) AS 在架skc
FROM    T1 a（JOIN periods）WHERE 基础过滤
GROUP BY ${dim_a}, ${dim_b} ORDER BY gmv DESC LIMIT 100;
```

- **输出：** 两维度交叉表
- **陷阱：** 二级品类 × 部门交叉行数可达数百，需 LIMIT；组合品归一 CASE 表达式较长，两维度 GROUP BY 时注意 SELECT 与 GROUP BY 列一致
- **特别提示：** 常用交叉：业务部门 × 是否当年新品（增长来源定位）、big_category × popular_type（商品分层）

### MTD-07 探查枚举

- **触发：** 字段取值未知、枚举不确定（如首次使用 tab_tag/style_tag/nation_line_name 等未登记字段）
- **适用表：** T1
- **参数：** 探查字段、过滤条件
- **步骤：**
  1. `SELECT 字段, COUNT(DISTINCT skc) FROM T1 WHERE pt='${pt}' AND is_online_adjustment=1 GROUP BY 字段`
  2. 固化为映射规则后再进入正式分析
- **输出：** 取值分布表 → 映射规则
- **陷阱：** 前置步骤，映射未确认前不做正式结论；分区选最新完整分区
- **特别提示：** 禁止凭假设写枚举值——已登记枚举见 warehouse_schema.md，新增维度字段必先探查

### MTD-08 漏斗转化率分析

- **触发：** "转化率""漏斗""流失""加购""点击率"
- **适用表：** T1（漏斗层自含于同一行，无需事件表）
- **参数：** 维度（可选）、周期窗口
- **步骤：**
  1. 聚合各层 UV：商列浏览→商列点击→详情页→详情页加购→销量
  2. 层间转化率分子分母分别 SUM 后再除
  3. 与环比期同结构对比，定位转化率掉的那一层
- **伪 SQL：**

```sql
SELECT  ${dim}, b.date_type,
        SUM(collection_view_user) AS 商列浏览uv, SUM(collection_click_user) AS 商列点击uv,
        SUM(pdp_view_user) AS 详情页uv, SUM(pdp_add_to_cart_user) AS 详情页加车uv,
        SUM(collection_click_user) / NULLIF(SUM(collection_view_user),0) AS ctr,
        SUM(pdp_add_to_cart_user) / NULLIF(SUM(pdp_view_user),0) AS 加车率,
        SUM(sale_quantity) / NULLIF(SUM(pdp_view_user),0) AS cvr
FROM    T1 a JOIN periods b ON ... WHERE 基础过滤
GROUP BY ${dim}, b.date_type;
```

- **输出：** 各层 UV + 转化率 × 周期对比表
- **陷阱：** 埋点 UV 覆盖范围与交易字段不完全对齐，报告须标注口径；UV 是"人"销量是"件"，CVR 是件/人
- **特别提示：** 按维度拆分可定位流失严重的维度值；跨层不可回退（用户可能直达详情页，层间转化率 >100% 不代表错误）

---

### MTD-09 量价拆解（销售归因特有）

- **触发：** "GMV 为什么涨/跌""是量的问题还是价的问题""销量/客单价影响"
- **适用表：** T1
- **参数：** 时间窗、维度
- **步骤：**
  1. 按 periods 算本期/环比期的销量与平均售价
  2. 应用分解：`ΔGMV = Δ量×基准均价 + 基准量×Δ价 + Δ量×Δ价`（基准取环比期值）
  3. 按维度重复，量效应/价效应分别排序
- **伪 SQL：**

```sql
SELECT  ${dim},
        SUM(IF(date_type='本期', sale_quantity, 0))       AS q1,
        SUM(IF(date_type='环比上一周期', sale_quantity, 0)) AS q0,
        SUM(IF(date_type='本期', sale_amount_usd, 0))      AS g1,
        SUM(IF(date_type='环比上一周期', sale_amount_usd, 0)) AS g0
FROM    T1 a JOIN periods b ON ... WHERE 基础过滤 GROUP BY ${dim}
-- 后处理：p1=g1/q1, p0=g0/q0；量效应=(q1-q0)*p0；价效应=q0*(p1-p0)；交互=(q1-q0)*(p1-p0)
```

- **输出：** 维度 × {量效应, 价效应, 交互效应} 分解表
- **陷阱：** 均价是聚合口径（GMV/销量）非算术均价；维度均价环比剧烈变化往往是品类结构迁移（混合效应），不是真实涨价降价
- **特别提示：** 量效应主导 → 查供给（MTD-11）或流量（MTD-08）；价效应主导 → 查结构（MTD-06 品类交叉）或促销折扣

### MTD-10 涨跌贡献度分解（销售归因特有）

- **触发：** "主要拖累是谁""贡献最大""哪个品类导致下滑"
- **适用表：** T1
- **参数：** 时间窗、贡献维度（品类/部门/新老品/popular_type）
- **步骤：**
  1. 按维度算 `(本期GMV - 环比GMV)` 差额
  2. 负差额（拖累）与正差额（驱动）分别按绝对值排序
  3. 交叉验证：各维度差额合计 == 整体差额，不等则检查口径
- **伪 SQL：**

```sql
SELECT  ${dim},
        SUM(IF(date_type='本期', sale_amount_usd, 0))
          - SUM(IF(date_type='环比上一周期', sale_amount_usd, 0)) AS delta_gmv
FROM    T1 a JOIN periods b ON ... WHERE 基础过滤 GROUP BY ${dim}
ORDER BY delta_gmv;  -- 升序=拖累榜，降序=驱动榜
```

- **输出：** 贡献度排序表（含贡献占比 = delta/整体delta）
- **陷阱：** 必须过体量门槛（MTD-02），否则尾部品类噪声淹没主因；差额合计≠整体差额说明维度有 NULL 未归组
- **特别提示：** 报告固定给 Top3 拖累 + Top3 驱动，并注明贡献占比

### MTD-11 三因子诊断（销售归因特有）

- **触发：** "流量/转化/客单哪个出了问题""UV 掉了""转化率下滑"
- **适用表：** T1
- **参数：** 时间窗、诊断对象维度值（如"泳衣"）
- **步骤：**
  1. 对目标维度算本期/环比期的 `详情页UV、CVR、平均售价` 三因子
  2. 逐因子算环比变化，定位变化幅度最大的因子为主因
  3. 主因为 UV → 再拆商列浏览 UV 与 CTR（MTD-08）；主因为 CVR → 拆加车率与商品分层（M18/M19）；主因为均价 → 拆品类结构（MTD-06）
- **伪 SQL：**

```sql
SELECT  b.date_type,
        SUM(pdp_view_user)                                  AS uv,
        SUM(sale_quantity)  / NULLIF(SUM(pdp_view_user),0)  AS cvr,
        SUM(sale_amount_usd)/ NULLIF(SUM(sale_quantity),0)  AS 均价,
        SUM(sale_amount_usd)                                AS gmv
FROM    T1 a JOIN periods b ON ... WHERE 基础过滤 AND ${维度过滤：如 big_category='泳衣'}
GROUP BY b.date_type;
```

- **输出：** 三因子 × 周期对比表 + 主因判定结论
- **陷阱：** 三因子相乘恒等于 GMV（恒等式），但因子间不独立（UV 降可能因爆款断货连带 CVR 变化），主因判定写"数据主因"而非"因果结论"
- **特别提示：** 恒等式作交叉验证：`UV环比 × CVR环比 × 均价环比 ≈ GMV环比`

### MTD-12 目标达成对比（销售归因特有）

- **触发：** "达成率""目标""缺口""KPI 完成情况"
- **适用表：** T2（月表，目标自含）
- **参数：** 月份（${month}，yyyy-mm）
- **步骤：**
  1. 按 `month_str = ${month}` 过滤，`PT > 0 AND is_online_adjust = 1 AND big_category != '赠品'`
  2. 部门实际值：`SUM(IF(business_group_name='XX' AND is_gift_cart='否' [AND big_category='成衣'], sale_amount_usd, NULL))`（成衣一部/二部、成衣合计须限定 `big_category='成衣'`）
  3. 达成率 = 实际/目标（目标 0 记 0）
  4. 缺口 = 实际 − 目标，按缺口排序定位薄弱部门
- **伪 SQL：**

```sql
SELECT  nvl(shiji.idx, mubiao.idx) AS idx, 月份,
        nvl(成衣一部目标,0), nvl(成衣一部实际,0), ...
FROM    (目标表 UNION 实际表) -- 实际：T2 按 style_position_adjust='正常目标' 聚合
```

- **输出：** 部门 × {目标, 实际, 达成率, 缺口} 表
- **陷阱：** T2 目标挂在 `style_position_adjust`（正常目标/无库存测试款）上，取数必须带此维度；全品类实际只加总 9 个已知部门，不 DISTINCT 部门会引入新部门重复计数
- **特别提示：** 目标口径为 `is_gift_cart='否'`；达成率表格须注明"月表口径"

### MTD-13 新老品结构分析（销售归因特有）

- **触发：** "新品表现""老品下滑""新品占比""增长靠新品还是老品"
- **适用表：** T1
- **参数：** 时间窗、新老口径（当年/当月）
- **步骤：**
  1. 构造 `是否当年新品`（跨月安全）或 `是否当月新品`（仅窗口在同一自然月内）
  2. 按 新老品 × 大类/部门 聚合 GMV、销量、在架 SKC
  3. 算新品 GMV 占比及占比环比（pp）
  4. 贡献拆分：整体 ΔGMV = 新品增量 + 老品增量 + 结构交互
- **伪 SQL：**

```sql
SELECT  是否当年新品, big_category,
        SUM(sale_amount_usd) AS gmv,
        SUM(sale_amount_usd) / NULLIF(SUM(SUM(sale_amount_usd)) OVER (PARTITION BY date_type),0) AS 占比
FROM    T1 a JOIN periods b ON ... WHERE 基础过滤
GROUP BY 是否当年新品, big_category, b.date_type;
```

- **输出：** 新老品结构表（当期 vs 环比占比）+ 增长贡献拆分
- **陷阱：** 当月新品维度跨月查询必错（见 metrics_definitions 陷阱 1）；渠道限定 `NVL(channels,'独立站') REGEXP '独立站'` 不可省
- **特别提示：** 新品占比升 + 老品基本盘跌 = "新品依赖症"，报告中要分开表述

---

## L3 场景配置

| 场景 ID | 场景名称 | 触发词 | 方法链 | 维度 | 指标 | 必需输入 | 固化查询 | 备注 |
| ----- | ----------------- | ------------ | --------------- | ------- | -------------- | -------------- | ------------- | --------- |
| S01 | GMV 趋势归因 | GMV为什么涨/跌、销售额变化原因、这个月卖得好不好 | MTD-01 → MTD-10 → MTD-09 | big_category / 业务部门 | M01,M02,M03,M21 | start_date, end_date | — | 环比=上月同期等长窗口；T+1 时效 |
| S02 | 品类/部门对比归因 | 哪个品类拖累、部门表现对比、结构变化 | MTD-01 → MTD-02 → MTD-06 | second_category / 业务部门 | M01,M06,M07,M23,M24,M25 | start_date, end_date | — | 排行先过 2% 体量门槛 |
| S03 | 新老品结构归因 | 新品表现、老品下滑、增长靠新品还是老品 | MTD-01 → MTD-13 → MTD-06 | 是否当年新品 × big_category | M01,M23,M24 | start_date, end_date | — | 当月口径仅限同月窗口 |
| S04 | 转化漏斗归因 | 转化率下滑、流量掉了、漏斗流失、加购率 | MTD-01 → MTD-08 → MTD-11 | big_category / second_category | M10-M17 | start_date, end_date | — | 埋点 UV 口径须标注 |
| S05 | 异常诊断（单维度下滑下钻） | XX品类跌了、XX部门异常、销量为什么掉 | MTD-10 → MTD-11 → MTD-08 → 供给检查 | 目标维度值（用户指定或 Top 拖累） | M01,M06,M04,M05,M18,库存 | 目标维度值（若用户未指明则取 MTD-10 Top1 拖累并告知） | — | 诊断顺序：供给→流量→效率→侵蚀 |
| S06 | 目标达成缺口归因 | 达成率、目标缺口、KPI 差多少 | MTD-12 → MTD-10 → MTD-11 | 业务部门（月表口径） | M01,M20 | month（yyyy-mm，默认当月） | — | 目标在 T2 自含，无需用户提供目标值 |
| S07 | 品类排行速查 | Top 品类、卖得最好的品类、GMV 排行 | MTD-01 → MTD-02 | big_category / second_category / third_category | M01,M23,M24 | start_date, end_date | — | 简单场景，直接出表+条形图 |

> **必需输入列**：声明该场景启动前必须从用户获取的数据（目标值、文件等）。空或 "—" = 无需额外输入。Agent 在前置校验阶段检查，未提供则主动索取。所有场景的公共必需输入为 `start_date`/`end_date`（yyyy-mm-dd），S05 的目标维度值与 S06 的 month 为场景特有输入。
> **固化查询列**：填写关联的 FQ-XX 编号（指向 [fixed_queries.md](fixed_queries.md)），未固化填 "—"。有固化查询的场景优先执行固化 SQL，无固化查询的场景走方法链编排。

### 场景配置模板（新增场景用）

```yaml
场景ID: Sx
场景名: <一句话>
触发词: [<口语化表达1>, <口语化表达2>, ...]   # 既有术语也有日常说法
方法链: [MTD-xx, MTD-yy]   # 引用 L2
维度: <group by 字段>
指标: [M_xx, M_yy]          # 引用 L1
必需输入: <描述需要的数据和语义，如：目标维度值（品类/部门名）>
固化查询: ""                  # 已验证后填写 FQ-xx，未固化留空
备注: <如：当月新品维度仅限同月窗口>
```

---

## L4 决策树（Agent 执行路径）

```
1. 解析意图
   ├─ 命中 L3 场景（S01-S07）？ → 取该场景配置（维度/指标/方法链/固化查询）
   └─ 未命中？ → 用 L2 方法临时编排（先 MTD-01 基线），并建议沉淀为新场景

2. 前置校验
   ├─ 必需输入检查：start_date/end_date 缺失？→ 向用户索取（提示：数据 T+1，end_date 最晚为昨天）
   ├─ S05 目标维度值未指定？→ 先跑 MTD-10 取 Top1 拖累，向用户确认后再下钻
   ├─ S06 month 未指定？→ 默认当月并告知
   ├─ 时间窗跨月且场景涉及"当月新品"口径？→ 强制降级为"当年新品"口径并告知
   ├─ 使用未登记维度字段（tab_tag/style_tag/nation_line_name…）？→ 先跑 MTD-07 探查
   └─ 环比窗口天数不等（如 3-31 vs 2-28）？→ 提示口径差异后再继续

3. 执行路径选择
   ├─ 场景有固化查询（FQ-XX）？
   │   └─ 从 fixed_queries.md 取 SQL → 注入 ${param} → odps-query 执行 → 跳到第 5 步
   └─ 无固化查询？
       ├─ 选表（L0 选表规则：时间窗场景用 T1，目标达成用 T2）
       └─ 按方法链顺序执行（L2 步骤 + 伪 SQL，经 odps-query 只读执行）
           └─ 每步校验：窗口等长？体量门槛？比率分子分母分别聚合？基础过滤继承？组合品归一？

4. （可选）固化建议
   └─ 方法链执行完毕、结果经确认正确 → 建议将该 SQL 固化到 fixed_queries.md（含验证日期与参数说明）

5. 输出（按 output_standards.md 七段式 HTML 报告）
   └─ 结论区分"统计显著"与"业务显著"，小样本不下强结论
```

### 全局 Checklist

> 方法链执行时每步必过：

1. **对比窗口等长**：环比 = 起止日各回拨 1 个月（等长）；跨大小月注意天数差异；避开大促与异常日（若窗口含大促须在报告标注）。
2. **排行/分层先过体量门槛**：GMV 占比 < 2% 的维度值不参与"拖累/驱动"结论。
3. **比率指标聚合规则**：分子分母分别 SUM 后再除，禁止对率值求平均；分母一律 `NULLIF(x,0)`。
4. **数据不足声明**：查询返回行数 < 10、时间窗口 < 7 天、或单维度日 GMV 很小时，提示"样本量不足，结论仅供参考"。
5. **建议必须可执行**：禁止"优化一下"，必须具体到"XX 维度 XX 指标 XX%，建议 XX 动作"（运营动作 / 品类策略 / 用户运营三选一起步，按优先级排序）。
6. **基础过滤继承**：每个 SQL 必须带 `is_online_adjustment=1 AND pt>='20240101' AND style_position!='无库存测试款' AND big_category!='赠品'`。
7. **组合品归一**：所有 SKC 计数走归一 CASE 表达式（warehouse_schema §一）。
8. **MAPJOIN hint**：periods 非等值 JOIN（`>=`/`<=`）必须加 `/* +MAPJOIN(b) */`；ORDER BY 引用的列必须在 GROUP BY 中。
9. **数字可追溯**：报告中每个数字必须来自某次 odps-query 结果或已声明的明细加总，禁止估算。
