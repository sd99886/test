# -*- coding: utf-8 -*-
"""独立全量校验：02_insert_offline_timeline.sql vs 面料齐备26-27年.xlsx
校验维度：
1) 行数一致
2) 每行字段数 = 5
3) date_key 集合一致（无多、无少、无重复）
4) 按 date_key 索引逐字段比对（与行序无关）
5) 全集多重集合比对（含 NULL）
6) NULL 数量统计一致
7) 随机抽样 8 行打印人工复核
"""
import re
import random
import pandas as pd

SRC = r"c:\Users\Cupshe\Desktop\面料齐备26-27年.xlsx"
SQL = r"c:\Users\Cupshe\Desktop\test\02_insert_offline_timeline.sql"
COLS = ["date_key", "fabric_60_plan_date", "fabric_100_plan_date",
        "fabric_80_create_time", "fabric_100_create_time"]

# ---- 读取 Excel ----
df = pd.read_excel(SRC)
for c in COLS:
    df[c] = pd.to_datetime(df[c])
assert df.date_key.duplicated().sum() == 0, "Excel 存在重复 date_key"
excel_map = {str(r.date_key.date()): tuple(str(r[c].date()) if pd.notna(r[c]) else None for c in COLS)
             for _, r in df.iterrows()}

# ---- 解析 SQL ----
text = open(SQL, encoding="utf-8").read()
header = text.split("VALUES", 1)[0]
print("[SQL header cols]", " ".join(header.split("(")[1].split(")")[0].split()))
print("字段列表与 COLS 一致:", [x.strip() for x in header.split("(", 1)[1].split(")")[0].split(",")] == COLS)

body = text.split("VALUES", 1)[1].strip().rstrip(";")
tuples = re.findall(r"\((.*?)\)", body, flags=re.S)
print(f"[1] 行数: SQL={len(tuples)}  Excel={len(df)}  ->", "PASS" if len(tuples) == len(df) else "FAIL")

def parse_tuple(raw):
    parts = [p.strip() for p in raw.split(",")]
    assert len(parts) == 5, f"字段数不为5: {raw}"
    out = []
    for p in parts:
        if p == "NULL":
            out.append(None)
        else:
            assert re.fullmatch(r"'\d{4}-\d{2}-\d{2}'", p), f"日期格式异常: {p!r}"
            out.append(p.strip("'"))
    return tuple(out)

sql_map = {}
dup_in_sql = []
bad_col_count = 0
for raw in tuples:
    try:
        t = parse_tuple(raw)
    except AssertionError as e:
        bad_col_count += 1
        print("  !", e)
        continue
    if t[0] in sql_map:
        dup_in_sql.append(t[0])
    sql_map[t[0]] = t

print(f"[2] 每行5字段且日期格式合法: {'PASS' if bad_col_count == 0 else 'FAIL (' + str(bad_col_count) + ' 行异常)'}")
print(f"[3] SQL 内 date_key 重复: {len(dup_in_sql)} ->", "PASS" if not dup_in_sql else "FAIL")

only_excel = set(excel_map) - set(sql_map)
only_sql = set(sql_map) - set(excel_map)
print(f"[4] date_key 集合: 仅在Excel={len(only_excel)} 仅在SQL={len(only_sql)} ->",
      "PASS" if not only_excel and not only_sql else "FAIL")
if only_excel:
    print("    缺失于SQL:", sorted(str(d) for d in only_excel)[:20])
if only_sql:
    print("    SQL多出:", sorted(str(d) for d in only_sql)[:20])

# [5] 逐 date_key 逐字段比对
diffs = []
for k in sorted(set(excel_map) & set(sql_map)):
    a, b = excel_map[k], sql_map[k]
    if a != b:
        for j, col in enumerate(COLS):
            if a[j] != b[j]:
                diffs.append((str(k), col, a[j], b[j]))
print(f"[5] 逐字段比对不一致数: {len(diffs)} ->", "PASS" if not diffs else "FAIL")
for d in diffs[:20]:
    print("    差异:", d)

# [6] 多重集合比对（顺序无关，含 NULL）
set_a = sorted(excel_map.values())
set_b = sorted(sql_map.values())
print(f"[6] 全行多重集合完全相等: {'PASS' if set_a == set_b else 'FAIL'}")

null_excel = {c: int(df[c].isna().sum()) for c in COLS[1:]}
null_sql = {c: sum(1 for t in sql_map.values() if t[COLS.index(c)] is None) for c in COLS[1:]}
print(f"[7] NULL 统计一致: {'PASS' if null_excel == null_sql else 'FAIL'}", null_excel, null_sql)

# [8] 随机抽样复核
random.seed(20261027)
print("[8] 随机抽样 8 行（date_key | Excel -> SQL）:")
for k in random.sample(sorted(excel_map), 8):
    ok = "OK " if excel_map[k] == sql_map[k] else "NG "
    print(f"    {ok} {k} | {excel_map[k]} -> {sql_map[k]}")

print("\n日期范围 Excel:", min(excel_map), "~", max(excel_map))
print("日期范围 SQL  :", min(sql_map), "~", max(sql_map))
print("总计:", "全部一致 [OK]" if (len(tuples) == len(df) and not diffs and set_a == set_b
                        and not only_excel and not only_sql and null_excel == null_sql) else "存在差异 [FAIL]")
