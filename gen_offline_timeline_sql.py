# -*- coding: utf-8 -*-
"""从 面料齐备26-27年.xlsx 生成 offline_timeline 导入 SQL"""
import pandas as pd

SRC = r"c:\Users\Cupshe\Desktop\面料齐备26-27年.xlsx"
OUT = r"c:\Users\Cupshe\Desktop\test\02_insert_offline_timeline.sql"

df = pd.read_excel(SRC)
for c in df.columns:
    df[c] = pd.to_datetime(df[c])
df = df.sort_values("date_key")
cols = ["date_key", "fabric_60_plan_date", "fabric_100_plan_date",
        "fabric_80_create_time", "fabric_100_create_time"]

def val(x):
    return "NULL" if pd.isna(x) else "'" + x.strftime("%Y-%m-%d") + "'"

lines = ["(" + ", ".join(val(r[c]) for c in cols) + ")" for _, r in df.iterrows()]

sql = (
    f"-- 脚本2：导入 offline_timeline（数据源：面料齐备26-27年.xlsx，共 {len(df)} 行，按 date_key 升序）\n"
    "INSERT INTO offline_timeline (date_key, fabric_60_plan_date, fabric_100_plan_date, "
    "fabric_80_create_time, fabric_100_create_time) VALUES\n"
    + ",\n".join(lines) + ";\n"
)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(sql)
print(f"已生成: {OUT}")
print(f"行数: {len(df)}, NULL 行数(fabric_80/100_create_time): {int(df.fabric_80_create_time.isna().sum())}")
