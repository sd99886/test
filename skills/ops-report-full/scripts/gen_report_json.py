# -*- coding: utf-8 -*-
"""生成飞书版经营分析报告的全部内容数据（feishu_report.json + 图表）。

本轮按新文档评论（11条，YOUR_DOC_ID）修订：
评论1/3：3.1/3.2 段落顺序改为 成衣→成衣一部→成衣二部→成衣结论→泳衣→泳衣产品部→泳衣买手部→泳衣结论；
          序号 (1)(2)(3)→无序号→(1)(2)(3)→无序号；结论按参考句式（整体+新品+两部门新品）。
评论2：忽略（用户确认不管）。
评论4：2.6 只描述爆款数和爆款率，大爆款/超爆款不进正文。
评论5：全局去除段落文字与图表标题中的口径标注，口径统一在第7章附录。
评论6：表2-1 补全全部部门（泳衣产品部/泳衣买手部/泳衣/内睡/acc/塑身衣项目部/全品类），并转为图片。
评论7：二级/三级品类分析待用户提供 data-analysis-skill-builder 技能包后另行处理（本轮不做）。
评论8：表3-1/3-2 转图片放对应标题下。
评论9：第4章电子表格说明保留不动。
评论10：电子表格 sheet1 改名「二级品类明细」（在 publish_report.py 发布时幂等处理）。
评论11：表6-1 转图片放标题下。

汇总口径与已有声明一致：明细加总；对比期原始值由 本期/(1+增长率) 还原，增长率缺失或 ≤-100% 按 0 处理。
"""
import argparse, calendar, csv, io, json, os
from datetime import date

# ================= 运行参数（时间窗口与章节开关） =================
# 用法：
#   py -3 gen_report_json.py                          # 默认：2026-10-01~10-20，全部七章
#   py -3 gen_report_json.py --start 2026-11-01 --end 2026-11-20 --out out\ops_20261121
#   py -3 gen_report_json.py --sections 1237           # 无归因模式：仅输出第 1/2/3/7 章
_ap = argparse.ArgumentParser(description="生成飞书版经营分析报告 feishu_report.json")
_ap.add_argument("--start", default="2026-10-01", help="分析窗口起始日 YYYY-MM-DD")
_ap.add_argument("--end", default="2026-10-20", help="分析窗口截止日 YYYY-MM-DD")
_ap.add_argument("--out", default=None, help="数据目录（CSV/图表/JSON 所在），默认 out/ops_<start+7天压缩>")
_ap.add_argument("--sections", default="1234567", help="输出的章节，如 1237=仅第1/2/3/7章（无归因分析）")
_ap.add_argument("--title", default=None, help="报告标题，默认「经营分析报告<今天>」")
ARGS = _ap.parse_args()

BASE = os.environ.get("OPS_BASE") or os.getcwd()  # 工作区根目录（可用环境变量 OPS_BASE 覆盖）
START, END = ARGS.start, ARGS.end
# --out 支持相对路径（相对 BASE）与绝对路径
_out = ARGS.out or os.path.join("out", "ops_" + START.replace("-", ""))
OUT = _out if os.path.isabs(_out) else os.path.join(BASE, _out)
CHARTS = os.path.join(OUT, "charts")
os.makedirs(CHARTS, exist_ok=True)

# 章节开关：'4'/'5'/'6' 不在集合内则跳过归因分析与策略建议
SECTIONS = set(ARGS.sections) or {"1", "2", "3", "4", "5", "6", "7"}
HAS_ATTR = "4" in SECTIONS and "5" in SECTIONS       # 是否含归因分析（第 4/5 章）
HAS_STRATEGY = "6" in SECTIONS                        # 是否含策略建议（第 6 章）

# 由窗口派生的时间变量（叙述性文字自动随窗口更新）
_Y, _M, _D = int(END[:4]), int(END[5:7]), int(END[8:10])
DAYS_IN_MONTH = calendar.monthrange(_Y, _M)[1]
ELAPSED = _D
TP = ELAPSED / DAYS_IN_MONTH            # 时间进度
DATE_TXT = f"截止到{_M}月{_D}日"        # 统一日期表述
MONTH_TXT = f"{_M}月"
TP_TXT = f"{TP*100:.2f}%"


def _shift_month(d, k):
    """日期回拨 k 个月（日号夹到目标月最大天数），用于环比期计算与文字描述"""
    m = d.month - 1 + k
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


_sd = date(int(START[:4]), int(START[5:7]), int(START[8:10]))   # 窗口起始日
_ed = date(_Y, _M, _D)                                          # 窗口截止日
_pd, _py = _shift_month(_ed, -1), _ed.replace(year=_ed.year - 1)
PM_TXT = f"{_pd.year:04d}-{_pd.month:02d}-{_pd.day:02d}"       # 环比期截止日
PY_TXT = f"{_py.year:04d}-{_py.month:02d}-{_py.day:02d}"       # 同比期截止日
PS_TXT = f"{_shift_month(_sd, -1).strftime('%Y-%m-%d')}"        # 环比期起始日
PYS_TXT = f"{_sd.replace(year=_sd.year - 1).strftime('%Y-%m-%d')}"  # 同比期起始日
PM_RANGE = f"{PS_TXT}~{PM_TXT[5:]}"     # 环比期区间文字，如 2026-09-01~09-20
PY_RANGE = f"{PYS_TXT}~{PY_TXT[5:]}"    # 同比期区间文字，如 2025-10-01~10-20
TITLE = ARGS.title or f"经营分析报告{date.today().isoformat()}"
# 含归因时口径声明用「第 3~6 章」，否则仅「第 3 章」
CH_RANGE = "第 3~6 章" if (HAS_ATTR and HAS_STRATEGY) else ("第 3~5 章" if HAS_ATTR else "第 3 章")

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
        return None, False
    if r is None or r <= -1:
        return 0.0, True
    return cur / (1.0 + r), False

def ssum(rows, col):
    return sum(v for v in (num(r.get(col)) for r in rows) if v is not None)

def rel(cur, pri):
    if cur is None or pri is None or pri == 0:
        return None
    return (cur - pri) / pri

def wan(x, d=2):
    return "N/A" if x is None else f"{x/10000:,.{d}f}万元"

def money(x, d=2):
    return "N/A" if x is None else f"{x:,.{d}f}"

def pct(x, d=2):
    return "N/A" if x is None else f"{x*100:.{d}f}%"

def intr(x):
    return "N/A" if x is None else f"{x:,.0f}"

def relf(x, d=2):
    return "N/A" if x is None else f"{x*100:+.{d}f}%"

def tp_diff(rate):
    """达成率-时间进度：返回 (方向文本, 差值)。负=差额，正=超额"""
    if rate is None:
        return None, None
    d = rate - TP
    return ("超时间进度" if d >= 0 else "落后时间进度"), d

def gap_of(rate, tgt):
    """差额/超额数值 = 时间进度差 × 目标值。返回 (标签, 数值)"""
    _, d = tp_diff(rate)
    if d is None or tgt is None:
        return "差额", None
    if d >= 0:
        return "超额", d * tgt
    return "差额", -d * tgt

# ================= S1 =================
s1 = load("S1_目标达成.csv")
DEPT_LABEL = {"acc": "ACC"}

def s1row(idx):
    for r in s1:
        if r["idx"] == idx:
            return r
    return None

def s1v(idx, dept, kind):
    r = s1row(idx)
    return num(r[f"{dept}{kind}"]) if r else None

# 周度/月度上新数（派生查询 S1W，口径与 S1 上新数一致；评论10 与合并表使用）
s1w = load("S1W_周度上新.csv")
WEEK = {r["周期"]: {d: num(r[d]) for d in r if d != "周期"} for r in s1w}

# 第2章段落顺序（人工指定）：None = 结论段
SEC_ORDER = ["成衣", "成衣一部", "成衣二部", None,
             "泳衣", "泳衣产品部", "泳衣买手部", None,
             "内睡", "acc", "塑身衣项目部", "全品类"]
SEC_SEQ = ["(1)", "(2)", "(3)", "",
           "(1)", "(2)", "(3)", "",
           "(1)", "(2)", "(1)", "(2)"]

def sec_name(dept):
    return DEPT_LABEL.get(dept, dept)

def sec_pairs():
    """产出 [(序号, 部门key, 显示名)]，结论位置由 None 标记"""
    out = []
    for dept, seq in zip(SEC_ORDER, SEC_SEQ):
        if dept is None:
            out.append(("", None, None))
        else:
            out.append((seq, dept, sec_name(dept)))
    return out

def gmv_line(idx, dept):
    """GMV/新品GMV/上新数/成功数等 目标-完成 型句式"""
    tgt = s1v(idx, dept, "目标"); act = s1v(idx, dept, "实际")
    rate = s1v(idx, dept, "达成率")
    tag, val = gap_of(rate, tgt)
    if tgt == 0 and act == 0:
        return f"{sec_name(dept)}：当期未设目标，无数据。"
    return (f"{sec_name(dept)} GMV 目标 {wan(tgt)}，{DATE_TXT}完成 {wan(act)}，"
            f"完成率 {pct(rate)}，{tp_diff(rate)[0]} {abs(tp_diff(rate)[1])*100:.2f}%，{tag} {wan(val)}。")

def newgmv_line(dept):
    return gmv_line("新品GMV", dept).replace(" GMV ", " 新品GMV ")

def kuanxiao_line(dept):
    tgt = s1v("新品款效", dept, "目标"); act = s1v("新品款效", dept, "实际")
    rate = s1v("新品款效", dept, "达成率")
    pos, d = tp_diff(rate)
    return (f"{sec_name(dept)} 新品款效 {MONTH_TXT}目标 {money(tgt)}，{DATE_TXT}实际款效 {money(act)}，"
            f"完成率 {pct(rate)}，{pos} {abs(d)*100:.2f}%。")

def shangxin_line(dept):
    tgt = s1v("上新数", dept, "目标"); act = s1v("上新数", dept, "实际")
    rate = s1v("上新数", dept, "达成率")
    tag, val = gap_of(rate, tgt)
    wk = (WEEK.get("本周") or {}).get(dept)
    lw = (WEEK.get("上周") or {}).get(dept)
    wk_txt = ""
    if wk is not None and lw is not None:
        if lw > 0:
            rw = (wk - lw) / lw
            wk_txt = (f"，本周上新 {intr(wk)} 款，上周上新 {intr(lw)} 款，"
                      f"环比上周{'增加' if rw >= 0 else '下降'} {abs(rw)*100:.2f}%")
        else:
            wk_txt = f"，本周上新 {intr(wk)} 款，上周上新 0 款"
    return (f"{sec_name(dept)} 新品上新数目标 {intr(tgt)} 款，{DATE_TXT}完成 {intr(act)} 款，"
            f"完成率 {pct(rate)}，{tp_diff(rate)[0]} {abs(tp_diff(rate)[1])*100:.2f}%{wk_txt}。")

def success_line(dept):
    t1 = s1v("成功数", dept, "目标"); a1 = s1v("成功数", dept, "实际"); r1 = s1v("成功数", dept, "达成率")
    t2 = s1v("成功率", dept, "目标"); a2 = s1v("成功率", dept, "实际"); r2 = s1v("成功率", dept, "达成率")
    return (f"{sec_name(dept)} 新品成功数目标 {intr(t1)} 款，{DATE_TXT}完成 {intr(a1)} 款，完成率 {pct(r1)}；"
            f"{sec_name(dept)} 新品成功率目标 {pct(t2)}，实际成功率 {pct(a2)}，完成率 {pct(r2)}。")

def bakuo_line(dept):
    """爆款数与爆款率：数+率成对（评论4：只描述爆款数和爆款率，大爆款/超爆款不进正文）。
    目标与实际全为 0 视为当期未设目标，整体说明无数据。"""
    parts = []
    for pre in ["爆款"]:
        tn = s1v(f"{pre}数", dept, "目标"); an = s1v(f"{pre}数", dept, "实际"); rn = s1v(f"{pre}数", dept, "达成率")
        tr = s1v(f"{pre}率", dept, "目标"); ar = s1v(f"{pre}率", dept, "实际"); rr = s1v(f"{pre}率", dept, "达成率")
        if (tn or 0) == 0 and (an or 0) == 0 and (tr or 0) == 0 and (ar or 0) == 0:
            continue
        parts.append(f"{sec_name(dept)}的新品{pre}数目标 {intr(tn)} 款，{DATE_TXT}完成 {intr(an)} 款，完成率 {pct(rn)}，"
                     f"{sec_name(dept)}的新品{pre}率目标 {pct(tr)}，{DATE_TXT}，实际{pre}率 {pct(ar)}，完成率 {pct(rr)}")
    if not parts:
        return f"{sec_name(dept)}：当期未设爆款类目标，无数据。"
    return "；".join(parts) + "。"

def cost_line(dept):
    """新品款均成本：目标/实际/高于低于"""
    tgt = s1v("新品款均成本", dept, "目标"); act = s1v("新品款均成本", dept, "实际")
    if tgt is None or act is None:
        return f"{sec_name(dept)}：无新品款均成本数据。"
    d = act - tgt
    word = "高于" if d >= 0 else "低于"
    return (f"{sec_name(dept)} 新品款均成本目标 {money(tgt)}，{DATE_TXT}，实际新品款均成本 {money(act)}，"
            f"{word} {money(abs(d))}。")

def concl_line(idx, big, d1, d2):
    """结论句式（参考）：结论：部门1 10月完成率 X%，部门2 10月完成率 Y%，整体 10月完成率 Z%，整体落后时间进度 W%，请大家重点关注"""
    r1 = s1v(idx, d1, "达成率"); r2 = s1v(idx, d2, "达成率"); rb = s1v(idx, big, "达成率")
    _, dd = tp_diff(rb)
    lag = f"整体落后时间进度 {abs(dd)*100:.2f}%" if dd < 0 else f"整体超时间进度 {dd*100:.2f}%"
    return (f"结论：{sec_name(d1)}{MONTH_TXT}完成率 {pct(r1)}，{sec_name(d2)}{MONTH_TXT}完成率 {pct(r2)}，"
            f"{sec_name(big)}{MONTH_TXT}整体完成率 {pct(rb)}，{lag}，请大家重点关注。")

def concl_bakuo(idx, big, d1, d2):
    """爆款结论（参考指定句式）：达成率+达标状态；无目标的部门标注为无目标而非未达标"""
    parts = []
    for d in (d1, d2):
        r = s1v("爆款率", d, "达成率")
        tgt = s1v("爆款数", d, "目标")
        if (tgt or 0) == 0:
            parts.append(f"{sec_name(d)}当期无爆款类目标")
        else:
            parts.append(f"{sec_name(d)}爆款率达成 {pct(r)}，为{'达标' if (r or 0) >= 1 else '未达标'}状态")
    tail = "，当期暂无跟踪要求。" if all("无爆款类目标" in p for p in parts) else "，请重点关注。"
    return "结论：" + "；".join(parts) + tail

def concl_cost(idx, big, d1, d2):
    """款均成本结论（参考指定句式）：高于/低于目标值"""
    parts = []
    for d in (d1, d2):
        tgt = s1v("新品款均成本", d, "目标"); act = s1v("新品款均成本", d, "实际")
        if tgt is None or act is None:
            continue
        diff = act - tgt
        parts.append(f"{sec_name(d)}{'高于' if diff >= 0 else '低于'}目标值 {money(abs(diff))}")
    return "结论：" + "，".join(parts) + "，请大家重点关注。"

def section_paragraphs(idx, line_fn, concl_idx=None, concl_fn=None):
    """按人工指定顺序产出 12 段（含成衣/泳衣结论段）。line_fn(dept) 生成主体段。"""
    lines = []
    for i, (seq, dept, _) in enumerate(sec_pairs()):
        if dept is None:
            fn = concl_fn or concl_line
            if i == 3:      # 成衣结论
                lines.append(fn(concl_idx or idx, "成衣", "成衣一部", "成衣二部"))
            else:           # 泳衣结论
                lines.append(fn(concl_idx or idx, "泳衣", "泳衣产品部", "泳衣买手部"))
        else:
            body = line_fn(dept)
            lines.append(f"{seq} {body}" if seq else body)
    return lines

# ---- S1 表（评论7：仅保留表2-1，idx 按指定顺序） ----
S1_DEPTS = ["成衣一部", "成衣二部", "品牌设计部", "新渠道产品部", "成衣",
            "泳衣产品部", "泳衣买手部", "泳衣", "内睡", "acc", "塑身衣项目部", "全品类"]
S1_IDX_ORDER = ["GMV", "新品GMV", "上新数", "法国线上新数", "成功数", "爆款数", "大爆款数", "超爆款数",
                "成功率", "爆款率", "大爆款率", "超爆款率", "新品款均成本", "新品款效"]
COUNT_IDX = {"上新数", "大爆款数", "爆款数", "超爆款数", "成功数", "法国线上新数"}

def s1_cell(idx, dept, kind):
    v = s1v(idx, dept, kind)
    if v is None:
        return "-"
    if kind == "达成率":
        return pct(v)
    if idx in COUNT_IDX:
        return f"{v:.0f}"
    return f"{v:,.2f}"

def table_s1():
    """表2-1（评论6）：补全全部部门（12 个，含泳衣/内睡/acc/塑身衣项目部/全品类），idx 顺序按上轮评论指定"""
    depts = S1_DEPTS
    header = ["idx\n（指标）"]
    for d in depts:
        header += [f"{sec_name(d)}\n目标", f"{sec_name(d)}\n实际", f"{sec_name(d)}\n达成率"]
    rows = []
    for idx in S1_IDX_ORDER:
        row = [idx]
        for d in depts:
            row += [s1_cell(idx, d, "目标"), s1_cell(idx, d, "实际"), s1_cell(idx, d, "达成率")]
        rows.append(row)
    return header, rows

# ================= S3：新旧品销售/流量（同比口径） =================
s3 = load("S3_新老品业务部门.csv")

def s3group(rows):
    nr = [r for r in rows if r["是否当月新品"] == "当月新品"]
    orow = [r for r in rows if r["是否当月新品"] == "当月老品"]
    g = {}
    def sub(rs):
        cur_sales = ssum(rs, "本期_销售额")
        pri_sales = sum((prior_of(num(r["本期_销售额"]), num(r["销售额_同比"]))[0] or 0.0) for r in rs)
        cur_uv = ssum(rs, "本期_详情页uv")
        pri_uv = sum((prior_of(num(r["本期_详情页uv"]), num(r["详情页uv_同比"]))[0] or 0.0) for r in rs)
        cur_click = ssum(rs, "本期_商列点击uv")
        pri_click = sum((prior_of(num(r["本期_商列点击uv"]), num(r["商列点击uv_同比"]))[0] or 0.0) for r in rs)
        cur_view = ssum(rs, "本期_商列浏览uv")
        pri_view = sum((prior_of(num(r["本期_商列浏览uv"]), num(r["商列浏览uv_同比"]))[0] or 0.0) for r in rs)
        cur_qty = ssum(rs, "本期_销量")
        pri_qty = sum((prior_of(num(r["本期_销量"]), num(r["销量_同比"]))[0] or 0.0) for r in rs)
        skc = ssum(rs, "本期_在架skc")
        d = dict(
            sales=cur_sales, sales_yoy=rel(cur_sales, pri_sales) if pri_sales else None,
            uv=cur_uv, uv_yoy=rel(cur_uv, pri_uv) if pri_uv else None,
            ctr=(cur_click / cur_view) if cur_view else None,
            ctr_yoy=rel(cur_click / cur_view if cur_view else None, pri_click / pri_view if pri_view else None),
            cvr=(cur_qty / cur_uv) if cur_uv else None,
            cvr_yoy=rel(cur_qty / cur_uv if cur_uv else None, pri_qty / pri_uv if pri_uv else None),
            uvv=(cur_sales / cur_uv) if cur_uv else None,
            uvv_yoy=rel(cur_sales / cur_uv if cur_uv else None, pri_sales / pri_uv if pri_uv else None),
            skc=skc,
        )
        if len(rs) == 1:
            d["skc_yoy"] = num(rs[0]["在架skc_同比"]); d["kx_yoy"] = num(rs[0]["款效_同比"])
            d["kx_val"] = num(rs[0]["本期_款效"])
        else:
            pri_skc = sum((prior_of(num(r["本期_在架skc"]), num(r["在架skc_同比"]))[0] or 0.0) for r in rs)
            d["skc_yoy"] = rel(skc, pri_skc) if pri_skc else None
            d["kx_val"] = (cur_sales / skc) if skc else None
            d["kx_yoy"] = rel(cur_sales / skc if skc else None, pri_sales / pri_skc if pri_skc else None)
        return d
    g["new"] = sub(nr)
    g["old"] = sub(orow)
    tot_sales = g["new"]["sales"] + g["old"]["sales"]
    pri_total = sum((prior_of(num(r["本期_销售额"]), num(r["销售额_同比"]))[0] or 0.0) for r in rows)
    pri_uv_total = sum((prior_of(num(r["本期_详情页uv"]), num(r["详情页uv_同比"]))[0] or 0.0) for r in rows)
    cur_uv_total = ssum(rows, "本期_详情页uv")
    pri_qty_total = sum((prior_of(num(r["本期_销量"]), num(r["销量_同比"]))[0] or 0.0) for r in rows)
    cur_qty_total = ssum(rows, "本期_销量")
    pri_click_total = sum((prior_of(num(r["本期_商列点击uv"]), num(r["商列点击uv_同比"]))[0] or 0.0) for r in rows)
    cur_click_total = ssum(rows, "本期_商列点击uv")
    pri_view_total = sum((prior_of(num(r["本期_商列浏览uv"]), num(r["商列浏览uv_同比"]))[0] or 0.0) for r in rows)
    cur_view_total = ssum(rows, "本期_商列浏览uv")
    g["all"] = dict(
        sales=tot_sales, sales_yoy=rel(tot_sales, pri_total) if pri_total else None,
        uv=cur_uv_total, uv_yoy=rel(cur_uv_total, pri_uv_total) if pri_uv_total else None,
        ctr=(cur_click_total / cur_view_total) if cur_view_total else None,
        ctr_yoy=rel(cur_click_total / cur_view_total if cur_view_total else None,
                    pri_click_total / pri_view_total if pri_view_total else None),
        cvr=(cur_qty_total / cur_uv_total) if cur_uv_total else None,
        cvr_yoy=rel(cur_qty_total / cur_uv_total if cur_uv_total else None,
                    pri_qty_total / pri_uv_total if pri_uv_total else None),
        uvv=(tot_sales / cur_uv_total) if cur_uv_total else None,
        uvv_yoy=rel(tot_sales / cur_uv_total if cur_uv_total else None,
                    pri_total / pri_uv_total if pri_uv_total else None),
    )
    g["new_share"] = g["new"]["sales"] / tot_sales if tot_sales else None
    g["old_share"] = g["old"]["sales"] / tot_sales if tot_sales else None
    return g

S3_GROUPS = []
for big in ["成衣", "泳衣"]:
    S3_GROUPS.append((f"{big}整体", [r for r in s3 if r["大类"] == big]))
for dept in ["成衣一部", "成衣二部", "泳衣买手部", "泳衣产品部"]:
    S3_GROUPS.append((dept, [r for r in s3 if r["业务部门"] == dept]))
G3 = {name: s3group(rows) for name, rows in S3_GROUPS}

def chap3_sales_para(name):
    g = G3[name]
    n, o, a = g["new"], g["old"], g["all"]
    return (f"{name}销售额同比去年 {relf(a['sales_yoy'])}。"
            f"新品销售额同比 {relf(n['sales_yoy'])}（SKC 同比 {relf(n['skc_yoy'])}），"
            f"新品销售额占比 {pct(g['new_share'])}，新品款效 {money(n['kx_val'])}（同比 {relf(n['kx_yoy'])}）；"
            f"老品销售额同比 {relf(o['sales_yoy'])}，老品销售额占比 {pct(g['old_share'])}，老品款效 {money(o['kx_val'])}。")

def chap3_traffic_para(name):
    g = G3[name]
    n, o, a = g["new"], g["old"], g["all"]
    return (f"{name}UV同比去年 {relf(a['uv_yoy'])}，新品UV同比 {relf(n['uv_yoy'])}，老品UV同比 {relf(o['uv_yoy'])}。"
            f"CTR {pct(a['ctr'])}（同比 {relf(a['ctr_yoy'])}），新品CTR同比 {relf(n['ctr_yoy'])}，老品CTR同比 {relf(o['ctr_yoy'])}；"
            f"CVR {pct(a['cvr'])}（同比 {relf(a['cvr_yoy'])}），新品CVR同比 {relf(n['cvr_yoy'])}，老品CVR同比 {relf(o['cvr_yoy'])}；"
            f"UV产出（UV价值）同比 {relf(a['uvv_yoy'])}，新品 {relf(n['uvv_yoy'])}，老品 {relf(o['uvv_yoy'])}。")

# ---- 评论1/3：3.1/3.2 段落顺序：成衣→成衣一部→成衣二部→成衣结论→泳衣→泳衣产品部→泳衣买手部→泳衣结论 ----
# ---- 序号：(1)(2)(3)→无序号→(1)(2)(3)→无序号；结论参考用户给定句式（整体+新品+两部门新品） ----
CHAP3_ORDER = ["成衣整体", "成衣一部", "成衣二部", None,
               "泳衣整体", "泳衣产品部", "泳衣买手部", None]
CHAP3_SEQ = ["(1)", "(2)", "(3)", "", "(1)", "(2)", "(3)", ""]

def _chap3_concl(big, metric, label):
    """结论句式（参考）：{big}整体{label}同比去年 X%，新品{label}同比去年 Y%；部门1新品{label}同比去年 Z%，部门2新品{label}同比去年 W%"""
    d1, d2 = (("成衣一部", "成衣二部") if big == "成衣" else ("泳衣产品部", "泳衣买手部"))
    g = G3[f"{big}整体"]
    return (f"结论：{big}整体{label}同比去年 {relf(g['all'][metric])}，新品{label}同比去年 {relf(g['new'][metric])}；"
            f"{d1}新品{label}同比去年 {relf(G3[d1]['new'][metric])}，{d2}新品{label}同比去年 {relf(G3[d2]['new'][metric])}。")

def chap3_sales_concl(big):
    return _chap3_concl(big, "sales_yoy", "销售额")

def chap3_traffic_concl(big):
    return _chap3_concl(big, "uv_yoy", "UV")

def chap3_paragraphs(para_fn, concl_fn):
    """按评论1/3 顺序产出 3.1/3.2 的 8 段（含成衣/泳衣结论段）"""
    out = []
    for seq, name in zip(CHAP3_SEQ, CHAP3_ORDER):
        if name is None:
            continue
        body = para_fn(name)
        out.append(f"{seq} {body}" if seq else body)
    out.insert(3, concl_fn("成衣"))
    out.insert(7, concl_fn("泳衣"))
    return out

# ---- 合并表（评论1：三合一，参考周报样表格式；数据=S3 明细加总 + S1W 上新数） ----
MERGED_DEPTS = {"成衣": ["成衣一部", "成衣二部"], "泳衣": ["泳衣买手部", "泳衣产品部"]}
# 多行表头（列宽统一 10 半角内，渲染图片时表头不折行）
MERGED_HEADER = ["日期", "业务部门", "是否\n当月新品",
                 "销售额", "销售额\n占比", "总销售额\n环比", "总销售额\n同比",
                 "总销量", "总销量\n环比", "总销量\n同比",
                 "在架skc数", "在架skc\n数环比", "在架skc\n数同比",
                 "上新数", "上新数\n环比", "上新数\n同比",
                 "款效", "款效\n环比", "款效\n同比",
                 "平均售价", "平均售价\n环比", "平均售价\n同比",
                 "详情页UV", "UV\n环比", "UV\n同比",
                 "CTR_UV", "CTR_UV\n环比", "CTR_UV\n同比",
                 "CVR_UV", "CVR_UV\n环比", "CVR_UV\n同比",
                 "UV产出", "UV产出\n环比", "UV产出\n同比"]

def _s_trip(cur, pm, py):
    return {"v": cur, "mom": rel(cur, pm), "yoy": rel(cur, py)}

def _r_trip(c_num, c_den, m_num, m_den, y_num, y_den):
    cur = c_num / c_den if c_den else None
    pm = m_num / m_den if m_den else None
    py = y_num / y_den if y_den else None
    return {"v": cur, "mom": rel(cur, pm), "yoy": rel(cur, py)}

def m_metrics(rows):
    """一组 S3 明细行的全指标汇总（本期/环比/同比；对比期由还原法加总）"""
    def cs(col):
        return ssum(rows, f"本期_{col}")
    def ps(col, cmp):
        return sum((prior_of(num(r[f"本期_{col}"]), num(r[f"{col}_{cmp}"]))[0] or 0.0) for r in rows)
    sales, qty, skc, uv = cs("销售额"), cs("销量"), cs("在架skc"), cs("详情页uv")
    view, click = cs("商列浏览uv"), cs("商列点击uv")
    s_m, s_y = ps("销售额", "环比"), ps("销售额", "同比")
    q_m, q_y = ps("销量", "环比"), ps("销量", "同比")
    k_m, k_y = ps("在架skc", "环比"), ps("在架skc", "同比")
    u_m, u_y = ps("详情页uv", "环比"), ps("详情页uv", "同比")
    v_m, v_y = ps("商列浏览uv", "环比"), ps("商列浏览uv", "同比")
    c_m, c_y = ps("商列点击uv", "环比"), ps("商列点击uv", "同比")
    return dict(
        sales=_s_trip(sales, s_m, s_y), qty=_s_trip(qty, q_m, q_y),
        skc=_s_trip(skc, k_m, k_y), uv=_s_trip(uv, u_m, u_y),
        kx=_r_trip(sales, skc, s_m, k_m, s_y, k_y),
        price=_r_trip(sales, qty, s_m, q_m, s_y, q_y),
        ctr=_r_trip(click, view, c_m, v_m, c_y, v_y),
        cvr=_r_trip(qty, uv, q_m, u_m, q_y, u_y),
        uvv=_r_trip(sales, uv, s_m, u_m, s_y, u_y),
    )

def sx_of(key):
    """上新数（当月上架款数，月度口径与 2.4 一致；环比=上月同期、同比=去年同期，派生查询 S1W）"""
    cur = (WEEK.get("本月累计") or {}).get(key)
    pm = (WEEK.get("上月同期") or {}).get(key)
    py = (WEEK.get("去年同期") or {}).get(key)
    return cur, rel(cur, pm), rel(cur, py)

def merged_table(big):
    """周报样表格式合并表：部门×新品/老品 + 业务部门小计 + 小计 + 月总计（9 行 × 34 列）"""
    depts = MERGED_DEPTS[big]
    rows3 = [r for r in s3 if r["大类"] == big]
    total_sales = ssum(rows3, "本期_销售额")
    out = []
    def emit(label, type_, rs, share_denom, sx_key):
        m = m_metrics(rs)
        share = pct(m["sales"]["v"] / share_denom) if share_denom else "N/A"
        if type_ == "老品" or sx_key is None:
            sx, sxm, sxy = 0, None, None
        else:
            sx, sxm, sxy = sx_of(sx_key)
        out.append([f"{START}~{END}", label, type_,
                    money(m["sales"]["v"]), share, relf(m["sales"]["mom"]), relf(m["sales"]["yoy"]),
                    intr(m["qty"]["v"]), relf(m["qty"]["mom"]), relf(m["qty"]["yoy"]),
                    intr(m["skc"]["v"]), relf(m["skc"]["mom"]), relf(m["skc"]["yoy"]),
                    intr(sx), relf(sxm), relf(sxy),
                    money(m["kx"]["v"]), relf(m["kx"]["mom"]), relf(m["kx"]["yoy"]),
                    money(m["price"]["v"]), relf(m["price"]["mom"]), relf(m["price"]["yoy"]),
                    intr(m["uv"]["v"]), relf(m["uv"]["mom"]), relf(m["uv"]["yoy"]),
                    pct(m["ctr"]["v"]), relf(m["ctr"]["mom"]), relf(m["ctr"]["yoy"]),
                    pct(m["cvr"]["v"]), relf(m["cvr"]["mom"]), relf(m["cvr"]["yoy"]),
                    money(m["uvv"]["v"]), relf(m["uvv"]["mom"]), relf(m["uvv"]["yoy"])])
    for d in depts:
        rs = [r for r in rows3 if r["业务部门"] == d]
        nr = [r for r in rs if r["是否当月新品"] == "当月新品"]
        orow = [r for r in rs if r["是否当月新品"] == "当月老品"]
        d_tot = ssum(rs, "本期_销售额")
        emit(d, "新品", nr, d_tot, d)
        emit(d, "老品", orow, d_tot, None)
        emit(d, "业务部门小计", rs, d_tot, d)
    all_new = [r for r in rows3 if r["是否当月新品"] == "当月新品"]
    all_old = [r for r in rows3 if r["是否当月新品"] == "当月老品"]
    emit("小计", "新品", all_new, total_sales, big)
    emit("小计", "老品", all_old, total_sales, None)
    emit("月总计", "月总计", rows3, total_sales, big)
    return MERGED_HEADER, out

# ================= S2 汇总（第5章整体指标） =================
s2 = load("S2_品类拆解L2.csv")
l3 = load("S2_品类拆解L3.csv")

def overall_metrics(rows):
    cur_sales = ssum(rows, "本期_销售额")
    pri_sales = sum((prior_of(num(r["本期_销售额"]), num(r["销售额_环比"]))[0] or 0.0) for r in rows)
    yoy_sales = sum((prior_of(num(r["本期_销售额"]), num(r["销售额_同比"]))[0] or 0.0) for r in rows)
    cur_view = ssum(rows, "本期_商列浏览uv")
    pri_view = sum((prior_of(num(r["本期_商列浏览uv"]), num(r["商列浏览uv_环比"]))[0] or 0.0) for r in rows)
    cur_click = ssum(rows, "本期_商列点击uv")
    pri_click = sum((prior_of(num(r["本期_商列点击uv"]), num(r["商列点击uv_环比"]))[0] or 0.0) for r in rows)
    cur_cart = ssum(rows, "本期_商列加车uv")
    pri_cart = sum((prior_of(num(r["本期_商列加车uv"]), num(r["商列加车uv_环比"]))[0] or 0.0) for r in rows)
    cur_uv = ssum(rows, "本期_详情页uv")
    pri_uv = sum((prior_of(num(r["本期_详情页uv"]), num(r["详情页uv_环比"]))[0] or 0.0) for r in rows)
    cur_qty = ssum(rows, "本期_销量")
    pri_qty = sum((prior_of(num(r["本期_销量"]), num(r["销量_环比"]))[0] or 0.0) for r in rows)
    cur_ret = ssum(rows, "本期_退货数量")
    cur_dstock = ssum(rows, "本期_日均可售库存")
    pri_dstock = sum((prior_of(num(r["本期_日均可售库存"]), num(r["日均可售库存_环比"]))[0] or 0.0) for r in rows)
    def r_(c, p):
        return rel(c, p) if p else None
    return dict(
        sales=cur_sales, mom=r_(cur_sales, pri_sales), yoy=r_(cur_sales, yoy_sales),
        uv=cur_uv, uv_mom=r_(cur_uv, pri_uv),
        view=cur_view, view_mom=r_(cur_view, pri_view),
        ctr=(cur_click / cur_view) if cur_view else None, ctr_mom=r_(cur_click / cur_view if cur_view else None, pri_click / pri_view if pri_view else None),
        cart=(cur_cart / cur_view) if cur_view else None, cart_mom=r_(cur_cart / cur_view if cur_view else None, pri_cart / pri_view if pri_view else None),
        uvv=(cur_sales / cur_uv) if cur_uv else None, uvv_mom=r_(cur_sales / cur_uv if cur_uv else None, pri_sales / pri_uv if pri_uv else None),
        cvr=(cur_qty / cur_uv) if cur_uv else None, cvr_mom=r_(cur_qty / cur_uv if cur_uv else None, pri_qty / pri_uv if pri_uv else None),
        qty=cur_qty, qty_mom=r_(cur_qty, pri_qty),
        ret=(cur_ret / cur_qty) if cur_qty else None,
        dstock=cur_dstock, dstock_mom=r_(cur_dstock, pri_dstock),
    )

OM = overall_metrics(s2)
OM_SWIM = overall_metrics([r for r in s2 if r["big_category"] == "泳衣"])
OM_KNIT = overall_metrics([r for r in s2 if r["second_category"] == "针织服装"])

# 关键品类数值（第5/6章引用，避免手写数字）
KNIT = OM_KNIT
SWIM_SALES_MOM = OM_SWIM["mom"]
TOT_SALES = OM["sales"]
NEW_SALES = 466658.79          # 当月新品窗口销售额（明细加总，原报告口径）
NEW_SHARE = 0.1013             # 10.13%
GMV_RATE = s1v("GMV", "全品类", "达成率")
GMV_TGT = s1v("GMV", "全品类", "目标")
_, GMV_GAP = gap_of(GMV_RATE, GMV_TGT)

# ================= 品类聚合（第4章品类拆解：大类/L2/L3 + 日趋势 + 三因子） =================
s2_no = [r for r in s2 if r["是否当月新品"] in ("当月新品", "当月老品")]   # 未上架款无销售，不纳入
l3_no = [r for r in l3 if r["是否当月新品"] in ("当月新品", "当月老品")]
BIG_OF_SEC = {r["second_category"]: r["big_category"] for r in s2_no}
SEC_OF_THD = {r["third_category"]: r["second_category"] for r in l3_no}

def cat_agg(rows):
    """销售额三件套：本期、环比期还原值、环比率"""
    cur = ssum(rows, "本期_销售额")
    mom0 = sum((prior_of(num(r["本期_销售额"]), num(r["销售额_环比"]))[0] or 0.0) for r in rows)
    return cur, mom0, rel(cur, mom0)

def group_agg(rows, key):
    return {k: cat_agg([r for r in rows if r[key] == k]) for k in {r[key] for r in rows}}

AGG_BIG = group_agg(s2_no, "big_category")
AGG_SEC = dict(sorted(group_agg(s2_no, "second_category").items(), key=lambda kv: -kv[1][0]))
AGG_THD = group_agg(l3_no, "third_category")
TOT_CAT = sum(v[0] for v in AGG_BIG.values())
TOT_PRI = sum(v[1] for v in AGG_BIG.values())
BIG_NAMES = [b for b, _ in sorted(AGG_BIG.items(), key=lambda kv: -kv[1][0])]

def yoy_rate(rows):
    cur = ssum(rows, "本期_销售额")
    yoy0 = sum((prior_of(num(r["本期_销售额"]), num(r["销售额_同比"]))[0] or 0.0) for r in rows)
    return rel(cur, yoy0)

BIG_YOY = {b: yoy_rate([r for r in s2_no if r["big_category"] == b]) for b in AGG_BIG}

SEC_TOP12 = list(AGG_SEC.items())[:12]
THD_DELTA = sorted(((t, v[0] - v[1]) for t, v in AGG_THD.items()), key=lambda kv: -kv[1])
THD_UP8 = [kv for kv in THD_DELTA if kv[1] > 0][:8]
THD_DOWN8 = [kv for kv in THD_DELTA if kv[1] < 0][-8:][::-1]     # 缺口最大在前
KNIT3 = [(t, AGG_THD[t][0] - AGG_THD[t][1]) for t in ("毛衣", "毛衣裙", "毛衣裤") if t in AGG_THD]
DOWN5 = THD_DOWN8[:5]

def sec_share(name):
    """品类占比：本期/环比期（二级品类优先，否则按大类）"""
    v = AGG_SEC.get(name) or AGG_BIG[name]
    return v[0] / TOT_CAT, v[1] / TOT_PRI

def sec_mom(name):
    """品类环比（二级品类优先，否则按大类）"""
    return (AGG_SEC.get(name) or AGG_BIG[name])[2]

# 日趋势（S2D 派生查询：本期 vs 环比期，按日粒度）
daily = load("S2D_品类日趋势.csv")
DAYS_CUR = sorted({r["date_str"] for r in daily if r["date_type"] == "本期"})
DAYS_PRI = sorted({r["date_str"] for r in daily if r["date_type"] == "环比上一周期"})

def day_total(dates, dtype):
    return [sum((num(r["销售额"]) or 0.0) for r in daily
                if r["date_str"] == dt and r["date_type"] == dtype) for dt in dates]

SER_CUR = day_total(DAYS_CUR, "本期")
SER_PRI = day_total(DAYS_PRI, "环比上一周期")
AVG_CUR = sum(SER_CUR) / len(SER_CUR)
AVG_PRI = sum(SER_PRI) / len(SER_PRI)
MAX_CUR = max(SER_CUR)
MAX_CUR_D = DAYS_CUR[SER_CUR.index(MAX_CUR)]

# 三因子分解（销售额 = UV × CVR × 价格，序贯替代 UV→CVR→价格）
def factor3(rows):
    cur_uv = ssum(rows, "本期_详情页uv")
    pri_uv = sum((prior_of(num(r["本期_详情页uv"]), num(r["详情页uv_环比"]))[0] or 0.0) for r in rows)
    cur_q = ssum(rows, "本期_销量")
    pri_q = sum((prior_of(num(r["本期_销量"]), num(r["销量_环比"]))[0] or 0.0) for r in rows)
    cur_s = ssum(rows, "本期_销售额")
    pri_s = sum((prior_of(num(r["本期_销售额"]), num(r["销售额_环比"]))[0] or 0.0) for r in rows)
    if not pri_uv or not pri_q or not pri_s:
        return None
    cvr0, cvr1 = pri_q / pri_uv, (cur_q / cur_uv if cur_uv else 0.0)
    p0, p1 = pri_s / pri_q, (cur_s / cur_q if cur_q else 0.0)
    return ((cur_uv - pri_uv) * cvr0 * p0,
            cur_uv * (cvr1 - cvr0) * p0,
            cur_uv * cvr1 * (p1 - p0),
            cur_s - pri_s)

FAC_BIG = {b: factor3([r for r in s2_no if r["big_category"] == b]) for b in AGG_BIG}

# ================= 图表 =================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
C_NEW, C_OLD = "#0072B2", "#E69F00"

def chart5():
    names = [n for n, _ in S3_GROUPS]
    new_yoy = [G3[n]["new"]["sales_yoy"] or 0 for n in names]
    old_yoy = [G3[n]["old"]["sales_yoy"] or 0 for n in names]
    x = range(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.bar([i - w/2 for i in x], [v*100 for v in new_yoy], w, label="当月新品", color=C_NEW)
    ax.bar([i + w/2 for i in x], [v*100 for v in old_yoy], w, label="当月老品", color=C_OLD)
    for i, (a, b) in enumerate(zip(new_yoy, old_yoy)):
        ax.text(i - w/2, a*100, f"{a*100:.0f}%", ha="center", va="bottom" if a >= 0 else "top", fontsize=8)
        ax.text(i + w/2, b*100, f"{b*100:.0f}%", ha="center", va="bottom" if b >= 0 else "top", fontsize=8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(list(x)); ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("销售额同比 (%)")
    ax.set_title("各分组：当月新品 / 老品销售额同比")
    ax.legend()
    fig.tight_layout()
    p = os.path.join(CHARTS, "chart5_newold_sales_yoy.png")
    fig.savefig(p); plt.close(fig)
    return p

def chart6():
    names = [n for n, _ in S3_GROUPS]
    new_uv = [G3[n]["new"]["uv_yoy"] or 0 for n in names]
    old_uv = [G3[n]["old"]["uv_yoy"] or 0 for n in names]
    x = range(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.bar([i - w/2 for i in x], [v*100 for v in new_uv], w, label="当月新品UV", color=C_NEW)
    ax.bar([i + w/2 for i in x], [v*100 for v in old_uv], w, label="当月老品UV", color=C_OLD)
    for i, (a, b) in enumerate(zip(new_uv, old_uv)):
        ax.text(i - w/2, a*100, f"{a*100:.0f}%", ha="center", va="bottom" if a >= 0 else "top", fontsize=8)
        ax.text(i + w/2, b*100, f"{b*100:.0f}%", ha="center", va="bottom" if b >= 0 else "top", fontsize=8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(list(x)); ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("详情页UV同比 (%)")
    ax.set_title("各分组：当月新品 / 老品详情页UV同比")
    ax.legend()
    fig.tight_layout()
    p = os.path.join(CHARTS, "chart6_newold_uv_yoy.png")
    fig.savefig(p); plt.close(fig)
    return p

CH5 = chart5()
CH6 = chart6()

# ---- 第4章品类拆解图表（评论7：品类分析并入文档，matplotlib 静态渲染） ----
C_POS, C_NEG, C_BLUE, C_ORANGE, C_GRAY = "#27ae60", "#e74c3c", "#3498db", "#f39c12", "#95a5a6"

def chart4_1():
    """大类销售额占比（环形图）"""
    vals = [AGG_BIG[b][0] / 10000 for b in BIG_NAMES]
    colors = ["#3498db", "#e74c3c", "#f39c12", "#9b59b6", "#27ae60", "#95a5a6"][:len(BIG_NAMES)]
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)
    _, _, autot = ax.pie(vals, labels=BIG_NAMES, colors=colors, autopct="%1.1f%%",
                         startangle=90, counterclock=False,
                         wedgeprops=dict(width=0.42, edgecolor="white"), pctdistance=0.78)
    for t in autot:
        t.set_color("white"); t.set_fontsize(9)
    ax.set_title(f"大类销售额占比（合计 {wan(TOT_CAT)}）")
    fig.tight_layout()
    p = os.path.join(CHARTS, "chart4_1_big_share.png")
    fig.savefig(p); plt.close(fig)
    return p

def chart4_2():
    """大类销售额环比 / 同比（分组柱状）"""
    moms = [(AGG_BIG[b][2] or 0) * 100 for b in BIG_NAMES]
    yoys = [(BIG_YOY[b] or 0) * 100 for b in BIG_NAMES]
    x = range(len(BIG_NAMES)); w = 0.38
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.bar([i - w / 2 for i in x], moms, w, label="环比", color=C_BLUE)
    ax.bar([i + w / 2 for i in x], yoys, w, label="同比", color="#9b59b6")
    for i, (a, b) in enumerate(zip(moms, yoys)):
        ax.text(i - w / 2, a, f"{a:.0f}%", ha="center", va="bottom" if a >= 0 else "top", fontsize=8)
        ax.text(i + w / 2, b, f"{b:.0f}%", ha="center", va="bottom" if b >= 0 else "top", fontsize=8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(list(x)); ax.set_xticklabels(BIG_NAMES, fontsize=9)
    ax.set_ylabel("销售额增速 (%)")
    ax.set_title("大类销售额环比 / 同比")
    ax.legend()
    fig.tight_layout()
    p = os.path.join(CHARTS, "chart4_2_big_mom_yoy.png")
    fig.savefig(p); plt.close(fig)
    return p

def _hbar(names, vals, colors, title, xlabel, path):
    """通用水平柱状图（数值标注在柱端）"""
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(names) + 1.8), dpi=150)
    y = list(range(len(names)))
    ax.barh(y, vals, 0.62, color=colors)
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v:,.1f}", ha="left" if v >= 0 else "right", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.margins(x=0.2)
    fig.tight_layout()
    fig.savefig(path); plt.close(fig)
    return path

def chart4_3():
    """二级品类销售额 Top12（水平柱状，环比着色）"""
    names = [f"{s}（{relf(v[2])}）" for s, v in SEC_TOP12][::-1]
    vals = [v[0] / 10000 for _, v in SEC_TOP12][::-1]
    colors = [C_BLUE if (v[2] or 0) >= 0 else C_NEG for _, v in SEC_TOP12][::-1]
    return _hbar(names, vals, colors, "二级品类销售额 Top12（万元，括号内为环比）", "万元",
                 os.path.join(CHARTS, "chart4_3_l2_top12.png"))

def chart4_4():
    """三级品类环比增量 Top8"""
    names = [f"{t}（{SEC_OF_THD.get(t, '')}）" for t, _ in THD_UP8][::-1]
    vals = [d / 10000 for _, d in THD_UP8][::-1]
    return _hbar(names, vals, [C_POS] * len(vals), "三级品类环比增量 Top8（万元）", "环比增量（万元）",
                 os.path.join(CHARTS, "chart4_4_l3_up8.png"))

def chart4_5():
    """三级品类环比缩减 Top8"""
    names = [f"{t}（{SEC_OF_THD.get(t, '')}）" for t, _ in THD_DOWN8][::-1]
    vals = [d / 10000 for _, d in THD_DOWN8][::-1]
    return _hbar(names, vals, [C_NEG] * len(vals), "三级品类环比缩减 Top8（万元）", "环比增量（万元）",
                 os.path.join(CHARTS, "chart4_5_l3_down8.png"))

def chart4_6():
    """全品类日销售额：本期 vs 环比期（折线）"""
    xs = list(range(1, len(DAYS_CUR) + 1))
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.plot(xs, [v / 10000 for v in SER_PRI], "-o", ms=3, color=C_BLUE, label="环比期(09-01~09-20)")
    ax.plot(xs, [v / 10000 for v in SER_CUR], "-o", ms=3, color=C_NEG, label="本期(10-01~10-20)")
    ax.set_xticks(xs); ax.set_xticklabels([d[5:] for d in DAYS_CUR], fontsize=8)
    ax.set_xlabel("日期（月-日）")
    ax.set_ylabel("日销售额（万元）")
    ax.set_title("全品类日销售额：本期 vs 环比期")
    ax.legend()
    fig.tight_layout()
    p = os.path.join(CHARTS, "chart4_6_daily.png")
    fig.savefig(p); plt.close(fig)
    return p

def chart4_7():
    """增长-份额矩阵：二级品类散点（x=销售额占比，y=环比）"""
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=150)
    for s, v in AGG_SEC.items():
        if not v[0] or v[2] is None:
            continue
        x, y = v[0] / TOT_CAT * 100, v[2] * 100
        ax.scatter(x, y, s=52, color=C_BLUE, alpha=0.75, edgecolor="white", lw=0.6, zorder=3)
        if x >= 3 or abs(y) >= 30:      # 只标注主要品类，避免遮挡
            ax.annotate(s, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("销售额占比 (%)")
    ax.set_ylabel("环比 (%)")
    ax.set_title("增长-份额矩阵：二级品类（x=销售额占比，y=环比）")
    fig.tight_layout()
    p = os.path.join(CHARTS, "chart4_7_matrix.png")
    fig.savefig(p); plt.close(fig)
    return p

def chart5_f():
    """销售额环比变化三因子分解（按大类，分组柱状）"""
    bigs = [b for b in BIG_NAMES if FAC_BIG.get(b)]
    x = range(len(bigs)); w = 0.2
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    for k, (lab, idx, c) in enumerate([("流量(UV)贡献", 0, C_NEG), ("转化(CVR)贡献", 1, C_POS),
                                       ("价格贡献", 2, C_ORANGE), ("销售额变化", 3, C_GRAY)]):
        vals = [FAC_BIG[b][idx] / 10000 for b in bigs]
        ax.bar([i + (k - 1.5) * w for i in x], vals, w, label=lab, color=c)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(list(x)); ax.set_xticklabels(bigs, fontsize=9)
    ax.set_ylabel("对环比变化的贡献（万元）")
    ax.set_title("销售额环比变化三因子分解（按大类，序贯替代 UV→CVR→价格）")
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = os.path.join(CHARTS, "chart5_factor.png")
    fig.savefig(p); plt.close(fig)
    return p

# ================= 表格渲染为图片（评论6/8/11：原生表格卡顿，全部转图片） =================
def _disp_w(s):
    """显示宽度：中文等全角字符计 2，半角计 1"""
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in str(s))

def wrap_txt(s, width):
    """按显示宽度换行：优先在空格处断词，单词超宽时硬切；保留已有换行符"""
    lines = []
    for para in str(s).split("\n"):
        cur, cw = "", 0
        for wd in para.split(" "):
            ww = _disp_w(wd)
            add = (1 if cur else 0) + ww
            if cur and cw + add > width:
                lines.append(cur); cur, cw = wd, ww
            else:
                cur = (cur + " " + wd) if cur else wd
                cw += add
            while cw > width:                      # 单词超宽，硬切
                i, hw = 0, 0
                for i, ch in enumerate(cur):
                    hw += 2 if ord(ch) > 0x2E7F else 1
                    if hw > width:
                        break
                lines.append(cur[:i] if i else cur[0])
                cur = cur[i:] if i else cur[1:]
                cw = _disp_w(cur)
        if cur:
            lines.append(cur)
    return "\n".join(lines)

def render_table_image(header, rows, path, col_ws=None, fs=7.0,
                       header_bg="#1F4E79", zebra="#F2F6FB", emph_rows=(), emph_bg="#FFF3D6"):
    """表格渲染为图片：col_ws 为每列内容显示宽度（半角字符，不含留白）；
    emph_rows 为强调行号（小计/总计），行内加粗+浅黄底。返回图片路径。"""
    ncol = len(header)
    if col_ws is None:
        col_ws = [max([_disp_w(str(header[j]))] + [_disp_w(str(r[j])) for r in rows]) for j in range(ncol)]
    hdr_cells = [wrap_txt(h, max(2, col_ws[j] - 1)) for j, h in enumerate(header)]
    body_cells = [[wrap_txt(c, max(2, col_ws[j] - 1)) for j, c in enumerate(r)] for r in rows]
    hdr_lines = max(len(h.split("\n")) for h in hdr_cells)
    row_lines = [max((len(c.split("\n")) for c in r), default=1) for r in body_cells]
    char_w = fs * 0.62 / 72.0                      # 每半角字符宽（inch，YaHei 近似）
    PAD_C = 2                                      # 单元格左右留白（半角字符）
    col_in = [(w + PAD_C) * char_w for w in col_ws]
    line_h = fs * 1.55 / 72.0                      # 单行文本高（含行距）
    pad_v = fs * 0.75 / 72.0                       # 单元格上下留白
    hdr_h = hdr_lines * line_h + 2 * pad_v
    row_h = [n * line_h + 2 * pad_v for n in row_lines]
    W, H = sum(col_in), hdr_h + sum(row_h)
    fig = plt.figure(figsize=(W + 0.04, H + 0.04), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    xs = [0.0]
    for w in col_in:
        xs.append(xs[-1] + w)
    ys = [H]
    ys.append(ys[-1] - hdr_h)
    for h in row_h:
        ys.append(ys[-1] - h)
    for j in range(ncol):
        ax.add_patch(plt.Rectangle((xs[j], ys[1]), col_in[j], hdr_h, facecolor=header_bg, edgecolor="#B7BFCC", lw=0.6))
        ax.text(xs[j] + col_in[j] / 2, ys[1] + hdr_h / 2, hdr_cells[j], ha="center", va="center",
                fontsize=fs, color="white", weight="bold", linespacing=1.5)
    for i, r in enumerate(body_cells):
        emph = i in emph_rows
        bg = emph_bg if emph else (zebra if i % 2 == 1 else "white")
        for j in range(ncol):
            ax.add_patch(plt.Rectangle((xs[j], ys[i + 2]), col_in[j], row_h[i], facecolor=bg, edgecolor="#B7BFCC", lw=0.6))
            ax.text(xs[j] + col_in[j] / 2, ys[i + 2] + row_h[i] / 2, r[j], ha="center", va="center",
                    fontsize=fs, color="#1F1F1F", weight="bold" if emph else "normal", linespacing=1.5)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    return path

# ================= 组装报告内容序列 =================
CONTENT = []
def h2(s): CONTENT.append({"kind": "h2", "text": s})
def h3(s): CONTENT.append({"kind": "h3", "text": s})
def text(s): CONTENT.append({"kind": "text", "text": s})
def table(header, rows, note=None):
    CONTENT.append({"kind": "table", "header": header, "rows": rows, "note": note})
def image(path, caption):
    CONTENT.append({"kind": "image", "path": path, "caption": caption})
def link(url, desc):
    CONTENT.append({"kind": "link", "url": url, "text": desc})

# ================= 第6章策略数据（策略总结模块与第6章共用） =================
strategy_header = ["优先级", "策略", "作用对象", "依据（第4/5章结论+数字）", "预估收益口径", "预估收益（区间）", "前置条件/风险"]
strategy_rows = [
    ["P0", "泳衣流量恢复专项：比基尼套装、连体泳衣主推款恢复站内外投放与活动坑位", "泳衣（比基尼套装、连体泳衣）",
     f"4.2：比基尼套装、连体泳衣为最大两个缩减项（合计缺口约70.00万美元）；5.3：泳衣UV {relf(OM_SWIM['uv_mom'])}、CVR为大类最低",
     f"泳衣详情页UV恢复至环比期水平（约307.10万，本期196.20万）的增量=(环比期UV-本期UV)×本期CVR {pct(OM_SWIM['cvr'])}×本期平均价34.57美元",
     "低档约49.32万美元 / 中档约98.63万美元（中档=全额，低档=50%）",
     "10月起北半球泳装进入淡季，流量恢复受季节制约；投放ROI需先小规模验证"],
    ["P0", "针织服装乘势扩量：毛衣、毛衣裙、毛衣裤追加备货与商列坑位倾斜", "成衣/针织服装",
     f"4.1：针织服装占比提升 9.6%、环比 {relf(KNIT['mom'])}，毛衣/毛衣裙/毛衣裤合计增量约31.70万美元；CVR 3.73%高于整体3.02%",
     f"增量销售额=当期针织服装销售额 {wan(KNIT['sales'])}×增幅假设10%（低）/20%（中）",
     "低档约10.67万美元 / 中档约21.34万美元",
     "备货与物流周期；11月竞品促销可能挤压增幅"],
    ["P1", "成衣二部新品提质：收缩低效铺货，资源集中到主推款", "成衣二部/当月新品",
     "5.3：新品在架SKC +152.94%但UV -50.28%、款效 -65.87%、销售额 -29.27%；2.2：新品GMV达成率21.18%",
     "止损性质：收益体现为低效款退出后流量与坑位的机会成本释放，无可靠的线性外推口径（需款级 SKC×UV×CVR 数据定位低效款后方可量化），故不给出估算区间",
     "不适用（见口径说明）",
     "需款级数据定位低效SKC后再收缩"],
    ["P1", "11月有效上新与打爆计划：提高新品承接与主推资源", "全品类新品（重点：泳衣产品部、成衣二部）",
     "5.1/5.2：当月新品占比10.13%（下降 5.5%）、新品销售额环比 -44.62%；新品GMV达成28.62%、成功率达成54.22%、大爆款1/7",
     f"新品占比恢复至环比期15.66%的增量=窗口销售额 {wan(TOT_SALES)}×(15.66%-10.13%)，按恢复程度50%（低）/100%（中）估算",
     "低档约12.72万美元 / 中档约25.43万美元",
     "打爆依赖库存深度与投放预算，需与备货计划联动"],
    ["P2", "保持退货/退件改善成果：尺码指引、评论与买家秀持续运营", "全品类",
     "5.3：退件率6.97%（环比期25.32%）、退货率6.56%（环比期24.03%）",
     f"守住已改善约18%的退件率：若回升5%（保守情景），净销售额回吐≈窗口销售额 {wan(TOT_SALES)}×5%，按守住一半/全部计",
     "低档约11.50万美元 / 中档约23.01万美元（避免的回吐）",
     "属持续运营项，中断后易反弹"],
]

# ---- 策略总结模块已删除（评论3/4/5：与第6章重复，保留第6章一份）；分市场建议已删除（评论8） ----

# ---- 第 1 章 ----
h2("1. 分析说明")
text(f"时间窗：{START} ~ {END}（{DATE_TXT}，{_M} 月时间进度 {TP_TXT}）。")
text(f"双口径声明：第 2 章目标达成为 {_Y}-{_M:02d} 月度口径（当月 1 日起累计，以「时间进度」为进度基准）；{CH_RANGE}为窗口口径（{START}~{END}），环比={PM_RANGE}（起止各回拨 1 个月），同比={PY_RANGE}（起止各回拨 1 年）。第 3 章对照《经营情况模板》采用同比口径。")
text("数据范围：线上在架商品（在线调整口径），排除赠品与无库存测试款；目标为「正常目标」类型；金额单位为美元（USD），段落中万元=美元/10000。")
text(f"汇总口径：整体/大类/品类/新老品汇总均由明细行加总；对比期原始值由「本期值 ÷ (1+增长率)」还原，增长率缺失或 ≤ -100% 的行按对比期=0 处理（销售额口径涉及 4/52 行，影响可忽略）。{"第 4 章全量明细（二级品类 70 行 × 115 列、三级品类 242 行 × 116 列，含全部指标的本期/环比/同比/占比）收录于随附电子表格，行已按维度排序。" if HAS_ATTR else ""}")

# ---- 第 2 章 ----
h2("2. 目标达成总览")
h3("2.1 整体GMV")
for ln in section_paragraphs("GMV", lambda d: gmv_line("GMV", d)):
    text(ln)
h3("2.2 新品GMV")
for ln in section_paragraphs("新品GMV", newgmv_line):
    text(ln)
h3("2.3 新品款效")
for ln in section_paragraphs("新品款效", kuanxiao_line):
    text(ln)
h3("2.4 新品上新数")
for ln in section_paragraphs("上新数", shangxin_line):
    text(ln)
h3("2.5 成功数与成功率")
for ln in section_paragraphs("成功数", success_line):
    text(ln)
h3("2.6 爆款数与爆款率")
for ln in section_paragraphs("爆款数", bakuo_line, concl_fn=concl_bakuo):
    text(ln)
h3("2.7 新品款均成本")
for ln in section_paragraphs("新品款均成本", cost_line, concl_fn=concl_cost):
    text(ln)
h3("2.8 目标达成全指标表")
# 表2-1 转图片（评论6：补全全部部门；原生表格卡顿）
tH21, tR21 = table_s1()
COLW_21 = [12] + [13] * (len(tH21) - 1)
render_table_image(tH21, tR21, os.path.join(CHARTS, "table_2_1.png"), col_ws=COLW_21, fs=7.0)
text("表2-1 目标达成情况数据")
image(os.path.join(CHARTS, "table_2_1.png"), None)

# ---- 第 3 章 ----
h2("3. 新老品与业务部门结构")
h3("3.1 新旧品销售分析")
for ln in chap3_paragraphs(chap3_sales_para, chap3_sales_concl):
    text(ln)
image(CH5, "图3-1 各分组当月新品/老品销售额同比")
h3("3.2 新旧品流量分析")
for ln in chap3_paragraphs(chap3_traffic_para, chap3_traffic_concl):
    text(ln)
image(CH6, "图3-2 各分组当月新品/老品详情页UV同比")
# 合并表转图片（评论8：做成图片放对应标题下）
COLW_M = [16, 12, 10] + [13] * 31
EMPH_M = {2, 5, 6, 7, 8}          # 业务部门小计/小计/月总计行强调
mH_c, mR_c = merged_table("成衣")
render_table_image(mH_c, mR_c, os.path.join(CHARTS, "table_3_1.png"), col_ws=COLW_M, fs=7.0, emph_rows=EMPH_M)
text("表3-1 当月新老品销售分析——成衣")
image(os.path.join(CHARTS, "table_3_1.png"), None)
mH_s, mR_s = merged_table("泳衣")
render_table_image(mH_s, mR_s, os.path.join(CHARTS, "table_3_2.png"), col_ws=COLW_M, fs=7.0, emph_rows=EMPH_M)
text("表3-2 当月新老品销售分析——泳衣")
image(os.path.join(CHARTS, "table_3_2.png"), None)
h3("3.3 新老品结构与目标达成结合")
text("新老品结构：当期新品销售额 46.67万元（占比 10.13%），老品 413.49万元（占比 89.87%）。环比看，新品占比下降 5.5%，老品占比上升 5.5%。")
text("分业务部门：泳衣买手部新品占比最高（23.66%），泳衣产品部老品依赖度最高（老品占比 90.94%）。")
text("与目标达成结合：达成落后的部门中，成衣二部（新品GMV达成率 21.18%）表现为新品不足——当月新品销售额环比 -29.27%、款效环比 -65.87%；泳衣产品部（GMV达成率 32.78%）表现为老品下滑——老品销售额环比 -28.64%，且新品占比仅 9.06%。")

# ---- 第 4 章（品类分析并入：纯品类维度；部门及部门×品类归第5章） ----
h2("4. 品类拆解")
h3("4.1 品类结构总览")
text(f"窗口销售额 {wan(TOT_CAT)}，环比 {relf(OM['mom'])}、同比 {relf(OM['yoy'])}。最大正贡献：针织服装环比 {relf(OM_KNIT['mom'])}，占比由 {pct(sec_share('针织服装')[1])} 升至 {pct(sec_share('针织服装')[0])}，其中{'、'.join(f'{t}（{d/10000:+,.2f}万元）' for t, d in KNIT3)}合计增量约 {wan(sum(d for _, d in KNIT3))}。")
text(f"最大负贡献：泳衣环比 {relf(OM_SWIM['mom'])}，占比由 {pct(sec_share('泳衣')[1])} 降至 {pct(sec_share('泳衣')[0])}，比基尼套装与连体泳衣为最大两个拖累项（详见 4.2）。")
text(f"品类结构迁移明显：针织服装占比由 {pct(sec_share('针织服装')[1])} 升至 {pct(sec_share('针织服装')[0])}，泳衣由 {pct(sec_share('泳衣')[1])} 降至 {pct(sec_share('泳衣')[0])}，连衣裙持平（{pct(sec_share('连衣裙')[1])}→{pct(sec_share('连衣裙')[0])}）。秋冬季品类对夏季品类形成整体替代，是本窗口结构变化的主线。")
image(chart4_1(), "图4-1 大类销售额占比")
image(chart4_2(), "图4-2 大类销售额环比 / 同比")
h3("4.2 品类下钻（L2 → L3）")
text(f"二级品类 Top12 中针织服装为唯一大幅正增长项（{relf(AGG_SEC['针织服装'][2])}）；泳衣、连衣裙、罩衫为最大三个缩减项。")
text(f"三级品类环比增量前三位：{'、'.join(f'{t}（{d/10000:+,.2f}万元）' for t, d in THD_UP8[:3])}；缩减前五位：{'、'.join(f'{t}（{d/10000:,.2f}万元）' for t, d in DOWN5)}，合计缺口 {wan(abs(sum(d for _, d in DOWN5)))}，全部来自泳衣与度假场景品类，季节切换是共同背景。")
image(chart4_3(), "图4-3 二级品类销售额 Top12（万元）")
image(chart4_4(), "图4-4 三级品类环比增量 Top8（万元）")
image(chart4_5(), "图4-5 三级品类环比缩减 Top8（万元）")
h3("4.3 品类按日趋势")
text(f"本期日均销售额 {wan(AVG_CUR)}，环比期日均 {wan(AVG_PRI)}（{relf(rel(AVG_CUR, AVG_PRI))}）；单日峰值 {wan(MAX_CUR)}（{MAX_CUR_D}）。")
image(chart4_6(), "图4-6 全品类日销售额：本期 vs 环比期")
h3("4.4 增长-份额矩阵")
text(f"横轴=销售额占比、纵轴=环比增速：针织服装（占比 {pct(sec_share('针织服装')[0])}、环比 {relf(sec_mom('针织服装'))}）为唯一「高份额高增长」明星品类；泳衣（占比 {pct(sec_share('泳衣')[0])}、环比 {relf(sec_mom('泳衣'))}）为最大「高份额负增长」风险项；连衣裙占比稳定（{pct(sec_share('连衣裙')[1])}→{pct(sec_share('连衣裙')[0])}，环比 {relf(sec_mom('连衣裙'))}），为体量压舱石。")
image(chart4_7(), "图4-7 增长-份额矩阵：二级品类")
text("查询返回的全部数据收录于随附电子表格《品类拆解全量明细》，包含：二级品类明细（70 行 × 115 列）与三级品类明细（242 行 × 116 列），涵盖在架/销售/退货/商列流量/详情页流量/价格/款效/CTR/CVR/UV价值/加车率/库存/成功款与爆款占比等指标的本期值、环比、同比、占比差，行列已按维度排序（大类→二级品类→三级品类→新老品），未拆表、未省略任何字段。")
text("说明：因飞书文档原生表格存在列数与单元格数量上限（约 100 列/表），全量明细以电子表格承载，点击下方链接查看。")
link("{{SHEET_L2_URL}}", "品类拆解全量明细（电子表格）：二级品类明细（70 行 × 115 列）/ 三级品类明细（242 行 × 116 列）")

# ---- 第 5 章（侧重部门及部门×品类；品类维度分析归第4章） ----
h2("5. 业绩原因分析")
h3("5.1 总览结论")
text(f"整体承压：窗口销售额 {wan(TOT_SALES)}，环比 {relf(OM['mom'])}，同比 {relf(OM['yoy'])}；GMV 达成率 {pct(GMV_RATE)}，落后时间进度 {(TP-GMV_RATE)*100:.2f}%，差额 {wan(GMV_GAP)}（见表2-1）。")
text(f"品类维度：最大正贡献为针织服装（环比 {relf(OM_KNIT['mom'])}），最大拖累为泳衣（环比 {relf(OM_SWIM['mom'])}），品类结构、下钻与趋势分析详见第 4 章。")
text(f"流量收缩、转化对冲：详情页UV环比 {relf(OM['uv_mom'])}，但 CVR 提升至 {pct(OM['cvr'])}（环比期 2.60%）；退件率 {pct(OM['ret'])}（环比期 25.32%）大幅改善。")
text("新品失速：当月新品销售额环比 -44.62%、占比降至 10.13%（下降 5.5%）；新品GMV达成率仅 28.62%，大爆款数 1/7（表2-1、表3-1/3-2）。")
h3("5.2 部门与新老品结构")
text("新老品：老品销售额环比 -8.7%，新品 -44.62%，下滑主因是新品断档而非老盘崩塌；当年新品占比 71.1%（环比 +0.3%）基本持平，说明全年新品盘稳定，弱在当月上新节奏与新品承接。")
text("部门层面：成衣一部老品 +15.32% 为表3-1/表3-2 中唯一环比正增长行（CVR 5.63%，环比 +8.2%）；泳衣产品部老品 -28.64% 与成衣二部新品 -29.27% 是两大失血点（表3-1/表3-2）。")
text("对照目标：上新数达成 78.44%（超时间进度 13.92%）、新品款均成本达成 100.80% 均属正常，但成功率达成 54.22%、大爆款率达成 18.86%、新品款效达成 36.51%——未达标主因是打爆效率与大盘流量，而非上新数量或成本（表2-1）。")
h3("5.3 效率因素（价、量、转化、流量、库存、退货）")
text(f"销售额 = 流量 × 转化 × 价格 分解：详情页UV {relf(OM['uv_mom'])}、CVR {relf(OM['cvr_mom'])}、平均价 -0.4%，三因子连乘约 -14.3%，与实际一致——下滑几乎全部来自流量收缩，转化是主要对冲项；商列浏览UV {relf(OM['view_mom'])}，流量收缩在曝光端已先行发生（按大类分解见图5-4）。")
text(f"转化链路全指标：CTR {pct(OM['ctr'])}（环比 {relf(OM['ctr_mom'])}）、商列加车率 {pct(OM['cart'])}（环比 {relf(OM['cart_mom'])}）、CVR {pct(OM['cvr'])}（环比 {relf(OM['cvr_mom'])}）、UV价值 {money(OM['uvv'])}（环比 {relf(OM['uvv_mom'])}）——曝光→点击→加车→成交的效率全线改善，进一步印证「量跌质升」。")
text(f"库存与供给：整体日均可售库存 {intr(OM['dstock'])}（环比 {relf(OM['dstock_mom'])}），供给端整体收缩，与在架SKC -6.7% 一致；但成衣二部当月新品在架SKC +152.94% 的同时 UV -50.28%、款效 -65.87%，属低效铺货；泳衣日均可售库存环比 {relf(OM_SWIM['dstock_mom'])}，供给收缩叠加需求下滑（表3-1/表3-2）。")
text("泳衣效率为大类最弱：详情页UV -36.1%（商列浏览UV -31.6%），CVR 2.57% 虽较环比期 2.30% 改善，但仍为四大类最低；退件率 8.00% 在大类中偏高。")
text(f"退货不再吞噬增长：退件率 {pct(OM['ret'])}、退货率 6.56%（环比期分别为 25.32%、24.03%）——环比期约四分之一的销售额被退货侵蚀，本期该因素已基本出清，是 CVR 与净销售额修复的重要来源。")
h3("5.4 可视化")
image(os.path.join(CHARTS, "chart1_dept_achievement.png"), "图5-1 各部门GMV达成率")
text("图5-1：11 个部门/大类中仅 ACC 达成率超过 60%（但体量小）；主力部门成衣一部 39.5% 最高，内睡 16.0% 最低，成衣二部 21.8% 与塑身衣项目部 23.1% 显著落后。")
image(os.path.join(CHARTS, "chart3_newold_mix.png"), "图5-2 当月新品/老品销售额结构：本期 vs 环比")
text("图5-2：当月新品销售额占比由 15.7% 降至 10.13%，老品占比升至 89.87%，新品对增长的承接明显弱于环比期。")
image(CH5, "图5-3 各分组当月新品/老品销售额同比")
image(chart5_f(), "图5-4 销售额环比变化三因子分解（按大类）")
text("图5-4：各大类流量（UV）贡献均为最大负项，转化（CVR）贡献普遍为正形成对冲，价格贡献很小——销售额下滑几乎全部来自流量收缩。")
# ---- 5.5 分市场因素已删除（评论8：全局剔除六国分市场与天气/穿搭/流行内容）；原图5-2/图5-5（品类 Top 图）移至第4章 4.2 ----

# ---- 第 6 章（评论3/4/5：唯一一份策略表，放模块内容之后；评论8：剔除分市场建议） ----
h2("6. 改善策略与预估收益")
text(f"总述：优先执行两条 P0——泳衣流量恢复针对最大拖累项，针织扩量是确定性最高的增长极；保守合计增量约 {wan(49.32*10000+10.67*10000)}、乐观约 {wan(98.63*10000+21.34*10000)}，约相当于本窗口销售额的 13%~26%。P1 两条为 11 月经营质量铺垫（新品承接与款效修复），P2 以守住退货改善成果为底线。")
# 表6-1 转图片（评论11：做成图片放标题下）
COLW_61 = [6, 26, 14, 46, 42, 26, 22]
render_table_image(strategy_header, strategy_rows, os.path.join(CHARTS, "table_6_1.png"), col_ws=COLW_61, fs=8.0)
text("表6-1 改善策略与预估收益")
image(os.path.join(CHARTS, "table_6_1.png"), None)

# ---- 第 7 章 ----
h2("7. 附录：关键指标口径")
for s in [
    f"达成率 = 实际 / 目标（目标为「正常目标」类型）；时间进度 = 截止日 / 当月天数（本期 {DATE_TXT}，即 {ELAPSED}/{DAYS_IN_MONTH} = {TP_TXT}）；落后/超时间进度 = 达成率 − 时间进度（以 % 表示）；差额/超额数值 = 时间进度差 × 对应目标值（落后为差额，超过为超额）。",
    f"环比 =（本期 − 上月同期）/ 上月同期；上月同期 = 起止日各回拨 1 个月（本期 {START}~{END}，环比期 {PM_RANGE}）。",
    f"同比 =（本期 − 去年同期）/ 去年同期（同比期 {PY_RANGE}）；第 3 章对照《经营情况模板》采用同比口径。",
    "占比 = 该维度行 / 全部维度合计（按各自周期计算）；占比变化以 % 表示。",
    "CTR = 商列点击UV / 商列浏览UV；CVR = 销量 / 详情页UV；UV产出（UV价值）= 销售额 / 详情页UV；加车率 = 商列加车UV / 商列浏览UV；平均价 = 销售额 / 销量；款效 = 销售额 / 在架SKC。",
    "退件率 = 退货数量 / 销量；退货率 = 退款总额 / 销售额。",
    "汇总口径：整体/大类/品类/新老品汇总均由明细行加总；对比期原始值由「本期值 ÷ (1+增长率)」还原，增长率缺失或 ≤ -100% 的行按对比期=0 处理（销售额口径涉及 4/52 行）。",
    f"口径差异：第 2 章为 {_Y}-{_M:02d} 月度口径（仅当期，进度基准=时间进度）；{CH_RANGE}为 {START}~{END} 窗口口径。两者数值不可直接混用。",
    f"合并表口径（表3-1/3-2）：销售额/销量/在架skc/UV 等为本期明细加总，环比=与上月同期（{PM_RANGE}）对比、同比=与去年同期（{PY_RANGE}）对比；占比为部门内/大类内占比；上新数为当月上架款数（月度口径，与 2.4 一致，环比/同比基于上月同期/去年同期派生查询）。",
]:
    text(s)

# ================= 章节过滤（--sections）：按 h2 编号截取 =================
import re as _re

def _filter_sections(content, sections):
    """按顶级标题编号过滤：编号不在 sections 的章节（含其下全部小节/图表/链接）整体移除"""
    out, keep = [], True
    for c in content:
        if c["kind"] == "h2":
            m = _re.match(r"^(\d+)\.", c["text"])
            keep = (m is None) or (m.group(1) in sections)
        if keep:
            out.append(c)
    return out

CONTENT[:] = _filter_sections(CONTENT, SECTIONS)

REPORT = {
    "title": TITLE,
    "content": CONTENT,
    "detail_sheets": [
        {"name": "二级品类明细L2", "csv": os.path.join(OUT, "S2_品类拆解L2.csv"), "rows": 70, "cols": 115},
        {"name": "三级品类明细L3", "csv": os.path.join(OUT, "S2_品类拆解L3.csv"), "rows": 242, "cols": 116},
    ],
    # 是否发布随附电子表格（仅当含第 4 章品类拆解时需要）
    "include_sheets": HAS_ATTR,
    "meta": {"start": START, "end": END, "time_progress": TP_TXT, "sections": ARGS.sections},
}

out_json = os.path.join(OUT, "feishu_report.json")
with io.open(out_json, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=1)
print("saved ->", out_json)
print("content blocks =", len(CONTENT))
# 打印第2章段落与策略表行数供检查
with io.open(os.path.join(OUT, "feishu_report_preview.txt"), "w", encoding="utf-8") as f:
    for c in CONTENT:
        if c["kind"] in ("h2", "h3"):
            f.write("\n" + c["text"] + "\n")
        elif c["kind"] == "text":
            f.write("  " + c["text"] + "\n")
        elif c["kind"] == "table":
            f.write(f"  [TABLE {len(c['header'])} cols x {len(c['rows'])} rows] {c.get('note','')}\n")
        elif c["kind"] == "image":
            f.write(f"  [IMAGE] {c['caption']}\n")
        elif c["kind"] == "link":
            f.write(f"  [LINK] {c['text']}\n")
print("preview -> feishu_report_preview.txt")
