# -*- coding: utf-8 -*-
"""往返一致性验证：render_sql.py 填充 2026-10-01~10-20 的结果，
去掉模板头 4 行注释后，应与 out/ops_20261021 的原始 SQL 逐行一致。"""
import io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="gbk", errors="replace")
NEW = r"c:\Users\Cupshe\Desktop\test\out\_tpl_test"
OLD = r"c:\Users\Cupshe\Desktop\test\out\ops_20261021"

pairs = [
    ("S1_目标达成.sql", "S1_目标达成.csv.sql"),
    ("S1W_周度上新.sql", "S1W_周度上新.csv.sql"),
    ("S2_品类拆解L2.sql", "S2_品类拆解L2.csv.sql"),
    ("S2_品类拆解L3.sql", "S2_品类拆解L3.csv.sql"),
    ("S2D_品类日趋势.sql", "S2D_品类日趋势.csv.sql"),
    ("S3_新老品业务部门.sql", "S3_新老品业务部门.csv.sql"),
]

ok = True
for new_f, old_f in pairs:
    a = io.open(os.path.join(NEW, new_f), encoding="utf-8").read().split("\n")
    b = io.open(os.path.join(OLD, old_f), encoding="utf-8").read().split("\n")
    a_body = a[4:]  # 去掉模板头 4 行注释
    if a_body == b:
        print(f"PASS {new_f}")
    else:
        ok = False
        print(f"FAIL {new_f}")
        import difflib
        for d in list(difflib.unified_diff(b, a_body, lineterm=""))[:12]:
            print("   ", d[:130])
print("ALL PASS" if ok else "HAS FAILURES")
