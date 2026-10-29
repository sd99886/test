# -*- coding: utf-8 -*-
"""面料时间表：将 start_date~end_date 区间展开为逐日明细表"""
import pandas as pd

SRC = r"c:\Users\Cupshe\Desktop\面料时间表.xlsx"
DST = r"c:\Users\Cupshe\Desktop\面料时间表_日明细.xlsx"

df = pd.read_excel(SRC)

# 确保日期列为 datetime
date_cols = ["start_date", "end_date", "fabric_80_create_time",
             "fabric_100_create_time", "fabric_60_plan_date", "fabric_100_plan_date"]
for c in date_cols:
    df[c] = pd.to_datetime(df[c])

rows = []
for _, r in df.iterrows():
    for d in pd.date_range(r["start_date"], r["end_date"], freq="D"):
        rows.append({
            "date_key": d,
            "fabric_80_create_time": r["fabric_80_create_time"],
            "fabric_100_create_time": r["fabric_100_create_time"],
            "fabric_60_plan_date": r["fabric_60_plan_date"],
            "fabric_100_plan_date": r["fabric_100_plan_date"],
        })

detail = pd.DataFrame(rows)
detail["date_key"] = detail["date_key"].dt.date
for c in date_cols[2:]:
    detail[c] = detail[c].dt.date

with pd.ExcelWriter(DST, engine="openpyxl") as writer:
    detail.to_excel(writer, index=False, sheet_name="日明细")
    ws = writer.sheets["日明细"]
    for col_cells in ws.columns:
        width = max(len(str(c.value)) for c in col_cells if c.value is not None)
        ws.column_dimensions[col_cells[0].column_letter].width = width + 4

print(f"源表区间数: {len(df)}, 展开明细行数: {len(detail)}")
print(f"日期范围: {detail['date_key'].min()} ~ {detail['date_key'].max()}")
print(f"已输出: {DST}")
