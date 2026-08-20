-- SQL 查询脚本（Notebook 版本）
-- 在此文件中编写你的 SQL 语句
-- 支持多行 SQL，使用分号分隔多条语句

with skc_with_combination_commonly_used_dim AS -- dws_prod_skc_with_combination_label_di
(
    SELECT  -- 组合品维表和单品维表部分逻辑有新旧之分，但分维度GMV受单品转组合品or组合品转单品的情况影响，因此采用优先组合品维度，组合品skc缺少采用单品维度做递补
        b.skc
        ,b.cp
        ,b.spu
        ,time_line_type timeline类型
        ,big_category 大类别
        ,first_category 一级品类
        ,second_category 二级品类
        ,third_category 三级品类
        ,business_group_name 业务部门
        ,group_name 组别
        ,首复色
        ,designer_name 设计师名
        ,image_src 图片链接
        ,sample_oss_url 样衣图片链接
        ,频道_tag
        ,scene_tag 原始场景tag
        ,fixed_scene_tag 场景tag
        ,user_tag 人群画像tag
        ,color1_tag 颜色1
        ,color2_tag 颜色2
        ,color3_tag 颜色3
        ,channels 渠道
        ,popular_type 畅滞销类型
        ,first_published_at 首次上架时间
        ,风格tag
        ,图案tag
        ,纯色印花tag
    FROM 
    (
        select  -- 存在组合品转单品or单品转组合品的情形，此时，最新pt的组合品or单品维度表，就会确实skc,因此需要分开取维后UNION
            skc
            ,time_line_type 
            ,big_category
            ,first_category
            ,second_category
            ,third_category
            ,business_group_name
            ,group_name
            ,case  
                when first_color = 1 then '首色'
                when first_color = 0 then '复色'
            end as 首复色
            ,designer_name
            ,image_src
            ,sample_oss_url
            ,case 
                when tab_tag = 'Tab-Vacation' or  tab_tag = 'Tab-Everyday|Tab-Vacation' or tab_tag is null then  'Tab-Vacation' 
                else tab_tag
            end as 频道_tag
            ,scene_tag
            ,fixed_scene_tag
            ,user_tag
            ,color1_tag
            ,color2_tag
            ,color3_tag
            ,channels
            ,popular_type
            ,first_published_at
            ,concat_ws('|',SORT_ARRAY(split(style_tag,"\\|"))) 风格tag
            ,concat_ws('|',SORT_ARRAY(split(pattern_tag,"\\|"))) 图案tag
            ,concat_ws('|',SORT_ARRAY(split(solid_print_tag,"\\|"))) 纯色印花tag
        FROM    cupshe_bigdata_cdm.dws_prod_skc_label_di
        WHERE 
            pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_label_di')
            and skc not in ( -- 存在单品skc在两个维度表有不同状态，优先取组合品的skc，缺少再用单品递补
                SELECT 
                    skc
                FROM cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di 
                where
                    pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
            )
        UNION
        SELECT 
            skc
            ,time_line_type
            ,big_category
            ,first_category
            ,second_category
            ,third_category
            ,business_group_name
            ,group_name
            ,case  
                when first_color = 1 then '首色'
                when first_color = 0 then '复色'
            end as 首复色
            ,designer_name
            ,image_src
            ,sample_oss_url
            ,case 
                when tab_tag = 'Tab-Vacation' or  tab_tag = 'Tab-Everyday|Tab-Vacation' or tab_tag is null then  'Tab-Vacation' 
                else tab_tag
            end as 频道_tag
            ,scene_tag
            ,fixed_scene_tag
            ,user_tag
            ,color1_tag
            ,color2_tag
            ,color3_tag
            ,channels
            ,popular_type
            ,first_published_at
            ,concat_ws('|',SORT_ARRAY(split(style_tag,"\\|"))) 风格tag
            ,concat_ws('|',SORT_ARRAY(split(pattern_tag,"\\|"))) 图案tag
            ,concat_ws('|',SORT_ARRAY(split(solid_print_tag,"\\|"))) 纯色印花tag
        FROM cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di 
        where
            pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
    ) a
    left JOIN 
    (
        select
            distinct 
                skc
                ,cp
                ,spu
        from cupshe_bigdata_cdm.dim_pub_sku_category
    ) b 
    on a.skc = b.skc

)
-- 退件率=（退款件数+退券件数）/ 销量
SELECT 
    -- substr(date_str,1,7) 销售月
    rid.cp
    ,rid.skc
    ,一级品类
    ,二级品类
    ,三级品类
    ,图片链接
    ,首次上架时间
    ,trim(if(sku_first_reason_name = '',null,sku_first_reason_name)) sku级别一级原因
    ,trim(if(sku_second_reason_name = '',null,sku_second_reason_name)) sku级别二级原因
    ,trim(if(sku_third_reason_name = '',null,sku_third_reason_name)) sku级别三级原因
    ,NVL(sum(sale_quantity),0) 销量
    ,NVL(sum(sale_amount_usd),0) GMV
    ,NVL(sum(refund_quantity),0) 退款数量
    ,NVL(sum(refund_amount_usd),0) 退款金额
    ,NVL(sum(refund_coupon_usd),0) 退券金额
    ,NVL(SUM(refund_amount_usd+0.8*refund_coupon_usd),0) 退款退券金额
    ,if(NVL(sum(sale_quantity),0)=0,0,NVL(sum(refund_quantity),0)/NVL(sum(sale_quantity),0)) 退件率
    ,IF(NVL(sum(sale_amount_usd),0)=0,0,NVL(sum(refund_amount_usd),0)/NVL(sum(sale_amount_usd),0)) 退款率
    ,IF(NVL(sum(sale_amount_usd),0)=0,0,NVL(sum(refund_coupon_usd),0)/NVL(sum(sale_amount_usd),0)) 退券率
    ,IF(NVL(sum(sale_amount_usd),0)=0,0,NVL(SUM(refund_amount_usd+0.8*refund_coupon_usd),0)/NVL(sum(sale_amount_usd),0)) 退货率
from cupshe_bigdata_ads.ads_scm_cp_refund_info_df rid
left join skc_with_combination_commonly_used_dim cud on cud.skc = rid.skc
WHERE 
    rid.channel = '独立站' 
    AND  date_str >= '2026-01-01' and date_str <= '2026-06-30'
    and cud.业务部门 = 'ACC'
    and substr(首次上架时间,1,7) >= '2026-01'  and substr(首次上架时间,1,7) <= '2026-06'
    -- and rid.skc in ('CAB01B6C001CC','CAB01A6B001MG','CAB01A6C001MG','CAB01B5M001CC','CAB01B6A002GG','CAB01B6C002CC','CAB02A6A001KK','CAB01A6B002AA','CAB01A6A001AJ','CAB01B6A001GG','CAB01B5M002CC')
group by 
        -- substr(date_str,1,7)
        rid.cp
        ,rid.skc
        ,首次上架时间
        ,sku级别一级原因
        ,sku级别二级原因
        ,sku级别三级原因
        ,一级品类
        ,二级品类
        ,三级品类
        ,图片链接
;





