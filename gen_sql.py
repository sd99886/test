# -*- coding: utf-8 -*-
"""生成六站点首次上架指标 SQL"""
sites = ['US','CA','UK','DE','FR','AU']
site_names = {'US':'美国','CA':'加拿大','UK':'英国','DE':'德国','FR':'法国','AU':'澳洲'}
windows = [3,5,7,15,30,45,60]
metrics = [
    ('is_online_adjust','在架天数'),
    ('sale_quantity','销量'),
    ('sale_amount_usd','销额'),
    ('collection_view_cnt','列表页浏览PV'),
    ('collection_view_user','列表页浏览UV'),
    ('pdp_view_cnt','详情页浏览PV'),
    ('pdp_view_user','详情页浏览UV'),
    ('collection_click_cnt','列表页点击PV'),
    ('collection_click_user','列表页点击UV'),
    ('pdp_add_to_cart_user','详情页加购UV'),
    ('collection_add_to_cart_user','列表页加购UV'),
]

L = []
L.append('-- 六站点首次上架后多窗口指标')
L.append('-- 站点：US/CA/UK/DE/FR/AU  窗口：3/5/7/15/30/45/60天')
L.append('-- 指标：在架天数、销量、销额、流量(列表页浏览PV/UV、详情页浏览PV/UV、列表页点击PV/UV、详情页加购UV、列表页加购UV)')
L.append('SELECT ')
L.append('    a.* ')
L.append('    ,c.combination_skc ')
L.append("    ,CASE when a.skc is not null and c.combination_skc is null then a.skc")
L.append("          when a.skc is not null and c.combination_skc is not null then c.combination_skc")
L.append("    end as skc_adjust")
L.append("    ,CASE when a.skc is not null and a.skc like '120%' then '组合品'")
L.append("          when a.skc is not null and c.combination_skc is null then '单品'")
L.append("          when a.skc is not null and c.combination_skc is not null then '组合品子品'")
L.append("          else '其他'")
L.append("    end as skc_status")
L.append("    ,d.* except(skc)")

# 新品判断
for s in sites:
    sn = site_names[s]
    fp = f'first_published_at_{s}'
    L.append(f"    ,CASE when substr(date_str,1,7)=substr(d.{fp},1,7) and nvl(channels,'独立站')='独立站' then '{sn}站当月新品'")
    L.append(f"          when substr(date_str,1,7)<substr(d.{fp},1,7) and nvl(channels,'独立站')='独立站' then '{sn}站未上架'")
    L.append(f"          when substr(date_str,1,7)>substr(d.{fp},1,7) and nvl(channels,'独立站')='独立站' then '{sn}站当月老品'")
    L.append(f"    end 是否{sn}站当月新品")

# 指标列
for s in sites:
    sn = site_names[s]
    fp = f'first_published_at_{s}'
    L.append(f'    -- ==================== {s} {sn}站 ====================')
    for w in windows:
        for col, label in metrics:
            L.append(f"    ,sum(if(a.country='{s}' and a.date_str between date_add({fp},1) and date_add({fp},{w}),a.{col},null)) over(partition by skc) {s}_首次上架{w}天{label}")

# FROM 子查询
L.append('')
L.append('FROM')
L.append('(')
L.append('SELECT')

a_cols = [
    'date_str','skc','country','is_online_adjust',
    'collection_view_cnt','collection_view_user','pdp_view_cnt','pdp_view_user',
    'collection_click_cnt','collection_click_user','pdp_add_to_cart_user','collection_add_to_cart_user',
    'sale_quantity','sale_amount_usd','return_quantity','refund_couponv_usd',
    'refund_amount_usd','total_refund_amount_usd','first_order_price','qty_first_receving',
    'spu','cp','time_line_type','big_category','first_category','second_category','third_category',
    'business_group_name','group_name','first_color','designer_name','image_src','sample_oss_url',
    'tab_tag','original_fixed_scene_tag','fixed_scene_tag','user_tag','style_tag','pattern_tag',
    'solid_print_tag','color1_tag','color2_tag','color3_tag','channels','popular_type',
    'design_details','fabric_construction','material_composition','collar_style','waistline_position',
    'coat_length','sleeve_length','sleeve_type','skirt_length','rise','silhouette',
    'style_position','product_layering','target_customer_group','theme_name',
    'tentative_release_date','expected_release_date','ingredient_content_cn',
    'plm_attributes_sets','plm_product_properties','model_code','model_name','model_type',
    'mail','phone','location','price','attiude','is_cooperate',
    'pdp_add_to_cart_cnt','collection_add_to_cart_cnt','checkout_cnt','checkout_user',
    'checkout_quantity','add_to_cart_cnt','add_to_cart_user','order_num','order_user',
    'order_quantity','order_amount_us','refund_store_credit_usd','series',
    'business_channels','business_level_name','nation_line_name','is_extend','extend_cp',
    'biz_model','special_design','special_material_type','complex_models','is_selected',
    'plan_id','design_structure','size_model','independent_station_selection_rating',
    'independent_station_bysize_qt_rating','product_rating','operational_rating',
    'commodity_rating','star_tag',
]

for i, col in enumerate(a_cols):
    prefix = '    ' if i == 0 else '    ,'
    L.append(f'{prefix}a.{col}')

decode_cols = [
    ("decode(a.product_ops_role_planning,1L,'TRUHERO',2L,'PREHERO')", 'product_ops_role_planning'),
    ("decode(a.product_ops_role_product,1L,'TRUHERO',2L,'PREHERO')", 'product_ops_role_product'),
    ("decode(a.product_ops_role_operation,1L,'TRUHERO',2L,'PREHERO')", 'product_ops_role_operation'),
    ("decode(a.product_ops_role_summary,1L,'TRUHERO',2L,'PREHERO')", 'product_ops_role_summary'),
]
for expr, alias in decode_cols:
    L.append(f'    ,{expr} {alias}')
L.append('    ,pt')
L.append('FROM cupshe_bigdata_ads.ads_prod_country_product_info_di a')
L.append("WHERE pt >= '20250101'")
L.append("    AND country IN ('US','CA','UK','DE','FR','AU')")
L.append("    AND big_category = '泳衣'")
L.append('    AND is_online_adjust = 1')
L.append(') a')

# c表
L.append('LEFT JOIN')
L.append('(')
L.append('    SELECT DISTINCT skc, combination_skc')
L.append('    FROM cupshe_bigdata_cdm.dwd_prod_product_variant_combination_df')
L.append(') c ON a.skc = c.skc')

# d表
L.append('LEFT JOIN')
L.append('(')
L.append('    SELECT a.skc')
for s in sites:
    L.append(f"        ,min(if(b.sale_site = '{s}',a.min_published_at,null)) first_published_at_{s}")
    L.append(f"        ,min(if(b.sale_site = '{s}',first_price*ex_rate,null)) first_price_{s}")
L.append("    FROM cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di a")
L.append('    JOIN (')
L.append("        SELECT subsite_comm, subsite_comm_name, sale_site")
L.append("        FROM cupshe_bigdata_cdm.dim_pub_full_channel")
L.append("        WHERE sale_site IN ('US','CA','UK','DE','FR','AU')")
L.append("    ) b ON b.subsite_comm = a.shop_id")
L.append("    LEFT JOIN cupshe_bigdata_cdm.dim_pub_fiscal_site_rate c")
L.append("        ON a.shop_id = c.shop_id AND a.min_published_at = c.date_str")
L.append("    WHERE pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_shopify_product_history_di')")
L.append("        AND nvl(a.first_published_at,'') <> ''")
L.append("        AND a.second_category = '泳衣'")
L.append("        AND SUBSTR(skc,1,2) != '13'")
L.append("        AND SUBSTR(skc,1,3) NOT IN ('321')")
L.append('    GROUP BY a.skc')
L.append(') d ON a.skc = d.skc')
L.append(';')

out_path = r'c:\Users\Cupshe\Desktop\test\六站点首次上架指标.sql'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))
print(f'Done, {len(L)} lines written to {out_path}')
