# -*- coding: utf-8 -*-
"""从 out/ops_20261021/*.sql 生成占位符模板 *.sql.tpl（供 skill 打包复用）。

替换规则（先长日期后短月份，避免部分替换）：
  '2026-10-19' -> {{W_CUR_START}}   本周周一（END 所在自然周）
  '2026-10-25' -> {{W_CUR_END}}     本周周日
  '2026-10-12' -> {{W_PREV_START}}  上周周一
  '2026-10-18' -> {{W_PREV_END}}    上周周日
  '2026-10-01' -> {{START}}         分析窗口起始日
  '2026-10-20' -> {{END}}           分析窗口截止日
  '2026-09-01' -> {{PM_START}}      环比期起始（窗口回拨 1 个月）
  '2026-09-20' -> {{PM_END}}        环比期截止
  '2025-10-01' -> {{PY_START}}      同比期起始（窗口回拨 1 年）
  '2025-10-20' -> {{PY_END}}        同比期截止
  '2026-10'    -> {{MONTH}}         本月（YYYY-MM，月度口径）
  '2026-09'    -> {{PM_MONTH}}      环比月
  '2025-10'    -> {{PY_MONTH}}      同比月
'20240101'（pt 下限常量）与注释中的历史日期不动。
"""
import io, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="gbk", errors="replace")

SRC = r"c:\Users\Cupshe\Desktop\test\out\ops_20261021"
DST = r"c:\Users\Cupshe\Desktop\test\skills_local\_shared\sql"

FILES = [
    "S1_目标达成.csv.sql",
    "S1W_周度上新.csv.sql",
    "S2_品类拆解L2.csv.sql",
    "S2_品类拆解L3.csv.sql",
    "S2D_品类日趋势.csv.sql",
    "S3_新老品业务部门.csv.sql",
]

# 注意顺序：10 字符完整日期在前，7 字符月串在后；保留 SQL 引号（占位符也带引号）
REPL = [
    ("'2026-10-19'", "'{{W_CUR_START}}'"),
    ("'2026-10-25'", "'{{W_CUR_END}}'"),
    ("'2026-10-12'", "'{{W_PREV_START}}'"),
    ("'2026-10-18'", "'{{W_PREV_END}}'"),
    ("'2026-10-01'", "'{{START}}'"),
    ("'2026-10-20'", "'{{END}}'"),
    ("'2026-09-01'", "'{{PM_START}}'"),
    ("'2026-09-20'", "'{{PM_END}}'"),
    ("'2025-10-01'", "'{{PY_START}}'"),
    ("'2025-10-20'", "'{{PY_END}}'"),
    ("'2026-10'", "'{{MONTH}}'"),
    ("'2026-09'", "'{{PM_MONTH}}'"),
    ("'2025-10'", "'{{PY_MONTH}}'"),
]

TPL_HDR = """-- [模板] 占位符由 render_sql.py 按 --start/--end 自动填充（占位符均带 SQL 引号）：
--   'START'/'END'=分析窗口；'PM_*'=环比期（回拨1个月）；'PY_*'=同比期（回拨1年）；
--   'MONTH'/'PM_MONTH'/'PY_MONTH'=月度口径（YYYY-MM）；'W_CUR_*'=END所在自然周（周一~周日）；'W_PREV_*'=上一周
-- 原始脚本产自 2026-10-01~10-20 窗口，历史演进注释保留原样。
"""

os.makedirs(DST, exist_ok=True)
for f in FILES:
    src = io.open(os.path.join(SRC, f), encoding="utf-8").read()
    out, n = src, 0
    for old, new in REPL:
        if old in out:
            n += out.count(old)
            out = out.replace(old, new)
    # 校验：不应再有 2026/2025 开头的引号日期（除注释行）
    dst_path = os.path.join(DST, f.replace(".csv.sql", ".sql.tpl"))
    io.open(dst_path, "w", encoding="utf-8").write(TPL_HDR + out)
    # 残留检查（忽略纯注释行）
    residue = [l.strip()[:100] for l in out.split("\n")
               if ("2026" in l or "2025" in l) and not l.strip().startswith("--")]
    print(f"{f} -> {os.path.basename(dst_path)}  替换 {n} 处；残留行 {len(residue)}")
    for r in residue[:5]:
        print("   残留:", r)
