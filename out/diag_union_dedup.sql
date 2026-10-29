---诊断: 只跑 T5 + detail 的 MultiChannel 分支，看 UNION 是否导致数据丢失
WITH T5 as (
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
---对比1: T5 直接聚合
select 'T5_direct' as source
    ,month_str
    ,sum(sale_quantity) as sale_qty
    ,sum(refund_quantity) as refund_qty
    ,count(*) as row_cnt
from T5
where month_str = '2026-07'
group by month_str

UNION ALL

---对比2: T5 经过 detail CTE 的 MultiChannel 分支 (模拟 UNION 去重)
select 'via_detail' as source
    ,month_str
    ,sum(sale_quantity) as sale_qty
    ,sum(refund_quantity) as refund_qty
    ,count(*) as row_cnt
from (
    SELECT 
    '多渠道' 渠道类型,
    T5.sale_channel, 
    T5.month_str,
    T5.skc, 
    cast(T5.subsite_id as string) subsite_id, 
    T5.subsite_name, 
    T5.business_year_str, 
    T5.business_week_str, 
    T5.business_week_start_date,
    T5.business_week_end_date, 
    T5.pay_time,
    T5.category,  
    T5.return_reason, 
    null as reason2,
    T5.refund_quantity, 
    T5.sale_quantity
    from T5
) detail
where 渠道类型 = '多渠道' and month_str = '2026-07'
group by month_str
;
