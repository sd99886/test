-- 派生查询：按日粒度二级品类销售额/UV 趋势（本期 vs 环比期）
-- 口径与 S2_品类拆解L2 原脚本一致：在线调整口径，排除无库存测试款与赠品
-- 本期 2026-10-01~10-20；环比=上月同期（起止各回拨 1 个月：2026-09-01~09-20）
WITH periods AS (
    SELECT '本期' AS date_type, '2026-10-01' AS start_date, '2026-10-20' AS end_date
    UNION ALL
    SELECT '环比上一周期' AS date_type, '2026-09-01' AS start_date, '2026-09-20' AS end_date
)
SELECT
    /* +MAPJOIN(b)*/
    b.date_type
    ,a.date_str
    ,a.big_category
    ,a.second_category
    ,CASE
        WHEN a.is_new_this_month = '新品' AND nvl(a.channels, '独立站') regexp '独立站' THEN '当月新品'
        WHEN a.is_new_this_month = '未上架' THEN '当月未上架'
        ELSE '当月老品'
    END AS 是否当月新品
    ,SUM(a.sale_amount_usd) AS 销售额
    ,SUM(a.sale_quantity) AS 销量
    ,SUM(a.pdp_view_user) AS 详情页uv
FROM cupshe_bigdata_ads.ads_prod_skc_product_info_di a
JOIN periods b
    ON a.date_str >= b.start_date
   AND a.date_str <= b.end_date
WHERE a.is_online_adjustment = 1
  AND a.pt >= 20240101
  AND a.style_position != '无库存测试款'
  AND a.big_category != '赠品'
GROUP BY
    b.date_type
    ,a.date_str
    ,a.big_category
    ,a.second_category
    ,CASE
        WHEN a.is_new_this_month = '新品' AND nvl(a.channels, '独立站') regexp '独立站' THEN '当月新品'
        WHEN a.is_new_this_month = '未上架' THEN '当月未上架'
        ELSE '当月老品'
    END
ORDER BY b.date_type, a.date_str, a.big_category, a.second_category, 是否当月新品
LIMIT 5000
;

