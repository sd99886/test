---脚本1: 指标平台多渠道总退件率逻辑 (target/macy)
WITH a as (
select substr(pay_time,1,7)month_str
        ,substr(a.pay_time,1,10)pay_time
        ,a.subsite_id
        ,a.subsite_name
        ,b.sale_channel
        -- ,skc
        ,first_category
        ,second_category
        ,third_category
        ,original_return_reason
        ,return_reason
        ,sum(sku_amount)sale_amount
        ,sum(quantity)sale_quantity
        ,sum(refund_shipped_amout+refund_unship_amout)refund_amount
        ,SUM(refund_shipped_quantity+refund_unship_quantity)refund_quantity
from cupshe_bigdata_ads.ads_fin_target_macys_return_data_df a
left join cupshe_bigdata_cdm.dim_pub_full_channel b on a.subsite_id=b.subsite_comm
where subsite_id not in('902','7600') AND substr(pay_time,1,7)>='2023' 
    and b.sale_channel !='Zalando'
---902是Cupshe-Walmart-US-web，7600是Cupshe-Zalando-ALL-web
group by substr(pay_time,1,7)
        ,substr(a.pay_time,1,10)
        ,a.subsite_id
        ,a.subsite_name
        ,b.sale_channel
        -- ,skc
        ,first_category
        ,second_category
        ,third_category
        ,original_return_reason
        ,return_reason
)
SELECT 
    month_str
    ,sum(sale_quantity) sale_quantity
    ,sum(refund_quantity) refund_quantity
from a
where  
month_str>='2026-01'
group by month_str
;
