# -*- coding: utf-8 -*-
"""render_sql.py — 把 SQL 模板（*.sql.tpl）的日期占位符填充为具体日期。

用法（在 skill 目录下）：
    py -3 scripts/render_sql.py --start 2026-10-01 --end 2026-10-20 \
        --sql-dir sql --out-dir <数据目录>

占位符（全部由 --start/--end 自动派生，无需手工计算）：
  {{START}}/{{END}}            分析窗口起止（如 2026-10-01 / 2026-10-20）
  {{PM_START}}/{{PM_END}}      环比期（窗口起止各回拨 1 个月，日号夹到目标月最大天数）
  {{PY_START}}/{{PY_END}}      同比期（窗口起止各回拨 1 年）
  {{MONTH}}/{{PM_MONTH}}/{{PY_MONTH}}   月度口径月串（YYYY-MM）
  {{W_CUR_START}}/{{W_CUR_END}}        END 所在自然周（周一~周日）
  {{W_PREV_START}}/{{W_PREV_END}}      上一自然周（周一~周日）

输出：<out-dir>/<模板名去 .tpl>（如 S1_目标达成.sql），已可直接交给 odps-query 执行。

Schema 占位符（脱敏版模板使用；本地模板含真实 schema 时这些参数不生效）：
  {{PROJECT_SCHEMA}}    主数仓项目/Schema（--schema 提供）
  {{CDM_SCHEMA}}        CDM 层项目/Schema（--cdm-schema 提供）
  {{ADS_DEV_SCHEMA}}    ADS 开发项目/Schema（--ads-dev-schema 提供）
"""
import argparse, calendar, glob, io, os, sys
from datetime import date, timedelta

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ap = argparse.ArgumentParser(description="填充 SQL 模板日期占位符")
ap.add_argument("--start", required=True, help="分析窗口起始日 YYYY-MM-DD")
ap.add_argument("--end", required=True, help="分析窗口截止日 YYYY-MM-DD")
ap.add_argument("--sql-dir", required=True, help="模板目录（*.sql.tpl）")
ap.add_argument("--out-dir", required=True, help="输出目录（填充后的 .sql）")
ap.add_argument("--schema", default=None,
                help="主数仓项目/Schema 名（脱敏模板中 {{PROJECT_SCHEMA}} 占位符的值；未提供且模板含该占位符时报错）")
ap.add_argument("--cdm-schema", default=None,
                help="CDM 层项目/Schema 名（{{CDM_SCHEMA}} 占位符的值）")
ap.add_argument("--ads-dev-schema", default=None,
                help="ADS 开发项目/Schema 名（{{ADS_DEV_SCHEMA}} 占位符的值）")
ARGS = ap.parse_args()


def parse_d(s):
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))


def shift_month(d, k):
    """日期回拨 k 个月（日号夹到目标月最大天数）"""
    m = d.month - 1 + k
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def fmt(d):
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


sd, ed = parse_d(ARGS.start), parse_d(ARGS.end)
assert sd <= ed, "--start 必须不晚于 --end"

# 自然周：周一为一周之始
w_cur_start = ed - timedelta(days=ed.weekday())
w_cur_end = w_cur_start + timedelta(days=6)
w_prev_start = w_cur_start - timedelta(days=7)
w_prev_end = w_cur_start - timedelta(days=1)

MAP = {
    "{{START}}": fmt(sd), "{{END}}": fmt(ed),
    "{{PM_START}}": fmt(shift_month(sd, -1)), "{{PM_END}}": fmt(shift_month(ed, -1)),
    "{{PY_START}}": fmt(sd.replace(year=sd.year - 1)), "{{PY_END}}": fmt(ed.replace(year=ed.year - 1)),
    "{{MONTH}}": f"{sd.year:04d}-{sd.month:02d}",
    "{{PM_MONTH}}": fmt(shift_month(sd, -1))[:7],
    "{{PY_MONTH}}": f"{sd.year - 1:04d}-{sd.month:02d}",
    "{{W_CUR_START}}": fmt(w_cur_start), "{{W_CUR_END}}": fmt(w_cur_end),
    "{{W_PREV_START}}": fmt(w_prev_start), "{{W_PREV_END}}": fmt(w_prev_end),
}

os.makedirs(ARGS.out_dir, exist_ok=True)
tpls = sorted(glob.glob(os.path.join(ARGS.sql_dir, "*.sql.tpl")))
assert tpls, f"模板目录无 *.sql.tpl: {ARGS.sql_dir}"

for tpl in tpls:
    src = io.open(tpl, encoding="utf-8").read()
    out = src
    if "{{PROJECT_SCHEMA}}" in out:
        assert ARGS.schema, "模板含 {{PROJECT_SCHEMA}} 占位符，需提供 --schema <项目名>"
        out = out.replace("{{PROJECT_SCHEMA}}", ARGS.schema)
    if "{{CDM_SCHEMA}}" in out:
        assert ARGS.cdm_schema, "模板含 {{CDM_SCHEMA}} 占位符，需提供 --cdm-schema <项目名>"
        out = out.replace("{{CDM_SCHEMA}}", ARGS.cdm_schema)
    if "{{ADS_DEV_SCHEMA}}" in out:
        assert ARGS.ads_dev_schema, "模板含 {{ADS_DEV_SCHEMA}} 占位符，需提供 --ads-dev-schema <项目名>"
        out = out.replace("{{ADS_DEV_SCHEMA}}", ARGS.ads_dev_schema)
    for k, v in MAP.items():
        if k in out:
            out = out.replace(k, v)
    # 残留占位符检查（忽略注释行）
    missing = [l.strip()[:80] for l in out.split("\n")
               if "{{" in l and not l.strip().startswith("--")]
    dst = os.path.join(ARGS.out_dir, os.path.basename(tpl)[:-4])  # 去掉 .tpl
    io.open(dst, "w", encoding="utf-8").write(out)
    print(f"  {os.path.basename(tpl)} -> {dst}")
    if missing:
        print(f"  [warn] 疑似未替换占位符:")
        for m in missing[:5]:
            print("    ", m)

print(f"done: {len(tpls)} 个 SQL 已填充，窗口 {ARGS.start}~{ARGS.end}，"
      f"环比 {MAP['{{PM_START}}']}~{MAP['{{PM_END}}']}，同比 {MAP['{{PY_START}}']}~{MAP['{{PY_END}}']}")
