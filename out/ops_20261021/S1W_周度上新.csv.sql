
with a as
(
    SELECT 
    month_str
    ,a.skc skc_original
    -- 改动七，增加组合品skc并用组合品skc替换原始skc，解决组合品和单品同时在架重复计算问题
    ,c.combination_skc 
    -- 懒得大规模改脚本，直接把skc_adjust改成skc
    ,CASE
        when a.skc is not null and c.combination_skc is null then a.skc
        when a.skc is not null and c.combination_skc is not null then c.combination_skc
    end as skc
    ,CASE
        when a.skc is not null and a.skc like '120%' then '组合品'
        when a.skc is not null and c.combination_skc is null then '单品'
        when a.skc is not null and c.combination_skc is not null then '组合品子品'
        else '其他'
    end as skc_status
    ,first_published_at
    ,is_new_this_month
    ,is_new_this_year
    ,first_shelves_7d
    ,first_shelves_7d_adjust
    ,first_shelves_price
    ,is_online_qc
    ,is_online_qc_adjust
    ,is_online_qm
    ,is_online_qm_adjust
    ,online_days
    ,online_days_adjust
    ,is_online
    ,is_online_adjust
    ,nvl(collection_view_cnt,0) collection_view_cnt
    ,nvl(collection_view_user,0) collection_view_user
    ,nvl(pdp_view_cnt,0) pdp_view_cnt
    ,nvl(pdp_view_user,0) pdp_view_user
    ,nvl(collection_click_cnt,0) collection_click_cnt
    ,nvl(collection_click_user,0) collection_click_user
    ,nvl(pdp_add_to_cart_user,0) pdp_add_to_cart_user
    ,nvl(collection_add_to_cart_user,0) collection_add_to_cart_user
    ,nvl(sale_quantity,0) sale_quantity
    ,nvl(sale_amount_usd,0) sale_amount_usd
    ,nvl(return_quantity,0) return_quantity
    ,nvl(refund_couponv_usd,0) refund_couponv_usd
    ,nvl(refund_amount_usd,0) refund_amount_usd
    ,nvl(total_refund_amount_usd,0) total_refund_amount_usd
    ,nvl(repeat_order_count,0) repeat_order_count
    ,nvl(repeat_quantity,0) repeat_quantity
    ,avg_sale_quantity_7d
    ,avg_sale_amount_usd_7d
    ,if(first_shelves_7d_adjust=0,0,sale_quantity_7d/first_shelves_7d_adjust) avg_sale_quantity_7d_adjust
    ,if(first_shelves_7d_adjust=0,0,sale_amount_usd_7d/first_shelves_7d_adjust) avg_sale_amount_usd_7d_adjust
    ,avg_price
    ,avg_price_range
    ,sale_quantity_7d
    ,sale_amount_usd_7d
    ,sale_quantity_15d
    ,sale_amount_usd_15d
    ,sale_quantity_30d
    ,sale_amount_usd_30d
    ,sale_quantity_45d
    ,sale_amount_usd_45d
    ,sale_quantity_60d
    ,sale_amount_usd_60d
    ,collection_click_user_7d
    ,pdp_view_user_7d
    ,collection_view_user_7d
    ,pdp_add_to_cart_user_7d
    ,collection_add_to_cart_user_7d
    ,collection_click_user_15d
    ,pdp_view_user_15d
    ,collection_view_user_15d
    ,pdp_add_to_cart_user_15d
    ,collection_add_to_cart_user_15d
    ,collection_click_user_30d
    ,pdp_view_user_30d
    ,collection_view_user_30d
    ,pdp_add_to_cart_user_30d
    ,collection_add_to_cart_user_30d
    ,collection_click_user_45d
    ,pdp_view_user_45d
    ,collection_view_user_45d
    ,pdp_add_to_cart_user_45d
    ,collection_add_to_cart_user_45d
    ,collection_click_user_60d
    ,pdp_view_user_60d
    ,collection_view_user_60d
    ,pdp_add_to_cart_user_60d
    ,collection_add_to_cart_user_60d
    ,is_gift_cart
    ,a.first_order_price
    ,a.qty_first_receving
    ,spu
    ,a.cp
    ,time_line_type
    ,big_category
    ,first_category
    ,second_category
    ,third_category
    ,-- 部门逻辑修改
    case 
        when business_group_name is null AND second_category = '泳衣' then '泳衣产品部'
        when business_group_name is null AND second_category in ("下装","运动服","连体装","针织服装","外套","罩衫","上衣","两件套","连衣裙","上装")  then '成衣一部'
        when business_group_name is null AND second_category in  ('内衣','睡衣','家居服','塑身衣')  then '内睡'
        when business_group_name is null AND first_category in  ('女士配饰','女士鞋品')  then 'ACC'
        else business_group_name
    end as business_group_name
    ,group_name
    ,first_color
    ,designer_name
    ,image_src
    ,sample_oss_url
    ,case 
        when tab_tag is null or tab_tag = 'Tab-Vacation|Tab-Everyday' or tab_tag = 'Tab-Everyday|Tab-Vacation' then 'Tab-Vacation'
        ELSE tab_tag
    end as tab_tag
    ,original_fixed_scene_tag
    ,fixed_scene_tag
    ,if(user_tag is null OR  user_tag = '' ,null,user_tag) user_tag
    ,style_tag
    ,pattern_tag
    ,solid_print_tag
    ,color1_tag
    ,color2_tag
    ,color3_tag
    -- 改动14，上新渠道统一修改为下单渠道
    ,channels -- 原渠道字段，定泳为下单渠道，成衣为开发渠道
    -- ,fob_channels channels -- 改为分码定量下单渠道
    ,business_channels -- 企划设计渠道（开发渠道）
    ,if(popular_type is null ,'不动销',popular_type) popular_type
    ,design_details
    ,fabric_construction
    ,material_composition
    ,collar_style
    ,waistline_position
    ,coat_length
    ,sleeve_length
    ,sleeve_type
    ,skirt_length
    ,rise
    ,silhouette
    ,a.style_position style_position
    -- 改动20，拆开无库存测试实际数和其他实际数（正常）
    ,case
        when a.style_position = '无库存测试款' then '无库存测试款'
        else '正常目标'
    end style_position_adjust
    ,product_layering
    ,a.target_customer_group
    ,a.theme_name 
    ,tentative_release_date
    ,expected_release_date
    ,ingredient_content_cn
    ,plm_attributes_sets
    ,plm_product_properties
    ,if(model_code is null or model_code = '',null,model_code) model_code
    ,if(model_name is null or model_name = '',null,model_name) model_name
    ,case 
        when model_type = 1 then '成人'
        when model_type = 0 then '儿童'
    end as model_type
    ,mail
    ,phone
    ,`location`
    ,price
    ,attiude
    ,is_cooperate
    ,product_level
    ,pt
    ,nation_line_name
FROM    cupshe_bigdata_ads.ads_prod_skc_product_info_mi a
left JOIN 
(
    SELECT  DISTINCT skc
            ,combination_skc
    FROM    cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df
) c on a.skc = c.skc
WHERE 
    PT>0 and is_online_adjust = 1 and big_category != '赠品'
)
,b as (
    SELECT '本周' period, business_group_name, big_category, skc FROM a
    WHERE PT>0 and is_online_adjust = 1 and month_str = '2026-10'
        and is_gift_cart = '否' and (channels regexp '独立站' or channels is null)
        and style_position_adjust = '正常目标'
        and month_str = substr(first_published_at,1,7)
        and substr(first_published_at,1,10) between '2026-10-19' and '2026-10-25'
    UNION ALL
    SELECT '上周' period, business_group_name, big_category, skc FROM a
    WHERE PT>0 and is_online_adjust = 1 and month_str = '2026-10'
        and is_gift_cart = '否' and (channels regexp '独立站' or channels is null)
        and style_position_adjust = '正常目标'
        and month_str = substr(first_published_at,1,7)
        and substr(first_published_at,1,10) between '2026-10-12' and '2026-10-18'
    UNION ALL
    SELECT '本月累计' period, business_group_name, big_category, skc FROM a
    WHERE PT>0 and is_online_adjust = 1 and month_str = '2026-10'
        and is_gift_cart = '否' and (channels regexp '独立站' or channels is null)
        and style_position_adjust = '正常目标'
        and month_str = substr(first_published_at,1,7)
        and substr(first_published_at,1,10) between '2026-10-01' and '2026-10-20'
    UNION ALL
    SELECT '上月同期' period, business_group_name, big_category, skc FROM a
    WHERE PT>0 and is_online_adjust = 1 and month_str = '2026-09'
        and is_gift_cart = '否' and (channels regexp '独立站' or channels is null)
        and style_position_adjust = '正常目标'
        and month_str = substr(first_published_at,1,7)
        and substr(first_published_at,1,10) between '2026-09-01' and '2026-09-20'
    UNION ALL
    SELECT '去年同期' period, business_group_name, big_category, skc FROM a
    WHERE PT>0 and is_online_adjust = 1 and month_str = '2025-10'
        and is_gift_cart = '否' and (channels regexp '独立站' or channels is null)
        and style_position_adjust = '正常目标'
        and month_str = substr(first_published_at,1,7)
        and substr(first_published_at,1,10) between '2025-10-01' and '2025-10-20'
)

SELECT
    period 周期
    ,NVL(count(distinct if(business_group_name = '成衣一部' and big_category = '成衣' ,skc,null)),0) 成衣一部
    ,NVL(count(distinct if(business_group_name = '成衣二部' and big_category = '成衣' ,skc,null)),0) 成衣二部
    ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and big_category = '成衣' ,skc,null)),0) 成衣
    ,NVL(count(distinct if(business_group_name = '泳衣产品部' ,skc,null)),0) 泳衣产品部
    ,NVL(count(distinct if(business_group_name = '泳衣买手部' ,skc,null)),0) 泳衣买手部
    ,NVL(count(distinct if((business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部') ,skc,null)),0) 泳衣
    ,NVL(count(distinct if(business_group_name = '内睡' ,skc,null)),0) 内睡
    ,NVL(count(distinct if(business_group_name = 'ACC' ,skc,null)),0) acc
    ,NVL(count(distinct if(business_group_name = '塑身衣项目部' ,skc,null)),0) 塑身衣项目部
    ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') ,skc,null)),0) 全品类
FROM b
WHERE period is not null
GROUP BY period
ORDER BY case period when '本周' then 1 when '上周' then 2 when '本月累计' then 3 when '上月同期' then 4 when '去年同期' then 5 end
LIMIT 20
;

