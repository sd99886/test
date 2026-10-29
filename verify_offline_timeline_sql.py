# -*- coding: utf-8 -*-
"""回读校验：解析生成的 INSERT SQL，与源 Excel 逐行比对"""
import re
import pandas as pd

SRC = r"c:\Users\Cupshe\Desktop\面料齐备26-27年.xlsx"
SQL = r"c:\Users\Cupshe\Desktop\test\02_insert_offline_timeline.sql"

df = pd.read_excel(SRC)
for c in df.columns:
    df[c] = pd.to_datetime(df[c])
df = df.sort_values("date_key").reset_index(drop=True)

text = open(SQL, encoding="utf-8").read()
values_part = text.split("VALUES\n", 1)[1].rstrip().rstrip(";")
rows = re.findall(r"\(([^)]*)\)", values_part)
assert len(rows) == len(df), f"行数不一致: SQL={len(rows)} Excel={len(df)}"

def parse(cell):
    cell = cell.strip()
    return pd.NaT if cell == "NULL" else pd.Timestamp(cell.strip("'"))

mismatch = 0
for i, raw in enumerate(rows):
    cells = [parse(x) for x in raw.split(",", 4)]
    for j, col in enumerate(df.columns):
        a, b = df.at[i, col], cells[j]
        if pd.isna(a) and pd.isna(b):
            continue
        if a != b:
            mismatch += 1
            print(f"不一致 行{i} {col}: Excel={a} SQL={b}")

print(f"SQL 行数: {len(rows)}, 逐行逐列比对完成, 不一致: {mismatch}")
print("首行:", rows[0])
print("含create_time示例:", next(r for r in rows if "NULL" not in r))
print("末行:", rows[-1])
