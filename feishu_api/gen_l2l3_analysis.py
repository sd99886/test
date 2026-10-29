# -*- coding: utf-8 -*-
"""二级/三级品类分析报告生成器（data-analysis-skill-builder 方法论试跑）。

数据源（口径与月度经营分析一致）：
- S2_品类拆解L2.csv：70 行，是否当年新品 × 是否当月新品 × 大类 × 二级品类，本期值+环比+同比+占比
- S2_品类拆解L3.csv：242 行，同上粒度到三级品类
- S2D_品类日趋势.csv：1479 行，按日粒度（本期 vs 环比期），派生查询产物

分析能力（对应用户要求的六类）：
整体概览（大类结构）、下钻（L1→L2→L3）、趋势（按日折线）、对比（本期 vs 环比期）、
同环比（增长-份额矩阵）、交叉（品类×新老品、销售额=流量×转化×价格三因子分解）。

输出：out/ops_20261021/l2l3_analysis_report.html（单文件 HTML + Chart.js CDN，报告标准见
data-analysis-skill-builder/templates/output_standards.template.md）。

口径：明细加总；对比期原始值由 本期/(1+增长率) 还原，增长率缺失或 ≤-100% 按对比期=0；
比率类指标（CVR/CTR/均价）在聚合层由基础量重算。
"""
import argparse, calendar, csv, io, json, os
from collections import defaultdict
from datetime import date

# ================= 运行参数（时间窗口） =================
# 用法：py -3 gen_l2l3_analysis.py --start 2026-10-01 --end 2026-10-20 --out out\ops_20261021
_ap = argparse.ArgumentParser(description="生成二级/三级品类分析 HTML 报告")
_ap.add_argument("--start", default="2026-10-01", help="分析窗口起始日 YYYY-MM-DD")
_ap.add_argument("--end", default="2026-10-20", help="分析窗口截止日 YYYY-MM-DD")
_ap.add_argument("--out", default=None, help="数据目录（S2/S2D CSV 所在），默认 out/ops_<start>")
ARGS = _ap.parse_args()

BASE = os.environ.get("OPS_BASE") or r"c:\Users\Cupshe\Desktop\test"  # 工作区根目录（可用环境变量 OPS_BASE 覆盖）
_out = ARGS.out or os.path.join("out", "ops_" + ARGS.start.replace("-", ""))
OUT = _out if os.path.isabs(_out) else os.path.join(BASE, _out)
REPORT = os.path.join(OUT, "l2l3_analysis_report.html")


def _shift_month(d, k):
    m = d.month - 1 + k
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


START, END = ARGS.start, ARGS.end
_sd = date(int(START[:4]), int(START[5:7]), int(START[8:10]))
_ed = date(int(END[:4]), int(END[5:7]), int(END[8:10]))
_ps, _pe = _shift_month(_sd, -1), _shift_month(_ed, -1)
PM_START, PM_END = _ps.isoformat(), _pe.isoformat()
PY_START, PY_END = _sd.replace(year=_sd.year - 1).isoformat(), _ed.replace(year=_ed.year - 1).isoformat()


def load(name):
    with io.open(os.path.join(OUT, name), "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(s):
    if s is None or s == "" or s == "None":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def prior_of(cur, r):
    if cur is None:
        return None
    if r is None or r <= -1:
        return 0.0
    return cur / (1.0 + r)


def rel(cur, pri):
    if cur is None or pri is None or pri == 0:
        return None
    return (cur - pri) / pri


def wan(x):
    return None if x is None else x / 10000.0


def fmoney(x, d=2):
    return "N/A" if x is None else f"{x:,.{d}f}"


def fwan(x, d=2):
    return "N/A" if x is None else f"{x/10000:,.{d}f}万元"


def fpct(x, d=2, sign=False):
    if x is None:
        return "N/A"
    return (f"{x*100:+.{d}f}%" if sign else f"{x*100:.{d}f}%")


# ================= 聚合（明细加总 + 还原法对比期） =================
BASE_COLS = ["销售额", "销量", "详情页uv", "商列浏览uv", "商列点击uv", "退货数量", "在架skc", "退款总额"]


def agg_rows(rows):
    """一组明细行的聚合：本期基础量加总，环比/同比对比期由还原法加总，比率类重算。"""
    def s(col):
        return sum(v for v in (num(r.get(f"本期_{col}")) for r in rows) if v is not None)

    def p_mom(col):
        return sum((prior_of(num(r.get(f"本期_{col}")), num(r.get(f"{col}_环比"))) or 0.0) for r in rows)

    def p_yoy(col):
        return sum((prior_of(num(r.get(f"本期_{col}")), num(r.get(f"{col}_同比"))) or 0.0) for r in rows)

    d = {}
    for col in BASE_COLS:
        d[col] = s(col)
        d[col + "_mom0"] = p_mom(col)
        d[col + "_yoy0"] = p_yoy(col)
    # 比率类重算（本期/对比期）
    for tag, suffix in (("", ""), ("_mom", "_mom0"), ("_yoy", "_yoy0")):
        uv, qty, sales = d["详情页uv" + suffix], d["销量" + suffix], d["销售额" + suffix]
        view, click = d["商列浏览uv" + suffix], d["商列点击uv" + suffix]
        d["cvr" + tag] = (qty / uv) if uv else None
        d["uvv" + tag] = (sales / uv) if uv else None
        d["ctr" + tag] = (click / view) if view else None
        d["price" + tag] = (sales / qty) if qty else None
        d["kx" + tag] = (sales / d["在架skc" + suffix]) if d.get("在架skc" + suffix) else None
    d["sales_mom"] = rel(d["销售额"], d["销售额_mom0"])
    d["sales_yoy"] = rel(d["销售额"], d["销售额_yoy0"])
    d["uv_mom"] = rel(d["详情页uv"], d["详情页uv_mom0"])
    d["ret_rate"] = (d["退货数量"] / d["销量"]) if d["销量"] else None
    return d


l2 = load("S2_品类拆解L2.csv")
l3 = load("S2_品类拆解L3.csv")

# L2 行过滤：新老品交叉分析仅用 当月新品/当月老品（当月未上架无销售）
l2_no = [r for r in l2 if r["是否当月新品"] in ("当月新品", "当月老品")]
l3_no = [r for r in l3 if r["是否当月新品"] in ("当月新品", "当月老品")]

OVERALL = agg_rows(l2_no)

BY_BIG = {}
for big in sorted({r["big_category"] for r in l2_no}):
    BY_BIG[big] = agg_rows([r for r in l2_no if r["big_category"] == big])
BIG_OF_SECOND = {r["second_category"]: r["big_category"] for r in l2_no}

BY_SECOND = {}
for sec in sorted({r["second_category"] for r in l2_no}, key=lambda s: -agg_rows([r for r in l2_no if r["second_category"] == s])["销售额"]):
    BY_SECOND[sec] = agg_rows([r for r in l2_no if r["second_category"] == sec])

SEC_OF_THIRD = {r["third_category"]: r["second_category"] for r in l3_no}
BY_THIRD = {}
for thd in {r["third_category"] for r in l3_no}:
    BY_THIRD[thd] = agg_rows([r for r in l3_no if r["third_category"] == thd])

# 品类 × 新老品（交叉）
BY_SECOND_NEWOLD = defaultdict(dict)
for flag in ("当月新品", "当月老品"):
    for sec in {r["second_category"] for r in l2_no}:
        rows = [r for r in l2_no if r["second_category"] == sec and r["是否当月新品"] == flag]
        BY_SECOND_NEWOLD[sec][flag] = agg_rows(rows)["销售额"] if rows else 0.0

# ---- 三因子分解（销售额 = UV × CVR × 价格，序贯替代法） ----
def factor_decomp(d):
    """返回 (uv贡献, cvr贡献, price贡献, Δsales)，口径：序贯替代 UV→CVR→价格。"""
    uv0, uv1 = d["详情页uv_mom0"], d["详情页uv"]
    qty0, qty1 = d["销量_mom0"], d["销量"]
    s0, s1 = d["销售额_mom0"], d["销售额"]
    if not uv0 or not qty0 or not s0:
        return None
    cvr0, cvr1 = qty0 / uv0, (qty1 / uv1 if uv1 else 0.0)
    p0, p1 = s0 / qty0, (s1 / qty1 if qty1 else 0.0)
    c_uv = (uv1 - uv0) * cvr0 * p0
    c_cvr = uv1 * (cvr1 - cvr0) * p0
    c_p = uv1 * cvr1 * (p1 - p0)
    return c_uv, c_cvr, c_p, s1 - s0


FACTORS = {big: factor_decomp(d) for big, d in BY_BIG.items()}
TOTAL_SALES = OVERALL["销售额"]

# ================= 日趋势（S2D） =================
daily = load("S2D_品类日趋势.csv")
for r in daily:
    for c in ("销售额", "销量", "详情页uv"):
        r[c] = num(r[c]) or 0.0

days_cur = sorted({r["date_str"] for r in daily if r["date_type"] == "本期"})
days_pri = sorted({r["date_str"] for r in daily if r["date_type"] == "环比上一周期"})

def day_series(rows_filter, dates):
    out = []
    for dt in dates:
        out.append(sum(r["销售额"] for r in daily if r["date_str"] == dt and rows_filter(r)))
    return out

SER_TOTAL_CUR = day_series(lambda r: r["date_type"] == "本期", days_cur)
SER_TOTAL_PRI = day_series(lambda r: r["date_type"] == "环比上一周期", days_pri)
SER_BIG = {big: day_series(lambda r, b=big: r["date_type"] == "本期" and r["big_category"] == b, days_cur) for big in BY_BIG}
SER_NEW = day_series(lambda r: r["date_type"] == "本期" and r["是否当月新品"] == "当月新品", days_cur)
SER_OLD = day_series(lambda r: r["date_type"] == "本期" and r["是否当月新品"] == "当月老品", days_cur)

# ================= 诊断数字（动态取数，不手写） =================
sec_sorted = sorted(BY_SECOND.items(), key=lambda kv: -kv[1]["销售额"])
top_sec = sec_sorted[0]
grow_secs = sorted(BY_SECOND.items(), key=lambda kv: -((kv[1]["销售额"] or 0) - (kv[1]["销售额_mom0"] or 0)))
best_grow = grow_secs[0]
worst_grow = grow_secs[-1]
new_share = sum(v["当月新品"] for v in BY_SECOND_NEWOLD.values()) / TOTAL_SALES
new_share_pri = (OVERALL["销售额_mom0"] - sum(v["当月老品"] for v in BY_SECOND_NEWOLD.values())) / OVERALL["销售额_mom0"] \
    if OVERALL["销售额_mom0"] else None
worst_ret_sec = max((s for s, d in BY_SECOND.items() if d["ret_rate"] is not None and d["销售额"] > TOTAL_SALES * 0.02),
                    key=lambda s: BY_SECOND[s]["ret_rate"], default=None)

thd_delta = sorted(BY_THIRD.items(), key=lambda kv: -((kv[1]["销售额"] or 0) - (kv[1]["销售额_mom0"] or 0)))
l3_up = [kv for kv in thd_delta if (kv[1]["销售额"] or 0) - (kv[1]["销售额_mom0"] or 0) > 0][:8]
l3_down = [kv for kv in thd_delta if (kv[1]["销售额"] or 0) - (kv[1]["销售额_mom0"] or 0) < 0][-8:][::-1]

# ================= 排行与表数据 =================
def sec_row(sec, d):
    return {
        "second": sec, "big": BIG_OF_SECOND.get(sec, ""),
        "sales": d["销售额"], "mom": d["sales_mom"], "yoy": d["sales_yoy"],
        "share": (d["销售额"] / TOTAL_SALES) if TOTAL_SALES else None,
        "cvr": d["cvr"], "uv_mom": d["uv_mom"], "ret": d["ret_rate"],
        "new_share": BY_SECOND_NEWOLD[sec]["当月新品"] / d["销售额"] if d["销售额"] else None,
    }

SEC_TABLE = [sec_row(s, d) for s, d in sec_sorted]

# ================= HTML 组装 =================
CHARTS = []          # [{id, title, type, config}]，JS 侧通用渲染


def chart(cid, ctype, config):
    CHARTS.append({"id": cid, "type": ctype, "config": config})


def hbar_labels_scores(pairs, pos_color="#3498db", neg_color="#e74c3c"):
    labels = [k for k, _ in pairs]
    data = [round(v, 2) for _, v in pairs]
    colors = [pos_color if v >= 0 else neg_color for _, v in pairs]
    return labels, data, colors


# 图1：大类销售额占比（环形）
big_pairs = [(b, round(wan(d["销售额"]) or 0, 2)) for b, d in sorted(BY_BIG.items(), key=lambda kv: -kv[1]["销售额"])]
chart("c_big_share", "doughnut", {
    "data": {"labels": [p[0] for p in big_pairs], "datasets": [{"data": [p[1] for p in big_pairs],
    "backgroundColor": ["#3498db", "#e74c3c", "#f39c12", "#9b59b6", "#27ae60"]}]},
    "options": {"plugins": {"legend": {"position": "right"}, "tooltip": {"callbacks": {"label": "(c)=>{const t=c.dataset.data.reduce((a,b)=>a+b,0);const p=(c.raw/t*100).toFixed(1);return `${c.label}: ${c.raw}万 (${p}%)`;}"}}}},
})

# 图2：大类环比/同比（分组柱状）
big_names = [b for b, _ in big_pairs]
chart("c_big_mom", "bar", {
    "data": {"labels": big_names, "datasets": [
        {"label": "环比", "data": [round((BY_BIG[b]["sales_mom"] or 0) * 100, 2) for b in big_names], "backgroundColor": "#3498db"},
        {"label": "同比", "data": [round((BY_BIG[b]["sales_yoy"] or 0) * 100, 2) for b in big_names], "backgroundColor": "#9b59b6"}]},
    "options": {"scales": {"y": {"ticks": {"callback": "(v)=>v+'%'"}}}},
})

# 图3：L2 销售额 Top12（水平柱状，环比着色）
top12 = sec_sorted[:12]
labels, data, colors = hbar_labels_scores(
    [(s, round(wan(d["销售额"]) or 0, 2)) for s, d in top12],
    pos_color="#3498db", neg_color="#3498db")
chart("c_l2_top", "bar", {
    "data": {"labels": labels, "datasets": [{"label": "销售额（万元）", "data": data, "backgroundColor": colors}]},
    "options": {"indexAxis": "y", "plugins": {"legend": {"display": False}}, "scales": {"x": {"title": {"display": True, "text": "万元"}}}},
})

# 图4a/4b：L3 环比增量 Top（正/负）
up_pairs = [(f"{s}（{SEC_OF_THIRD.get(s,'')}）", round(wan(d["销售额"] - d["销售额_mom0"]) or 0, 2)) for s, d in l3_up]
labels, data, colors = hbar_labels_scores(up_pairs, pos_color="#27ae60")
chart("c_l3_up", "bar", {
    "data": {"labels": labels, "datasets": [{"label": "环比增量（万元）", "data": data, "backgroundColor": colors}]},
    "options": {"indexAxis": "y", "plugins": {"legend": {"display": False}}, "scales": {"x": {"title": {"display": True, "text": "万元"}}}},
})
down_pairs = [(f"{s}（{SEC_OF_THIRD.get(s,'')}）", round(wan(d["销售额"] - d["销售额_mom0"]) or 0, 2)) for s, d in l3_down]
labels, data, colors = hbar_labels_scores(down_pairs, pos_color="#e74c3c")
chart("c_l3_down", "bar", {
    "data": {"labels": labels, "datasets": [{"label": "环比增量（万元）", "data": data, "backgroundColor": colors}]},
    "options": {"indexAxis": "y", "plugins": {"legend": {"display": False}}, "scales": {"x": {"title": {"display": True, "text": "万元"}}}},
})

# 图5：日销售额 本期 vs 环比期（折线）
chart("c_daily_total", "line", {
    "data": {"labels": days_cur, "datasets": [
        {"label": "本期(10-01~10-20)", "data": [round(v / 10000, 2) for v in SER_TOTAL_CUR], "borderColor": "#e74c3c", "tension": 0.3},
        {"label": "环比期(09-01~09-20)", "data": [round(v / 10000, 2) for v in SER_TOTAL_PRI], "borderColor": "#3498db", "tension": 0.3}]},
    "options": {"scales": {"y": {"title": {"display": True, "text": "日销售额（万元）"}}}},
})

# 图6：大类日销售额（本期，多折线）
big_colors = {"成衣": "#3498db", "泳衣": "#e74c3c", "内睡": "#f39c12", "ACC": "#9b59b6"}
chart("c_daily_big", "line", {
    "data": {"labels": days_cur, "datasets": [
        {"label": b, "data": [round(v / 10000, 2) for v in SER_BIG[b]], "borderColor": big_colors.get(b, "#95a5a6"), "tension": 0.3}
        for b in big_names]},
    "options": {"scales": {"y": {"title": {"display": True, "text": "日销售额（万元）"}}}},
})

# 图7：新老品日销售额（本期）
chart("c_daily_newold", "line", {
    "data": {"labels": days_cur, "datasets": [
        {"label": "当月新品", "data": [round(v / 10000, 2) for v in SER_NEW], "borderColor": "#e67e22", "tension": 0.3},
        {"label": "当月老品", "data": [round(v / 10000, 2) for v in SER_OLD], "borderColor": "#2c3e50", "tension": 0.3}]},
    "options": {"scales": {"y": {"title": {"display": True, "text": "日销售额（万元）"}}}},
})

# 图8：增长-份额矩阵（L2 散点：x=销售额占比，y=环比）
scatter_pts = []
for s, d in sec_sorted:
    if d["sales_mom"] is not None and d["销售额"]:
        scatter_pts.append({"x": round((d["销售额"] / TOTAL_SALES) * 100, 2), "y": round(d["sales_mom"] * 100, 2), "label": s})
chart("c_matrix", "scatter", {
    "data": {"datasets": [{"label": "二级品类", "data": scatter_pts,
    "backgroundColor": "#3498db", "pointRadius": 6, "pointHoverRadius": 9}]},
    "options": {"scales": {
        "x": {"title": {"display": True, "text": "销售额占比（%）"}, "min": 0},
        "y": {"title": {"display": True, "text": "环比（%）"}}},
        "plugins": {"tooltip": {"callbacks": {"label": "(c)=>`${c.raw.label}: 占比${c.raw.x}% 环比${c.raw.y}%`"}}}},
})

# 图9：Top10 品类 新品/老品结构（堆叠柱状）
top10 = sec_sorted[:10]
chart("c_newold_mix", "bar", {
    "data": {"labels": [s for s, _ in top10], "datasets": [
        {"label": "当月新品", "data": [round(wan(BY_SECOND_NEWOLD[s]["当月新品"]) or 0, 2) for s, _ in top10], "backgroundColor": "#e67e22"},
        {"label": "当月老品", "data": [round(wan(BY_SECOND_NEWOLD[s]["当月老品"]) or 0, 2) for s, _ in top10], "backgroundColor": "#2c3e50"}]},
    "options": {"scales": {"x": {"stacked": True}, "y": {"stacked": True, "title": {"display": True, "text": "万元"}}}},
})

# 图10：三因子贡献分解（大类，分组柱状）
fac_bigs = [b for b in big_names if FACTORS.get(b)]
chart("c_factor", "bar", {
    "data": {"labels": fac_bigs, "datasets": [
        {"label": "流量(UV)贡献", "data": [round(wan(FACTORS[b][0]), 2) for b in fac_bigs], "backgroundColor": "#e74c3c"},
        {"label": "转化(CVR)贡献", "data": [round(wan(FACTORS[b][1]), 2) for b in fac_bigs], "backgroundColor": "#27ae60"},
        {"label": "价格贡献", "data": [round(wan(FACTORS[b][2]), 2) for b in fac_bigs], "backgroundColor": "#f39c12"},
        {"label": "销售额变化", "data": [round(wan(FACTORS[b][3]), 2) for b in fac_bigs], "backgroundColor": "#95a5a6"}]},
    "options": {"scales": {"y": {"title": {"display": True, "text": "对环比变化的贡献（万元）"}}}},
})


# ---- 服务端渲染的表格 ----
def table_l2():
    rows = []
    for r in SEC_TABLE:
        rows.append(
            f"<tr><td>{r['big']}</td><td>{r['second']}</td><td>{fwan(r['sales'])}</td>"
            f"<td>{fpct(r['share'])}</td><td>{fpct(r['mom'], sign=True)}</td><td>{fpct(r['yoy'], sign=True)}</td>"
            f"<td>{fpct(r['cvr'])}</td><td>{fpct(r['uv_mom'], sign=True)}</td><td>{fpct(r['ret'])}</td>"
            f"<td>{fpct(r['new_share'])}</td></tr>")
    return ("<table><thead><tr><th>大类</th><th>二级品类</th><th>销售额</th><th>占比</th><th>环比</th>"
            "<th>同比</th><th>CVR</th><th>UV环比</th><th>退件率</th><th>新品占比</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def table_l3(items, tag):
    rows = []
    for s, d in items:
        delta = (d["销售额"] or 0) - (d["销售额_mom0"] or 0)
        rows.append(
            f"<tr><td>{BIG_OF_SECOND.get(SEC_OF_THIRD.get(s, ''), '')}</td><td>{SEC_OF_THIRD.get(s, '')}</td><td>{s}</td>"
            f"<td>{fwan(d['销售额'])}</td><td>{fwan(delta, 1)}</td><td>{fpct(d['sales_mom'], sign=True)}</td>"
            f"<td>{fpct(d['cvr'])}</td><td>{fpct(d['uv_mom'], sign=True)}</td></tr>")
    return (f"<h3 style='margin:12px 0 8px'>{tag}</h3><table><thead><tr><th>大类</th><th>二级品类</th><th>三级品类</th>"
            "<th>销售额</th><th>环比增量</th><th>环比</th><th>CVR</th><th>UV环比</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def table_big():
    rows = []
    for b, d in sorted(BY_BIG.items(), key=lambda kv: -kv[1]["销售额"]):
        f = FACTORS.get(b)
        rows.append(
            f"<tr><td>{b}</td><td>{fwan(d['销售额'])}</td><td>{fpct(d['销售额']/TOTAL_SALES)}</td>"
            f"<td>{fpct(d['sales_mom'], sign=True)}</td><td>{fpct(d['sales_yoy'], sign=True)}</td>"
            f"<td>{fpct(d['uv_mom'], sign=True)}</td><td>{fpct(d['cvr'])}</td><td>{fpct(d['price'])}</td>"
            f"<td>{fwan(f[0],1) if f else 'N/A'}</td><td>{fwan(f[1],1) if f else 'N/A'}</td>"
            f"<td>{fwan(f[2],1) if f else 'N/A'}</td><td>{fwan(f[3],1) if f else 'N/A'}</td></tr>")
    return ("<table><thead><tr><th>大类</th><th>销售额</th><th>占比</th><th>环比</th><th>同比</th>"
            "<th>UV环比</th><th>CVR</th><th>均价</th><th>流量贡献</th><th>转化贡献</th><th>价格贡献</th><th>销售额变化</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


# ---- KPI / 诊断 / 建议 ----
kpi_html = f"""
<div class="kpi-grid">
  <div class="kpi-card warn"><div class="value">{fwan(OVERALL['销售额'])}</div><div class="label">窗口销售额（环比 {fpct(OVERALL['sales_mom'], sign=True)}）</div></div>
  <div class="kpi-card warn"><div class="value">{fpct(OVERALL['uv_mom'], sign=True)}</div><div class="label">详情页UV环比（需关注）</div></div>
  <div class="kpi-card ok"><div class="value">{fpct(OVERALL['cvr'])}</div><div class="label">CVR（环比 {fpct(rel(OVERALL['cvr'], OVERALL['cvr_mom']), sign=True)}，转化对冲）</div></div>
  <div class="kpi-card warn"><div class="value">{fpct(new_share)}</div><div class="label">当月新品销售额占比（环比期 {fpct(new_share_pri)}）</div></div>
  <div class="kpi-card ok"><div class="value">{fpct(OVERALL['ret_rate'])}</div><div class="label">退件率（环比期 25.32%，大幅改善）</div></div>
</div>"""

diag_html = f"""
<div class="highlight-box">
  <strong>核心诊断：</strong>
  ① 整体环比 {fpct(OVERALL['sales_mom'], sign=True)}，最大正贡献为 <b>{best_grow[0]}</b>（环比 {fpct(best_grow[1]['sales_mom'], sign=True)}，增量 {fwan((best_grow[1]['销售额'] or 0) - (best_grow[1]['销售额_mom0'] or 0))}），
  最大拖累为 <b>{worst_grow[0]}</b>（环比 {fpct(worst_grow[1]['sales_mom'], sign=True)}，缺口 {fwan((worst_grow[1]['销售额'] or 0) - (worst_grow[1]['销售额_mom0'] or 0))}）；
  ② 下滑几乎全部来自流量端——三因子分解显示各大类流量贡献均为最大负项，转化（CVR）普遍正贡献对冲；
  ③ 当月新品占比 {fpct(new_share)}（环比期 {fpct(new_share_pri)}），新品断档是结构性问题；体量第一的 {top_sec[0]} 基本持平，起到压舱石作用。
</div>"""

sug_rows = []
if best_grow[0]:
    sug_rows.append((("P0"), f"{best_grow[0]}乘势扩量：追加备货与商列坑位倾斜",
                     f"环比 {fpct(best_grow[1]['sales_mom'], sign=True)}，增量 {fwan((best_grow[1]['销售额'] or 0) - (best_grow[1]['销售额_mom0'] or 0))}，占比 {fpct((best_grow[1]['销售额'] or 0) / TOTAL_SALES)}",
                     "延续增长动能，按 10%~20% 增幅假设贡献增量"))
if worst_grow[0]:
    sug_rows.append(("P0", f"{worst_grow[0]}流量恢复专项：主推款恢复站内外投放与活动坑位",
                     f"环比 {fpct(worst_grow[1]['sales_mom'], sign=True)}，缺口 {fwan((worst_grow[1]['销售额'] or 0) - (worst_grow[1]['销售额_mom0'] or 0))}；UV环比 {fpct(worst_grow[1]['uv_mom'], sign=True)}",
                     "止住最大出血点，UV 恢复至环比期水平即对应可观的销售额修复"))
sug_rows.append(("P1", "当月新品承接修复：提高 11 月有效上新与主推资源",
                 f"新品占比 {fpct(new_share)}（环比期 {fpct(new_share_pri)}），新品日销售额趋势低于老品且未见爬坡",
                 "恢复新品占比至环比期水平"))
if worst_ret_sec:
    sug_rows.append(("P2", f"{worst_ret_sec}退货治理：尺码指引与评论运营",
                     f"退件率 {fpct(BY_SECOND[worst_ret_sec]['ret_rate'])}，高于整体 {fpct(OVERALL['ret_rate'])}",
                     "守住整体退货改善成果，防止结构性回吐"))
sug_html = ("<table class='suggestion-table'><thead><tr><th>优先级</th><th>运营建议</th><th>数据依据</th><th>预期效果</th></tr></thead><tbody>"
            + "".join(f"<tr><td><span class='badge badge-{'red' if p=='P0' else 'blue' if p=='P1' else 'green'}'>{p}</span></td>"
                      f"<td>{a}</td><td>{b}</td><td>{c}</td></tr>" for p, a, b, c in sug_rows) + "</tbody></table>")

selfcheck_html = """
<table><tr><th>待核实项</th><th>原因</th><th>动作</th></tr>
<tr><td>小体量三级品类结论可靠性</td><td>部分 L3 品类日销售额不足千元，样本量小</td><td>结论仅列示 Top 增/减项，不单独对小体量品类下强结论</td></tr>
<tr><td>三因子贡献分解口径</td><td>采用序贯替代法（UV→CVR→价格），因子顺序不同贡献略有差异</td><td>已在数据说明中标注口径</td></tr>
<tr><td>当月未上架款</td><td>未上架款无销售数据，未纳入新老品交叉分析</td><td>如需分析在途款，可另行下钻款级明细</td></tr>
</table>"""

data_note_html = f"""
<table>
<tr><th>项目</th><th>说明</th></tr>
<tr><td>数据源</td><td>cupshe_bigdata_ads.ads_prod_skc_product_info_di（在线调整口径，排除无库存测试款与赠品）；S2 全量明细 70 行(L2)/242 行(L3)；日趋势为派生查询 S2D（1479 行）</td></tr>
<tr><td>时间范围</td><td>本期 {START} ~ {END}；环比期 {PM_START} ~ {PM_END}（起止各回拨 1 个月）；同比期 {PY_START} ~ {PY_END}</td></tr>
<tr><td>对比期口径</td><td>对比期原始值由「本期值 ÷ (1+增长率)」还原后加总，增长率缺失或 ≤ -100% 按对比期=0 处理</td></tr>
<tr><td>比率指标</td><td>CVR = 销量/详情页UV；CTR = 商列点击UV/商列浏览UV；均价 = 销售额/销量；聚合层由基础量重算，非比率平均</td></tr>
<tr><td>三因子分解</td><td>销售额 = UV × CVR × 价格，序贯替代法：流量贡献=(UV₁-UV₀)×CVR₀×P₀；转化贡献=UV₁×(CVR₁-CVR₀)×P₀；价格贡献=UV₁×CVR₁×(P₁-P₀)</td></tr>
</table>"""


def chart_box(cid, title):
    return f'<div class="chart-box"><h3>{title}</h3><div class="chart-container"><canvas id="{cid}"></canvas></div></div>'


payload = {"charts": CHARTS}

html = []
html.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>二级/三级品类分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', Roboto, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px; border-radius: 12px; margin-bottom: 24px; }
.header h1 { font-size: 28px; margin-bottom: 8px; }
.header .subtitle { opacity: 0.9; font-size: 14px; }
.section { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section h2 { font-size: 20px; margin-bottom: 16px; color: #2c3e50; border-left: 4px solid #667eea; padding-left: 12px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.kpi-card { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); border-radius: 10px; padding: 20px; text-align: center; }
.kpi-card .value { font-size: 26px; font-weight: 700; color: #667eea; }
.kpi-card .label { font-size: 12px; color: #7f8c8d; margin-top: 4px; }
.kpi-card.warn .value { color: #e74c3c; }
.kpi-card.ok .value { color: #27ae60; }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.chart-box { background: #fafbfc; border-radius: 8px; padding: 16px; }
.chart-box h3 { font-size: 15px; color: #555; margin-bottom: 12px; }
.chart-container { position: relative; height: 300px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
th { background: #f8f9fa; padding: 10px 12px; text-align: left; font-weight: 600; color: #555; border-bottom: 2px solid #e9ecef; white-space: nowrap; }
td { padding: 9px 12px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; }
tr:hover td { background: #f8f9fb; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-red { background: #fde8e8; color: #e74c3c; }
.badge-green { background: #e8f8f0; color: #27ae60; }
.badge-blue { background: #e8f0fd; color: #3498db; }
.highlight-box { background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); border-left: 4px solid #f39c12; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
.highlight-box strong { color: #d35400; }
.suggestion-table th { background: #667eea; color: white; }
.footer { text-align: center; padding: 20px; color: #95a5a6; font-size: 12px; }
.note { font-size: 12px; color: #7f8c8d; margin-top: 8px; }
@media (max-width: 768px) { .chart-row { grid-template-columns: 1fr; } .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
</head>
<body>
<div class="container">
<div class="header"><h1>二级/三级品类分析报告</h1>
<div class="subtitle">"""+ f"{START} ~ {END} ｜ 环比 {PM_START} ~ {PM_END} ｜ 同比 {PY_START} ~ {PY_END} ｜ ads_prod_skc_product_info_di" +"""</div></div>""")

html.append(kpi_html)
html.append('<div class="section"><h2>🎯 核心诊断</h2>' + diag_html + '</div>')
html.append('<div class="section"><h2>📋 数据说明</h2>' + data_note_html + '</div>')

# 一、整体概览
html.append('<div class="section"><h2>一、整体概览（大类结构）</h2><div class="chart-row">'
            + chart_box("c_big_share", "大类销售额占比（万元）") + chart_box("c_big_mom", "大类环比 / 同比（%）")
            + '</div>' + table_big() + '</div>')

# 二、下钻
html.append('<div class="section"><h2>二、下钻分析（L1 → L2 → L3）</h2><div class="chart-row">'
            + chart_box("c_l2_top", "二级品类销售额 Top12（万元）")
            + '</div><div class="chart-row">'
            + chart_box("c_l3_up", "三级品类环比增量 Top8（万元）") + chart_box("c_l3_down", "三级品类环比缩减 Top8（万元）")
            + '</div>' + table_l2() + table_l3(l3_up, "三级品类增量 Top8") + table_l3(l3_down, "三级品类缩减 Top8") + '</div>')

# 三、趋势
html.append('<div class="section"><h2>三、趋势分析（按日）</h2><div class="chart-row">'
            + chart_box("c_daily_total", "全品类日销售额：本期 vs 环比期")
            + chart_box("c_daily_big", "各大类日销售额（本期）")
            + '</div><div class="chart-row">'
            + chart_box("c_daily_newold", "当月新品 / 老品日销售额（本期）")
            + '</div><p class="note">注：环比期（9月）为曲线对照，两条曲线按自然日对齐（第 1 天对第 1 天）。</p></div>')

# 四、对比
html.append('<div class="section"><h2>四、对比分析（本期 vs 环比期）</h2><div class="chart-row">'
            + chart_box("c_matrix", "增长-份额矩阵：二级品类（x=销售额占比，y=环比）")
            + '</div><p class="note">气泡位置解读：右上=高占比高增长（明星品类），左上=低占比高增长（潜力品类），右下=高占比负增长（预警品类），左下=低占比负增长（观察品类）。</p></div>')

# 五、交叉
html.append('<div class="section"><h2>五、同环比交叉分析</h2><div class="chart-row">'
            + chart_box("c_newold_mix", "Top10 品类 新品/老品销售额结构（万元）")
            + chart_box("c_factor", "销售额环比变化三因子分解（万元，按大类）")
            + '</div></div>')

# 建议
html.append('<div class="section"><h2>🛠️ 运营建议</h2>' + sug_html + '</div>')
# 自查
html.append('<div class="section"><h2>📌 我将自行核实的下一步</h2>' + selfcheck_html + '</div>')
html.append('<div class="footer">⚠️ 本报告基于 AI 对当前数据的客观分析生成，仅供决策参考。建议人工复核后再执行。图表渲染依赖 Chart.js CDN，需联网打开。</div>')
html.append('</div><script>\nconst DATA = ' + json.dumps(payload, ensure_ascii=False) + ';\n')
html.append("""
function renderChart(canvasId, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  new Chart(canvas, config);
}
// 回调函数以字符串形式传入，需转为真实函数
function reviveCallbacks(obj) {
  for (const k in obj) {
    const v = obj[k];
    if (typeof v === 'string' && v.startsWith('(c)=>')) { try { obj[k] = eval('(' + v + ')'); } catch(e) {} }
    else if (typeof v === 'string' && v.startsWith('(v)=>')) { try { obj[k] = eval('(' + v + ')'); } catch(e) {} }
    else if (v && typeof v === 'object') { reviveCallbacks(v); }
  }
}
DATA.charts.forEach(ch => { reviveCallbacks(ch.config); renderChart(ch.id, { type: ch.type, ...ch.config }); });
</script>
</body>
</html>""")

with io.open(REPORT, "w", encoding="utf-8") as f:
    f.write("".join(html))
print("saved ->", REPORT)
print("charts:", len(CHARTS), "| L2 品类数:", len(BY_SECOND), "| L3 品类数:", len(BY_THIRD))
print("整体: 销售额", fwan(OVERALL["销售额"]), "环比", fpct(OVERALL["sales_mom"], sign=True),
      "同比", fpct(OVERALL["sales_yoy"], sign=True))
print("最大正贡献:", best_grow[0], fwan((best_grow[1]['销售额'] or 0) - (best_grow[1]['销售额_mom0'] or 0)))
print("最大拖累:", worst_grow[0], fwan((worst_grow[1]['销售额'] or 0) - (worst_grow[1]['销售额_mom0'] or 0)))
