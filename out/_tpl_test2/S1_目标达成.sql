-- [模板] 占位符由 render_sql.py 按 --start/--end 自动填充（占位符均带 SQL 引号）：
--   'START'/'END'=分析窗口；'PM_*'=环比期（回拨1个月）；'PY_*'=同比期（回拨1年）；
--   'MONTH'/'PM_MONTH'/'PY_MONTH'=月度口径（YYYY-MM）；'W_CUR_*'=END所在自然周（周一~周日）；'W_PREV_*'=上一周
-- 原始脚本产自 2026-10-01~10-20 窗口，历史演进注释保留原样。

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
FROM    my_project.ads_prod_skc_product_info_mi a
left JOIN 
(
    SELECT  DISTINCT skc
            ,combination_skc
    FROM    cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df
) c on a.skc = c.skc
WHERE 
    PT>0 and is_online_adjust = 1 and big_category != '赠品'
)
SELECT 
    nvl(shiji.idx,mubiao.idx) idx
    ,nvl(shiji.月份,mubiao.`month`) 月份
    ,nvl(shiji.style_position_adjust,mubiao.目标类型) 目标类型
    ,nvl(成衣一部目标,0) 成衣一部目标
    ,nvl(成衣一部实际,0)  成衣一部实际
    ,if(nvl(成衣一部目标,0)=0,0,nvl(成衣一部实际,0)/nvl(成衣一部目标,0)) 成衣一部达成率
    ,nvl(成衣二部目标,0) 成衣二部目标
    ,nvl(成衣二部实际,0)  成衣二部实际
    ,if(nvl(成衣二部目标,0)=0,0,nvl(成衣二部实际,0)/nvl(成衣二部目标,0)) 成衣二部达成率
    ,nvl(品牌设计部目标,0) 品牌设计部目标
    ,nvl(品牌设计部实际,0)  品牌设计部实际
    ,if(nvl(品牌设计部目标,0)=0,0,nvl(品牌设计部实际,0)/nvl(品牌设计部目标,0)) 品牌设计部达成率
    ,nvl(新渠道产品部目标,0) 新渠道产品部目标
    ,nvl(新渠道产品部实际,0)  新渠道产品部实际
    ,if(nvl(新渠道产品部目标,0)=0,0,nvl(新渠道产品部实际,0)/nvl(新渠道产品部目标,0)) 新渠道产品部达成率
    ,nvl(成衣目标,0) 成衣目标
    ,nvl(成衣实际,0)  成衣实际
    ,if(nvl(成衣目标,0)=0,0,nvl(成衣实际,0)/nvl(成衣目标,0)) 成衣达成率
    ,nvl(泳衣产品部目标,0) 泳衣产品部目标
    ,nvl(泳衣产品部实际,0)  泳衣产品部实际
    ,if(nvl(泳衣产品部目标,0)=0,0,nvl(泳衣产品部实际,0)/nvl(泳衣产品部目标,0)) 泳衣产品部达成率
    ,nvl(泳衣买手部目标,0) 泳衣买手部目标
    ,nvl(泳衣买手部实际,0)  泳衣买手部实际
    ,if(nvl(泳衣买手部目标,0)=0,0,nvl(泳衣买手部实际,0)/nvl(泳衣买手部目标,0)) 泳衣买手部达成率
    ,nvl(泳衣目标,0) 泳衣目标
    ,nvl(泳衣实际,0)  泳衣实际
    ,if(nvl(泳衣目标,0)=0,0,nvl(泳衣实际,0)/nvl(泳衣目标,0)) 泳衣达成率
    ,nvl(内睡目标,0) 内睡目标
    ,nvl(内睡实际,0)  内睡实际
    ,if(nvl(内睡目标,0)=0,0,nvl(内睡实际,0)/nvl(内睡目标,0)) 内睡达成率
    ,nvl(ACC目标,0) ACC目标
    ,nvl(ACC实际,0)  ACC实际
    ,if(nvl(ACC目标,0)=0,0,nvl(ACC实际,0)/nvl(ACC目标,0)) ACC达成率
    ,nvl(塑身衣项目部目标,0) 塑身衣项目部目标
    ,nvl(塑身衣项目部实际,0)  塑身衣项目部实际
    ,if(nvl(塑身衣项目部目标,0)=0,0,nvl(塑身衣项目部实际,0)/nvl(塑身衣项目部目标,0)) 塑身衣项目部达成率
    ,nvl(全品类目标,0) 全品类目标
    ,nvl(全品类实际,0)  全品类实际
   ,if(nvl(全品类目标,0)=0,0,nvl(全品类实际,0)/nvl(全品类目标,0)) 全品类达成率
FROM 
( -- 塑身衣是从成衣和内睡拆出来的，无库存测试也是从各个部门数据里拆出来的，法国线是包含在各个部门数据里的
    -- 改动21，增加成衣限定，把品牌设计部和新渠道产品部从成衣拆开，全品类则不拆出来 20260106
    SELECT 
        'GMV' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' ,sale_amount_usd,null)),0)成衣一部实际
        ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' and big_category = '成衣' ,sale_amount_usd,null)),0)成衣一部实际
        -- ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否',sale_amount_usd,null)),0) 成衣二部实际
        ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否' and big_category = '成衣',sale_amount_usd,null)),0) 成衣二部实际
        ,NVL(sum(if(business_group_name = '品牌设计部' and is_gift_cart = '否',sale_amount_usd,null)),0) 品牌设计部实际 -- 不区分成衣泳衣等等
        ,NVL(sum(if(business_group_name = '新渠道产品部' and is_gift_cart = '否',sale_amount_usd,null)),0) 新渠道产品部实际
        -- ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否',sale_amount_usd,null)),0) 成衣实际 
        ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and big_category = '成衣' and is_gift_cart = '否',sale_amount_usd,null)),0) 成衣实际 -- 只计算成衣中的成衣一部和成衣二部
        ,NVL(sum(if(business_group_name = '泳衣产品部' and is_gift_cart = '否',sale_amount_usd,null)),0) 泳衣产品部实际
        ,NVL(sum(if(business_group_name = '泳衣买手部' and is_gift_cart = '否',sale_amount_usd,null)),0) 泳衣买手部实际
        ,NVL(sum(if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否',sale_amount_usd,null)),0)泳衣实际
        ,NVL(sum(if(business_group_name = '内睡' and is_gift_cart = '否',sale_amount_usd,null)),0)内睡实际
        ,NVL(sum(if(business_group_name = 'ACC' and is_gift_cart = '否',sale_amount_usd,null)),0) ACC实际
        -- 20251127新增塑身衣项目部
        ,NVL(sum(if(business_group_name = '塑身衣项目部' and is_gift_cart = '否',sale_amount_usd,null)),0) 塑身衣项目部实际
        ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否',sale_amount_usd,null)),0) 全品类实际
    FROM   a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '新品GMV' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,sale_amount_usd,null)),0)成衣一部实际
        ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',sale_amount_usd,null)),0)成衣一部实际
        -- ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 成衣二部实际
        ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',sale_amount_usd,null)),0) 成衣二部实际
        ,NVL(sum(if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 品牌设计部实际
        ,NVL(sum(if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 新渠道产品部实际
        -- ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 成衣实际 
        ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',sale_amount_usd,null)),0) 成衣实际 
        ,NVL(sum(if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 泳衣产品部实际
        ,NVL(sum(if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 泳衣买手部实际
        ,NVL(sum(if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)泳衣实际
        ,NVL(sum(if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)内睡实际
        ,NVL(sum(if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) ACC实际
        --
        ,NVL(sum(if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 塑身衣项目部实际
        ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION
    SELECT 
        '上新数' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)成衣一部实际
        ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣' ,skc,null)),0)成衣一部实际
        -- ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 品牌设计部实际
        ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 新渠道产品部实际
        -- ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 成衣实际 
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0) 成衣实际 
        ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 泳衣产品部实际
        ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 泳衣买手部实际
        ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)泳衣实际
        ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)内睡实际
        ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) ACC实际
        --
        ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 塑身衣项目部实际
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT -- 大爆款数为畅滞销标签为大爆款，统一修改逻辑，爆款数修改为爆款总数，指爆款，大爆款，超爆款
        '大爆款数' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款'),skc,null)),0)成衣一部实际
        ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款') and big_category = '成衣',skc,null)),0)成衣一部实际
        -- ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款'),skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款') and big_category = '成衣',skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) 品牌设计部实际
        ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) 新渠道产品部实际
        -- ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款'),skc,null)),0) 成衣实际 
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款') and big_category = '成衣',skc,null)),0) 成衣实际 
        ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) 泳衣产品部实际
        ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) 泳衣买手部实际
        ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) 泳衣实际
        ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)内睡实际
        ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) ACC实际
        --
        ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) 塑身衣项目部实际
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '大爆款率' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣一部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣一部实际
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 品牌设计部实际
        ,IF(NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 新渠道产品部实际
        -- ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣实际 
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣实际 
        ,IF(NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣产品部实际
        ,IF(NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣买手部实际
        ,IF(NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣实际
        ,IF(NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 内睡实际
        ,IF(NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) ACC实际
        --
         ,IF(NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 塑身衣项目部实际
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT -- 此处指爆款总数
        '爆款数' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)成衣一部实际
        ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款') and big_category = '成衣',skc,null)),0)成衣一部实际
        -- ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款') and big_category = '成衣',skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 品牌设计部实际
        ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 新渠道产品部实际
        -- ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 成衣实际 
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款') and big_category = '成衣',skc,null)),0) 成衣实际 
        ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 泳衣产品部实际
        ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 泳衣买手部实际
        ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 泳衣实际
        ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)内睡实际
        ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) ACC实际
        --
        ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 塑身衣项目部实际
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '爆款率' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣一部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣' ,skc,null)),0)) 成衣一部实际
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 品牌设计部实际
        ,IF(NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 新渠道产品部实际
        -- ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣实际 
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣实际
        ,IF(NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣产品部实际
        ,IF(NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣买手部实际
        ,IF(NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣实际
        ,IF(NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 内睡实际
        ,IF(NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) ACC实际
        --
         ,IF(NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 塑身衣项目部实际
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 全品类实际
    FROM   a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '超爆款数' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('超爆款'),skc,null)),0)成衣一部实际
        ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('超爆款') and big_category = '成衣',skc,null)),0)成衣一部实际
        -- ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款') and big_category = '成衣',skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 品牌设计部实际
        ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 新渠道产品部实际
        -- ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 成衣实际 
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款') and big_category = '成衣',skc,null)),0) 成衣实际 
        ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 泳衣产品部实际
        ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 泳衣买手部实际
        ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 泳衣实际
        ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)内睡实际
        ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) ACC实际
        --
        ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 塑身衣项目部实际
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '超爆款率' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣一部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣' ,skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('超爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣' ,skc,null)),0)) 成衣一部实际
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 品牌设计部实际
        ,IF(NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 新渠道产品部实际
        -- ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣实际
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣实际  
        ,IF(NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣产品部实际
        ,IF(NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣买手部实际
        ,IF(NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣实际
        ,IF(NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 内睡实际
        ,IF(NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) ACC实际
        -- 
        ,IF(NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 塑身衣项目部实际
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC'  or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('超爆款'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '成功数' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)成衣一部实际
        ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款','畅销') and big_category = '成衣',skc,null)),0)成衣一部实际
        -- ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销') and big_category = '成衣',skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 品牌设计部实际
        ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 新渠道产品部实际
        -- ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 成衣实际 
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销') and big_category = '成衣',skc,null)),0) 成衣实际 
        ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 泳衣产品部实际
        ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 泳衣买手部实际
        ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 泳衣实际
        ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)内睡实际
        ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) ACC实际
        -- 
        ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 塑身衣项目部实际
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '成功率' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣一部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null)  and popular_type in ('大爆款','超爆款','爆款','畅销') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣一部实际
        -- ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣二部实际
        ,IF(NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 品牌设计部实际
        ,IF(NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 新渠道产品部实际
        -- ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
        --     ,0
        --     ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 成衣实际 
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销') and big_category = '成衣',skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣实际 
        ,IF(NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣产品部实际
        ,IF(NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣买手部实际
        ,IF(NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 泳衣实际
        ,IF(NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 内睡实际
        ,IF(NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) ACC实际
        -- 
        ,IF(NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 塑身衣项目部实际
        ,IF(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)=0
            ,0
            ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and popular_type in ('大爆款','超爆款','爆款','畅销'),skc,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),skc,null)),0)) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '新品款均成本' idx -- 上新skc采购价/skc上新数
        ,month_str 月份
        ,style_position_adjust
        -- ,if(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
        --     ,0
        --     ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣一部实际
        ,if(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣一部实际
        -- ,if(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
        --     ,0
        --     ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣二部实际
        ,if(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣二部实际
        ,if(NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 品牌设计部实际
        ,if(NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 新渠道产品部实际
        -- ,if(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
        --     ,0
        --     ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣实际
         ,if(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0) = 0
            ,0
            ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',first_order_price,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣实际
        ,if(NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 泳衣产品部实际
        ,if(NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 泳衣买手部实际
        ,if(NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 泳衣实际
        ,if(NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 内睡实际
        ,if(NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) ACC实际
        -- 
        ,if(NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 塑身衣项目部实际      
        ,if(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC'  or business_group_name = '塑身衣项目部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),first_order_price,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC'  or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION 
    SELECT 
        '新品款效' idx -- 上新skcGMV/skc上新数
        ,month_str 月份
        ,style_position_adjust
        -- ,if(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
        --     ,0
        --     ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣一部实际
         ,if(NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣' ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣一部实际
        -- ,if(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
        --     ,0
        --     ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣二部实际
        ,if(NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣' ,skc,null)),0)) 成衣二部实际
        ,if(NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 品牌设计部实际
        ,if(NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 新渠道产品部实际
        -- ,if(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
        --     ,0
        --     ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 成衣实际
        ,if(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0) = 0
            ,0
            ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',sale_amount_usd,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and big_category = '成衣',skc,null)),0)) 成衣实际
        ,if(NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 泳衣产品部实际
        ,if(NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 泳衣买手部实际
        ,if(NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 泳衣实际
        ,if(NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 内睡实际
        ,if(NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) ACC实际
        --
        ,if(NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 塑身衣项目部实际
        ,if(NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0) = 0
            ,0
            ,NVL(sum(if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null),sale_amount_usd,null)),0)/NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) ,skc,null)),0)) 全品类实际
   from  a
        WHERE 
            PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
    UNION -- 20250924增加法国线上新数（包含于总上新数）
    SELECT 
        '法国线上新数' idx
        ,month_str 月份
        ,style_position_adjust
        -- ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国' ,skc,null)),0)成衣一部实际
        ,NVL(count(distinct if(business_group_name = '成衣一部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国' and big_category = '成衣' ,skc,null)),0)成衣一部实际
        -- ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '成衣二部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国' and big_category = '成衣',skc,null)),0) 成衣二部实际
        ,NVL(count(distinct if(business_group_name = '品牌设计部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 品牌设计部实际
        ,NVL(count(distinct if(business_group_name = '新渠道产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 新渠道产品部实际
        -- ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 成衣实际 
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国' and big_category = '成衣',skc,null)),0) 成衣实际 
        ,NVL(count(distinct if(business_group_name = '泳衣产品部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 泳衣产品部实际
        ,NVL(count(distinct if(business_group_name = '泳衣买手部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 泳衣买手部实际
        ,NVL(count(distinct if((business_group_name = '泳衣产品部'or business_group_name = '泳衣买手部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0)泳衣实际
        ,NVL(count(distinct if(business_group_name = '内睡' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)) ,0)内睡实际
        ,NVL(count(distinct if(business_group_name = 'ACC' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) ACC实际
        --
        ,NVL(count(distinct if(business_group_name = '塑身衣项目部' and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 塑身衣项目部实际
        ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '品牌设计部' or business_group_name = '新渠道产品部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') and is_gift_cart = '否' and month_str = substr(first_published_at,1,7) and (channels regexp '独立站' or channels is null) and nation_line_name = '法国',skc,null)),0) 全品类实际
    FROM    a
    WHERE 
        PT>0 and is_online_adjust = 1
    group by 
        idx
        ,month_str
        ,style_position_adjust
) shiji
full JOIN 
(
    -- 改动19，增加目标类型，以此筛选无库存测试和正常目标
    SELECT  
        idx
        ,month
        ,'正常目标' 目标类型
        ,all_category  全品类目标
        ,swimming_design 泳衣产品部目标
        ,swimming_buyer 泳衣买手部目标
        ,swimming 泳衣目标
        ,garment1 成衣一部目标
        ,garment2 成衣二部目标
        ,garment 成衣目标
        ,lingerie 内睡目标
        ,acc acc目标
        ,garment_brand_design 品牌设计部目标
        ,garment_new_channel 新渠道产品部目标
        ,shapewear 塑身衣项目部目标
    FROM  CUPSHE_BIGDATA_ADS_dev.prookrdata_new2
    union
    SELECT  
        idx
        ,month
        ,'无库存测试款' 目标类型
        ,all_category  全品类目标
        ,swimming_design 泳衣产品部目标
        ,swimming_buyer 泳衣买手部目标
        ,swimming 泳衣目标
        ,garment1 成衣一部目标
        ,garment2 成衣二部目标
        ,garment 成衣目标
        ,lingerie 内睡目标
        ,acc acc目标
        ,garment_brand_design 品牌设计部目标
        ,garment_new_channel 新渠道产品部目标
        ,shapewear 塑身衣项目部目标
    FROM   CUPSHE_BIGDATA_ADS_dev.prookrdata_new2_no_inventory_test
) mubiao
on shiji.idx = mubiao.idx and shiji.月份 = mubiao.`month` and shiji.style_position_adjust = mubiao.目标类型
where nvl(shiji.月份,mubiao.`month`) not like '%H%' and nvl(shiji.月份,mubiao.`month`) not like '%年%'
 and nvl(shiji.月份,mubiao.`month`) = '2026-10' 
 and  nvl(shiji.style_position_adjust,mubiao.目标类型) != '无库存测试款'
;

