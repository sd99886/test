---各业务线退件率指标分拆
WITH T1 AS 
(
    SELECT  t1.month_str
            ,t1.skc 
            ,t1.subsite_id
            ,t1.subsite_name
            ,t1.business_year_str
            ,t1.business_week_str
            ,t1.business_week_start_date
            ,t1.business_week_end_date
            ,t1.buy_time
            ,t1.category_group
            ,t1.item_refund_reason_level_one
            ,t1.item_refund_reason_level_two
            ,SUM(refund_quantity) refund_quantity
    FROM    (
                SELECT  SUBSTR(buy_time,1,7) month_str
                        ,a.subsite_id
                        ,a.subsite_name
                        ,b.business_year_str
                        ,b.business_week_str
                        ,b.business_week_start_date
                        ,b.business_week_end_date
                        ,substr(a.buy_time,1,10)buy_time
                        ,skc
                        ,case when second_category='泳衣' then '泳衣' else '成衣' end  as category_group
                        ,trim(tolower(item_refund_reason_level_one))item_refund_reason_level_one
                        ,trim(tolower(item_refund_reason_level_two))item_refund_reason_level_two
                        ,SUM(refund_quantity) AS refund_quantity
                FROM    cupshe_bigdata_ads.ads_ops_salesforce_trd_refund_report_df a
                LEFT JOIN cupshe_bigdata_CDM.dim_pub_mdm_nature_week b on substr(a.buy_time,1,10)=b.date_str
                WHERE   SUBSTR(buy_time,1,7) >= '2023-01' 
                    and subsite_name like 'Cupshe-独立站-US-%'
                AND     skc IS NOT NULL
                GROUP BY SUBSTR(buy_time,1,7) 
                        ,a.subsite_id
                        ,a.subsite_name
                        ,b.business_year_str
                        ,b.business_week_str
                        ,b.business_week_start_date
                        ,b.business_week_end_date
                        ,substr(a.buy_time,1,10)
                        ,skc
                         ,case when second_category='泳衣' then '泳衣' else '成衣' end 
                         ,trim(tolower(item_refund_reason_level_one))
                         ,trim(tolower(item_refund_reason_level_two))
            ) t1
    LEFT JOIN   (
                    SELECT  DISTINCT t1.skc
                            ,CASE   WHEN t1.second_category = '泳衣'
                                        AND t1.style_type = '1' THEN '泳衣买手款'
                                    when t1.second_category = '泳衣'
                                        AND t1.style_type = '0' THEN '泳衣设计款'
                                    ELSE '成衣'
                            END AS style_type
                    FROM    (
                                SELECT  DISTINCT skc
                                        ,second_category
                                        ,style_type
                                FROM    cupshe_bigdata_cdm.dim_pub_sku_category
                                WHERE   skc NOT LIKE '12000%'
                            ) t1
                    LEFT JOIN cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df t2
                    ON      t1.skc = t2.skc
                ) t2
    ON      t1.skc = t2.skc
    group by t1.month_str
            ,t1.skc 
            ,t1.subsite_id
            ,t1.subsite_name
            ,t1.business_year_str
            ,t1.business_week_str
            ,t1.business_week_start_date
            ,t1.business_week_end_date
            ,t1.buy_time
            ,t1.category_group
            ,t1.item_refund_reason_level_one
            ,t1.item_refund_reason_level_two
),

T2 as(
    SELECT  SUBSTR(t1.buy_time,1,7) month_str
            ,t1.skc
            ,t1.subsite_id
            ,t1.subsite_name
            ,t1.created_order_time
            ,b.business_year_str
            ,b.business_week_str
            ,b.business_week_start_date
            ,b.business_week_end_date
            ,case when t1.second_category='泳衣' then '泳衣' else '成衣' end as category_group
            ,SUM(t1.sale_count) sale_count
    FROM    cupshe_bigdata_ads.ads_ops_order_sku_detail_df t1
    LEFT JOIN cupshe_bigdata_CDM.dim_pub_mdm_nature_week b on t1.created_order_time=b.date_str
    LEFT JOIN   (
                    SELECT  DISTINCT t1.skc
                            ,CASE   WHEN t1.second_category = '泳衣'
                                        AND t1.style_type = '1' THEN '泳衣买手款'
                                    when t1.second_category = '泳衣'
                                        AND t1.style_type = '0' THEN '泳衣设计款'
                                    ELSE '成衣'
                            END AS style_type
                    FROM    (
                                SELECT  DISTINCT skc
                                        ,second_category
                                        ,style_type
                                FROM    cupshe_bigdata_cdm.dim_pub_sku_category
                                WHERE   skc NOT LIKE '12000%'
                            ) t1
                ) t2
    ON      t1.skc = t2.skc
    WHERE   buy_time >= '2023-01-01' 
        and subsite_name like 'Cupshe-独立站-US-%'
    GROUP BY SUBSTR(t1.buy_time,1,7) 
            ,t1.skc
            ,t1.subsite_id
            ,t1.subsite_name
            ,t1.created_order_time
            ,b.business_year_str
            ,b.business_week_str
            ,b.business_week_start_date
            ,b.business_week_end_date
            ,case when t1.second_category='泳衣' then '泳衣' else '成衣' end
),

T3 as (
select substr(a.pay_date,1,7) month_str
    ,a.skc
    ,cast(a.subsite_id as string) subsite_id
    ,a.subsite_name
    ,b.business_year_str
    ,b.business_week_str
    ,b.business_week_start_date
    ,b.business_week_end_date
    ,a.pay_date
    ,case when second_category_ch='泳衣' then '泳衣' else '成衣' end  as category_group
    ,cnfirst_reason
    ,cnsecond_reason
    ,sum(refund_quantity) refund_quantity
from cupshe_bigdata_ads.ads_fin_amazon_order_refund_reason_df a
LEFT JOIN cupshe_bigdata_CDM.dim_pub_mdm_nature_week b on substr(a.pay_date,1,10)=b.date_str
where a.pay_date is not null 
    and   subsite_name in ('Cupshe Apparel-Amazon-US-web','Cupshe-Amazon-US-web')
group by substr(a.pay_date,1,7)
    ,a.skc
    ,cast(a.subsite_id as string)
    ,a.subsite_name
    ,b.business_year_str
    ,b.business_week_str
    ,b.business_week_start_date
    ,b.business_week_end_date
    ,a.pay_date
    ,case when second_category_ch='泳衣' then '泳衣' else '成衣' end
    ,cnfirst_reason
    ,cnsecond_reason
),

T4 as(
select substr(a.pay_date,1,7) month_str
    ,a.skc   
    ,b.business_week_start_date
    ,b.business_week_end_date
    ,a.subsite_id
    ,a.subsite_name
    ,a.pay_date
    ,case when a.second_category_ch='泳衣' then '泳衣' else '成衣' end  as category_group
    ,sum(a.sale_quantity) sale_quantity
from (
    select pay_date
        ,skc
        ,cast(subsite_id as string) subsite_id
        ,subsite_name
        ,sku
        ,first_category_ch
        ,second_category_ch
        ,third_category_ch
        ,sum(avg(sale_quantity)) over(partition by pay_date,cast(subsite_id as string),sku) sale_quantity
    from    cupshe_bigdata_ads.ads_fin_amazon_order_refund_reason_df
    where pay_date is not null 
        and subsite_name in ('Cupshe Apparel-Amazon-US-web','Cupshe-Amazon-US-web')
    group by  pay_date
        ,skc
        ,cast(subsite_id as string) 
        ,subsite_name
        ,sku
        ,first_category_ch
        ,second_category_ch
        ,third_category_ch
    )a
left join cupshe_bigdata_CDM.dim_pub_mdm_nature_week b on substr(a.pay_date,1,10)=b.date_str
group by substr(a.pay_date,1,7)
    ,a.skc 
    ,a.pay_date
    ,b.business_week_start_date
    ,b.business_week_end_date
    ,a.subsite_id
    ,a.subsite_name
    ,case when a.second_category_ch='泳衣' then '泳衣' else '成衣' end
),

T5 as (
select substr(pay_time,1,7)month_str
        ,substr(a.pay_time,1,10)pay_time
        ,a.subsite_id
        ,a.subsite_name
        ,b.sale_channel
        ,skc
        ,first_category
        ,second_category
        ,third_category
        ,IF(second_category='泳衣','泳衣','成衣') category
        ,original_return_reason
        ,return_reason
        ,c.business_year_str
        ,c.business_week_str
        ,c.business_week_start_date
        ,c.business_week_end_date
        ,sum(sku_amount)sale_amount
        ,sum(quantity)sale_quantity
        ,sum(refund_shipped_amout+refund_unship_amout)refund_amount
        ,SUM(refund_shipped_quantity+refund_unship_quantity)refund_quantity
from cupshe_bigdata_ads.ads_fin_target_macys_return_data_df a
left join cupshe_bigdata_cdm.dim_pub_full_channel b on a.subsite_id=b.subsite_comm
LEFT JOIN cupshe_bigdata_CDM.dim_pub_mdm_nature_week c on substr(a.pay_time,1,10) = c.date_str
where subsite_id not in('902','7600') AND substr(pay_time,1,7)>='2023' 
    and b.sale_channel !='Zalando'
group by substr(pay_time,1,7)
        ,substr(a.pay_time,1,10)
        ,a.subsite_id
        ,a.subsite_name
        ,b.sale_channel
        ,skc
        ,first_category
        ,second_category
        ,third_category
        ,original_return_reason
        ,return_reason
        ,c.business_year_str
        ,c.business_week_str
        ,c.business_week_start_date
        ,c.business_week_end_date
        ,IF(second_category='泳衣','泳衣','成衣')
)
, detail as (

    SELECT  
    'DTC' 渠道类型,
    'DTC' channel,
    NVL(T1.month_str,T2.month_str) month_str,
    NVL(T1.skc,T2.skc) skc,
    NVL(T1.subsite_id,T2.subsite_id) subsite_id,
    NVL(T1.subsite_name,T2.subsite_name) subsite_name,
    NVL(T1.business_year_str,T2.business_year_str) business_year_str,
    NVL(T1.business_week_str,T2.business_week_str) business_week_str,
    NVL(T1.business_week_start_date,T2.business_week_start_date) business_week_start_date,
    NVL(T1.business_week_end_date,T2.business_week_end_date) business_week_end_date,
    NVL(T1.buy_time,T2.created_order_time) buy_time,
    NVL(T1.category_group,T2.category_group) category_group,
    T1.item_refund_reason_level_one,
    T1.item_refund_reason_level_two,

    T1.refund_quantity,
    T2.sale_count
    FROM    T1
    FULL JOIN   T2
    ON      T1.month_str = T2.month_str
    and     NVL(T1.skc,'') =NVL(T2.skc,'')
    and     T1.buy_time=  T2.created_order_time
    AND     T1.category_group = T2.category_group
    and     T1.subsite_id=T2.subsite_id

    UNION ALL

    select 
    '多渠道' 渠道类型
    ,'Amazon' channel
    , T3.*
    ,T4.sale_quantity
    from T3
    left join T4
    on T3.pay_date=T4.pay_date
    and NVL(T3.skc,'')= NVL(T4.skc,'')
    and T3.subsite_id=T4.subsite_id
    and T3.category_group=T4.category_group

    union ALL

    SELECT 
    '多渠道' 渠道类型,
    T5.sale_channel, 
    T5.month_str,
    T5.skc, 
    cast(T5.subsite_id as string) subsite_id , 
    T5.subsite_name, 
    T5.business_year_str, 
    T5.business_week_str, 
    T5.business_week_start_date,
    T5.business_week_end_date, 
    T5.pay_time,
    T5.category,  
    T5.return_reason, 
    null,
    T5.refund_quantity, 
    T5.sale_quantity
    from T5 
)
select 
month_str
,sum(sale_count)
,sum(refund_quantity)
from detail
where
    渠道类型 = '多渠道'
    and channel!='Amazon'
    and month_str >= '2026-01'
group by month_str
;
