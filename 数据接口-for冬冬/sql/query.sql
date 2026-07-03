-- 示例SQL：商品销售数据查询
-- 数分在此编写SQL，业务通过API调用

SELECT
    月,
    category,
    second_category,
    third_category,
    style_position_name,
    SUM(销量) as 总销量,
    SUM(CAST(销售额 AS DECIMAL(18,2))) as 总销售额,
    COUNT(DISTINCT skc) as skc数量
FROM your_table
WHERE 月 >= '2026-01'
GROUP BY 月, category, second_category, third_category, style_position_name
ORDER BY 月, 总销售额 DESC
