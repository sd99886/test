---诊断: 检查 detail CTE 三个分支的列数和列名
---分支1: DTC (T1 FULL JOIN T2)
SELECT 'DTC' as branch, 1 as col_pos, '渠道类型' as col_name, 'STRING' as col_type
UNION ALL SELECT 'DTC', 2, 'channel', 'STRING'
UNION ALL SELECT 'DTC', 3, 'month_str', 'STRING'
UNION ALL SELECT 'DTC', 4, 'skc', 'STRING'
UNION ALL SELECT 'DTC', 5, 'subsite_id', 'STRING'
UNION ALL SELECT 'DTC', 6, 'subsite_name', 'STRING'
UNION ALL SELECT 'DTC', 7, 'business_year_str', 'STRING'
UNION ALL SELECT 'DTC', 8, 'business_week_str', 'STRING'
UNION ALL SELECT 'DTC', 9, 'business_week_start_date', 'STRING'
UNION ALL SELECT 'DTC', 10, 'business_week_end_date', 'STRING'
UNION ALL SELECT 'DTC', 11, 'buy_time', 'STRING'
UNION ALL SELECT 'DTC', 12, 'category_group', 'STRING'
UNION ALL SELECT 'DTC', 13, 'item_refund_reason_level_one', 'STRING'
UNION ALL SELECT 'DTC', 14, 'item_refund_reason_level_two', 'STRING'
UNION ALL SELECT 'DTC', 15, 'refund_quantity', 'BIGINT'
UNION ALL SELECT 'DTC', 16, 'sale_count', 'BIGINT'

UNION ALL

---分支2: Amazon (T3.* + T4.sale_quantity)
SELECT 'Amazon', 1, '渠道类型', 'STRING'
UNION ALL SELECT 'Amazon', 2, 'channel', 'STRING'
UNION ALL SELECT 'Amazon', 3, 'month_str(T3)', 'STRING'
UNION ALL SELECT 'Amazon', 4, 'skc(T3)', 'STRING'
UNION ALL SELECT 'Amazon', 5, 'subsite_id(T3)', 'STRING'
UNION ALL SELECT 'Amazon', 6, 'subsite_name(T3)', 'STRING'
UNION ALL SELECT 'Amazon', 7, 'business_year_str', 'STRING'
UNION ALL SELECT 'Amazon', 8, 'business_week_str', 'STRING'
UNION ALL SELECT 'Amazon', 9, 'business_week_start_date', 'STRING'
UNION ALL SELECT 'Amazon', 10, 'business_week_end_date', 'STRING'
UNION ALL SELECT 'Amazon', 11, 'pay_date', 'STRING'
UNION ALL SELECT 'Amazon', 12, 'category_group', 'STRING'
UNION ALL SELECT 'Amazon', 13, 'cnfirst_reason', 'STRING'
UNION ALL SELECT 'Amazon', 14, 'cnsecond_reason', 'STRING'
UNION ALL SELECT 'Amazon', 15, 'refund_quantity', 'BIGINT'
UNION ALL SELECT 'Amazon', 16, 'sale_quantity(T4)', 'BIGINT'

UNION ALL

---分支3: 多渠道 (T5)
SELECT 'MultiChannel', 1, '渠道类型', 'STRING'
UNION ALL SELECT 'MultiChannel', 2, 'sale_channel', 'STRING'
UNION ALL SELECT 'MultiChannel', 3, 'month_str', 'STRING'
UNION ALL SELECT 'MultiChannel', 4, 'skc', 'STRING'
UNION ALL SELECT 'MultiChannel', 5, 'subsite_id', 'STRING'
UNION ALL SELECT 'MultiChannel', 6, 'subsite_name', 'STRING'
UNION ALL SELECT 'MultiChannel', 7, 'business_year_str', 'STRING'
UNION ALL SELECT 'MultiChannel', 8, 'business_week_str', 'STRING'
UNION ALL SELECT 'MultiChannel', 9, 'business_week_start_date', 'STRING'
UNION ALL SELECT 'MultiChannel', 10, 'business_week_end_date', 'STRING'
UNION ALL SELECT 'MultiChannel', 11, 'pay_time', 'STRING'
UNION ALL SELECT 'MultiChannel', 12, 'category', 'STRING'
UNION ALL SELECT 'MultiChannel', 13, 'return_reason', 'STRING'
UNION ALL SELECT 'MultiChannel', 14, 'null', 'STRING'
UNION ALL SELECT 'MultiChannel', 15, 'refund_quantity', 'BIGINT'
UNION ALL SELECT 'MultiChannel', 16, 'sale_quantity', 'BIGINT'
ORDER BY branch, col_pos
;
