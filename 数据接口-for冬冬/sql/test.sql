-- SQL 查询脚本（Notebook 版本）
-- 在此文件中编写你的 SQL 语句
-- 支持多行 SQL，使用分号分隔多条语句

WITH shangjia_skc_us_info AS 
(
    SELECT  a.skc
            ,a.first_published_at
            ,rate -- 改动11，取消抓修改了首次商家时间的逻辑，会影响到首次商家时间跨月和不跨月的那个逻辑；首次上架价格仅采用美国站的首次上架价格
            -- ,if(a.first_published_at != b.first_published_at,b.first_published_at,a.first_published_at) first_published_at
            ,b.first_price first_price_us
            ,b.first_price * rate first_price_rmb
    FROM    (
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
    LEFT JOIN    -- 改动11，取消抓修改了首次商家时间的逻辑，会影响到首次商家时间跨月和不跨月的那个逻辑；首次上架价格仅采用美国站的首次上架价格
        (
                    -- 改动7，增加首次上架价格，按照美国站思路，首次上架时间更新调整
                    SELECT  skc
                            ,IF(SUBSTR(first_published_us,1,7) = SUBSTR(first_published_dtc,1,7),first_published_us,LEAST(first_published_us,first_published_dtc)) first_published_at -- 如果没有美国站上架时间，就用DTC最早上架日期对应的价格
                            ,IF(first_price_us = 99999,first_price_dtc,first_price_us) first_price
                    FROM    (
                                -- 全站
                                SELECT  skc
                                        ,MIN(min_published_at) first_published_dtc
                                        ,MIN(IF(a.shop_id = 1,min_published_at,'9999-99-99')) first_published_us
                                        ,MIN_BY(first_price * ex_rate,min_published_at) first_price_dtc -- DTC最早上架日期对应的价格
                                        ,MIN(IF(a.shop_id = 1,first_price * ex_rate,99999)) first_price_us -- 美国站的最早上架价格
                                FROM    cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di a
                                LEFT JOIN CUPSHE_BIGDATA_CDM.dim_pub_fiscal_site_rate b
                                ON      a.shop_id = b.shop_id
                                AND     a.min_published_at = b.date_str
                                WHERE   pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di')
                                GROUP BY skc
                            ) 
                ) b
    ON      a.skc = b.skc
    LEFT JOIN   (
                    SELECT  fmonth_str
                            ,cur_code
                            ,base_cur_code
                            ,rate
                    FROM    cupshe_bigdata_cdm.dim_pub_full_cur_rate
                    WHERE   `type` = 2 -- 人民币
                    AND     cur_code = 'USD'
                ) cur_rate
    ON      cur_rate.fmonth_str = SUBSTR(b.first_published_at,1,7)
)
,sale_info AS 
(
    SELECT  skc
            ,sku
            ,subsite_id
            ,SUBSTR(buy_time,1,10) AS date_str
            ,CAST(SUM(quantity) AS BIGINT) AS sale_quantity
            ,SUM(sku_org_money_us) AS sale_amount_us
    FROM    cupshe_bigdata_cdm.dwd_trd_order_detail_combination_df
    GROUP BY skc
             ,subsite_id
             ,subsite_name
             ,sku
             ,SUBSTR(buy_time,1,10)
)
,sku_is_online AS 
(
    SELECT  CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2)) month_str
            ,skc
            ,sku
            ,SUM(is_online) > 1 sku_is_online_month
    FROM    cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di
    WHERE   pt >= 20260101
    AND     pt <= 20260630
    GROUP BY CONCAT(SUBSTR(pt,1,4),'-',SUBSTR(pt,5,2))
             ,skc
             ,sku
)
SELECT  sio.month_str 月
        ,sio.skc
        ,sio.sku
        ,shangjia_skc_us_info.first_published_at
        ,d.second_category
        ,d.third_category
        ,d.category
        ,c.skc当月在架天数
        ,d.style_position_name
        ,d.theme -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,3),sale_quantity,null)) over (partition by sale_info.sku) 上架3天销量
        -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,5),sale_quantity,null)) over (partition by sale_info.sku) 上架5天销量
        -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,7),sale_quantity,null)) over (partition by sale_info.sku) 上架7天销量
        -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,15),sale_quantity,null)) over (partition by sale_info.sku)上架15天销量
        -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,30),sale_quantity,null)) over (partition by sale_info.sku) 上架30天销量
        -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,45),sale_quantity,null)) over (partition by sale_info.sku) 上架45天销量
        -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,60),sale_quantity,null)) over (partition by sale_info.sku) 上架60天销量
        -- ,sum(if(date_str between first_published_at and DATE_ADD(first_published_at,90),sale_quantity,null)) over (partition by sale_info.sku) 上架90天销量
        ,SUM(销量) 销量
        ,SUM(销售额) 销售额 -- skc当月在架天数
FROM    (
            SELECT  *
            FROM    sku_is_online sio
            WHERE   sku_is_online_month = true
        ) sio
LEFT JOIN   (
                SELECT  SUBSTR(date_str,1,7) 月
                        ,skc
                        ,sku
                        ,SUM(sale_quantity) 销量
                        ,SUM(sale_amount_us) 销售额
                FROM    sale_info
                GROUP BY SUBSTR(date_str,1,7)
                         ,skc
                         ,sku
            ) si
ON      sio.month_str = si.月
AND     sio.skc = si.skc
AND     sio.sku = si.sku
LEFT JOIN shangjia_skc_us_info
ON      sio.skc = shangjia_skc_us_info.skc
LEFT JOIN   (
                SELECT  SUBSTR(date_str,1,7) month_str
                        ,skc
                        ,SUM(is_online_adjustment) skc当月在架天数
                FROM    cupshe_bigdata_ads.ads_prod_skc_product_info_di
                WHERE   pt >= 20260101
                AND     pt <= 20260630
                GROUP BY SUBSTR(date_str,1,7)
                         ,skc
            ) c
ON      c.skc = sio.skc
AND     c.month_str = sio.month_str
LEFT JOIN   (
                SELECT  skc
                        ,combination_skc
                        ,category
                        ,second_category_name second_category
                        ,third_category_name third_category
                        ,MAX(style_position_name) style_position_name
                        ,MAX(theme) theme
                FROM    cupshe_bigdata_cdm.dim_pub_cp_skc_info_di
                WHERE   pt = MAX_PT('cupshe_bigdata_cdm.dim_pub_cp_skc_info_di')
                GROUP BY skc
                         ,combination_skc
                         ,category
                         ,second_category
                         ,third_category
            ) d
ON      NVL(d.combination_skc,d.skc) = sio.skc
WHERE   d.category IN ('成衣','内睡')
GROUP BY sio.month_str
         ,sio.skc
         ,sio.sku
         ,shangjia_skc_us_info.first_published_at
         ,d.second_category
         ,d.third_category
         ,d.category
         ,c.skc当月在架天数
         ,d.style_position_name
         ,d.theme
 ;