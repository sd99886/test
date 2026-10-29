"""
分析 Datasets Fusion Excel 文件的数据结构
"""
import openpyxl
from collections import defaultdict

wb = openpyxl.load_workbook(r"C:\Users\Cupshe\Downloads\Datasets Fusion 2026-09-17 16-30-37.xlsx", read_only=True)
print(f"Sheet names: {wb.sheetnames}")

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    print(f"\n{'='*60}")
    print(f"Sheet: {sheet_name}")
    print(f"{'='*60}")
    
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        print("  (empty)")
        continue
    
    header = rows[0]
    print(f"  列数: {len(header)}")
    print(f"  数据行数: {len(rows) - 1}")
    print(f"  字段名: {list(header)}")
    print()
    
    # 打印前10行数据
    print(f"  前10行数据:")
    for i, row in enumerate(rows[1:11], 1):
        print(f"    Row {i}: {list(row)}")
    
    # 分析每列的数据分布（对前几列）
    print(f"\n  各列数据类型及样例:")
    for col_idx in range(len(header)):
        values = [row[col_idx] for row in rows[1:] if row[col_idx] is not None]
        null_count = sum(1 for row in rows[1:] if row[col_idx] is None)
        if values:
            sample = values[:3]
            print(f"    [{header[col_idx]}] 非空:{len(values)}, 空:{null_count}, 类型:{type(values[0]).__name__}, 样例:{sample}")
        else:
            print(f"    [{header[col_idx]}] 全部为空")

wb.close()
