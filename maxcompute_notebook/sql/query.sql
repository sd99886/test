WITH shangjia_skc_us_info as  -- dws_prod_skc_with_combination_label_di
(   -- 取产品中心逻辑的首次上架时间

    SELECT 
        a.skc
        -- 产品中心上架时间和价格：优先美国站上架时间,没有取最早上架时间
        ,a.first_published_at
        -- 改动11，取消抓修改了首次商家时间的逻辑，会影响到首次商家时间跨月和不跨月的那个逻辑；首次上架价格仅采用美国站的首次上架价格
        -- ,if(a.first_published_at != b.first_published_at,b.first_published_at,a.first_published_at) first_published_at
        ,b.first_price
        -- DE站上架时间
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
        SELECT  skc
                ,first_published_at
        FROM    cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di
        WHERE   pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
        UNION
        SELECT  skc
                ,first_published_at
        FROM    cupshe_bigdata_cdm.dws_prod_skc_label_di
        WHERE   pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_label_di')
        AND     skc NOT IN (
                    -- 存在单品skc在两个维度表有不同状态，优先取组合品的skc，缺少再用单品递补
                    SELECT  skc
                    FROM    cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di
                    WHERE   pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
                ) 
    ) a 
    left join -- 改动11，取消抓修改了首次商家时间的逻辑，会影响到首次商家时间跨月和不跨月的那个逻辑；首次上架价格仅采用美国站的首次上架价格
    (   -- 改动7，增加首次上架价格，按照美国站思路，首次上架时间更新调整
        select
            skc
            ,if(SUBSTR(first_published_us,1,7)=SUBSTR(first_published_dtc,1,7), first_published_us, LEAST(first_published_us,first_published_dtc)) first_published_at
            -- 如果没有美国站上架时间，就用DTC最早上架日期对应的价格
            ,if(first_price_us=99999, first_price_dtc, first_price_us) first_price
            ,first_published_de
            ,first_price_de
        FROM 
        (   -- 全站
            SELECT 
                skc
                ,min(min_published_at) first_published_dtc
                ,min(IF(a.shop_id in (1,7),min_published_at,'9999-99-99')) first_published_us
                ,MIN_BY(first_price * ex_rate,min_published_at) first_price_dtc -- DTC最早上架日期对应的价格
                ,min(IF(a.shop_id in (1,7),first_price * ex_rate,null)) first_price_us -- 美国站的最早上架价格
                ,min(IF(a.shop_id in (2,53),min_published_at,'9999-99-99')) first_published_de -- 德国站最早上架时间
                ,min(IF(a.shop_id in (2,53),first_price * ex_rate,null)) first_price_de -- 德国站的最早上架价格
            FROM cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di a
            LEFT JOIN CUPSHE_BIGDATA_CDM.dim_pub_fiscal_site_rate b
            ON      a.shop_id = b.shop_id
            AND     a.min_published_at = b.date_str
            WHERE  pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di')

            group by skc
        ) 

    ) b
    on a.skc = b.skc
)

,history_day AS (
    SELECT
        SUBSTR(TO_DATE(h.pt,'yyyyMmdd'),1,10) dt,
        h.skc,
        MAX(h.is_online) is_online
    FROM cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di h
    JOIN shangjia_skc_us_info s
      ON h.skc = s.skc
     AND SUBSTR(TO_DATE(h.pt,'yyyyMmdd'),1,10) BETWEEN s.fd1_de AND s.fd60_de
    WHERE h.pt >= 20200101 
        and shop_id in (2,53) -- 德国站
    GROUP BY SUBSTR(TO_DATE(h.pt,'yyyyMmdd'),1,10), h.skc
),
gmv_day AS (
    SELECT
        SUBSTR(o.buy_time,1,10) dt,
        o.skc,
        SUM(o.sku_org_money_us) dt_gmv
    FROM cupshe_bigdata_cdm.dwd_trd_order_detail_combination_df o
    JOIN shangjia_skc_us_info s
      ON o.skc = s.skc
     AND SUBSTR(o.buy_time,1,10) BETWEEN s.fd1_de AND s.fd60_de
     and subsite_id in (2,53) -- 德国站
    GROUP BY SUBSTR(o.buy_time,1,10), o.skc
)
, first_online_days as 
(
    SELECT
        h.skc,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd3_de AND (h.is_online = 1 OR NVL(g.dt_gmv,0) > 0),1,0)) online_days_3_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd5_de AND (h.is_online = 1 OR NVL(g.dt_gmv,0) > 0),1,0)) online_days_5_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd7_de AND (h.is_online = 1 OR NVL(g.dt_gmv,0) > 0),1,0)) online_days_7_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd15_de AND (h.is_online = 1 OR NVL(g.dt_gmv,0) > 0),1,0)) online_days_15_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd30_de AND (h.is_online = 1 OR NVL(g.dt_gmv,0) > 0),1,0)) online_days_30_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd45_de AND (h.is_online = 1 OR NVL(g.dt_gmv,0) > 0),1,0)) online_days_45_de,
        SUM(IF(h.dt BETWEEN s.fd1_de AND s.fd60_de AND (h.is_online = 1 OR NVL(g.dt_gmv,0) > 0),1,0)) online_days_60_de
    FROM history_day h
    JOIN shangjia_skc_us_info s
    ON h.skc = s.skc
    LEFT JOIN gmv_day g
    ON h.skc = g.skc
    AND h.dt = g.dt
    GROUP BY h.skc
) 
,first_gmv AS (
    SELECT
        o.skc,
        SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd3_de,o.sku_org_money_us,0)) 3_gmv_de,
        SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd5_de,o.sku_org_money_us,0)) 5_gmv_de,
        SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd7_de,o.sku_org_money_us,0)) 7_gmv_de,
        SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd15_de,o.sku_org_money_us,0)) 15_gmv_de,
        SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd30_de,o.sku_org_money_us,0)) 30_gmv_de,
        SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd45_de,o.sku_org_money_us,0)) 45_gmv_de,
        SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd60_de,o.sku_org_money_us,0)) 60_gmv_de,
        CAST(SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd3_de,o.quantity,0)) AS BIGINT) 3_quantity_de,
        cast(SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd5_de,o.quantity,0)) as bigint) 5_quantity_de,
        cast(SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd7_de,o.quantity,0))  as bigint)7_quantity_de,
        cast(SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd15_de,o.quantity,0)) as bigint) 15_quantity_de,
        cast(SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd30_de,o.quantity,0)) as bigint) 30_quantity_de,
        cast(SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd45_de,o.quantity,0)) as bigint) 45_quantity_de,
        cast(SUM(if(SUBSTR(o.buy_time,1,10) BETWEEN fd1_de and fd60_de,o.quantity,0)) as bigint) 60_quantity_de
    FROM cupshe_bigdata_cdm.dwd_trd_order_detail_combination_df o
    JOIN shangjia_skc_us_info s
      ON o.skc = s.skc
     AND SUBSTR(o.buy_time,1,10) BETWEEN s.fd1_de AND s.fd60_de
     and subsite_id in (2,53) -- 德国站
    GROUP BY o.skc
)
,first_flow as (
     SELECT 
        o.skc
        -- ,CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) AS date_str
        -- 商列浏览pv
        -- ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd3_de,collection_view_cnt,0)) AS collection_view_cnt
        
        -- 商列浏览uv
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd3_de,collection_view_user,0)) 3_collection_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd5_de,collection_view_user,0)) 5_collection_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd7_de,collection_view_user,0)) 7_collection_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd15_de,collection_view_user,0)) 15_collection_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd30_de,collection_view_user,0)) 30_collection_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd45_de,collection_view_user,0)) 45_collection_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd60_de,collection_view_user,0)) 60_collection_view_user_de

        -- 详情页浏览pv
        -- ,SUM(pdp_view_cnt) AS pdp_view_cnt
        
        -- 详情页浏览uv
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd3_de,pdp_view_user,0)) 3_pdp_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd5_de,pdp_view_user,0)) 5_pdp_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd7_de,pdp_view_user,0)) 7_pdp_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd15_de,pdp_view_user,0)) 15_pdp_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd30_de,pdp_view_user,0)) 30_pdp_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd45_de,pdp_view_user,0)) 45_pdp_view_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd60_de,pdp_view_user,0)) 60_pdp_view_user_de
        
        -- 商列点击pv
        -- ,SUM(collection_click_cnt) AS collection_click_cnt

        -- 商列点击uv
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd3_de,collection_click_user,0)) 3_collection_click_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd5_de,collection_click_user,0)) 5_collection_click_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd7_de,collection_click_user,0)) 7_collection_click_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd15_de,collection_click_user,0)) 15_collection_click_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd30_de,collection_click_user,0)) 30_collection_click_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd45_de,collection_click_user,0)) 45_collection_click_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd60_de,collection_click_user,0)) 60_collection_click_user_de

        -- 详情页加车uv
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd3_de,pdp_add_to_cart_user,0)) 3_pdp_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd5_de,pdp_add_to_cart_user,0)) 5_pdp_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd7_de,pdp_add_to_cart_user,0)) 7_pdp_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd15_de,pdp_add_to_cart_user,0)) 15_pdp_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd30_de,pdp_add_to_cart_user,0)) 30_pdp_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd45_de,pdp_add_to_cart_user,0)) 45_pdp_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd60_de,pdp_add_to_cart_user,0)) 60_pdp_add_to_cart_user_de

        -- 商列加车uv
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd3_de,collection_add_to_cart_user,0)) 3_collection_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd5_de,collection_add_to_cart_user,0)) 5_collection_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd7_de,collection_add_to_cart_user,0)) 7_collection_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd15_de,collection_add_to_cart_user,0)) 15_collection_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd30_de,collection_add_to_cart_user,0)) 30_collection_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd45_de,collection_add_to_cart_user,0)) 45_collection_add_to_cart_user_de
        ,SUM(if(CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN fd1_de and fd60_de,collection_add_to_cart_user,0)) 60_collection_add_to_cart_user_de  
        
        FROM    cupshe_bigdata_cdm.dws_track_skc_di o
        JOIN shangjia_skc_us_info s
        ON o.skc = s.skc
        AND CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2)) BETWEEN s.fd1_de AND s.fd60_de
        WHERE   pt >= '20230701'
            and subsite_id in (2,53) -- 德国站
        GROUP BY o.skc
                -- subsite_id             
                -- ,CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2),'-',SUBSTR(pt,7,2))

)
,cp_combination_mapping_info AS (
    WITH
    -- ① 读取一次plm主表最大分区，全局复用，避免重复扫描
    pps_base AS (
        SELECT
            cp,
            skc,
            planning_type,
            is_del,
            business_type,
            first_category_name,
            second_category_name,
            third_category_name
        FROM cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di
        WHERE
            pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di')
            AND is_del = 0
            AND cp IS NOT NULL
    ),
    -- ② 提取分体款(planning_type=2)，剥离-X/-S，聚合得到父cp、上下分体cp
    pps_combination_sx AS (
        SELECT
            regexp_replace(cp,'-X|-S','') AS combination_cp,
            MAX(IF(cp RLIKE '-S', cp, NULL)) AS cp_S,
            MAX(IF(cp RLIKE '-X', cp, NULL)) AS cp_X
        FROM pps_base
        WHERE
            planning_type = 2
            AND business_type = 1
            AND cp RLIKE '-X|-S'
        GROUP BY combination_cp
    ),
    -- ③ cp -> skc映射（多张地方复用，cp多skc粗暴max，业务注意）
    cp_2_skc AS (
        SELECT
            cp,
            MAX(skc) AS skc
        FROM cupshe_bigdata_cdm.dim_pub_sku_category
        WHERE cp IS NOT NULL
        GROUP BY cp
    ),
    -- ④ 分体120虚拟skc映射：子skc -> combination_120skc
    comb_120skc_map AS (
        SELECT DISTINCT
            combination_skc AS combination_120skc,
            skc
        FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df
    )
    SELECT
        pps.cp,
        dim.skc,
        comb.combination_cp,
        comb.cp_S,
        comb.skc_S,
        comb.cp_X,
        comb.skc_X,
        -- 修复：skc_S关联不到，尝试skc_X去匹配120虚拟skc
        COALESCE(s1.combination_120skc, s2.combination_120skc) AS combination_120skc,
        DECODE(pps.planning_type,0L,'非组合品',1L,'组合品套装',2L,'组合品分体') AS planning_type,
        pps.first_category_name,
        pps.second_category_name,
        pps.third_category_name,
        COALESCE(COALESCE(s1.combination_120skc, s2.combination_120skc), dim.skc) AS skc_with_combination
    FROM (
        -- 主表先过滤：只取非分体：0非组合品 /1组合品套装
        SELECT * FROM pps_base WHERE planning_type IN (0,1)
    ) pps
    -- 关联分体解析结果
    LEFT JOIN (
        SELECT
            sx.combination_cp,
            sx.cp_S,
            s_skc.skc AS skc_S,
            sx.cp_X,
            x_skc.skc AS skc_X
        FROM pps_combination_sx sx
        LEFT JOIN cp_2_skc s_skc ON sx.cp_S = s_skc.cp
        LEFT JOIN cp_2_skc x_skc ON sx.cp_X = x_skc.cp
    ) comb
        ON comb.combination_cp = pps.cp
    -- cp转skc dim
    LEFT JOIN cp_2_skc dim
        ON pps.cp = dim.cp
    -- skc_S查120虚拟skc
    LEFT JOIN comb_120skc_map s1
        ON s1.skc = comb.skc_S
    -- skc_X兜底查120虚拟skc（原SQL缺失，修复逻辑）
    LEFT JOIN comb_120skc_map s2
        ON s2.skc = comb.skc_X
)

,t15 AS (
    -- 样衣链接：skc_with_combination + 优先级样衣oss_url
    WITH
    -- 公共plm基础：只读取一次最大分区，消除4次重复扫描
    plm_cp_id AS (
        SELECT
            cp,
            id
        FROM cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di
        WHERE pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di')
          AND cp IS NOT NULL
    ),
    -- oss关系：按cp+biz_type+biz_scene取第一条图片 rk=1
    oss_img_raw AS (
        SELECT
            b.cp,
            a.biz_type,
            a.biz_scene,
            a.deleted,
            a.oss_url,
            ROW_NUMBER() OVER(PARTITION BY b.cp, a.biz_type, a.biz_scene ORDER BY a.oss_url) AS rk
        FROM cupshe_bigdata_ods.ods_scm_t_oss_relation_df a
        RIGHT JOIN plm_cp_id b
            ON a.biz_id = b.id
    ),
    -- 各个业务类型图片，行转列
    oss_img_pivot AS (
        SELECT
            cp,
            MAX(IF(biz_type=25 AND biz_scene=60, oss_url, NULL)) AS oss_url_prototype_25,
            MAX(IF(biz_type=10 AND biz_scene=60, oss_url, NULL)) AS oss_url_prototype_10,
            MAX(IF(biz_type=215 AND biz_scene=135 AND deleted=0, oss_url, NULL)) AS oss_url_prototype_215,
            MAX(IF(biz_type=510 AND biz_scene=320 AND deleted=0, oss_url, NULL)) AS oss_url_prototype_510
        FROM oss_img_raw
        WHERE rk = 1
        GROUP BY cp
    ),
    image_prototype AS (
        SELECT
            cp,
            -- 严格保留原有优先级：25 →10 →215 →510
            COALESCE(oss_url_prototype_25, oss_url_prototype_10, oss_url_prototype_215, oss_url_prototype_510) AS oss_url_prototype
        FROM oss_img_pivot
    )
    SELECT
        a.skc_with_combination AS skc,
        img.oss_url_prototype
    FROM cp_combination_mapping_info a
    LEFT JOIN image_prototype img
        ON a.cp = img.cp
    WHERE a.skc_with_combination IS NOT NULL
)
,t10 as (
    -- 评级
    SELECT 
        *
    from 
    (
        SELECT 
            DISTINCT  
            -- t1.cp
            t3.skc
            ,case
                WHEN second_category_name = '泳衣'  then 
                    (
                        case 
                            when independent_station_selection_rating = 'D' THEN 'S'
                            when independent_station_selection_rating = 'E' THEN 'S'
                            when independent_station_selection_rating = 'F' THEN 'S'
                            when independent_station_selection_rating = 'G' THEN 'A'
                            when independent_station_selection_rating = 'H' THEN 'A'
                            when independent_station_selection_rating = 'I' THEN 'B' 
                            when independent_station_selection_rating = 'J' THEN 'C'
                        ELSE independent_station_selection_rating
                        end 
                    )
                WHEN second_category_name != '泳装'  then 
                (
                    case 
                        WHEN  independent_station_selection_rating = 'S' THEN 'S'
                        WHEN  independent_station_selection_rating = 'A' THEN 'A'
                        WHEN  independent_station_selection_rating = 'B' THEN 'B'
                        WHEN  independent_station_selection_rating = 'C' THEN 'C'
                    ELSE independent_station_selection_rating
                    end
                )
            END AS independent_station_selection_rating -- 独立站选品会分级，定用看选品会分级，其他看分码定量 
            ,case 
                when second_category_name = '泳衣' THEN 
                (
                    case 
                        when independent_station_bysize_qt_rating = 'D' THEN 'S'
                        when independent_station_bysize_qt_rating = 'E' THEN 'S'
                        when independent_station_bysize_qt_rating = 'F' THEN 'S'
                        when independent_station_bysize_qt_rating = 'G' THEN 'A'
                        when independent_station_bysize_qt_rating = 'H' THEN 'A'
                        when independent_station_bysize_qt_rating = 'I' THEN 'B' 
                        when independent_station_bysize_qt_rating = 'J' THEN 'C'
                    else independent_station_bysize_qt_rating
                    end
                )
                when second_category_name != '泳装' THEN 
                (
                    case 
                        when independent_station_bysize_qt_rating = 'S' THEN 'S'
                        when independent_station_bysize_qt_rating = 'A' THEN 'A'
                        when independent_station_bysize_qt_rating = 'B' THEN 'B'
                        when independent_station_bysize_qt_rating = 'C' THEN 'C'
                        else independent_station_bysize_qt_rating
                        end
                )
                end as independent_station_bysize_qt_rating -- 独立站分码定量评级 -- 独立站评级改这个逻辑
            ,t2.product_rating -- 产品评级 
            ,t2.operational_rating -- 运营评级
            ,t2.commodity_rating -- 企划评级
            -- ,t2.other_channel_rating -- 渠道拓展评级
            -- ,t2.tiktok_channel_rating -- Tiktok评级
        FROM cupshe_bigdata_ads.ads_scm_cp_product_rating_df t1
        LEFT JOIN cupshe_bigdata_ods.odsp_scm_proc_process_sheets t2
        ON t1.cp = t2.cp
        LEFT JOIN cupshe_bigdata_cdm.dim_pub_sku_category t3
        ON t1.cp = t3.cp
        WHERE t2.pt=MAX_PT('cupshe_bigdata_ods.odsp_scm_proc_process_sheets') 
        union
        SELECT  -- 组合品
            skc
            ,case 
                when independent_station_bysize_qt_rating = 4 then 'S'
                when independent_station_bysize_qt_rating = 3 then 'A'
                when independent_station_bysize_qt_rating = 2 then 'B'
                when independent_station_bysize_qt_rating = 1 then 'C'
            END AS independent_station_bysize_qt_rating
            ,CASE 
                when independent_station_selection_rating = 4 then 'S'
                when independent_station_selection_rating = 3 then 'A'
                when independent_station_selection_rating = 2 then 'B'
                when independent_station_selection_rating = 1 then 'C'
            END AS independent_station_selection_rating -- 独立站选品会分级，定泳看选品会分级，其他看分码定量 
            ,CASE 
                WHEN product_rating = 10 then 'S'
                WHEN product_rating = 9 then 'A'
                WHEN product_rating = 8 then 'B'
                WHEN product_rating = 7 then 'C'
                WHEN product_rating = 6 then 'D'
                WHEN product_rating = 5 then 'E'
                WHEN product_rating = 4 then 'F'
                WHEN product_rating = 3 then 'G'
                WHEN product_rating = 2 then 'H'
                WHEN product_rating = 1 then 'I'
                WHEN product_rating = 0 then 'J'
            END AS product_rating
            ,CASE 
                WHEN operational_rating = 10 then 'S'
                WHEN operational_rating = 9 then 'A'
                WHEN operational_rating = 8 then 'B'
                WHEN operational_rating = 7 then 'C'
                WHEN operational_rating = 6 then 'D'
                WHEN operational_rating = 5 then 'E'
                WHEN operational_rating = 4 then 'F'
                WHEN operational_rating = 3 then 'G'
                WHEN operational_rating = 2 then 'H'
                WHEN operational_rating = 1 then 'I'
                WHEN operational_rating = 0 then 'J'
            END AS operational_rating
            ,CASE 
                WHEN commodity_rating = 10 then 'S'
                WHEN commodity_rating = 9 then 'A'
                WHEN commodity_rating = 8 then 'B'
                WHEN commodity_rating = 7 then 'C'
                WHEN commodity_rating = 6 then 'D'
                WHEN commodity_rating = 5 then 'E'
                WHEN commodity_rating = 4 then 'F'
                WHEN commodity_rating = 3 then 'G'
                WHEN commodity_rating = 2 then 'H'
                WHEN commodity_rating = 1 then 'I'
                WHEN commodity_rating = 0 then 'J'
            END AS commodity_rating    
        FROM 
        (
            SELECT 
                skc
                ,max(independent_station_bysize_qt_rating) independent_station_bysize_qt_rating
                ,max(independent_station_selection_rating) independent_station_selection_rating
                ,max(product_rating) product_rating
                ,max(operational_rating) operational_rating
                ,max(commodity_rating) commodity_rating
                -- ,max(other_channel_rating) other_channel_rating
                -- ,max(tiktok_channel_rating) tiktok_channel_rating
            FROM 
            (
                select
                        combination_skc skc
                        -- ,cb.skc
                        -- 把文本转换为值，取最大评级
                        ,case 
                            when independent_station_selection_rating = 'S' THEN 4
                            when independent_station_selection_rating = 'A' THEN 3 -- 独立站选品会评级  
                            when independent_station_selection_rating = 'B' THEN 2
                            when independent_station_selection_rating = 'C' THEN 1
                        END as independent_station_selection_rating       
                        ,CASE 
                            WHEN independent_station_bysize_qt_rating = 'S' THEN 4 -- 独立站分码定量评级
                            WHEN independent_station_bysize_qt_rating = 'A' THEN 3
                            WHEN independent_station_bysize_qt_rating = 'B' THEN 2
                            WHEN independent_station_bysize_qt_rating = 'C' THEN 1
                        END AS independent_station_bysize_qt_rating
                        ,case -- 产品评级
                            when product_rating = 'S' then 10 
                            WHEN product_rating = 'A' THEN 9
                            WHEN product_rating = 'B' THEN 8
                            WHEN product_rating = 'C' THEN 7
                            WHEN product_rating = 'D' THEN 6
                            WHEN product_rating = 'E' THEN 5
                            WHEN product_rating = 'F' THEN 4
                            WHEN product_rating = 'G' THEN 3
                            WHEN product_rating = 'H' THEN 2
                            WHEN product_rating = 'I' THEN 1
                            WHEN product_rating = 'J' THEN 0
                        END product_rating 

                        ,CASE 
                            when operational_rating= 'S' then 10 
                            WHEN operational_rating= 'A' THEN 9
                            WHEN operational_rating= 'B' THEN 8
                            WHEN operational_rating= 'C' THEN 7
                            WHEN operational_rating= 'D' THEN 6
                            WHEN operational_rating= 'E' THEN 5
                            WHEN operational_rating= 'F' THEN 4
                            WHEN operational_rating= 'G' THEN 3
                            WHEN operational_rating= 'H' THEN 2
                            WHEN operational_rating= 'I' THEN 1
                            WHEN operational_rating= 'J' THEN 0
                        END operational_rating -- 运营评级
                        ,CASE 
                            when commodity_rating= 'S' then 10 
                            WHEN commodity_rating= 'A' THEN 9
                            WHEN commodity_rating= 'B' THEN 8
                            WHEN commodity_rating= 'C' THEN 7
                            WHEN commodity_rating= 'D' THEN 6
                            WHEN commodity_rating= 'E' THEN 5
                            WHEN commodity_rating= 'F' THEN 4
                            WHEN commodity_rating= 'G' THEN 3
                            WHEN commodity_rating= 'H' THEN 2
                            WHEN commodity_rating= 'I' THEN 1
                            WHEN commodity_rating= 'J' THEN 0
                        END commodity_rating -- 企划评级
                        -- ,other_channel_rating -- 渠道拓展评级
                        -- ,tiktok_channel_rating -- Tiktok评级
                from cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df cb
                left JOIN 
                (
                    SELECT DISTINCT  
                        -- t1.cp
                        t3.skc
                        ,case
                            WHEN second_category_name = '泳衣'  then 
                                (
                                    case 
                                        when independent_station_selection_rating = 'D' THEN 'S'
                                        when independent_station_selection_rating = 'E' THEN 'S'
                                        when independent_station_selection_rating = 'F' THEN 'S'
                                        when independent_station_selection_rating = 'G' THEN 'A'
                                        when independent_station_selection_rating = 'H' THEN 'A'
                                        when independent_station_selection_rating = 'I' THEN 'B' 
                                        when independent_station_selection_rating = 'J' THEN 'C'
                                    ELSE independent_station_selection_rating
                                    end 
                                )
                            WHEN second_category_name != '泳装'  then 
                            (
                                case 
                                    WHEN  independent_station_selection_rating = 'S' THEN 'S'
                                    WHEN  independent_station_selection_rating = 'A' THEN 'A'
                                    WHEN  independent_station_selection_rating = 'B' THEN 'B'
                                    WHEN  independent_station_selection_rating = 'C' THEN 'C'
                                ELSE independent_station_selection_rating
                                end
                            )
                        END AS independent_station_selection_rating -- 独立站选品会分级，定用看选品会分级，其他看分码定量 
                        ,case 
                            when second_category_name = '泳衣' THEN 
                            (
                                case 
                                    when independent_station_bysize_qt_rating = 'D' THEN 'S'
                                    when independent_station_bysize_qt_rating = 'E' THEN 'S'
                                    when independent_station_bysize_qt_rating = 'F' THEN 'S'
                                    when independent_station_bysize_qt_rating = 'G' THEN 'A'
                                    when independent_station_bysize_qt_rating = 'H' THEN 'A'
                                    when independent_station_bysize_qt_rating = 'I' THEN 'B' 
                                    when independent_station_bysize_qt_rating = 'J' THEN 'C'
                                else independent_station_bysize_qt_rating
                                end
                            )
                            when second_category_name != '泳装' THEN 
                            (
                                case 
                                    when independent_station_bysize_qt_rating = 'S' THEN 'S'
                                    when independent_station_bysize_qt_rating = 'A' THEN 'A'
                                    when independent_station_bysize_qt_rating = 'B' THEN 'B'
                                    when independent_station_bysize_qt_rating = 'C' THEN 'C'
                                    else independent_station_bysize_qt_rating
                                    end
                            )
                            end as independent_station_bysize_qt_rating -- 独立站分码定量评级 -- 独立站评级改这个逻辑
                        ,t2.product_rating -- 产品评级 
                        ,t2.operational_rating -- 运营评级
                        ,t2.commodity_rating -- 企划评级
                        -- ,t2.other_channel_rating -- 渠道拓展评级
                        -- ,t2.tiktok_channel_rating -- Tiktok评级
                    FROM cupshe_bigdata_ads.ads_scm_cp_product_rating_df t1
                    LEFT JOIN cupshe_bigdata_ods.odsp_scm_proc_process_sheets t2
                    ON t1.cp = t2.cp
                    LEFT JOIN cupshe_bigdata_cdm.dim_pub_sku_category t3
                    ON t1.cp = t3.cp
                    WHERE t2.pt=MAX_PT('cupshe_bigdata_ods.odsp_scm_proc_process_sheets') 
                ) d
                on cb.skc = d.skc
            )
            group by skc
        )
    )
    WHERE 
        skc is not null
) 
, t16 as (
    WITH
    -- cp业务属性基础：只读取一次，输出 skc,theme,target_customer_group
    cp_biz_attr AS (
        SELECT
            b.skc,
            c.theme,
            CASE
                WHEN a.target_customer_group = 1 THEN '22-28岁'
                WHEN a.target_customer_group = 2 THEN '29-34岁'
                WHEN a.target_customer_group = 3 THEN '35-44岁'
            END AS target_customer_group
        FROM cupshe_bigdata_ods.ods_scm_proc_cp_business_df a
        LEFT JOIN (
            SELECT DISTINCT skc, cp
            FROM cupshe_bigdata_cdm.dim_pub_sku_category
        ) b ON a.cp = b.cp
        LEFT JOIN (
            SELECT id, theme
            FROM cupshe_bigdata_ods.ods_scm_proc_config_theme_df
            WHERE pt = MAX_PT('cupshe_bigdata_ods.ods_scm_proc_config_theme_df')
        ) c ON a.theme_id = c.id
        WHERE
            pt = MAX_PT('cupshe_bigdata_ods.ods_scm_proc_cp_business_df')
            AND a.cp IS NOT NULL
            AND b.skc IS NOT NULL
    ),
    -- 组合虚拟120skc：子skc取属性，聚合回填给combination_skc
    comb_skc_attr AS (
        SELECT
            v.combination_skc AS skc,
            MAX(attr.theme) AS theme,
            MAX(attr.target_customer_group) AS target_customer_group
        FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df v
        LEFT JOIN cp_biz_attr attr
            ON v.skc = attr.skc
        GROUP BY v.combination_skc
    )
    SELECT
        skc,
        MAX(theme) AS theme,
        MAX(target_customer_group) AS target_customer_group
    FROM (
        SELECT skc, theme, target_customer_group FROM cp_biz_attr
        UNION ALL
        SELECT skc, theme, target_customer_group FROM comb_skc_attr
    ) t
    GROUP BY skc
) 

,t17 as (
    --商业层级tag
    SELECT 
        skc
        ,business_level
    FROM 
    (
        SELECT -- 单品
            -- cp
            b.skc
            ,CASE 
                when business_level = 1 then 'Hero'
                when business_level = 2 then 'Core'
                when business_level = 3 then 'Seasonal'
                when business_level = 4 then 'Capsule'
                when business_level = 5 then '其他'
            end as business_level
        from cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di pps
        LEFT JOIN 
        (
            select
                distinct 
                process_sheets_id
                ,business_level
            from cupshe_bigdata_ods.ods_proc_process_sheets_extra_df
            WHERE 
                pt = MAX_PT('cupshe_bigdata_ods.ods_proc_process_sheets_extra_df')
                and is_del = 0 
        ) business_level on business_level.process_sheets_id = pps.id 
        left join 
        (
            select
                distinct
                skc,cp
            from cupshe_bigdata_cdm.dim_pub_sku_category
        ) b on pps.cp = b.cp
        WHERE  
            pps.pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di')
            and is_del = 0 
        union
        SELECT -- 组合品
        combination_skc skc
        ,max(business_level) business_level
        FROM 
        (
            SELECT 
                combination_skc
                ,v.skc
                ,business_level
            from cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df v 
            left JOIN 
            (
                SELECT -- 单品
                    -- cp
                    b.skc
                    ,CASE 
                        when business_level = 1 then 'Hero'
                        when business_level = 2 then 'Core'
                        when business_level = 3 then 'Seasonal'
                        when business_level = 4 then 'Capsule'
                        when business_level = 5 then '其他'
                    end as business_level
                from cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di pps
                LEFT JOIN 
                (
                    select
                        distinct 
                        process_sheets_id
                        ,business_level
                    from cupshe_bigdata_ods.ods_proc_process_sheets_extra_df
                    WHERE 
                        pt = MAX_PT('cupshe_bigdata_ods.ods_proc_process_sheets_extra_df')
                        and is_del = 0 
                ) business_level on business_level.process_sheets_id = pps.id 
                left join 
                (
                    select
                        distinct
                        skc,cp
                    from cupshe_bigdata_cdm.dim_pub_sku_category
                ) b on pps.cp = b.cp
                WHERE  
                    pps.pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_plm_proc_process_sheets_di')
                    and is_del = 0 
            ) a on v.skc = a.skc
        )
        group by combination_skc 
    )
) 
, detail as
(
    SELECT 
        month_str
        ,country
        ,t1.skc
        ,t7.combination_skc 组合品子品对应组合品skc
        ,CASE
            when t1.skc is not null and t7.combination_skc is null then t1.skc
            when t1.skc is not null and t7.combination_skc is not null then t7.combination_skc
        end as skc_adjust
        ,CASE
            when t1.skc is not null and t1.skc like '120%' then '组合品'
            when t1.skc is not null and t7.combination_skc is null then '单品'
            when t1.skc is not null and t7.combination_skc is not null then '组合品子品'
            else '其他'
        end as skc架上形式
        ,cp
        ,spu
        -- 当月新品的判断有点争议，按照站点上架时间和产品中心定义上架时间逻辑的话
        ,t1.first_published_at 首次上架时间_产品中心全站
        ,t1.first_shelves_price 首次上架价格_产品中心全站
        ,case when is_new_this_month = '新品' and (channels regexp '独立站' or channels is null) then '新品'
        when is_new_this_month = '未上架' then '未上架'  
        else '老品'end 是否当月上新_产品中心全站
        ,case when is_new_this_year = '新品' and (channels regexp '独立站' or channels is null) then '新品'
        when is_new_this_year = '未上架' then '未上架'  
        else '老品'end 是否当年上新_产品中心全站


        ,t2.first_published_de 首次上架时间_德站
        ,t2.first_price_de 首次上架价格_德站
        ,case when substr(t2.first_published_de,1,7) > month_str  then '未上架'
        when substr(t2.first_published_de,1,7) = month_str  and (channels regexp '独立站' or channels is null) then '新品'
        else '老品' end  是否当月上新_德站
        ,case when substr(t2.first_published_de,1,4) > substr(month_str,1,4)  then '未上架'
        when substr(t2.first_published_de,1,4) = substr(month_str,1,4)  and (channels regexp '独立站' or channels is null) then '新品'
        else '老品' end  是否当年上新_德站

        -- 畅滞销也两套逻辑
        ,nvl(popular_type,'不动销') 畅滞销_产品中心全站

        ,case when is_online_adjust = 1 then '在架'
        else '不在架' end 当月是否在架
        ,is_online_qc_adjust 月初是否在架
        ,is_online_qm_adjust 月末是否在架
        ,online_days_adjust 当月在架天数
        ,first_order_price 首单采购价
        ,qty_first_receving 首单采购量

        


        ,nvl(sale_quantity,0) 销量
        ,nvl(sale_amount_usd,0) 销售额
        ,NVL(sale_amount_usd / NULLIF(sale_quantity, 0), 0) 平均售价
        ,CASE   WHEN NVL(sale_quantity,0) = 0 THEN '[0-19)'
                    ELSE 
                        CASE    WHEN ((sale_amount_usd) / (sale_quantity) >= 0  AND (sale_amount_usd) / (sale_quantity) < 19 ) THEN '[0,19)'
                                WHEN ((sale_amount_usd) / (sale_quantity) >= 19 AND (sale_amount_usd) / (sale_quantity) < 22 ) THEN '[19,22)'
                                WHEN ((sale_amount_usd) / (sale_quantity) >= 22 AND (sale_amount_usd) / (sale_quantity) < 25 ) THEN '[22,25)'
                                WHEN ((sale_amount_usd) / (sale_quantity) >= 25 AND (sale_amount_usd) / (sale_quantity) < 28 ) THEN '[25,28)'
                                WHEN ((sale_amount_usd) / (sale_quantity) >= 28 AND (sale_amount_usd) / (sale_quantity) < 31 ) THEN '[28,31)'
                                WHEN ((sale_amount_usd) / (sale_quantity) >= 31 AND (sale_amount_usd) / (sale_quantity) < 34 ) THEN '[31,34)'
                                WHEN ((sale_amount_usd) / (sale_quantity) >= 34 AND (sale_amount_usd) / (sale_quantity) < 37 ) THEN '[34,37)'
                                WHEN ((sale_amount_usd) / (sale_quantity) >= 37 AND (sale_amount_usd) / (sale_quantity) < 40 ) THEN '[37,40)'
                                WHEN ((sale_amount_usd) / (sale_quantity)) >= 40 THEN '[40,+)'
                    END
        END 单价区间
        ,nvl(return_quantity,0) 退货数量
        ,nvl(refund_amount_usd,0) 退款金额
        ,nvl(refund_couponv_usd,0) 退券金额
        ,nvl(refund_store_credit_usd,0) 钱包金额
        ,nvl(total_refund_amount_usd,0) `退款+退券+钱包总金额`
        ,nvl(collection_view_user,0) 商列浏览uv
        ,nvl(collection_click_user,0) 商列点击uv
        ,nvl(collection_add_to_cart_user,0) 商列加车uv 
        ,nvl(pdp_view_user,0) 商详浏览uv
        ,nvl(pdp_add_to_cart_user,0) 商详加车uv
        ,nvl(sale_amount_usd/nullif(pdp_view_user,0),0) uv产出
        ,nvl(collection_click_user/nullif(collection_view_user,0),0) ctr_uv
        ,nvl(sale_quantity/nullif(pdp_view_user,0),0) cvr_uv

        ,nvl(online_days_3_de,0) 上架3天实际在架天数_德站
        ,nvl(online_days_5_de,0) 上架5天实际在架天数_德站
        ,nvl(online_days_7_de,0) 上架7天实际在架天数_德站
        ,nvl(online_days_15_de,0) 上架15天实际在架天数_德站
        ,nvl(online_days_30_de,0) 上架30天实际在架天数_德站
        ,nvl(online_days_45_de,0) 上架45天实际在架天数_德站
        ,nvl(online_days_60_de,0) 上架后60天实际在架天数_德站

        ,nvl(3_gmv_de,0) 上架3天gmv_德站
        ,nvl(5_gmv_de,0) 上架5天gmv_德站
        ,nvl(7_gmv_de,0) 上架7天gmv_德站
        ,nvl(15_gmv_de,0) 上架15天gmv_德站
        ,nvl(30_gmv_de,0) 上架30天gmv_德站
        ,nvl(45_gmv_de,0) 上架45天gmv_德站
        ,nvl(60_gmv_de,0) 上架60天gmv_德站
        ,nvl(3_quantity_de,0) 上架3天销量_德站
        ,nvl(5_quantity_de,0) 上架5天销量_德站
        ,nvl(7_quantity_de,0) 上架7天销量_德站
        ,nvl(15_quantity_de,0) 上架15天销量_德站
        ,nvl(30_quantity_de,0) 上架30天销量_德站
        ,nvl(45_quantity_de,0) 上架45天销量_德站
        ,nvl(60_quantity_de,0) 上架60天销量_德站

        ,NVL(3_collection_view_user_de,0) AS 上架3天商列浏览uv_德站
        ,NVL(5_collection_view_user_de,0) AS 上架5天商列浏览uv_德站
        ,NVL(7_collection_view_user_de,0) AS 上架7天商列浏览uv_德站
        ,NVL(15_collection_view_user_de,0) AS 上架15天商列浏览uv_德站
        ,NVL(30_collection_view_user_de,0) AS 上架30天商列浏览uv_德站
        ,NVL(45_collection_view_user_de,0) AS 上架45天商列浏览uv_德站
        ,NVL(60_collection_view_user_de,0) AS 上架60天商列浏览uv_德站
        ,NVL(3_pdp_view_user_de,0) AS 上架3天商详浏览uv_德站
        ,NVL(5_pdp_view_user_de,0) AS 上架5天商详浏览uv_德站
        ,NVL(7_pdp_view_user_de,0) AS 上架7天商详浏览uv_德站
        ,NVL(15_pdp_view_user_de,0) AS 上架15天商详浏览uv_德站
        ,NVL(30_pdp_view_user_de,0) AS 上架30天商详浏览uv_德站
        ,NVL(45_pdp_view_user_de,0) AS 上架45天商详浏览uv_德站
        ,NVL(60_pdp_view_user_de,0) AS 上架60天商详浏览uv_德站
        ,NVL(3_collection_click_user_de,0) AS 上架3天商列点击uv_德站
        ,NVL(5_collection_click_user_de,0) AS 上架5天商列点击uv_德站
        ,NVL(7_collection_click_user_de,0) AS 上架7天商列点击uv_德站
        ,NVL(15_collection_click_user_de,0) AS 上架15天商列点击uv_德站
        ,NVL(30_collection_click_user_de,0) AS 上架30天商列点击uv_德站
        ,NVL(45_collection_click_user_de,0) AS 上架45天商列点击uv_德站
        ,NVL(60_collection_click_user_de,0) AS 上架60天商列点击uv_德站
        ,NVL(3_pdp_add_to_cart_user_de,0) AS 上架3天商详加车uv_德站
        ,NVL(5_pdp_add_to_cart_user_de,0) AS 上架5天商详加车uv_德站
        ,NVL(7_pdp_add_to_cart_user_de,0) AS 上架7天商详加车uv_德站
        ,NVL(15_pdp_add_to_cart_user_de,0) AS 上架15天商详加车uv_德站
        ,NVL(30_pdp_add_to_cart_user_de,0) AS 上架30天商详加车uv_德站
        ,NVL(45_pdp_add_to_cart_user_de,0) AS 上架45天商详加车uv_德站
        ,NVL(60_pdp_add_to_cart_user_de,0) AS 上架60天商详加车uv_德站
        ,NVL(3_collection_add_to_cart_user_de,0) AS 上架3天商列加车uv_德站
        ,NVL(5_collection_add_to_cart_user_de,0) AS 上架5天商列加车uv_德站
        ,NVL(7_collection_add_to_cart_user_de,0) AS 上架7天商列加车uv_德站
        ,NVL(15_collection_add_to_cart_user_de,0) AS 上架15天商列加车uv_德站
        ,NVL(30_collection_add_to_cart_user_de,0) AS 上架30天商列加车uv_德站
        ,NVL(45_collection_add_to_cart_user_de,0) AS 上架45天商列加车uv_德站
        ,NVL(60_collection_add_to_cart_user_de,0) AS 上架60天商列加车uv_德站

        ,NVL(3_collection_click_user_de / NULLIF(3_collection_view_user_de, 0), 0) AS 上架3天商列CTR_德站
        ,NVL(5_collection_click_user_de / NULLIF(5_collection_view_user_de, 0), 0) AS 上架5天商列CTR_德站
        ,NVL(7_collection_click_user_de / NULLIF(7_collection_view_user_de, 0), 0) AS 上架7天商列CTR_德站
        ,NVL(15_collection_click_user_de / NULLIF(15_collection_view_user_de, 0), 0) AS 上架15天商列ctr_德站
        ,NVL(30_collection_click_user_de / NULLIF(30_collection_view_user_de, 0), 0) AS 上架30天商列ctr_德站
        ,NVL(45_collection_click_user_de / NULLIF(45_collection_view_user_de, 0), 0) AS 上架45天商列ctr_德站
        ,NVL(60_collection_click_user_de / NULLIF(60_collection_view_user_de, 0), 0) AS 上架60天商列ctr_德站

        ,nvl(3_quantity_de/NULLIF(3_pdp_view_user_de,0),0) 上架3天cvr_德站
        ,nvl(5_quantity_de/NULLIF(5_pdp_view_user_de,0),0) 上架5天cvr_德站
        ,nvl(7_quantity_de/NULLIF(7_pdp_view_user_de,0),0) 上架7天cvr_德站
        ,nvl(15_quantity_de/NULLIF(15_pdp_view_user_de,0),0) 上架15天cvr_德站
        ,nvl(30_quantity_de/NULLIF(30_pdp_view_user_de,0),0) 上架30天cvr_德站
        ,nvl(45_quantity_de/NULLIF(45_pdp_view_user_de,0),0) 上架45天cvr_德站
        ,nvl(60_quantity_de/NULLIF(60_pdp_view_user_de,0),0) 上架60天cvr_德站

        ,nvl(3_quantity_de/NULLIF(online_days_3_de,0),0) 上架3天日均销量
        ,NVL(5_quantity_de / NULLIF(online_days_5_de, 0), 0) AS 上架5天日均销量
        ,NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) AS 上架7天日均销量
        ,NVL(15_quantity_de / NULLIF(online_days_15_de, 0), 0) AS 上架15天日均销量
        ,NVL(30_quantity_de / NULLIF(online_days_30_de, 0), 0) AS 上架30天日均销量
        ,NVL(45_quantity_de / NULLIF(online_days_45_de, 0), 0) AS 上架45天日均销量
        ,NVL(60_quantity_de / NULLIF(online_days_60_de, 0), 0) AS 上架60天日均销量

        ,nvl(3_gmv_de/NULLIF(online_days_3_de,0),0) 上架3天日均gmv
        ,NVL(5_gmv_de / NULLIF(online_days_5_de, 0), 0) AS 上架5天日均gmv
        ,NVL(7_gmv_de / NULLIF(online_days_7_de, 0), 0) AS 上架7天日均gmv
        ,NVL(15_gmv_de / NULLIF(online_days_15_de, 0), 0) AS 上架15天日均gmv
        ,NVL(30_gmv_de / NULLIF(online_days_30_de, 0), 0) AS 上架30天日均gmv
        ,NVL(45_gmv_de / NULLIF(online_days_45_de, 0), 0) AS 上架45天日均gmv
        ,NVL(60_gmv_de / NULLIF(online_days_60_de, 0), 0) AS 上架60天日均gmv

         ,CASE 
                when  second_category = '泳衣'  THEN  
                    case 
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=0 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 1 then '不动销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=1 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 2.5 then '滞销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=2.5 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 5 then '平销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=5 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 30 then '畅销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=30 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 50 then '爆款'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=50 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 100 then '大爆款'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=100 then '超爆款'
                    END 
                when second_category != '泳衣' then 
                    case 
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=0 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 1 then '不动销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=1 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 2.5 then '滞销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=2.5 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 5 then '平销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=5 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 15 then '畅销'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=15 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 30 then '爆款'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=30 and NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) < 50 then '大爆款'
                        when NVL(7_quantity_de / NULLIF(online_days_7_de, 0), 0) >=50 then '超爆款'
                    END 
            end popular_condition1,
            case
                WHEN  (second_category = '泳衣' and NVL(7_gmv_de / NULLIF(online_days_7_de, 0), 0) >= 140.4 )
                    or (second_category = '连衣裙' and NVL(7_gmv_de / NULLIF(online_days_7_de, 0), 0) >= 140 )
                    or (second_category = '罩衫' and NVL(7_gmv_de / NULLIF(online_days_7_de, 0), 0) >= 133 )
                    or (second_category = '连体装' and NVL(7_gmv_de / NULLIF(online_days_7_de, 0), 0) >= 149 )
                    or (second_category = '上衣' and NVL(7_gmv_de / NULLIF(online_days_7_de, 0), 0) >= 111 )
                    or (second_category = '下装' and NVL(7_gmv_de / NULLIF(online_days_7_de, 0), 0) >= 131 ) then '畅销'
            end popular_condition2

    from 
    (
        select *
        from cupshe_bigdata_ads.ads_prod_country_product_info_mi t1
        where 
            pt >= 202201
            and country = 'DE' 
            and is_online_adjust = 1 
            and big_category = '泳衣'
            -- and t1.skc not like '120%' and t2.first_price_de != t1.first_shelves_price
            -- and case when substr(t2.first_published_de,1,7) > month_str  then '未上架'
            -- when substr(t2.first_published_de,1,7) = month_str  and (channels regexp '独立站' or channels is null) then '新品'
            -- else '老品' end = '未上架'
            -- and nvl(refund_store_credit_usd,0) != 0
    ) t1
    left join shangjia_skc_us_info t2 on t1.skc = t2.skc
    left join first_gmv t3 on t1.skc = t3.skc
    left join first_flow t4 on t1.skc = t4.skc
    left join first_online_days t5 on t1.skc = t5.skc
    left JOIN 
    (
        SELECT  DISTINCT skc
                ,combination_skc
        FROM    cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df
    ) t7 on t1.skc = t7.skc
)
SELECT 
    t1.* except (popular_condition1,popular_condition2)
    ,nvl(case when substr(首次上架时间_德站,1,7) <= '2026-08' and popular_condition2 IS NOT NULL AND popular_condition1 NOT IN ("爆款","大爆款","超爆款") then popular_condition2
    else popular_condition1 end,'不动销')  AS  畅滞销_德站 
    ,t2.tentative_release_date 预计上架时间
    ,t2.expected_release_date 期望上架时间
    ,t2.is_gift_cart 是否礼品卡
    ,t2.image_src 图片链接
    ,t15.oss_url_prototype  样衣图片链接
       ,case 
        when t2.business_group_name is null AND t2.second_category = '泳衣' then '泳衣产品部'
        when t2.business_group_name is null AND t2.second_category in ("下装","运动服","连体装","针织服装","外套","罩衫","上衣","两件套","连衣裙","上装")  then '成衣一部'
        when t2.business_group_name is null AND t2.second_category in  ('内衣','睡衣','家居服','塑身衣')  then '内睡'
        when t2.business_group_name is null AND t2.first_category in  ('女士配饰','女士鞋品')  then 'ACC'
        else t2.business_group_name
    end as 业务部门
    ,t2.group_name
    ,t2.first_color
    ,t2.designer_name
    ,t2.time_line_type timeline类型
    ,t2.channels 渠道
    ,t2.big_category 大类
    ,t2.first_category 一级品类
    ,t2.second_category 二级品类
    ,t2.third_category 三级品类
    ,t2.original_fixed_scene_tag 场景tag
    ,if(t2.series is null OR  t2.series = '' ,null,t2.series) 原始人群画像 -- 20260901 人群画像改为人群线，字段名不变
    ,if(t2.series not in ('SEA','SOL','DAWN'),'OTHERS',t2.series) 人群画像
    ,nvl(t16.target_customer_group,t2.target_customer_group) 目标客户群体
    ,t2.style_position 款式定位
    ,if(nvl(t16.theme,t2.theme_name) is null or nvl(t16.theme,t2.theme_name) = '',null,nvl(t16.theme,t2.theme_name))  主题名称
    ,t2.style_tag 风格
    ,t2.pattern_tag 图案
    ,t2.solid_print_tag 纯色印花
    ,t2.product_layering `plm商品分层（商品款式分类）`
    ,t2.color1_tag 颜色1
    ,t2.color2_tag 颜色2
    ,t2.color3_tag 颜色3
    ,t2.design_details 设计细节
    ,ingredient_content_cn 成分含量_cn
    ,t2.fabric_construction 织造方式
    ,t2.material_composition 主要成分
    ,t2.collar_style 领型
    ,t2.waistline_position 腰线
    ,t2.coat_length 衣长
    ,t2.sleeve_length 袖长
    ,t2.sleeve_type 袖型
    ,t2.skirt_length 裙长
    ,t2.rise 腰高
    ,t2.silhouette 廓型
    ,t2.first_color 首复色
    ,if(t2.model_code is null or t2.model_code = '',null,t2.model_code) model_code
    ,if(t2.model_name is null or t2.model_name = '',null,t2.model_name) 模特名称
    ,case 
        when t2.model_type = 1 then '成人'
        when t2.model_type = 0 then '儿童'
    end as 模特类型
    ,t2.mail 模特mail
    ,t2.phone 模特phone
    ,t2.`location` 模特location
    ,t2.price 模特price
    ,t2.attiude 模特attiude
    ,t2.is_cooperate 模特is_cooperate

    ,t10.independent_station_bysize_qt_rating 独立站选品会评级 -- 独立站选品会评级，定泳看选品会评级，其他看分码定量评级
    ,t10.independent_station_selection_rating 独立站分码定量评级 -- 独立站分码定量评级
    ,t10.product_rating 产品评级 -- 产品评级
    ,t10.operational_rating 运营评级 -- 运营评级
    ,t10.commodity_rating 企划评级 -- 企划评级
    ,t17.business_level 商业层级
from detail t1
left join (select * from cupshe_bigdata_ads.ads_prod_skc_product_info_mi t1 where pt = MAX_PT('cupshe_bigdata_ads.ads_prod_skc_product_info_mi')) t2 on t1.skc = t2.skc 
left join t15 on t1.skc = t15.skc 
left join t16 on t1.skc = t16.skc
left join t10 on t1.skc = t10.skc
left join t17 on t1.skc = t17.skc







    ;