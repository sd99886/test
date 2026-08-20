
-- V5优化测试方向：用factory_code也可以；factory_code+confirm_color，批色时不具体到颜色可以用供应商代码
-- 一个供应商名称可能会对应多个供应商代码,因此不要用供应商名称
-- 20260515 V6:增加新的物料类别、用料类别、是否现货、是否特殊面料、限制物料状态
with mianliaoV4 AS 
(
    SELECT -- 面料脚本v4 主料，取面布用量第1的布
        a.*
        -- ,ROW_NUMBER() over (partition by cp order by `面料用量（总）` desc) rk
        -- ,ROW_NUMBER() over (partition by cp order by case when 布料位置 = '面布' or 布料位置 is null then `面料用量（总）` else 0 end desc) rk
    FROM 
    (
        SELECT 
            pps.cp
            ,dim.skc
            ,pps.first_category_name 一级品类
            ,pps.second_category_name 二级品类
            ,pps.third_category_name 三级品类
            ,Case when pps.state=0 then '进行中'
                When  pps.state=1 then '完成'
                When pps.state=2 then '已取消'
                When  pps.state=3 then '待定'
            End as 单据状态
            ,m2.material_detail_no 物料编码
            ,m.material_type_name 物料名称
            ,m.factory_code 供应商代码
            ,m.material_type_no `物料编码（旧）`
            ,m.supplier_name 供应商
            ,m.component 成分
            ,m.material_type 物料类别
            ,m.color 颜色
            ,m.weight 克重
            ,m.door_width 幅宽
            ,case when m.fabric_category=1 then '面布'
                when  m.fabric_category=2 then '里布' 
            end as 布料位置
            ,decode(m.fabric_type,1L,'面布',2L,'里布') 面料类型
            ,(m.quantity+m.loss_num) `单件面料用量（总）`
            ,m.quantity `单件面料用量（损耗后）`
            ,m.loss_num 单件损耗用量
            ,m.utilization_rate 唛架使用率
            ,m2.zonal_shrinkage 纬向缩水率
            ,m2.shrinkage 经向缩水率
            -- ,case 
            --     when m.special_fabrics=1 then '是' 
            --     when m.special_fabrics=0 then '否' 
            -- end 是否特殊面料
            ,m.unit_price `计划价格（元/米）`
            ,m.unit_price*(m.quantity+m.loss_num) 单件面料采购金额
            ,m.confirm_color 确认色号
            ,pps.site 渠道
            -- ,m2.special_fabrics 是否特殊面料
            ,m2.is_spot_goods 是否现货
            ,m2.is_spot_goods_sub 是否现货_色号
            ,m2.largo_cargo_cycle 大货周期
            ,m2. is_special_material 是否特殊辅料
            ,m2.specification 规格
            ,m2.unit 价格单位
            ,m2.fabric_library 面料库
            -- ,m3.`素色/印花`
            ,pdm.物料一级类别
            ,pdm.物料二级类别
            ,pdm.物料三级类别
            ,pdm.物料四级类别
            ,pdm.新物料一级类别 运营一级类别
            ,pdm.新物料二级类别 运营二级类别
            ,pdm.新物料三级类别 运营三级类别
            ,pdm.新物料四级类别 运营四级类别
            ,pdm.材料类别
            ,pdm.面料供应商全称
            ,pdm.面料供应商简称
            -- 调整字段
            ,pdm.物料名称 物料名称_物料库

            -- ,ppsm.* -- 工艺单信息
            
            -- pps表
            ,pps.id process_sheets_id
            ,pps.style_position_id
            
        FROM ( -- 核价表信息优先保证
            select * 
            from cupshe_bigdata_ods.odsp_scm_proc_pricing 
            where pt = MAX_PT('cupshe_bigdata_ods.odsp_scm_proc_pricing') 
                -- and cp = 'CPPIS970174'
                
        ) PP
        LEFT JOIN 
        (
            select 
                *
                ,ROW_NUMBER() over (partition by pricing_id order by quantity desc ) rk
            from cupshe_bigdata_ods.odsp_scm_proc_pricing_material 
            where pt =MAX_PT('cupshe_bigdata_ods.odsp_scm_proc_pricing_material' ) 
                and is_del = 0  
                -- and pricing_id = '24487'
                -- and pricing_id = '180499'
                -- and material_scene = 1
        ) m on pp.id = m.pricing_id and pp.is_del = 0
        inner join 
        (
            select *
            from cupshe_bigdata_ods.odsp_scm_proc_process_sheets 
            WHERE 
                pt = MAX_PT('cupshe_bigdata_ods.odsp_scm_proc_process_sheets')

        ) pps on pp.cp = pps.cp
        LEFT JOIN 
        (
            select 
                cp
                ,max(skc) skc
            from cupshe_bigdata_cdm.dim_pub_sku_category
            where 
                cp is not null  
                -- and cp = 'CPEA40004' -- 一个cp有两个skc
            group by cp
        ) dim on  pps.cp = dim.cp
        left JOIN 
        (
            select
                material_type_no,material_detail_no,zonal_shrinkage,shrinkage,confirm_color,factory_code
                ,max(decode(special_fabrics,1L,'是',0L,'否')) special_fabrics -- 是否特殊面料
                ,max(decode(is_spot_goods,1L,'现货',0L,'定制')) is_spot_goods
                ,max(decode(is_spot_goods_sub,1L,'现货',0L,'定制')) is_spot_goods_sub

                ,max(large_cargo_cycle) largo_cargo_cycle
                ,max(decode(is_special_material,1L,'是',0L,'否')) is_special_material -- 是否特殊辅料
                ,max(specification) specification -- 规格
                ,max(unit) unit -- 计量单位
                ,max(decode(fabric_library,1L,'A库',2L,'B库',3L,'C库',4L,'红库',5L,'黑库',6L,'其他')) fabric_library


            from cupshe_bigdata_ods.ods_scm_proc_doc_material_price_df
            WHERE 
                is_del = 0
                --and parent_id is null -- 这个不能限制
                and (state = 0 or state is null)
            group by material_type_no,material_detail_no,zonal_shrinkage,shrinkage,confirm_color,factory_code
        ) m2  on m.factory_code = m2.factory_code  and nvl(m2.confirm_color,'') = nvl(m.confirm_color,'')
        left JOIN 
        (
            select
                distinct
                cp
                ,factory_code
                -- ,CASE 
                --     when fabric_type=1 then '素色' 
                --     when fabric_type=2 then '印花' 
                -- end as `素色/印花`
                ,confirm_color
            from cupshe_bigdata_ods.ods_scm_proc_process_bulk_material_df
            WHERE 
                is_del = 0
        ) m3 on m3.cp = pps.cp and m3.factory_code = m.factory_code and nvl(m3.confirm_color,'') = nvl(m.confirm_color,'')
        left JOIN 
        (
            select
                check_no
                ,material_type_no,material_detail_no,
                first_category_name 物料一级类别,
                second_category_name 物料二级类别,
                third_category_name 物料三级类别,
                four_category_name 物料四级类别,
                material_type_name 物料名称,
                new_first_category_name 新物料一级类别,
                new_second_category_name 新物料二级类别,
                new_third_category_name 新物料三级类别,
                new_four_category_name  新物料四级类别,
                material_type 材料类别,
                pds1.supplier_name 面料供应商全称,
                pds2.supplier_alias 面料供应商简称
            from cupshe_bigdata_ods.ods_scm_proc_doc_material_df pdm
            left join cupshe_bigdata_ods.odsp_scm_proc_doc_supplier pds1 on pds1.id = pdm.supplier_id and pds1.is_del = 0 AND  pds1.pt = MAX_PT('cupshe_bigdata_ods.odsp_scm_proc_doc_supplier')
            left join cupshe_bigdata_ods.ods_scm_proc_doc_supplier_hf  pds2 on pds2.id = pdm.supplier_id and pds2.is_del = 0
            WHERE 
                pdm.is_del = 0
                and (state = 0 or state is null)
        ) pdm on pdm.material_detail_no=m2.material_detail_no
         left join 
        ( -- 20260105更新 -- 此表为工艺单面料信息proc_process_sheets_material
            SELECT 
                -- material_detail_no -- 用不了              
                factory_code,confirm_color
                ,process_sheets_id -- 这张表的process_sheets_id不能用有缺失
                ,technology
                ,panton
                ,component
                ,weave
                ,color
                ,weight
                ,specification
                ,unit
                ,unit_price -- 和m表的unit_price：6000+数据不一致
                -- ,unit_use_num -- 用不了
                ,lining_color -- 有数,但只有500条
                ,material_url -- 用不了
                ,yarn_count
                ,needle_num
                ,door_width
                ,supplier_name --和m表的supplier_name：7条数据不一致
                ,img_url
            from cupshe_bigdata_ods.ods_scm_proc_process_sheets_material_df -- 这张表的属性信息相对较全 -- supplier_name 对应的是supplier_id 不是factory_code
            where
                pt = max_pt('cupshe_bigdata_ods.ods_scm_proc_process_sheets_material_df')
                and is_del = 0
        ) ppsm on ppsm.factory_code = m2.factory_code and nvl(m2.confirm_color,'') = nvl(ppsm.confirm_color,'') 
            and pps.id = ppsm.process_sheets_id -- 研发工艺单的面料数对比核价表存在缺失，因此导致用此表的process_sheets_id字段会导致后续数据缺失
        where
            pps.is_del = 0
            and m.is_del = 0
            -- and m.material_scene = 1 -- 主料
            and m.material_scene in (2,3)

            and pp.status<>2 -- 取主料这里条件为<>2，即包含核价中数据
    ) a
    -- qualify rk = 1
)
SELECT 
    -- *
    pp.cp
    ,decode(ppse.goods_major_category,1L,'自研泳衣',2L,'买手泳衣',3L,'ACC',4L,'内衣',5L,'睡衣',6L,'成衣') 商品大类
    ,pp.审核时间
    ,pp.采购单订单总数量
    
    -- ,pc.dict_desc 款式定位 -- 维度用公用数据集
    ,m.* except(cp,style_position_id)
    ,NVL(pp.采购单订单总数量,0)*nvl(m.`单件面料用量（损耗后）`,0) `总面料用量（损耗后）`
    ,NVL(pp.采购单订单总数量,0)*nvl(m.单件损耗用量,0) 总单件损耗用量
    ,NVL(pp.采购单订单总数量,0)*nvl(m.`单件面料用量（总）`,0) 总用量
    ,NVL(pp.采购单订单总数量,0)*nvl(m.单件面料采购金额,0) 总采购金额
    
-- from mianliaoV4
from (select cp, substr(pp.submit_time,1,10) 审核时间,sum(qty_expected_all) 采购单订单总数量 from cupshe_bigdata_cdm.dwd_scm_plm_purchase_orders_sku_detail_df pp where state = 5 and substr(pp.submit_time,1,10) >= '2023-01-01' group by cp,substr(pp.submit_time,1,10) ) pp
join mianliaoV4 m on m.cp = pp.cp and m.供应商代码 is not null  -- 未走入核价环节的CP及其面料信息查不到
-- left join cupshe_bigdata_ods.odsp_scm_proc_process_sheets pps on m.process_sheets_id = pps.id  and pps.pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_plm_proc_dict_di')
-- left join cupshe_bigdata_cdm.dwd_prod_plm_proc_dict_di pc on m.style_position_id = dict_code and dict_type = 45 and pc.pt = MAX_PT('cupshe_bigdata_cdm.dwd_prod_plm_proc_dict_di')
left join cupshe_bigdata_ods.ods_proc_process_sheets_extra_df ppse on ppse.process_sheets_id = m.process_sheets_id  and ppse.pt = MAX_PT('cupshe_bigdata_ods.ods_proc_process_sheets_extra_df')
where 
    pp.cp is not null 
    AND decode(ppse.goods_major_category,1L,'自研泳衣',2L,'买手泳衣',3L,'ACC',4L,'内衣',5L,'睡衣',6L,'成衣')  != '自研泳衣'
    -- and pp.cp = 'CPPIS970174'
    ;



