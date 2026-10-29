# -*- coding: utf-8 -*-
"""生成派生查询：各部门/周期 上新数（本周/上周/本月累计/上月同期/去年同期）。
a CTE 原样复用原始脚本1（S1_目标达成.csv.sql 前181行），仅替换最终聚合——不改动原始脚本。"""
import io, os

BASE = r"c:\Users\Cupshe\Desktop\test"
S1_SQL = os.path.join(BASE, r"out\ops_20261021\S1_目标达成.csv.sql")
OUT_SQL = os.path.join(BASE, r"out\ops_20261021\S1W_周度上新.csv.sql")

with io.open(S1_SQL, encoding="utf-8") as f:
    lines = f.read().splitlines()

# a CTE = 第1行到第181行（'）' 结束 CTE）
cte = "\n".join(lines[:181])
assert lines[180].strip() == ")", f"a CTE 结束行异常: {lines[180]!r}"

def period_block(name, month, d1, d2):
    return f"""    SELECT '{name}' period, business_group_name, big_category, skc FROM a
    WHERE PT>0 and is_online_adjust = 1 and month_str = '{month}'
        and is_gift_cart = '否' and (channels regexp '独立站' or channels is null)
        and style_position_adjust = '正常目标'
        and month_str = substr(first_published_at,1,7)
        and substr(first_published_at,1,10) between '{d1}' and '{d2}'"""

blocks = [
    period_block("本周", "2026-10", "2026-10-19", "2026-10-25"),
    period_block("上周", "2026-10", "2026-10-12", "2026-10-18"),
    period_block("本月累计", "2026-10", "2026-10-01", "2026-10-20"),
    period_block("上月同期", "2026-09", "2026-09-01", "2026-09-20"),
    period_block("去年同期", "2025-10", "2025-10-01", "2025-10-20"),
]

select_part = """
SELECT
    period 周期
    ,NVL(count(distinct if(business_group_name = '成衣一部' and big_category = '成衣' ,skc,null)),0) 成衣一部
    ,NVL(count(distinct if(business_group_name = '成衣二部' and big_category = '成衣' ,skc,null)),0) 成衣二部
    ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' ) and big_category = '成衣' ,skc,null)),0) 成衣
    ,NVL(count(distinct if(business_group_name = '泳衣产品部' ,skc,null)),0) 泳衣产品部
    ,NVL(count(distinct if(business_group_name = '泳衣买手部' ,skc,null)),0) 泳衣买手部
    ,NVL(count(distinct if((business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部') ,skc,null)),0) 泳衣
    ,NVL(count(distinct if(business_group_name = '内睡' ,skc,null)),0) 内睡
    ,NVL(count(distinct if(business_group_name = 'ACC' ,skc,null)),0) acc
    ,NVL(count(distinct if(business_group_name = '塑身衣项目部' ,skc,null)),0) 塑身衣项目部
    ,NVL(count(distinct if((business_group_name = '成衣一部' or business_group_name = '成衣二部' or business_group_name = '泳衣产品部' or business_group_name = '泳衣买手部' or business_group_name = '内睡' or business_group_name = 'ACC' or business_group_name = '塑身衣项目部') ,skc,null)),0) 全品类
FROM b
WHERE period is not null
GROUP BY period
ORDER BY case period when '本周' then 1 when '上周' then 2 when '本月累计' then 3 when '上月同期' then 4 when '去年同期' then 5 end
LIMIT 20
;
"""

agg = "\n,b as (\n" + "\n    UNION ALL\n".join(blocks) + "\n)\n" + select_part

with io.open(OUT_SQL, "w", encoding="utf-8") as f:
    f.write(cte + agg)
print("saved ->", OUT_SQL)
print("lines:", len((cte + agg).splitlines()))
