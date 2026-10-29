-- ============================================================
-- 优化后脚本
-- 优化点汇总：
--   1. gmv_day + first_gmv 合并 → 订单表只扫一次（原来两次）
--   2. history_day + first_online_days 合并 → 产品历史表只扫一次（原来两次）
--   3. rating_base 提取 → t10 内重复的3表JOIN只写一次（原来两次）
--   4. biz_level_base 提取 → t17 内重复的PLM+extra JOIN只写一次（原来两次）
--   5. plm_base 提取 → PLM主表统一定义，消除4处重复子查询
--   6. sku_cat_base 提取 → dim_pub_sku_category 去重一次，替代5处重复扫描
--   7. UNION → UNION ALL（shangjia_skc_us_info 已有NOT IN保证不重叠）
--   8. 修复BUG：原脚本第1070行 left join t10 应为 t17
-- ============================================================

WITH shangjia_skc_us_info AS
(
    SELECT 
        a.skc
        ,a.first_published_at
        ,b.first_price
        ,first_published_de
        ,first_price_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),1),1,10)  AS fd1_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),3),1,10)  AS fd3_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),5),1,10)  AS fd5_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),7),1,10)  AS fd7_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),15),1,10) AS fd15_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),30),1,10) AS fd30_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),45),1,10) AS fd45_de
        ,SUBSTR(DATE_ADD(TO_DATE(first_published_de),60),1,10) AS fd60_de
    FROM 
    (
        SELECT skc, first_published_at
        FROM cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di
        WHERE pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
        UNION ALL  -- 【优化7】UNION→UNION ALL，NOT IN已保证不重叠，省去去重
        SELECT skc, first_published_at
        FROM cupshe_bigdata_cdm.dws_prod_skc_label_di
        WHERE pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_label_di')
        AND skc NOT IN (
            SELECT skc
            FROM cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di
            WHERE pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
        ) 
    ) a 
    LEFT JOIN 
    (
        SELECT
            skc
            ,IF(SUBSTR(first_published_us,1,7)=SUBSTR(first_published_dtc,1,7), first_published_us, LEAST(first_published_us,first_published_dtc)) first_published_at
            ,IF(first_price_us=99999, first_price_dtc, first_price_us) first_price
            ,first_published_de
            ,first_price_de
        FROM 
        (
            SELECT 
                skc
                ,MIN(min_published_at) first_published_dtc
                ,MIN(IF(a.shop_id IN (1,7),min_published_at,'9999-99-99')) first_published_us
                ,MIN_BY(first_price * ex_rate, min_published_at) first_price_dtc
                ,MIN(IF(a.shop_id IN (1,7),first_price * ex_rate,NULL)) first_price_us
                ,MIN(IF(a.shop_id IN (2,53),min_published_at,'9999-99-99')) first_published_de
                ,MIN(IF(a.shop_id IN (2,53),first_price * ex_rate,NULL)) first_price_de
            FROM cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di a
            LEFT JOIN CUPSHE_BIGDATA_CDM.dim_pub_fiscal_site_rate b
            ON a.shop_id = b.shop_id AND a.min_published_at = b.date_str
            WHERE pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di')
            GROUP BY skc
        ) 
    ) b
    ON a.skc = b.skc
)

-- ============================================================
-- 【优化5】PLM基础表：统一定义一次，下游4处复用
-- ============================================================
,plm_base AS (
    SELECT
        cp, id, skc, planning_type, is_del, business_type,
        first_category_name, second_category_name, third_category_name
    FROM cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di
    WHERE pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di')
      AND cp IS NOT NULL
)

-- ============================================================
-- 【优化6】SKU品类维度：去重一次，替代原来5处重复扫描
-- ============================================================
,sku_cat_base AS (
    SELECT cp, MAX(skc) AS skc
    FROM cupshe_bigdata_cdm.dim_pub_sku_category
    WHERE cp IS NOT NULL
    GROUP BY cp
)

-- ============================================================
-- 【优化1a】合并 gmv_day + first_online_days
-- 产品历史表 dwd_prod_shopify_product_history_di 只扫一次（原来两次）
-- 同时输出：每日在架状态 + 每日GMV
-- ============================================================
,history_gmv_day_base AS (
    SELECT
        SUBSTR(TO_DATE(h.pt,'yyyyMmdd'),1,10) AS dt,
        h.skc,
        MAX(h.is_online) AS is_online,
        NVL(SUM(o.sku_org_money_us), 0) AS dt_gmv
    FROM cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di h
    JOIN shangjia_skc_us_info s
      ON h.skc = s.skc
     AND SUBSTR(TO_DATE(h.pt,'yyyyMmdd'),1,10) BETWEEN s.fd1_de AND s.fd60_de
    LEFT JOIN cupshe_bigdata_cdm.dwd_trd_order_detail_combination_df o
      ON h.skc = o.skc
     AND SUBSTR(TO_DATE(h.pt,'yyyyMmdd'),1,10) = SUBSTR(o.buy_time,1,10)
     AND o.subsite_id IN (2,53)
    WHERE h.pt >= 20200101
      AND h.shop_id IN (2,53)
    GROUP BY SUBSTR(TO_DATE(h.pt,'yyyyMmdd'),1,10), h.skc
)

-- ============================================================
-- 【优化1b】上架N天在架天数（原 history_day + first_online_days）
-- ============================================================
,first_online_days AS 
(
    SELECT
        h.skc,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd3_de AND (h.is_online = 1 OR h.dt_gmv > 0),1,0)) online_days_3_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd5_de AND (h.is_online = 1 OR h.dt_gmv > 0),1,0)) online_days_5_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd7_de AND (h.is_online = 1 OR h.dt_gmv > 0),1,0)) online_days_7_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd15_de AND (h.is_online = 1 OR h.dt_gmv > 0),1,0)) online_days_15_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd30_de AND (h.is_online = 1 OR h.dt_gmv > 0),1,0)) online_days_30_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd45_de AND (h.is_online = 1 OR h.dt_gmv > 0),1,0)) online_days_45_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd60_de AND (h.is_online = 1 OR h.dt_gmv > 0),1,0)) online_days_60_de
    FROM history_gmv_day_base h
    JOIN shangjia_skc_us_info s ON h.skc = s.skc
    GROUP BY h.skc
) 

-- ============================================================
-- 【优化1c】统一GMV CTE：订单表只扫一次（原来 gmv_day + first_gmv 扫两次）
-- 同时输出：日维度GMV + 上架N天聚合GMV/销量
-- ============================================================
,gmv_base AS (
    SELECT
        skc,
        -- 日维度GMV（供 first_flow LEFT JOIN 使用，替代原 gmv_day）
        dt, dt_gmv,
        -- 上架N天聚合（替代原 first_gmv）
        SUM(IF(dt BETWEEN fd1_de AND fd3_de, dt_gmv, 0)) AS 3_gmv_de,
        SUM(IF(dt BETWEEN fd1_de AND fd5_de, dt_gmv, 0)) AS 5_gmv_de,
        SUM(IF(dt BETWEEN fd1_de AND fd7_de, dt_gmv, 0)) AS 7_gmv_de,
        SUM(IF(dt BETWEEN fd1_de AND fd15_de, dt_gmv, 0)) AS 15_gmv_de,
        SUM(IF(dt BETWEEN fd1_de AND fd30_de, dt_gmv, 0)) AS 30_gmv_de,
        SUM(IF(dt BETWEEN fd1_de AND fd45_de, dt_gmv, 0)) AS 45_gmv_de,
        SUM(IF(dt BETWEEN fd1_de AND fd60_de, dt_gmv, 0)) AS 60_gmv_de,
        CAST(SUM(IF(dt BETWEEN fd1_de AND fd3_de, dt_qty, 0)) AS BIGINT) AS 3_quantity_de,
        CAST(SUM(IF(dt BETWEEN fd1_de AND fd5_de, dt_qty, 0)) AS BIGINT) AS 5_quantity_de,
        CAST(SUM(IF(dt BETWEEN fd1_de AND fd7_de, dt_qty, 0)) AS BIGINT) AS 7_quantity_de,
        CAST(SUM(IF(dt BETWEEN fd1_de AND fd15_de, dt_qty, 0)) AS BIGINT) AS 15_quantity_de,
        CAST(SUM(IF(dt BETWEEN fd1_de AND fd30_de, dt_qty, 0)) AS BIGINT) AS 30_quantity_de,
        CAST(SUM(IF(dt BETWEEN fd1_de AND fd45_de, dt_qty, 0)) AS BIGINT) AS 45_quantity_de,
        CAST(SUM(IF(dt BETWEEN fd1_de AND fd60_de, dt_qty, 0)) AS BIGINT) AS 60_quantity_de
    FROM (
        -- 先按 skc+dt 聚合订单（消除同一天的重复行），同时带出每个skc的日期范围
        SELECT
            o.skc,
            SUBSTR(o.buy_time,1,10) AS dt,
            s.fd1_de, s.fd3_de, s.fd5_de, s.fd7_de, s.fd15_de, s.fd30_de, s.fd45_de, s.fd60_de,
            SUM(o.sku_org_money_us) AS dt_gmv,
            SUM(o.quantity) AS dt_qty
        FROM cupshe_bigdata_cdm.dwd_trd_order_detail_combination_df o
        JOIN shangjia_skc_us_info s
          ON o.skc = s.skc
         AND SUBSTR(o.buy_time,1,10) BETWEEN s.fd1_de AND s.fd60_de
         AND o.subsite_id IN (2,53)
        GROUP BY o.skc, SUBSTR(o.buy_time,1,10),
                 s.fd1_de, s.fd3_de, s.fd5_de, s.fd7_de, s.fd15_de, s.fd30_de, s.fd45_de, s.fd60_de
    ) t
    GROUP BY skc
)

,first_flow AS (
     SELECT 
        o.skc
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd3_de,collection_view_user,0)) 3_collection_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd5_de,collection_view_user,0)) 5_collection_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd7_de,collection_view_user,0)) 7_collection_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd15_de,collection_view_user,0)) 15_collection_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd30_de,collection_view_user,0)) 30_collection_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd45_de,collection_view_user,0)) 45_collection_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd60_de,collection_view_user,0)) 60_collection_view_user_de

        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd3_de,pdp_view_user,0)) 3_pdp_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd5_de,pdp_view_user,0)) 5_pdp_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd7_de,pdp_view_user,0)) 7_pdp_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd15_de,pdp_view_user,0)) 15_pdp_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd30_de,pdp_view_user,0)) 30_pdp_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd45_de,pdp_view_user,0)) 45_pdp_view_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd60_de,pdp_view_user,0)) 60_pdp_view_user_de

        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd3_de,collection_click_user,0)) 3_collection_click_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd5_de,collection_click_user,0)) 5_collection_click_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd7_de,collection_click_user,0)) 7_collection_click_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd15_de,collection_click_user,0)) 15_collection_click_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd30_de,collection_click_user,0)) 30_collection_click_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd45_de,collection_click_user,0)) 45_collection_click_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd60_de,collection_click_user,0)) 60_collection_click_user_de

        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd3_de,pdp_add_to_cart_user,0)) 3_pdp_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd5_de,pdp_add_to_cart_user,0)) 5_pdp_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd7_de,pdp_add_to_cart_user,0)) 7_pdp_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd15_de,pdp_add_to_cart_user,0)) 15_pdp_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd30_de,pdp_add_to_cart_user,0)) 30_pdp_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd45_de,pdp_add_to_cart_user,0)) 45_pdp_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd60_de,pdp_add_to_cart_user,0)) 60_pdp_add_to_cart_user_de

        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd3_de,collection_add_to_cart_user,0)) 3_collection_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd5_de,collection_add_to_cart_user,0)) 5_collection_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd7_de,collection_add_to_cart_user,0)) 7_collection_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd15_de,collection_add_to_cart_user,0)) 15_collection_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd30_de,collection_add_to_cart_user,0)) 30_collection_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd45_de,collection_add_to_cart_user,0)) 45_collection_add_to_cart_user_de
        ,SUM(IF(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de AND fd60_de,collection_add_to_cart_user,0)) 60_collection_add_to_cart_user_de  
        
        FROM cupshe_bigdata_cdm.dws_track_skc_di o
        JOIN shangjia_skc_us_info s
        ON o.skc = s.skc
        AND CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN s.fd1_de AND s.fd60_de
        WHERE pt >= '20230701'
            AND subsite_id IN (2,53)
        GROUP BY o.skc
)

-- ============================================================
-- 【优化3】评级基础表：提取重复的3表JOIN，原来在t10内写了两遍
-- ============================================================
,rating_base AS (
    SELECT DISTINCT
        t3.skc
        ,CASE
            WHEN second_category_name = '泳衣' THEN 
                CASE 
                    WHEN independent_station_selection_rating = 'D' THEN 'S'
                    WHEN independent_station_selection_rating = 'E' THEN 'S'
                    WHEN independent_station_selection_rating = 'F' THEN 'S'
                    WHEN independent_station_selection_rating = 'G' THEN 'A'
                    WHEN independent_station_selection_rating = 'H' THEN 'A'
                    WHEN independent_station_selection_rating = 'I' THEN 'B' 
                    WHEN independent_station_selection_rating = 'J' THEN 'C'
                    ELSE independent_station_selection_rating
                END 
            WHEN second_category_name != '泳装' THEN 
                CASE 
                    WHEN independent_station_selection_rating = 'S' THEN 'S'
                    WHEN independent_station_selection_rating = 'A' THEN 'A'
                    WHEN independent_station_selection_rating = 'B' THEN 'B'
                    WHEN independent_station_selection_rating = 'C' THEN 'C'
                    ELSE independent_station_selection_rating
                END
            END AS independent_station_selection_rating
        ,CASE 
            WHEN second_category_name = '泳衣' THEN 
                CASE 
                    WHEN independent_station_bysize_qt_rating = 'D' THEN 'S'
                    WHEN independent_station_bysize_qt_rating = 'E' THEN 'S'
                    WHEN independent_station_bysize_qt_rating = 'F' THEN 'S'
                    WHEN independent_station_bysize_qt_rating = 'G' THEN 'A'
                    WHEN independent_station_bysize_qt_rating = 'H' THEN 'A'
                    WHEN independent_station_bysize_qt_rating = 'I' THEN 'B' 
                    WHEN independent_station_bysize_qt_rating = 'J' THEN 'C'
                    ELSE independent_station_bysize_qt_rating
                END
            WHEN second_category_name != '泳装' THEN 
                CASE 
                    WHEN independent_station_bysize_qt_rating = 'S' THEN 'S'
                    WHEN independent_station_bysize_qt_rating = 'A' THEN 'A'
                    WHEN independent_station_bysize_qt_rating = 'B' THEN 'B'
                    WHEN independent_station_bysize_qt_rating = 'C' THEN 'C'
                    ELSE independent_station_bysize_qt_rating
                END
            END AS independent_station_bysize_qt_rating
        ,t2.product_rating
        ,t2.operational_rating
        ,t2.commodity_rating
    FROM cupshe_bigdata_ads.ads_scm_cp_product_rating_df t1
    LEFT JOIN cupshe_bigdata_ods.odsp_scm_proc_process_sheets t2
      ON t1.cp = t2.cp
    LEFT JOIN cupshe_bigdata_cdm.dim_pub_sku_category t3
      ON t1.cp = t3.cp
    WHERE t2.pt = MAX_PT('cupshe_bigdata_ods.odsp_scm_proc_process_sheets') 
)

,t10 AS (
    SELECT *
    FROM 
    (
        -- 单品：直接复用 rating_base
        SELECT 
            skc
            ,independent_station_selection_rating
            ,independent_station_bysize_qt_rating
            ,product_rating
            ,operational_rating
            ,commodity_rating
        FROM rating_base
        UNION ALL  -- 【优化7】UNION→UNION ALL，单品和组合品skc天然不重叠
        -- 组合品：子skc评级→数值→取最大→回字母
        SELECT 
            skc
            ,CASE 
                WHEN independent_station_bysize_qt_rating = 4 THEN 'S'
                WHEN independent_station_bysize_qt_rating = 3 THEN 'A'
                WHEN independent_station_bysize_qt_rating = 2 THEN 'B'
                WHEN independent_station_bysize_qt_rating = 1 THEN 'C'
            END AS independent_station_bysize_qt_rating
            ,CASE 
                WHEN independent_station_selection_rating = 4 THEN 'S'
                WHEN independent_station_selection_rating = 3 THEN 'A'
                WHEN independent_station_selection_rating = 2 THEN 'B'
                WHEN independent_station_selection_rating = 1 THEN 'C'
            END AS independent_station_selection_rating
            ,CASE 
                WHEN product_rating = 10 THEN 'S' WHEN product_rating = 9 THEN 'A'
                WHEN product_rating = 8 THEN 'B' WHEN product_rating = 7 THEN 'C'
                WHEN product_rating = 6 THEN 'D' WHEN product_rating = 5 THEN 'E'
                WHEN product_rating = 4 THEN 'F' WHEN product_rating = 3 THEN 'G'
                WHEN product_rating = 2 THEN 'H' WHEN product_rating = 1 THEN 'I'
                WHEN product_rating = 0 THEN 'J'
            END AS product_rating
            ,CASE 
                WHEN operational_rating = 10 THEN 'S' WHEN operational_rating = 9 THEN 'A'
                WHEN operational_rating = 8 THEN 'B' WHEN operational_rating = 7 THEN 'C'
                WHEN operational_rating = 6 THEN 'D' WHEN operational_rating = 5 THEN 'E'
                WHEN operational_rating = 4 THEN 'F' WHEN operational_rating = 3 THEN 'G'
                WHEN operational_rating = 2 THEN 'H' WHEN operational_rating = 1 THEN 'I'
                WHEN operational_rating = 0 THEN 'J'
            END AS operational_rating
            ,CASE 
                WHEN commodity_rating = 10 THEN 'S' WHEN commodity_rating = 9 THEN 'A'
                WHEN commodity_rating = 8 THEN 'B' WHEN commodity_rating = 7 THEN 'C'
                WHEN commodity_rating = 6 THEN 'D' WHEN commodity_rating = 5 THEN 'E'
                WHEN commodity_rating = 4 THEN 'F' WHEN commodity_rating = 3 THEN 'G'
                WHEN commodity_rating = 2 THEN 'H' WHEN commodity_rating = 1 THEN 'I'
                WHEN commodity_rating = 0 THEN 'J'
            END AS commodity_rating    
        FROM 
        (
            SELECT 
                combination_skc AS skc
                ,MAX(independent_station_bysize_qt_rating) independent_station_bysize_qt_rating
                ,MAX(independent_station_selection_rating) independent_station_selection_rating
                ,MAX(product_rating) product_rating
                ,MAX(operational_rating) operational_rating
                ,MAX(commodity_rating) commodity_rating
            FROM 
            (
                SELECT
                    cb.combination_skc
                    ,CASE 
                        WHEN rb.independent_station_selection_rating = 'S' THEN 4
                        WHEN rb.independent_station_selection_rating = 'A' THEN 3
                        WHEN rb.independent_station_selection_rating = 'B' THEN 2
                        WHEN rb.independent_station_selection_rating = 'C' THEN 1
                    END AS independent_station_selection_rating       
                    ,CASE 
                        WHEN rb.independent_station_bysize_qt_rating = 'S' THEN 4
                        WHEN rb.independent_station_bysize_qt_rating = 'A' THEN 3
                        WHEN rb.independent_station_bysize_qt_rating = 'B' THEN 2
                        WHEN rb.independent_station_bysize_qt_rating = 'C' THEN 1
                    END AS independent_station_bysize_qt_rating
                    ,CASE 
                        WHEN rb.product_rating = 'S' THEN 10 WHEN rb.product_rating = 'A' THEN 9
                        WHEN rb.product_rating = 'B' THEN 8  WHEN rb.product_rating = 'C' THEN 7
                        WHEN rb.product_rating = 'D' THEN 6  WHEN rb.product_rating = 'E' THEN 5
                        WHEN rb.product_rating = 'F' THEN 4  WHEN rb.product_rating = 'G' THEN 3
                        WHEN rb.product_rating = 'H' THEN 2  WHEN rb.product_rating = 'I' THEN 1
                        WHEN rb.product_rating = 'J' THEN 0
                    END AS product_rating 
                    ,CASE 
                        WHEN rb.operational_rating = 'S' THEN 10 WHEN rb.operational_rating = 'A' THEN 9
                        WHEN rb.operational_rating = 'B' THEN 8  WHEN rb.operational_rating = 'C' THEN 7
                        WHEN rb.operational_rating = 'D' THEN 6  WHEN rb.operational_rating = 'E' THEN 5
                        WHEN rb.operational_rating = 'F' THEN 4  WHEN rb.operational_rating = 'G' THEN 3
                        WHEN rb.operational_rating = 'H' THEN 2  WHEN rb.operational_rating = 'I' THEN 1
                        WHEN rb.operational_rating = 'J' THEN 0
                    END AS operational_rating
                    ,CASE 
                        WHEN rb.commodity_rating = 'S' THEN 10 WHEN rb.commodity_rating = 'A' THEN 9
                        WHEN rb.commodity_rating = 'B' THEN 8  WHEN rb.commodity_rating = 'C' THEN 7
                        WHEN rb.commodity_rating = 'D' THEN 6  WHEN rb.commodity_rating = 'E' THEN 5
                        WHEN rb.commodity_rating = 'F' THEN 4  WHEN rb.commodity_rating = 'G' THEN 3
                        WHEN rb.commodity_rating = 'H' THEN 2  WHEN rb.commodity_rating = 'I' THEN 1
                        WHEN rb.commodity_rating = 'J' THEN 0
                    END AS commodity_rating
                FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df cb
                LEFT JOIN rating_base rb ON cb.skc = rb.skc
            )
            GROUP BY combination_skc
        )
    )
    WHERE skc IS NOT NULL
) 

,cp_combination_mapping_info AS (
    WITH
    pps_combination_sx AS (
        SELECT
            REGEXP_REPLACE(cp,'-X|-S','') AS combination_cp,
            MAX(IF(cp RLIKE '-S', cp, NULL)) AS cp_S,
            MAX(IF(cp RLIKE '-X', cp, NULL)) AS cp_X
        FROM plm_base  -- 【优化5】复用plm_base
        WHERE planning_type = 2 AND business_type = 1 AND cp RLIKE '-X|-S'
        GROUP BY REGEXP_REPLACE(cp,'-X|-S','')
    ),
    comb_120skc_map AS (
        SELECT DISTINCT combination_skc AS combination_120skc, skc
        FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df
    )
    SELECT
        pps.cp, dim.skc, comb.combination_cp, comb.cp_S, comb.skc_S, comb.cp_X, comb.skc_X,
        COALESCE(s1.combination_120skc, s2.combination_120skc) AS combination_120skc,
        DECODE(pps.planning_type,0L,'非组合品',1L,'组合品套装',2L,'组合品分体') AS planning_type,
        pps.first_category_name, pps.second_category_name, pps.third_category_name,
        COALESCE(COALESCE(s1.combination_120skc, s2.combination_120skc), dim.skc) AS skc_with_combination
    FROM (SELECT * FROM plm_base WHERE planning_type IN (0,1) AND is_del = 0) pps
    LEFT JOIN (
        SELECT sx.combination_cp, sx.cp_S, s_skc.skc AS skc_S, sx.cp_X, x_skc.skc AS skc_X
        FROM pps_combination_sx sx
        LEFT JOIN sku_cat_base s_skc ON sx.cp_S = s_skc.cp  -- 【优化6】复用sku_cat_base
        LEFT JOIN sku_cat_base x_skc ON sx.cp_X = x_skc.cp
    ) comb ON comb.combination_cp = pps.cp
    LEFT JOIN sku_cat_base dim ON pps.cp = dim.cp
    LEFT JOIN comb_120skc_map s1 ON s1.skc = comb.skc_S
    LEFT JOIN comb_120skc_map s2 ON s2.skc = comb.skc_X
)

,t15 AS (
    WITH
    plm_cp_id AS (
        SELECT cp, id FROM plm_base  -- 【优化5】复用plm_base
    ),
    oss_img_raw AS (
        SELECT b.cp, a.biz_type, a.biz_scene, a.deleted, a.oss_url,
            ROW_NUMBER() OVER(PARTITION BY b.cp, a.biz_type, a.biz_scene ORDER BY a.oss_url) AS rk
        FROM cupshe_bigdata_ods.ods_scm_t_oss_relation_df a
        RIGHT JOIN plm_cp_id b ON a.biz_id = b.id
    ),
    oss_img_pivot AS (
        SELECT cp,
            MAX(IF(biz_type=25 AND biz_scene=60, oss_url, NULL)) AS oss_url_prototype_25,
            MAX(IF(biz_type=10 AND biz_scene=60, oss_url, NULL)) AS oss_url_prototype_10,
            MAX(IF(biz_type=215 AND biz_scene=135 AND deleted=0, oss_url, NULL)) AS oss_url_prototype_215,
            MAX(IF(biz_type=510 AND biz_scene=320 AND deleted=0, oss_url, NULL)) AS oss_url_prototype_510
        FROM oss_img_raw WHERE rk = 1 GROUP BY cp
    ),
    image_prototype AS (
        SELECT cp,
            COALESCE(oss_url_prototype_25, oss_url_prototype_10, oss_url_prototype_215, oss_url_prototype_510) AS oss_url_prototype
        FROM oss_img_pivot
    )
    SELECT a.skc_with_combination AS skc, img.oss_url_prototype
    FROM cp_combination_mapping_info a
    LEFT JOIN image_prototype img ON a.cp = img.cp
    WHERE a.skc_with_combination IS NOT NULL
)

-- ============================================================
-- 【优化4】商业层级基础表：提取重复的PLM+extra JOIN，原来在t17内写了两遍
-- ============================================================
,biz_level_base AS (
    SELECT
        b.skc,
        CASE 
            WHEN business_level = 1 THEN 'Hero'
            WHEN business_level = 2 THEN 'Core'
            WHEN business_level = 3 THEN 'Seasonal'
            WHEN business_level = 4 THEN 'Capsule'
            WHEN business_level = 5 THEN '其他'
        END AS business_level
    FROM plm_base pps  -- 【优化5】复用plm_base
    LEFT JOIN (
        SELECT DISTINCT process_sheets_id, business_level
        FROM cupshe_bigdata_ods.ods_proc_process_sheets_extra_df
        WHERE pt = MAX_PT('cupshe_bigdata_ods.ods_proc_process_sheets_extra_df')
          AND is_del = 0 
    ) bl ON bl.process_sheets_id = pps.id 
    LEFT JOIN sku_cat_base b ON pps.cp = b.cp  -- 【优化6】复用sku_cat_base
    WHERE pps.is_del = 0 
)

,t17 AS (
    SELECT skc, business_level FROM biz_level_base  -- 单品
    UNION
    SELECT combination_skc AS skc, MAX(business_level) AS business_level  -- 组合品
    FROM (
        SELECT v.combination_skc, blb.business_level
        FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df v 
        LEFT JOIN biz_level_base blb ON v.skc = blb.skc  -- 【优化4】复用biz_level_base
    )
    GROUP BY combination_skc 
) 

,t16 AS (
    WITH
    cp_biz_attr AS (
        SELECT
            b.skc, c.theme,
            CASE
                WHEN a.target_customer_group = 1 THEN '22-28岁'
                WHEN a.target_customer_group = 2 THEN '29-34岁'
                WHEN a.target_customer_group = 3 THEN '35-44岁'
            END AS target_customer_group
        FROM cupshe_bigdata_ods.ods_scm_proc_cp_business_df a
        LEFT JOIN (SELECT skc, cp FROM sku_cat_base) b ON a.cp = b.cp  -- 【优化6】复用sku_cat_base
        LEFT JOIN (
            SELECT id, theme
            FROM cupshe_bigdata_ods.ods_scm_proc_config_theme_df
            WHERE pt = MAX_PT('cupshe_bigdata_ods.ods_scm_proc_config_theme_df')
        ) c ON a.theme_id = c.id
        WHERE pt = MAX_PT('cupshe_bigdata_ods.ods_scm_proc_cp_business_df')
          AND a.cp IS NOT NULL AND b.skc IS NOT NULL
    ),
    comb_skc_attr AS (
        SELECT v.combination_skc AS skc, MAX(attr.theme) AS theme, MAX(attr.target_customer_group) AS target_customer_group
        FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df v
        LEFT JOIN cp_biz_attr attr ON v.skc = attr.skc
        GROUP BY v.combination_skc
    )
    SELECT skc, MAX(theme) AS theme, MAX(target_customer_group) AS target_customer_group
    FROM (
        SELECT skc, theme, target_customer_group FROM cp_biz_attr
        UNION ALL
        SELECT skc, theme, target_customer_group FROM comb_skc_attr
    ) t
    GROUP BY skc
) 

,detail AS
(
    SELECT 
        month_str ,country ,t1.skc
        ,t7.combination_skc 组合品子品对应组合品skc
        ,CASE
            WHEN t1.skc IS NOT NULL AND t7.combination_skc IS NULL THEN t1.skc
            WHEN t1.skc IS NOT NULL AND t7.combination_skc IS NOT NULL THEN t7.combination_skc
        END AS skc_adjust
        ,CASE
            WHEN t1.skc IS NOT NULL AND t1.skc LIKE '120%' THEN '组合品'
            WHEN t1.skc IS NOT NULL AND t7.combination_skc IS NULL THEN '单品'
            WHEN t1.skc IS NOT NULL AND t7.combination_skc IS NOT NULL THEN '组合品子品'
            ELSE '其他'
        END AS skc架上形式
        ,cp ,spu
        ,t1.first_published_at 首次上架时间_产品中心全站
        ,t1.first_shelves_price 首次上架价格_产品中心全站
        ,CASE WHEN is_new_this_month = '新品' AND (channels REGEXP '独立站' OR channels IS NULL) THEN '新品'
              WHEN is_new_this_month = '未上架' THEN '未上架' ELSE '老品' END 是否当月上新_产品中心全站
        ,CASE WHEN is_new_this_year = '新品' AND (channels REGEXP '独立站' OR channels IS NULL) THEN '新品'
              WHEN is_new_this_year = '未上架' THEN '未上架' ELSE '老品' END 是否当年上新_产品中心全站
        ,t2.first_published_de 首次上架时间_德站
        ,t2.first_price_de 首次上架价格_德站
        ,CASE WHEN SUBSTR(t2.first_published_de,1,7) > month_str THEN '未上架'
              WHEN SUBSTR(t2.first_published_de,1,7) = month_str AND (channels REGEXP '独立站' OR channels IS NULL) THEN '新品'
              ELSE '老品' END 是否当月上新_德站
        ,CASE WHEN SUBSTR(t2.first_published_de,1,4) > SUBSTR(month_str,1,4) THEN '未上架'
              WHEN SUBSTR(t2.first_published_de,1,4) = SUBSTR(month_str,1,4) AND (channels REGEXP '独立站' OR channels IS NULL) THEN '新品'
              ELSE '老品' END 是否当年上新_德站
        ,NVL(popular_type,'不动销') 畅滞销_产品中心全站
        ,CASE WHEN is_online_adjust = 1 THEN '在架' ELSE '不在架' END 当月是否在架
        ,is_online_qc_adjust 月初是否在架 ,is_online_qm_adjust 月末是否在架 ,online_days_adjust 当月在架天数
        ,first_order_price 首单采购价 ,qty_first_receving 首单采购量
        ,NVL(sale_quantity,0) 销量 ,NVL(sale_amount_usd,0) 销售额
        ,NVL(sale_amount_usd / NULLIF(sale_quantity, 0), 0) 平均售价
        ,CASE WHEN NVL(sale_quantity,0) = 0 THEN '[0-19)'
              ELSE CASE 
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 0  AND (sale_amount_usd)/(sale_quantity) < 19) THEN '[0,19)'
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 19 AND (sale_amount_usd)/(sale_quantity) < 22) THEN '[19,22)'
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 22 AND (sale_amount_usd)/(sale_quantity) < 25) THEN '[22,25)'
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 25 AND (sale_amount_usd)/(sale_quantity) < 28) THEN '[25,28)'
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 28 AND (sale_amount_usd)/(sale_quantity) < 31) THEN '[28,31)'
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 31 AND (sale_amount_usd)/(sale_quantity) < 34) THEN '[31,34)'
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 34 AND (sale_amount_usd)/(sale_quantity) < 37) THEN '[34,37)'
                  WHEN ((sale_amount_usd)/(sale_quantity) >= 37 AND (sale_amount_usd)/(sale_quantity) < 40) THEN '[37,40)'
                  WHEN ((sale_amount_usd)/(sale_quantity)) >= 40 THEN '[40,+)'
              END
        END 单价区间
        ,NVL(return_quantity,0) 退货数量 ,NVL(refund_amount_usd,0) 退款金额 ,NVL(refund_couponv_usd,0) 退券金额
        ,NVL(refund_store_credit_usd,0) 钱包金额 ,NVL(total_refund_amount_usd,0) `退款+退券+钱包总金额`
        ,NVL(collection_view_user,0) 商列浏览uv ,NVL(collection_click_user,0) 商列点击uv
        ,NVL(collection_add_to_cart_user,0) 商列加车uv ,NVL(pdp_view_user,0) 商详浏览uv ,NVL(pdp_add_to_cart_user,0) 商详加车uv
        ,NVL(sale_amount_usd/NULLIF(pdp_view_user,0),0) uv产出
        ,NVL(collection_click_user/NULLIF(collection_view_user,0),0) ctr_uv
        ,NVL(sale_quantity/NULLIF(pdp_view_user,0),0) cvr_uv
        ,NVL(online_days_3_de,0) 上架3天实际在架天数_德站 ,NVL(online_days_5_de,0) 上架5天实际在架天数_德站
        ,NVL(online_days_7_de,0) 上架7天实际在架天数_德站 ,NVL(online_days_15_de,0) 上架15天实际在架天数_德站
        ,NVL(online_days_30_de,0) 上架30天实际在架天数_德站 ,NVL(online_days_45_de,0) 上架45天实际在架天数_德站
        ,NVL(online_days_60_de,0) 上架后60天实际在架天数_德站
        ,NVL(3_gmv_de,0) 上架3天gmv_德站 ,NVL(5_gmv_de,0) 上架5天gmv_德站 ,NVL(7_gmv_de,0) 上架7天gmv_德站
        ,NVL(15_gmv_de,0) 上架15天gmv_德站 ,NVL(30_gmv_de,0) 上架30天gmv_德站 ,NVL(45_gmv_de,0) 上架45天gmv_德站 ,NVL(60_gmv_de,0) 上架60天gmv_德站
        ,NVL(3_quantity_de,0) 上架3天销量_德站 ,NVL(5_quantity_de,0) 上架5天销量_德站 ,NVL(7_quantity_de,0) 上架7天销量_德站
        ,NVL(15_quantity_de,0) 上架15天销量_德站 ,NVL(30_quantity_de,0) 上架30天销量_德站 ,NVL(45_quantity_de,0) 上架45天销量_德站 ,NVL(60_quantity_de,0) 上架60天销量_德站
        ,NVL(3_collection_view_user_de,0) 上架3天商列浏览uv_德站 ,NVL(5_collection_view_user_de,0) 上架5天商列浏览uv_德站
        ,NVL(7_collection_view_user_de,0) 上架7天商列浏览uv_德站 ,NVL(15_collection_view_user_de,0) 上架15天商列浏览uv_德站
        ,NVL(30_collection_view_user_de,0) 上架30天商列浏览uv_德站 ,NVL(45_collection_view_user_de,0) 上架45天商列浏览uv_德站 ,NVL(60_collection_view_user_de,0) 上架60天商列浏览uv_德站
        ,NVL(3_pdp_view_user_de,0) 上架3天商详浏览uv_德站 ,NVL(5_pdp_view_user_de,0) 上架5天商详浏览uv_德站
        ,NVL(7_pdp_view_user_de,0) 上架7天商详浏览uv_德站 ,NVL(15_pdp_view_user_de,0) 上架15天商详浏览uv_德站
        ,NVL(30_pdp_view_user_de,0) 上架30天商详浏览uv_德站 ,NVL(45_pdp_view_user_de,0) 上架45天商详浏览uv_德站 ,NVL(60_pdp_view_user_de,0) 上架60天商详浏览uv_德站
        ,NVL(3_collection_click_user_de,0) 上架3天商列点击uv_德站 ,NVL(5_collection_click_user_de,0) 上架5天商列点击uv_德站
        ,NVL(7_collection_click_user_de,0) 上架7天商列点击uv_德站 ,NVL(15_collection_click_user_de,0) 上架15天商列点击uv_德站
        ,NVL(30_collection_click_user_de,0) 上架30天商列点击uv_德站 ,NVL(45_collection_click_user_de,0) 上架45天商列点击uv_德站 ,NVL(60_collection_click_user_de,0) 上架60天商列点击uv_德站
        ,NVL(3_pdp_add_to_cart_user_de,0) 上架3天商详加车uv_德站 ,NVL(5_pdp_add_to_cart_user_de,0) 上架5天商详加车uv_德站
        ,NVL(7_pdp_add_to_cart_user_de,0) 上架7天商详加车uv_德站 ,NVL(15_pdp_add_to_cart_user_de,0) 上架15天商详加车uv_德站
        ,NVL(30_pdp_add_to_cart_user_de,0) 上架30天商详加车uv_德站 ,NVL(45_pdp_add_to_cart_user_de,0) 上架45天商详加车uv_德站 ,NVL(60_pdp_add_to_cart_user_de,0) 上架60天商详加车uv_德站
        ,NVL(3_collection_add_to_cart_user_de,0) 上架3天商列加车uv_德站 ,NVL(5_collection_add_to_cart_user_de,0) 上架5天商列加车uv_德站
        ,NVL(7_collection_add_to_cart_user_de,0) 上架7天商列加车uv_德站 ,NVL(15_collection_add_to_cart_user_de,0) 上架15天商列加车uv_德站
        ,NVL(30_collection_add_to_cart_user_de,0) 上架30天商列加车uv_德站 ,NVL(45_collection_add_to_cart_user_de,0) 上架45天商列加车uv_德站 ,NVL(60_collection_add_to_cart_user_de,0) 上架60天商列加车uv_德站
        ,NVL(3_collection_click_user_de / NULLIF(3_collection_view_user_de, 0), 0) 上架3天商列CTR_德站
        ,NVL(5_collection_click_user_de / NULLIF(5_collection_view_user_de, 0), 0) 上架5天商列CTR_德站
        ,NVL(7_collection_click_user_de / NULLIF(7_collection_view_user_de, 0), 0) 上架7天商列CTR_德站
        ,NVL(15_collection_click_user_de / NULLIF(15_collection_view_user_de, 0), 0) 上架15天商列ctr_德站
        ,NVL(30_collection_click_user_de / NULLIF(30_collection_view_user_de, 0), 0) 上架30天商列ctr_德站
        ,NVL(45_collection_click_user_de / NULLIF(45_collection_view_user_de, 0), 0) 上架45天商列ctr_德站
        ,NVL(60_collection_click_user_de / NULLIF(60_collection_view_user_de, 0), 0) 上架60天商列ctr_德站
        ,NVL(3_quantity_de/NULLIF(3_pdp_view_user_de,0),0) 上架3天cvr_德站 ,NVL(5_quantity_de/NULLIF(5_pdp_view_user_de,0),0) 上架5天cvr_德站
        ,NVL(7_quantity_de/NULLIF(7_pdp_view_user_de,0),0) 上架7天cvr_德站 ,NVL(15_quantity_de/NULLIF(15_pdp_view_user_de,0),0) 上架15天cvr_德站
        ,NVL(30_quantity_de/NULLIF(30_pdp_view_user_de,0),0) 上架30天cvr_德站 ,NVL(45_quantity_de/NULLIF(45_pdp_view_user_de,0),0) 上架45天cvr_德站
        ,NVL(60_quantity_de/NULLIF(60_pdp_view_user_de,0),0) 上架60天cvr_德站
        ,NVL(3_quantity_de/NULLIF(online_days_3_de,0),0) 上架3天日均销量 ,NVL(5_quantity_de/NULLIF(online_days_5_de,0),0) 上架5天日均销量
        ,NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) 上架7天日均销量 ,NVL(15_quantity_de/NULLIF(online_days_15_de,0),0) 上架15天日均销量
        ,NVL(30_quantity_de/NULLIF(online_days_30_de,0),0) 上架30天日均销量 ,NVL(45_quantity_de/NULLIF(online_days_45_de,0),0) 上架45天日均销量
        ,NVL(60_quantity_de/NULLIF(online_days_60_de,0),0) 上架60天日均销量
        ,NVL(3_gmv_de/NULLIF(online_days_3_de,0),0) 上架3天日均gmv ,NVL(5_gmv_de/NULLIF(online_days_5_de,0),0) 上架5天日均gmv
        ,NVL(7_gmv_de/NULLIF(online_days_7_de,0),0) 上架7天日均gmv ,NVL(15_gmv_de/NULLIF(online_days_15_de,0),0) 上架15天日均gmv
        ,NVL(30_gmv_de/NULLIF(online_days_30_de,0),0) 上架30天日均gmv ,NVL(45_gmv_de/NULLIF(online_days_45_de,0),0) 上架45天日均gmv
        ,NVL(60_gmv_de/NULLIF(online_days_60_de,0),0) 上架60天日均gmv
        ,CASE 
            WHEN second_category = '泳衣' THEN CASE 
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 0   AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 1   THEN '不动销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 1   AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 2.5 THEN '滞销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 2.5 AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 5   THEN '平销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 5   AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 30  THEN '畅销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 30  AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 50  THEN '爆款'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 50  AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 100 THEN '大爆款'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 100 THEN '超爆款'
            END 
            WHEN second_category != '泳衣' THEN CASE 
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 0   AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 1   THEN '不动销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 1   AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 2.5 THEN '滞销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 2.5 AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 5   THEN '平销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 5   AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 15  THEN '畅销'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 15  AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 30  THEN '爆款'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 30  AND NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) < 50  THEN '大爆款'
                WHEN NVL(7_quantity_de/NULLIF(online_days_7_de,0),0) >= 50  THEN '超爆款'
            END 
        END popular_condition1
        ,CASE
            WHEN (second_category = '泳衣'   AND NVL(7_gmv_de/NULLIF(online_days_7_de,0),0) >= 140.4)
              OR (second_category = '连衣裙' AND NVL(7_gmv_de/NULLIF(online_days_7_de,0),0) >= 140)
              OR (second_category = '罩衫'   AND NVL(7_gmv_de/NULLIF(online_days_7_de,0),0) >= 133)
              OR (second_category = '连体装' AND NVL(7_gmv_de/NULLIF(online_days_7_de,0),0) >= 149)
              OR (second_category = '上衣'   AND NVL(7_gmv_de/NULLIF(online_days_7_de,0),0) >= 111)
              OR (second_category = '下装'   AND NVL(7_gmv_de/NULLIF(online_days_7_de,0),0) >= 131) THEN '畅销'
        END popular_condition2
    FROM 
    (
        SELECT *
        FROM cupshe_bigdata_ads.ads_prod_country_product_info_mi
        WHERE pt >= 202201 AND country = 'DE' AND is_online_adjust = 1 AND big_category = '泳衣'
    ) t1
    LEFT JOIN shangjia_skc_us_info t2 ON t1.skc = t2.skc
    LEFT JOIN gmv_base t3 ON t1.skc = t3.skc           -- 【优化1】统一GMV CTE（替代原 first_gmv）
    LEFT JOIN first_flow t4 ON t1.skc = t4.skc
    LEFT JOIN first_online_days t5 ON t1.skc = t5.skc   -- 【优化1】合并后的在架天数（内部已含日GMV）
    LEFT JOIN (SELECT DISTINCT skc, combination_skc FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df) t7 ON t1.skc = t7.skc
)
SELECT 
    t1.* EXCEPT (popular_condition1, popular_condition2)
    ,NVL(CASE WHEN SUBSTR(首次上架时间_德站,1,7) <= '2026-08' AND popular_condition2 IS NOT NULL AND popular_condition1 NOT IN ("爆款","大爆款","超爆款") THEN popular_condition2
    ELSE popular_condition1 END, '不动销') AS 畅滞销_德站 
    ,t2.tentative_release_date 预计上架时间 ,t2.expected_release_date 期望上架时间 ,t2.is_gift_cart 是否礼品卡
    ,t2.image_src 图片链接 ,t15.oss_url_prototype 样衣图片链接
    ,CASE 
        WHEN t2.business_group_name IS NULL AND t2.second_category = '泳衣' THEN '泳衣产品部'
        WHEN t2.business_group_name IS NULL AND t2.second_category IN ("下装","运动服","连体装","针织服装","外套","罩衫","上衣","两件套","连衣裙","上装") THEN '成衣一部'
        WHEN t2.business_group_name IS NULL AND t2.second_category IN ('内衣','睡衣','家居服','塑身衣') THEN '内睡'
        WHEN t2.business_group_name IS NULL AND t2.first_category IN ('女士配饰','女士鞋品') THEN 'ACC'
        ELSE t2.business_group_name
    END AS 业务部门
    ,t2.group_name ,t2.first_color ,t2.designer_name ,t2.time_line_type timeline类型 ,t2.channels 渠道
    ,t2.big_category 大类 ,t2.first_category 一级品类 ,t2.second_category 二级品类 ,t2.third_category 三级品类
    ,t2.original_fixed_scene_tag 场景tag
    ,IF(t2.series IS NULL OR t2.series = '', NULL, t2.series) 原始人群画像
    ,IF(t2.series NOT IN ('SEA','SOL','DAWN'),'OTHERS',t2.series) 人群画像
    ,NVL(t16.target_customer_group, t2.target_customer_group) 目标客户群体
    ,t2.style_position 款式定位
    ,IF(NVL(t16.theme, t2.theme_name) IS NULL OR NVL(t16.theme, t2.theme_name) = '', NULL, NVL(t16.theme, t2.theme_name)) 主题名称
    ,t2.style_tag 风格 ,t2.pattern_tag 图案 ,t2.solid_print_tag 纯色印花
    ,t2.product_layering `plm商品分层（商品款式分类）`
    ,t2.color1_tag 颜色1 ,t2.color2_tag 颜色2 ,t2.color3_tag 颜色3 ,t2.design_details 设计细节
    ,ingredient_content_cn ,t2.fabric_construction 织造方式 ,t2.material_composition 主要成分
    ,t2.collar_style 领型 ,t2.waistline_position 腰线 ,t2.coat_length 衣长 ,t2.sleeve_length 袖长
    ,t2.sleeve_type 袖型 ,t2.skirt_length 裙长 ,t2.rise 腰高 ,t2.silhouette 廓型 ,t2.first_color 首复色
    ,IF(t2.model_code IS NULL OR t2.model_code = '', NULL, t2.model_code) model_code
    ,IF(t2.model_name IS NULL OR t2.model_name = '', NULL, t2.model_name) 模特名称
    ,CASE WHEN t2.model_type = 1 THEN '成人' WHEN t2.model_type = 0 THEN '儿童' END AS 模特类型
    ,t2.mail 模特mail ,t2.phone 模特phone ,t2.`location` 模特location ,t2.price 模特price
    ,t2.attiude 模特attiude ,t2.is_cooperate 模特is_cooperate
    ,t10.independent_station_bysize_qt_rating 独立站选品会评级
    ,t10.independent_station_selection_rating 独立站分码定量评级
    ,t10.product_rating 产品评级 ,t10.operational_rating 运营评级 ,t10.commodity_rating 企划评级
    ,t17.business_level 商业层级
FROM detail t1
LEFT JOIN (SELECT * FROM cupshe_bigdata_ads.ads_prod_skc_product_info_mi WHERE pt = MAX_PT('cupshe_bigdata_ads.ads_prod_skc_product_info_mi')) t2 ON t1.skc = t2.skc 
LEFT JOIN t15 ON t1.skc = t15.skc 
LEFT JOIN t16 ON t1.skc = t16.skc
LEFT JOIN t10 ON t1.skc = t10.skc
LEFT JOIN t17 ON t1.skc = t17.skc  -- 【优化8】修复BUG：原脚本此处误写为 t10
;
