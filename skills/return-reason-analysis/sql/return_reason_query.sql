-- ============================================================
-- 退货原因分析取数模板
-- 数据范围：channel = '独立站'（固定条件，不可修改）
-- 占位符说明：
--   {{date_start}}      销售开始日期，如 '2026-08-01'
--   {{date_end}}        销售结束日期，如 '2026-10-31'
--   {{launch_start}}    上新开始月份，如 '2026-01'
--   {{launch_end}}      上新结束月份，如 '2026-06'
--   {{skc_filter}}      SKC 过滤，如 rid.skc = 'CAB03C6H001JK'
--                       或 rid.skc IN ('A','B','C')
--   {{biz_dept_filter}} 业务部门过滤，如 cud.业务部门 = 'ACC'
--   {{big_cat_filter}}  大类别过滤，如 cud.大类别 = '鞋品'
--
-- 规则：如用户未指定某条件，则删除对应行（不加该过滤）
-- ============================================================

WITH skc_with_combination_commonly_used_dim AS
(
    SELECT
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
        SELECT
            skc
            ,time_line_type
            ,big_category
            ,first_category
            ,second_category
            ,third_category
            ,business_group_name
            ,group_name
            ,CASE WHEN first_color = 1 THEN '首色'
                  WHEN first_color = 0 THEN '复色'
             END AS 首复色
            ,designer_name
            ,image_src
            ,sample_oss_url
            ,CASE
                WHEN tab_tag = 'Tab-Vacation' OR tab_tag = 'Tab-Everyday|Tab-Vacation' OR tab_tag IS NULL
                    THEN 'Tab-Vacation'
                ELSE tab_tag
             END AS 频道_tag
            ,scene_tag
            ,fixed_scene_tag
            ,user_tag
            ,color1_tag
            ,color2_tag
            ,color3_tag
            ,channels
            ,popular_type
            ,first_published_at
            ,concat_ws('|', SORT_ARRAY(split(style_tag, "\\|"))) 风格tag
            ,concat_ws('|', SORT_ARRAY(split(pattern_tag, "\\|"))) 图案tag
            ,concat_ws('|', SORT_ARRAY(split(solid_print_tag, "\\|"))) 纯色印花tag
        FROM cupshe_bigdata_cdm.dws_prod_skc_label_di
        WHERE pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_label_di')
          AND skc NOT IN (
              SELECT skc
              FROM cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di
              WHERE pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
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
            ,CASE WHEN first_color = 1 THEN '首色'
                  WHEN first_color = 0 THEN '复色'
             END AS 首复色
            ,designer_name
            ,image_src
            ,sample_oss_url
            ,CASE
                WHEN tab_tag = 'Tab-Vacation' OR tab_tag = 'Tab-Everyday|Tab-Vacation' OR tab_tag IS NULL
                    THEN 'Tab-Vacation'
                ELSE tab_tag
             END AS 频道_tag
            ,scene_tag
            ,fixed_scene_tag
            ,user_tag
            ,color1_tag
            ,color2_tag
            ,color3_tag
            ,channels
            ,popular_type
            ,first_published_at
            ,concat_ws('|', SORT_ARRAY(split(style_tag, "\\|"))) 风格tag
            ,concat_ws('|', SORT_ARRAY(split(pattern_tag, "\\|"))) 图案tag
            ,concat_ws('|', SORT_ARRAY(split(solid_print_tag, "\\|"))) 纯色印花tag
        FROM cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di
        WHERE pt = MAX_PT('cupshe_bigdata_cdm.dws_prod_skc_with_combination_label_di')
    ) a
    LEFT JOIN
    (
        SELECT DISTINCT skc, cp, spu
        FROM cupshe_bigdata_cdm.dim_pub_sku_category
    ) b
    ON a.skc = b.skc
)

-- 退件率 =（退款件数 + 退券件数）/ 销量
SELECT
    substr(date_str, 1, 7) 销售月
    ,rid.cp
    ,rid.skc
    ,一级品类
    ,二级品类
    ,三级品类
    ,图片链接
    ,首次上架时间
    ,trim(if(sku_first_reason_name = '', null, sku_first_reason_name))  sku级别一级原因
    ,trim(if(sku_second_reason_name = '', null, sku_second_reason_name)) sku级别二级原因
    ,trim(if(sku_third_reason_name = '', null, sku_third_reason_name))  sku级别三级原因
    ,NVL(sum(sale_quantity), 0)        销量
    ,NVL(sum(sale_amount_usd), 0)      GMV
    ,NVL(sum(refund_quantity), 0)      退款数量
    ,NVL(sum(refund_amount_usd), 0)    退款金额
    ,NVL(sum(refund_coupon_usd), 0)    退券金额
    ,NVL(SUM(refund_amount_usd + 0.8 * refund_coupon_usd), 0) 退款总额
    ,if(NVL(sum(sale_quantity), 0) = 0, 0,
        NVL(sum(refund_quantity), 0) / NVL(sum(sale_quantity), 0)) 退件率
    ,IF(NVL(sum(sale_amount_usd), 0) = 0, 0,
        NVL(sum(refund_amount_usd), 0) / NVL(sum(sale_amount_usd), 0)) 退款率
    ,IF(NVL(sum(sale_amount_usd), 0) = 0, 0,
        NVL(sum(refund_coupon_usd), 0) / NVL(sum(sale_amount_usd), 0)) 退券率
    ,IF(NVL(sum(sale_amount_usd), 0) = 0, 0,
        NVL(SUM(refund_amount_usd + 0.8 * refund_coupon_usd), 0) / NVL(sum(sale_amount_usd), 0)) 退货率
FROM cupshe_bigdata_ads.ads_scm_cp_refund_info_df rid
LEFT JOIN skc_with_combination_commonly_used_dim cud ON cud.skc = rid.skc
WHERE
    rid.channel = '独立站'
    -- ====== 以下为可选筛选条件，根据用户确认结果决定是否保留 ======
    -- AND date_str >= '{{date_start}}' AND date_str <= '{{date_end}}'
    -- AND substr(首次上架时间, 1, 7) >= '{{launch_start}}' AND substr(首次上架时间, 1, 7) <= '{{launch_end}}'
    -- AND {{skc_filter}}
    -- AND {{biz_dept_filter}}
    -- AND {{big_cat_filter}}
GROUP BY
    substr(date_str, 1, 7)
    ,rid.cp
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
