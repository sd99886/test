# -*- coding: utf-8 -*-
"""本次运行（2026-10-01 ~ 2026-10-20）的执行文件构建器。
原始脚本 S1/S2/S3 只读，绝不修改；仅生成参数代入副本与派生 L3 查询。
"""
import io, os, sys

BASE = r"c:\Users\Cupshe\Desktop\test"
DATA = os.path.join(BASE, r"monthly-ops-analysis\skills\monthly-ops-analysis\data")
RUN = os.path.join(BASE, r"generated_sql\run_20261021_20261020")
GEN = os.path.join(BASE, "generated_sql")

START, END, MONTH = "2026-10-01", "2026-10-20", "2026-10"
P_START = "${输入start_date，格式为yyyy-mm-dd}"
P_END = "${输入end_date，格式为yyyy-mm-dd}"
P_MONTH = "${输入月份格式为yyyy-mm-dd_占位}"  # placeholder not used

def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)

s1 = read(os.path.join(DATA, "skill数据集1-目标达成情况数据.txt"))
s2 = read(os.path.join(DATA, "skill数据集2-品类拆解数据.txt"))
s3 = read(os.path.join(DATA, "skill数据集3-新老品业务部门.txt"))

# ---- 1) S1 执行副本：月份参数代入 ----
assert s1.count("${输入月份格式为yyyy-mm}") == 1, "S1 月份占位符数量异常"
s1_exec = s1.replace("${输入月份格式为yyyy-mm}", MONTH)
write(os.path.join(RUN, "S1__exec.sql"), s1_exec)

# ---- 2) S2/S3 执行副本：日期参数代入 ----
for name, src in (("S2__exec.sql", s2), ("S3__exec.sql", s3)):
    assert src.count(P_START) == 2 and src.count(P_END) == 2, name + " 占位符数量异常: %d/%d" % (src.count(P_START), src.count(P_END))
    out = src.replace(P_START, START).replace(P_END, END)
    write(os.path.join(RUN, name), out)

# ---- 3) 派生 S2__l3__generated.sql：恢复 third_category 维度 ----
# 8 空格缩进处 4 个（agg SELECT / agg GROUP BY / pivoted SELECT / pivoted GROUP BY）
p8_old = ",second_category\n        -- ,third_category"
p8_new = ",second_category\n        ,third_category"
# 4 空格缩进处 2 个（最终 SELECT / ORDER BY）
p4_old = ",second_category\n    -- ,third_category"
p4_new = ",second_category\n    ,third_category"

n8 = s2.count(p8_old)
n4 = s2.count(p4_old)
assert (n8, n4) == (4, 2), "L3 补丁定位失败: n8=%d n4=%d" % (n8, n4)

header = (
    "-- 派生脚本（generated）：三级品类拆解\n"
    "-- 源脚本: skill数据集2-品类拆解数据.txt (S2, readonly)\n"
    "-- 用途: 报告 §4 表B（三级品类），基于 S2 恢复 third_category 维度，其余口径/过滤/指标与 S2 完全一致\n"
    "-- 参数: start_date / end_date（yyyy-mm-dd，写入 SQL 时带引号）\n"
    "-- 继承过滤: is_online_adjustment=1, pt>=20240101, style_position!='无库存测试款', big_category!='赠品'\n"
    "-- 创建日期: 2026-10-21\n"
    "-- status: candidate\n\n"
)
l3 = s2.replace(p8_old, p8_new).replace(p4_old, p4_new)
assert l3.count("third_category") == s2.count("third_category")  # 数量不减（注释去掉、维度启用）
write(os.path.join(GEN, "S2__l3__generated.sql"), header + l3)

# L3 执行副本
l3_exec = (header + l3).replace(P_START, START).replace(P_END, END)
assert "${输入" not in l3_exec
write(os.path.join(RUN, "S2__l3__exec.sql"), l3_exec)

# 自检：所有执行副本无残留占位符
for name in ("S1__exec.sql", "S2__exec.sql", "S3__exec.sql", "S2__l3__exec.sql"):
    p = os.path.join(RUN, name)
    body = read(p)
    assert "${输入" not in body, name + " 存在未替换占位符"
    print("built:", p, len(body), "chars")

# 自检：原始脚本未被改动（只读保护确认）
import hashlib
for name in ("skill数据集1-目标达成情况数据.txt", "skill数据集2-品类拆解数据.txt", "skill数据集3-新老品业务部门.txt"):
    print("md5", hashlib.md5(read(os.path.join(DATA, name)).encode("utf-8")).hexdigest(), name)
print("ALL OK")
