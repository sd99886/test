-- 派生脚本（generated）：三级品类拆解
-- 源脚本: skill数据集2-品类拆解数据.txt (S2, readonly)
-- 用途: 报告 §4 表B（三级品类），基于 S2 恢复 third_category 维度，其余口径/过滤/指标与 S2 完全一致
-- 参数: start_date / end_date（yyyy-mm-dd，写入 SQL 时带引号）
-- 继承过滤: is_online_adjustment=1, pt>=20240101, style_position!='无库存测试款', big_category!='赠品'
-- 创建日期: 2026-10-21
-- status: candidate

-- 对比上一周期：环比 + 同比（透视成列）+ 全指标同环比 + 指定指标占比
-- 脚本参数：start_date、end_date（yyyy-mm-dd，参数值不要加引号）
-- 环比：等长、紧挨本期之前；同比：起止日各回拨 1 年
-- 同环比公式：(本期 - 对比期) / 对比期
-- 占比：该维度行 / 全部维度合计（按各自周期算）；占比环比/同比用百分点差（本期占比 - 
-- 新品字段含当月新品维度，不要跨月查询！

WITH params AS (
    SELECT
        CAST(TO_DATE('2026-10-01', 'yyyy-mm-dd') AS DATETIME) AS start_dt,
        CAST(TO_DATE('2026-10-20', 'yyyy-mm-dd') AS DATETIME) AS end_dt,
        DATEDIFF(
            CAST(TO_DATE('2026-10-20', 'yyyy-mm-dd') AS DATETIME),
            CAST(TO_DATE('2026-10-01', 'yyyy-mm-dd') AS DATETIME),
            'dd'
        ) + 1 AS period_days
)
,periods AS (
    SELECT
        '本期' AS date_type,
        1 AS date_sort,
        TO_CHAR(start_dt, 'yyyy-mm-dd') AS start_date,
        TO_CHAR(end_dt, 'yyyy-mm-dd') AS end_date
    FROM params

    UNION ALL

    -- -- 按天数倒退
    -- SELECT
    --     '环比上一周期' AS date_type,
    --     2 AS date_sort,
    --     TO_CHAR(DATEADD(start_dt, -period_days, 'dd'), 'yyyy-mm-dd') AS start_date,
    --     TO_CHAR(DATEADD(start_dt, -1, 'dd'), 'yyyy-mm-dd') AS end_date
    -- FROM params
    -- 环比 = 上月同期：起止各减 1 个月
    SELECT
        '环比上一周期' AS date_type,
        2 AS date_sort,
        TO_CHAR(DATEADD(start_dt, -1, 'mm'), 'yyyy-mm-dd') AS start_date,
        TO_CHAR(DATEADD(end_dt, -1, 'mm'), 'yyyy-mm-dd') AS end_date
    FROM params

    UNION ALL

    SELECT
        '同比上一周期' AS date_type,
        3 AS date_sort,
        TO_CHAR(DATEADD(start_dt, -1, 'yyyy'), 'yyyy-mm-dd') AS start_date,
        TO_CHAR(DATEADD(end_dt, -1, 'yyyy'), 'yyyy-mm-dd') AS end_date
    FROM params
)
,agg AS (
    SELECT
        /* +MAPJOIN(b)*/
        b.date_type
        ,b.date_sort
        ,b.start_date
        ,b.end_date
        ,CASE
            WHEN is_new_this_year = '新品' AND nvl(channels, '独立站') regexp '独立站' THEN '当年新品'
            WHEN is_new_this_year = '未上架' THEN '当年未上架'
            ELSE '当年老品'
        END AS 是否当年新品
        ,CASE
            WHEN is_new_this_month = '新品' AND nvl(channels, '独立站') regexp '独立站' THEN '当月新品'
            WHEN is_new_this_month = '未上架' THEN '当月未上架'
            ELSE '当月老品'
        END AS 是否当月新品
        ,big_category
        ,second_category
        ,third_category
        ,COUNT(DISTINCT CASE
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
        END) AS 在架skc
        ,SUM(is_online_adjustment) AS 在架天数
        ,SUM(sale_amount_usd) AS 销售额
        ,SUM(sale_quantity) AS 销量
        ,SUM(return_quantity) AS 退货数量
        ,SUM(total_refund_amount_usd) AS 退款总额
        ,SUM(collection_view_user) AS 商列浏览uv
        ,SUM(collection_click_user) AS 商列点击uv
        ,SUM(collection_add_to_cart_user) AS 商列加车uv
        ,SUM(pdp_view_user) AS 详情页uv
        ,SUM(pdp_add_to_cart_user) AS 详情页加车uv
        ,SUM(sale_amount_usd) / NULLIF(SUM(sale_quantity), 0) AS 平均售价
        ,SUM(is_online_adjustment) / NULLIF(COUNT(DISTINCT CASE
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
        END), 0) AS 款均在架天数
        ,SUM(sale_amount_usd) / NULLIF(COUNT(DISTINCT CASE
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
        END), 0) AS 款效
        ,SUM(sale_quantity) / NULLIF(COUNT(DISTINCT CASE
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
        END), 0) AS 款均销量
        ,SUM(pdp_view_user) / NULLIF(COUNT(DISTINCT CASE
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
        END), 0) AS 款均uv
        ,SUM(collection_click_user) / NULLIF(SUM(collection_view_user), 0) AS ctr
        ,SUM(sale_quantity) / NULLIF(SUM(pdp_view_user), 0) AS cvr
        ,SUM(sale_amount_usd) / NULLIF(SUM(pdp_view_user), 0) AS uv价值
        ,SUM(pdp_add_to_cart_user) / NULLIF(SUM(pdp_view_user), 0) AS 加车率uv
        ,SUM(total_refund_amount_usd) / NULLIF(SUM(sale_amount_usd), 0) AS 退货率
        ,SUM(return_quantity) / NULLIF(SUM(sale_quantity), 0) AS 退件率
        ,SUM(sale_available_inventory)
            / (DATEDIFF(TO_DATE(b.end_date, 'yyyy-mm-dd'), TO_DATE(b.start_date, 'yyyy-mm-dd')) + 1) AS 日均可售库存
        ,SUM(transit_inventory)
            / (DATEDIFF(TO_DATE(b.end_date, 'yyyy-mm-dd'), TO_DATE(b.start_date, 'yyyy-mm-dd')) + 1) AS 日均采购在途库存
        ,(nvl(SUM(IF(a.date_str = b.start_date, sale_available_inventory, NULL)), 0)
          + nvl(SUM(IF(a.date_str = b.end_date, sale_available_inventory, NULL)), 0)) / 2 AS 平均可售库存
        ,(nvl(SUM(IF(a.date_str = b.start_date, transit_inventory, NULL)), 0)
          + nvl(SUM(IF(a.date_str = b.end_date, transit_inventory, NULL)), 0)) / 2 AS 平均采购在途库存
        ,count(distinct 
        case 
        when popular_type in ('畅销','爆款','大爆款','超爆款') THEN 
            CASE
                WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
                WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
            END
        end)
        /COUNT(DISTINCT 
        CASE
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
        END) AS 成功款占比
        ,count(distinct 
        case 
        when popular_type in ('爆款','大爆款','超爆款') THEN 
            CASE
                WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
                WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
            END
        end)
        /COUNT(DISTINCT 
        CASE
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NULL THEN a.skc
            WHEN a.skc IS NOT NULL AND c.combination_skc IS NOT NULL THEN c.combination_skc
        END) AS 爆款以上占比
    FROM cupshe_bigdata_ads.ads_prod_skc_product_info_di a
    JOIN periods b
        ON a.date_str >= b.start_date
       AND a.date_str <= b.end_date
    LEFT JOIN (
        SELECT DISTINCT skc, combination_skc
        FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df
    ) c
        ON a.skc = c.skc
    WHERE a.is_online_adjustment = 1
      AND pt >= 20240101
      AND style_position != '无库存测试款'
      AND big_category != '赠品'
    GROUP BY
        b.date_type
        ,b.date_sort
        ,b.start_date
        ,b.end_date
        ,CASE
            WHEN is_new_this_year = '新品' AND nvl(channels, '独立站') regexp '独立站' THEN '当年新品'
            WHEN is_new_this_year = '未上架' THEN '当年未上架'
            ELSE '当年老品'
        END
        ,CASE
            WHEN is_new_this_month = '新品' AND nvl(channels, '独立站') regexp '独立站' THEN '当月新品'
            WHEN is_new_this_month = '未上架' THEN '当月未上架'
            ELSE '当月老品'
        END
        ,big_category
        ,second_category
        ,third_category
)
,pivoted AS (
    SELECT
        是否当年新品
        ,是否当月新品
        ,big_category
        ,second_category
        ,third_category

        ,MAX(CASE WHEN date_type = '本期' THEN start_date END) AS 本期_start
        ,MAX(CASE WHEN date_type = '本期' THEN end_date END) AS 本期_end
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN start_date END) AS 环比_start
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN end_date END) AS 环比_end
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN start_date END) AS 同比_start
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN end_date END) AS 同比_end

        -- 在架skc
        ,MAX(CASE WHEN date_type = '本期' THEN 在架skc END) AS 本期_在架skc
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 在架skc END) AS 环比_在架skc
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 在架skc END) AS 同比_在架skc
        -- 在架天数
        ,MAX(CASE WHEN date_type = '本期' THEN 在架天数 END) AS 本期_在架天数
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 在架天数 END) AS 环比_在架天数
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 在架天数 END) AS 同比_在架天数
        -- 销售额
        ,MAX(CASE WHEN date_type = '本期' THEN 销售额 END) AS 本期_销售额
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 销售额 END) AS 环比_销售额
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 销售额 END) AS 同比_销售额
        -- 销量
        ,MAX(CASE WHEN date_type = '本期' THEN 销量 END) AS 本期_销量
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 销量 END) AS 环比_销量
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 销量 END) AS 同比_销量
        -- 退货数量
        ,MAX(CASE WHEN date_type = '本期' THEN 退货数量 END) AS 本期_退货数量
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 退货数量 END) AS 环比_退货数量
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 退货数量 END) AS 同比_退货数量
        -- 退款总额
        ,MAX(CASE WHEN date_type = '本期' THEN 退款总额 END) AS 本期_退款总额
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 退款总额 END) AS 环比_退款总额
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 退款总额 END) AS 同比_退款总额
        -- 商列浏览uv
        ,MAX(CASE WHEN date_type = '本期' THEN 商列浏览uv END) AS 本期_商列浏览uv
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 商列浏览uv END) AS 环比_商列浏览uv
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 商列浏览uv END) AS 同比_商列浏览uv
        -- 商列点击uv
        ,MAX(CASE WHEN date_type = '本期' THEN 商列点击uv END) AS 本期_商列点击uv
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 商列点击uv END) AS 环比_商列点击uv
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 商列点击uv END) AS 同比_商列点击uv
        -- 商列加车uv
        ,MAX(CASE WHEN date_type = '本期' THEN 商列加车uv END) AS 本期_商列加车uv
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 商列加车uv END) AS 环比_商列加车uv
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 商列加车uv END) AS 同比_商列加车uv
        -- 详情页uv
        ,MAX(CASE WHEN date_type = '本期' THEN 详情页uv END) AS 本期_详情页uv
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 详情页uv END) AS 环比_详情页uv
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 详情页uv END) AS 同比_详情页uv
        -- 详情页加车uv
        ,MAX(CASE WHEN date_type = '本期' THEN 详情页加车uv END) AS 本期_详情页加车uv
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 详情页加车uv END) AS 环比_详情页加车uv
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 详情页加车uv END) AS 同比_详情页加车uv
        -- 平均售价
        ,MAX(CASE WHEN date_type = '本期' THEN 平均售价 END) AS 本期_平均售价
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 平均售价 END) AS 环比_平均售价
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 平均售价 END) AS 同比_平均售价
        -- 款均在架天数
        ,MAX(CASE WHEN date_type = '本期' THEN 款均在架天数 END) AS 本期_款均在架天数
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 款均在架天数 END) AS 环比_款均在架天数
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 款均在架天数 END) AS 同比_款均在架天数
        -- 款效
        ,MAX(CASE WHEN date_type = '本期' THEN 款效 END) AS 本期_款效
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 款效 END) AS 环比_款效
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 款效 END) AS 同比_款效
        -- 款均销量
        ,MAX(CASE WHEN date_type = '本期' THEN 款均销量 END) AS 本期_款均销量
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 款均销量 END) AS 环比_款均销量
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 款均销量 END) AS 同比_款均销量
        -- 款均uv
        ,MAX(CASE WHEN date_type = '本期' THEN 款均uv END) AS 本期_款均uv
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 款均uv END) AS 环比_款均uv
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 款均uv END) AS 同比_款均uv
        -- ctr
        ,MAX(CASE WHEN date_type = '本期' THEN ctr END) AS 本期_ctr
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN ctr END) AS 环比_ctr
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN ctr END) AS 同比_ctr
        -- cvr
        ,MAX(CASE WHEN date_type = '本期' THEN cvr END) AS 本期_cvr
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN cvr END) AS 环比_cvr
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN cvr END) AS 同比_cvr
        -- uv价值
        ,MAX(CASE WHEN date_type = '本期' THEN uv价值 END) AS 本期_uv价值
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN uv价值 END) AS 环比_uv价值
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN uv价值 END) AS 同比_uv价值
        -- 加车率uv
        ,MAX(CASE WHEN date_type = '本期' THEN 加车率uv END) AS 本期_加车率uv
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 加车率uv END) AS 环比_加车率uv
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 加车率uv END) AS 同比_加车率uv
        -- 退货率
        ,MAX(CASE WHEN date_type = '本期' THEN 退货率 END) AS 本期_退货率
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 退货率 END) AS 环比_退货率
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 退货率 END) AS 同比_退货率
        -- 退件率
        ,MAX(CASE WHEN date_type = '本期' THEN 退件率 END) AS 本期_退件率
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 退件率 END) AS 环比_退件率
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 退件率 END) AS 同比_退件率
        -- 日均可售库存
        ,MAX(CASE WHEN date_type = '本期' THEN 日均可售库存 END) AS 本期_日均可售库存
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 日均可售库存 END) AS 环比_日均可售库存
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 日均可售库存 END) AS 同比_日均可售库存
        -- 日均采购在途库存
        ,MAX(CASE WHEN date_type = '本期' THEN 日均采购在途库存 END) AS 本期_日均采购在途库存
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 日均采购在途库存 END) AS 环比_日均采购在途库存
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 日均采购在途库存 END) AS 同比_日均采购在途库存
        -- 平均可售库存
        ,MAX(CASE WHEN date_type = '本期' THEN 平均可售库存 END) AS 本期_平均可售库存
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 平均可售库存 END) AS 环比_平均可售库存
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 平均可售库存 END) AS 同比_平均可售库存
        -- 平均采购在途库存
        ,MAX(CASE WHEN date_type = '本期' THEN 平均采购在途库存 END) AS 本期_平均采购在途库存
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 平均采购在途库存 END) AS 环比_平均采购在途库存
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 平均采购在途库存 END) AS 同比_平均采购在途库存
        -- 成功款占比
        ,MAX(CASE WHEN date_type = '本期' THEN 成功款占比 END) AS 本期_成功款占比
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 成功款占比 END) AS 环比_成功款占比
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 成功款占比 END) AS 同比_成功款占比
        -- 爆款以上占比
        ,MAX(CASE WHEN date_type = '本期' THEN 爆款以上占比 END) AS 本期_爆款以上占比
        ,MAX(CASE WHEN date_type = '环比上一周期' THEN 爆款以上占比 END) AS 环比_爆款以上占比
        ,MAX(CASE WHEN date_type = '同比上一周期' THEN 爆款以上占比 END) AS 同比_爆款以上占比
        
    FROM agg
    GROUP BY
        是否当年新品
        ,是否当月新品
        ,big_category
        ,second_category
        ,third_category
)
SELECT
    是否当年新品
    ,是否当月新品
    ,big_category
    ,second_category
    ,third_category
    ,本期_start ,本期_end ,环比_start ,环比_end ,同比_start ,同比_end

    -- ===== 在架skc =====
    ,本期_在架skc 
    -- ,环比_在架skc ,同比_在架skc
    ,(本期_在架skc - 环比_在架skc) / NULLIF(环比_在架skc, 0) AS 在架skc_环比
    ,(本期_在架skc - 同比_在架skc) / NULLIF(同比_在架skc, 0) AS 在架skc_同比
    ,本期_在架skc / NULLIF(SUM(本期_在架skc) OVER (), 0) 本期_在架skc占比
    ,本期_在架skc / NULLIF(SUM(本期_在架skc) OVER (), 0)
        - 环比_在架skc / NULLIF(SUM(环比_在架skc) OVER (), 0) AS 在架skc占比_环比_比差 -- 比差
    ,本期_在架skc / NULLIF(SUM(本期_在架skc) OVER (), 0)
        - 同比_在架skc / NULLIF(SUM(同比_在架skc) OVER (), 0) AS 在架skc占比_同比_比差


    -- ===== 在架天数 =====
    ,本期_在架天数 
    -- ,环比_在架天数 ,同比_在架天数
    ,(本期_在架天数 - 环比_在架天数) / NULLIF(环比_在架天数, 0) AS 在架天数_环比
    ,(本期_在架天数 - 同比_在架天数) / NULLIF(同比_在架天数, 0) AS 在架天数_同比

    -- ===== 销售额 + 占比 =====
    ,本期_销售额 
    -- ,环比_销售额 ,同比_销售额
    ,(本期_销售额 - 环比_销售额) / NULLIF(环比_销售额, 0) AS 销售额_环比
    ,(本期_销售额 - 同比_销售额) / NULLIF(同比_销售额, 0) AS 销售额_同比
    ,本期_销售额 / NULLIF(SUM(本期_销售额) OVER (), 0) AS 本期_销售额占比
    -- ,环比_销售额 / NULLIF(SUM(环比_销售额) OVER (), 0) AS 环比_销售额占比,同比_销售额 / NULLIF(SUM(同比_销售额) OVER (), 0) AS 同比_销售额占比
    ,本期_销售额 / NULLIF(SUM(本期_销售额) OVER (), 0)
        - 环比_销售额 / NULLIF(SUM(环比_销售额) OVER (), 0) AS 销售额占比_环比_比差 
    ,本期_销售额 / NULLIF(SUM(本期_销售额) OVER (), 0)
        - 同比_销售额 / NULLIF(SUM(同比_销售额) OVER (), 0) AS 销售额占比_同比_比差

    -- ===== 销量 + 占比 =====
    ,本期_销量 
    --,环比_销量 ,同比_销量
    ,(本期_销量 - 环比_销量) / NULLIF(环比_销量, 0) AS 销量_环比
    ,(本期_销量 - 同比_销量) / NULLIF(同比_销量, 0) AS 销量_同比
    ,本期_销量 / NULLIF(SUM(本期_销量) OVER (), 0) AS 本期_销量占比
    --,环比_销量 / NULLIF(SUM(环比_销量) OVER (), 0) AS 环比_销量占比,同比_销量 / NULLIF(SUM(同比_销量) OVER (), 0) AS 同比_销量占比
    ,本期_销量 / NULLIF(SUM(本期_销量) OVER (), 0)
        - 环比_销量 / NULLIF(SUM(环比_销量) OVER (), 0) AS 销量占比_环比_比差
    ,本期_销量 / NULLIF(SUM(本期_销量) OVER (), 0)
        - 同比_销量 / NULLIF(SUM(同比_销量) OVER (), 0) AS 销量占比_同比_比差
    
    -- ===== 投入产出比 =====
    ,(本期_销量 / NULLIF(SUM(本期_销量) OVER (), 0))/ (本期_在架skc / NULLIF(SUM(本期_在架skc) OVER (), 0)) 本期_投入产出比
    ,(本期_销量 / NULLIF(SUM(本期_销量) OVER (), 0))/ (本期_在架skc / NULLIF(SUM(本期_在架skc) OVER (), 0))
    - (环比_销量 / NULLIF(SUM(环比_销量) OVER (), 0))/ (环比_在架skc / NULLIF(SUM(环比_在架skc) OVER (), 0)) 投入产出比_环比_比差
    ,(本期_销量 / NULLIF(SUM(本期_销量) OVER (), 0))/ (本期_在架skc / NULLIF(SUM(本期_在架skc) OVER (), 0))
    - (同比_销量 / NULLIF(SUM(同比_销量) OVER (), 0))/ (同比_在架skc / NULLIF(SUM(同比_在架skc) OVER (), 0)) 投入产出比_同比_比差

    -- ===== 退货数量 + 占比 =====
    ,本期_退货数量 
    -- ,环比_退货数量 ,同比_退货数量
    ,(本期_退货数量 - 环比_退货数量) / NULLIF(环比_退货数量, 0) AS 退货数量_环比
    ,(本期_退货数量 - 同比_退货数量) / NULLIF(同比_退货数量, 0) AS 退货数量_同比
    ,本期_退货数量 / NULLIF(SUM(本期_退货数量) OVER (), 0) AS 本期_退货数量占比
    --,环比_退货数量 / NULLIF(SUM(环比_退货数量) OVER (), 0) AS 环比_退货数量占比,同比_退货数量 / NULLIF(SUM(同比_退货数量) OVER (), 0) AS 同比_退货数量占比
    ,本期_退货数量 / NULLIF(SUM(本期_退货数量) OVER (), 0)
        - 环比_退货数量 / NULLIF(SUM(环比_退货数量) OVER (), 0) AS 退货数量占比_环比_比差
    ,本期_退货数量 / NULLIF(SUM(本期_退货数量) OVER (), 0)
        - 同比_退货数量 / NULLIF(SUM(同比_退货数量) OVER (), 0) AS 退货数量占比_同比_比差

    -- ===== 退款总额 + 占比 =====
    ,本期_退款总额 
    --,环比_退款总额 ,同比_退款总额
    ,(本期_退款总额 - 环比_退款总额) / NULLIF(环比_退款总额, 0) AS 退款总额_环比
    ,(本期_退款总额 - 同比_退款总额) / NULLIF(同比_退款总额, 0) AS 退款总额_同比
    ,本期_退款总额 / NULLIF(SUM(本期_退款总额) OVER (), 0) AS 本期_退款总额占比
    -- ,环比_退款总额 / NULLIF(SUM(环比_退款总额) OVER (), 0) AS 环比_退款总额占比,同比_退款总额 / NULLIF(SUM(同比_退款总额) OVER (), 0) AS 同比_退款总额占比
    ,本期_退款总额 / NULLIF(SUM(本期_退款总额) OVER (), 0)
        - 环比_退款总额 / NULLIF(SUM(环比_退款总额) OVER (), 0) AS 退款总额占比_环比_比差
    ,本期_退款总额 / NULLIF(SUM(本期_退款总额) OVER (), 0)
        - 同比_退款总额 / NULLIF(SUM(同比_退款总额) OVER (), 0) AS 退款总额占比_同比_比差

    -- ===== 商列浏览uv =====
    ,本期_商列浏览uv 
    --,环比_商列浏览uv ,同比_商列浏览uv
    ,(本期_商列浏览uv - 环比_商列浏览uv) / NULLIF(环比_商列浏览uv, 0) AS 商列浏览uv_环比
    ,(本期_商列浏览uv - 同比_商列浏览uv) / NULLIF(同比_商列浏览uv, 0) AS 商列浏览uv_同比

    -- ===== 商列点击uv =====
    ,本期_商列点击uv 
    --,环比_商列点击uv ,同比_商列点击uv
    ,(本期_商列点击uv - 环比_商列点击uv) / NULLIF(环比_商列点击uv, 0) AS 商列点击uv_环比
    ,(本期_商列点击uv - 同比_商列点击uv) / NULLIF(同比_商列点击uv, 0) AS 商列点击uv_同比

    -- ===== 商列加车uv =====
    ,本期_商列加车uv 
    --,环比_商列加车uv ,同比_商列加车uv
    ,(本期_商列加车uv - 环比_商列加车uv) / NULLIF(环比_商列加车uv, 0) AS 商列加车uv_环比
    ,(本期_商列加车uv - 同比_商列加车uv) / NULLIF(同比_商列加车uv, 0) AS 商列加车uv_同比

    -- ===== 详情页uv + 占比 =====
    ,本期_详情页uv 
    --,环比_详情页uv ,同比_详情页uv
    ,(本期_详情页uv - 环比_详情页uv) / NULLIF(环比_详情页uv, 0) AS 详情页uv_环比
    ,(本期_详情页uv - 同比_详情页uv) / NULLIF(同比_详情页uv, 0) AS 详情页uv_同比
    ,本期_详情页uv / NULLIF(SUM(本期_详情页uv) OVER (), 0) AS 本期_详情页uv占比
    --,环比_详情页uv / NULLIF(SUM(环比_详情页uv) OVER (), 0) AS 环比_详情页uv占比,同比_详情页uv / NULLIF(SUM(同比_详情页uv) OVER (), 0) AS 同比_详情页uv占比
    ,本期_详情页uv / NULLIF(SUM(本期_详情页uv) OVER (), 0)
        - 环比_详情页uv / NULLIF(SUM(环比_详情页uv) OVER (), 0) AS 详情页uv占比_环比_比差
    ,本期_详情页uv / NULLIF(SUM(本期_详情页uv) OVER (), 0)
        - 同比_详情页uv / NULLIF(SUM(同比_详情页uv) OVER (), 0) AS 详情页uv占比_同比_比差

    -- ===== 详情页加车uv =====
    ,本期_详情页加车uv 
    --,环比_详情页加车uv ,同比_详情页加车uv
    ,(本期_详情页加车uv - 环比_详情页加车uv) / NULLIF(环比_详情页加车uv, 0) AS 详情页加车uv_环比
    ,(本期_详情页加车uv - 同比_详情页加车uv) / NULLIF(同比_详情页加车uv, 0) AS 详情页加车uv_同比

    -- ===== 平均售价 =====
    ,本期_平均售价 
    --,环比_平均售价 ,同比_平均售价
    ,(本期_平均售价 - 环比_平均售价) / NULLIF(环比_平均售价, 0) AS 平均售价_环比
    ,(本期_平均售价 - 同比_平均售价) / NULLIF(同比_平均售价, 0) AS 平均售价_同比

    -- ===== 款均在架天数 =====
    ,本期_款均在架天数 
    --,环比_款均在架天数 ,同比_款均在架天数
    ,(本期_款均在架天数 - 环比_款均在架天数) / NULLIF(环比_款均在架天数, 0) AS 款均在架天数_环比
    ,(本期_款均在架天数 - 同比_款均在架天数) / NULLIF(同比_款均在架天数, 0) AS 款均在架天数_同比

    -- ===== 款效 =====
    ,本期_款效 
    --,环比_款效 ,同比_款效
    ,(本期_款效 - 环比_款效) / NULLIF(环比_款效, 0) AS 款效_环比
    ,(本期_款效 - 同比_款效) / NULLIF(同比_款效, 0) AS 款效_同比

    -- ===== 款均销量 =====
    ,本期_款均销量 
    --,环比_款均销量 ,同比_款均销量
    ,(本期_款均销量 - 环比_款均销量) / NULLIF(环比_款均销量, 0) AS 款均销量_环比
    ,(本期_款均销量 - 同比_款均销量) / NULLIF(同比_款均销量, 0) AS 款均销量_同比

    -- ===== 款均uv =====
    ,本期_款均uv 
    --,环比_款均uv ,同比_款均uv
    ,(本期_款均uv - 环比_款均uv) / NULLIF(环比_款均uv, 0) AS 款均uv_环比
    ,(本期_款均uv - 同比_款均uv) / NULLIF(同比_款均uv, 0) AS 款均uv_同比

    -- ===== ctr =====
    ,本期_ctr 
    --,环比_ctr ,同比_ctr
    ,(本期_ctr - 环比_ctr) / NULLIF(环比_ctr, 0) AS ctr_环比
    ,(本期_ctr - 同比_ctr) / NULLIF(同比_ctr, 0) AS ctr_同比

    -- ===== cvr =====
    ,本期_cvr
    --,环比_cvr ,同比_cvr
    ,(本期_cvr - 环比_cvr) / NULLIF(环比_cvr, 0) AS cvr_环比
    ,(本期_cvr - 同比_cvr) / NULLIF(同比_cvr, 0) AS cvr_同比

    -- ===== uv价值 =====
    ,本期_uv价值 
    --,环比_uv价值 ,同比_uv价值
    ,(本期_uv价值 - 环比_uv价值) / NULLIF(环比_uv价值, 0) AS uv价值_环比
    ,(本期_uv价值 - 同比_uv价值) / NULLIF(同比_uv价值, 0) AS uv价值_同比

    -- ===== 加车率uv =====
    ,本期_加车率uv 
    --,环比_加车率uv ,同比_加车率uv
    ,(本期_加车率uv - 环比_加车率uv) / NULLIF(环比_加车率uv, 0) AS 加车率uv_环比
    ,(本期_加车率uv - 同比_加车率uv) / NULLIF(同比_加车率uv, 0) AS 加车率uv_同比

    -- ===== 退货率 =====
    ,本期_退货率 
    --,环比_退货率 ,同比_退货率
    ,(本期_退货率 - 环比_退货率) / NULLIF(环比_退货率, 0) AS 退货率_环比
    ,(本期_退货率 - 同比_退货率) / NULLIF(同比_退货率, 0) AS 退货率_同比

    -- ===== 退件率 =====
    ,本期_退件率 
    --,环比_退件率 ,同比_退件率
    ,(本期_退件率 - 环比_退件率) / NULLIF(环比_退件率, 0) AS 退件率_环比
    ,(本期_退件率 - 同比_退件率) / NULLIF(同比_退件率, 0) AS 退件率_同比

    -- ===== 日均可售库存 =====
    ,本期_日均可售库存 
    --,环比_日均可售库存 ,同比_日均可售库存
    ,(本期_日均可售库存 - 环比_日均可售库存) / NULLIF(环比_日均可售库存, 0) AS 日均可售库存_环比
    ,(本期_日均可售库存 - 同比_日均可售库存) / NULLIF(同比_日均可售库存, 0) AS 日均可售库存_同比

    -- ===== 日均采购在途库存 =====
    ,本期_日均采购在途库存 
    --,环比_日均采购在途库存 ,同比_日均采购在途库存
    ,(本期_日均采购在途库存 - 环比_日均采购在途库存) / NULLIF(环比_日均采购在途库存, 0) AS 日均采购在途库存_环比
    ,(本期_日均采购在途库存 - 同比_日均采购在途库存) / NULLIF(同比_日均采购在途库存, 0) AS 日均采购在途库存_同比

    -- ===== 平均可售库存 =====
    ,本期_平均可售库存 
    --,环比_平均可售库存 ,同比_平均可售库存
    ,(本期_平均可售库存 - 环比_平均可售库存) / NULLIF(环比_平均可售库存, 0) AS 平均可售库存_环比
    ,(本期_平均可售库存 - 同比_平均可售库存) / NULLIF(同比_平均可售库存, 0) AS 平均可售库存_同比

    -- ===== 平均采购在途库存 =====
    ,本期_平均采购在途库存 
    --,环比_平均采购在途库存 ,同比_平均采购在途库存
    ,(本期_平均采购在途库存 - 环比_平均采购在途库存) / NULLIF(环比_平均采购在途库存, 0) AS 平均采购在途库存_环比
    ,(本期_平均采购在途库存 - 同比_平均采购在途库存) / NULLIF(同比_平均采购在途库存, 0) AS 平均采购在途库存_同比
    
    -- ===== 成功款占比 =====
    ,本期_成功款占比
    ,本期_成功款占比 - 环比_成功款占比 成功款占比_环比差
    ,本期_成功款占比 - 同比_成功款占比 成功款占比_同比差

    -- ===== 爆款以上占比 =====
    ,本期_爆款以上占比
    ,本期_爆款以上占比 - 环比_爆款以上占比 爆款以上占比_环比差
    ,本期_爆款以上占比 - 同比_爆款以上占比 爆款以上占比_同比差
FROM pivoted
ORDER BY
    是否当年新品
    ,是否当月新品
    ,big_category
    ,second_category
    ,third_category
;

