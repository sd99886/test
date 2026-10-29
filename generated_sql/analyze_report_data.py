# -*- coding: utf-8 -*-
"""月度经营分析：从 S1/S2/S3/L3 查询结果计算报告所需全部数字。
- 明细行齐全的汇总：按明细加总（报告中声明）。
- 环比期原始值：prior = cur / (1 + r)；r 为空或 r=-1 时按 prior=0 处理并计数。
- 生成：analysis_summary.md（叙述用指标）+ report_tables.md（可直接粘贴的表格）+ 4 张图表。
"""
import csv, io, os

BASE = r"c:\Users\Cupshe\Desktop\test"
OUT = os.path.join(BASE, r"out\ops_20261021")
CHARTS = os.path.join(OUT, "charts")
os.makedirs(CHARTS, exist_ok=True)

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
    """由 本期值 与 环比率 还原环比期值。返回 (prior, assumed_zero)"""
    if cur is None:
        return None, False
    if r is None or r <= -1:
        return 0.0, True
    return cur / (1.0 + r), False

def ssum(rows, col):
    vals = [num(r.get(col)) for r in rows]
    return sum(v for v in vals if v is not None)

def prior_sum(rows, cur_col, r_col):
    tot, n_assume, n_rows = 0.0, 0, 0
    for r in rows:
        cur = num(r.get(cur_col)); rr = num(r.get(r_col))
        if cur is None:
            continue
        p, assumed = prior_of(cur, rr)
        tot += (p or 0.0)
        n_assume += 1 if assumed else 0
        n_rows += 1
    return tot, n_assume, n_rows

# ---------- 格式化 ----------
def money(x):
    return "N/A" if x is None else f"{x:,.2f}"
def pct(x, d=1):
    return "N/A" if x is None else f"{x*100:.{d}f}%"
def ppt(x, d=1):
    if x is None: return "N/A"
    return f"{x*100:+.{d}f}pp"
def intr(x):
    return "N/A" if x is None else f"{x:,.0f}"
def rel(x, d=1):
    return "N/A" if x is None else f"{x*100:+.{d}f}%"

SUM = io.StringIO()
TAB = io.StringIO()
def w_sum(s=""): SUM.write(s + "\n")
def w_tab(s=""): TAB.write(s + "\n")

# ================= S1 =================
s1 = load("S1_目标达成.csv")
DEPTS = ["成衣一部", "成衣二部", "品牌设计部", "新渠道产品部", "成衣", "泳衣产品部", "泳衣买手部", "泳衣", "内睡", "acc", "塑身衣项目部", "全品类"]
DEPT_LABEL = {"acc": "ACC"}
def dkey(d, k):  # 列名
    return f"{d}{k}"
def s1row(idx):
    for r in s1:
        if r["idx"] == idx:
            return r
    return None

w_tab("### 表2-1 全品类目标达成（S1，2026-10 月度口径）")
w_tab("| 指标 | 目标 | 实际 | 达成率 |")
w_tab("|---|---:|---:|---:|")
COUNT_IDX = {"上新数", "大爆款数", "爆款数", "超爆款数", "成功数", "法国线上新数"}
RATE_IDX = {"大爆款率", "爆款率", "超爆款率", "成功率"}
MONEY_IDX = {"GMV", "新品GMV", "新品款效", "新品款均成本"}
for r in s1:
    idx = r["idx"]
    tgt, act = num(r["全品类目标"]), num(r["全品类实际"])
    rate = num(r["全品类达成率"])
    if idx in COUNT_IDX:
        f_t, f_a = intr(tgt), intr(act)
    elif idx in MONEY_IDX:
        f_t, f_a = money(tgt), money(act)
    else:
        f_t, f_a = money(tgt) if tgt is not None else "N/A", money(act)
    w_tab(f"| {idx} | {f_t} | {f_a} | {pct(rate)} |")

w_tab()
w_tab("### 表2-2 分部门达成（S1，2026-10 月度口径）")
w_tab("| 部门 | GMV目标 | GMV实际 | GMV达成率 | 新品GMV实际 | 上新数目标 | 上新数实际 | 上新数达成率 |")
w_tab("|---|---:|---:|---:|---:|---:|---:|---:|")
r_gmv, r_newgmv, r_sx = s1row("GMV"), s1row("新品GMV"), s1row("上新数")
for d in DEPTS:
    lab = DEPT_LABEL.get(d, d)
    gt = num(r_gmv[dkey(d, "目标")]) if r_gmv else None
    ga = num(r_gmv[dkey(d, "实际")]) if r_gmv else None
    gr = num(r_gmv[dkey(d, "达成率")]) if r_gmv else None
    ng = num(r_newgmv[dkey(d, "实际")]) if r_newgmv else None
    st = num(r_sx[dkey(d, "目标")]) if r_sx else None
    sa = num(r_sx[dkey(d, "实际")]) if r_sx else None
    sr = num(r_sx[dkey(d, "达成率")]) if r_sx else None
    w_tab(f"| {lab} | {money(gt)} | {money(ga)} | {pct(gr)} | {money(ng)} | {intr(st)} | {intr(sa)} | {pct(sr)} |")

w_sum("## S1 关键指标（2026-10 月度口径，目标类型=正常目标）")
g = r_gmv
for d in DEPTS:
    w_sum(f"GMV·{DEPT_LABEL.get(d,d)}: 目标={money(num(g[dkey(d,'目标')]))} 实际={money(num(g[dkey(d,'实际')]))} 达成率={pct(num(g[dkey(d,'达成率')]))}")
for idx in ["新品GMV", "上新数", "大爆款数", "大爆款率", "爆款数", "爆款率", "超爆款数", "超爆款率", "成功数", "成功率", "新品款效", "新品款均成本", "法国线上新数"]:
    r = s1row(idx)
    w_sum(f"{idx}: 全品类目标={money(num(r['全品类目标'])) if idx in MONEY_IDX else intr(num(r['全品类目标']))} 实际={money(num(r['全品类实际'])) if idx in MONEY_IDX or idx not in COUNT_IDX else intr(num(r['全品类实际']))} 率={pct(num(r['全品类达成率']))}")
    det = ", ".join(f"{DEPT_LABEL.get(d,d)}={money(num(r[dkey(d,'实际')])) if idx in MONEY_IDX or idx not in COUNT_IDX else intr(num(r[dkey(d,'实际')]))}" for d in DEPTS[:-1])
    w_sum(f"  分部门实际: {det}")

# ================= S2 (L2) =================
s2 = load("S2_品类拆解L2.csv")
w_sum()
w_sum("## S2 窗口总览（2026-10-01~10-20；环比=2026-09-01~09-20；同比=2025-10-01~10-20）")
w_sum(f"窗口: 本期 {s2[0]['本期_start']}~{s2[0]['本期_end']}  环比 {s2[0]['环比_start']}~{s2[0]['环比_end']}  同比 {s2[0]['同比_start']}~{s2[0]['同比_end']}  行数={len(s2)}")

tot_cur_sales = ssum(s2, "本期_销售额")
tot_prior_sales, n_as_s, n_r_s = prior_sum(s2, "本期_销售额", "销售额_环比")
tot_cur_qty = ssum(s2, "本期_销量")
tot_prior_qty, _, _ = prior_sum(s2, "本期_销量", "销量_环比")
tot_cur_uv = ssum(s2, "本期_详情页uv")
tot_prior_uv, _, _ = prior_sum(s2, "本期_详情页uv", "详情页uv_环比")
tot_cur_clv = ssum(s2, "本期_商列浏览uv")
tot_prior_clv, _, _ = prior_sum(s2, "本期_商列浏览uv", "商列浏览uv_环比")
tot_cur_ret = ssum(s2, "本期_退货数量")
tot_prior_ret, _, _ = prior_sum(s2, "本期_退货数量", "退货数量_环比")
tot_cur_refund = ssum(s2, "本期_退款总额")
tot_prior_refund, _, _ = prior_sum(s2, "本期_退款总额", "退款总额_环比")
tot_cur_skc = ssum(s2, "本期_在架skc")
tot_prior_skc, _, _ = prior_sum(s2, "本期_在架skc", "在架skc_环比")

def rr(cur, prior):
    if prior is None or prior == 0 or cur is None: return None
    return (cur - prior) / prior

w_sum(f"整体: 销售额 本期={money(tot_cur_sales)} 环比期={money(tot_prior_sales)}(还原, 假设0的行数={n_as_s}/{n_r_s}) 环比={rel(rr(tot_cur_sales, tot_prior_sales))}")
w_sum(f"整体: 销量 本期={intr(tot_cur_qty)} 环比期={intr(tot_prior_qty)} 环比={rel(rr(tot_cur_qty, tot_prior_qty))}")
w_sum(f"整体: 详情页UV 本期={intr(tot_cur_uv)} 环比期={intr(tot_prior_uv)} 环比={rel(rr(tot_cur_uv, tot_prior_uv))}")
w_sum(f"整体: 商列浏览UV 本期={intr(tot_cur_clv)} 环比期={intr(tot_prior_clv)} 环比={rel(rr(tot_cur_clv, tot_prior_clv))}")
w_sum(f"整体: 平均价 本期={money(tot_cur_sales/tot_cur_qty if tot_cur_qty else None)} 环比期={money(tot_prior_sales/tot_prior_qty if tot_prior_qty else None)} 环比={rel(rr(tot_cur_sales/tot_cur_qty if tot_cur_qty else None, tot_prior_sales/tot_prior_qty if tot_prior_qty else None))}")
cvr_c = tot_cur_qty/tot_cur_uv if tot_cur_uv else None
cvr_p = tot_prior_qty/tot_prior_uv if tot_prior_uv else None
w_sum(f"整体: CVR 本期={pct(cvr_c,2)} 环比期={pct(cvr_p,2)} 环比={rel(rr(cvr_c, cvr_p))}")
rj_c = tot_cur_ret/tot_cur_qty if tot_cur_qty else None
rj_p = tot_prior_ret/tot_prior_qty if tot_prior_qty else None
w_sum(f"整体: 退件率 本期={pct(rj_c,2)} 环比期={pct(rj_p,2)} 环比={rel(rr(rj_c, rj_p))}")
th_c = tot_cur_refund/tot_cur_sales if tot_cur_sales else None
th_p = tot_prior_refund/tot_prior_sales if tot_prior_sales else None
w_sum(f"整体: 退货率(退款额/销售额) 本期={pct(th_c,2)} 环比期={pct(th_p,2)} 环比={rel(rr(th_c, th_p))}")
w_sum(f"整体: 在架SKC 本期={intr(tot_cur_skc)} 环比期={intr(tot_prior_skc)} 环比={rel(rr(tot_cur_skc, tot_prior_skc))}")

# --- 按是否当月新品 / 当年新品 ---
def bucket_stats(rows, key):
    res = {}
    for v in sorted(set(r[key] for r in rows)):
        sub = [r for r in rows if r[key] == v]
        cur = ssum(sub, "本期_销售额"); pri, _, _ = prior_sum(sub, "本期_销售额", "销售额_环比")
        curq = ssum(sub, "本期_销量")
        res[v] = dict(cur=cur, prior=pri, qty=curq, share=cur/tot_cur_sales if tot_cur_sales else None,
                      pshare=pri/tot_prior_sales if tot_prior_sales else None)
    return res

w_sum()
w_sum("## 新老品结构（S2，按是否当月新品，销售额口径，明细加总）")
bym = bucket_stats(s2, "是否当月新品")
for v, d in bym.items():
    w_sum(f"{v}: 本期销售额={money(d['cur'])} 占比={pct(d['share'])} | 环比期={money(d['prior'])} 占比={pct(d['pshare'])} | 占比变化={ppt((d['share']-d['pshare']) if d['share'] is not None and d['pshare'] is not None else None)} | 销售额环比={rel(rr(d['cur'], d['prior']))}")
w_sum("## 当年新品结构（S2，按是否当年新品）")
byy = bucket_stats(s2, "是否当年新品")
for v, d in byy.items():
    w_sum(f"{v}: 本期销售额={money(d['cur'])} 占比={pct(d['share'])} | 环比期={money(d['prior'])} 占比={pct(d['pshare'])} | 占比变化={ppt((d['share']-d['pshare']) if d['share'] is not None and d['pshare'] is not None else None)}")

# --- 按大类 ---
w_sum()
w_sum("## 大类（S2，明细加总）")
bybig = {}
for r in s2:
    bybig.setdefault(r["big_category"], []).append(r)
big_rows = []
for b, rows in bybig.items():
    cur = ssum(rows, "本期_销售额"); pri, _, _ = prior_sum(rows, "本期_销售额", "销售额_环比")
    curq = ssum(rows, "本期_销量"); priorq, _, _ = prior_sum(rows, "本期_销量", "销量_环比")
    curuv = ssum(rows, "本期_详情页uv"); prioruv, _, _ = prior_sum(rows, "本期_详情页uv", "详情页uv_环比")
    big_rows.append((b, cur, pri, curq, priorq, curuv, prioruv))
    w_sum(f"{b}: 销售额={money(cur)} 环比={rel(rr(cur,pri))} 占比={pct(cur/tot_cur_sales if tot_cur_sales else None)} | 销量环比={rel(rr(curq,priorq))} | UV环比={rel(rr(curuv,prioruv))} | CVR={pct(curq/curuv if curuv else None,2)}")

# --- 表A：二级品类 ---
w_sum()
w_sum("## 表A 二级品类汇总（S2 明细加总；环比期由本期/(1+环比)还原）")
bysec = {}
for r in s2:
    bysec.setdefault(r["second_category"], []).append(r)
sec_rows = []
for sec, rows in bysec.items():
    cur = ssum(rows, "本期_销售额"); pri, n_as, _ = prior_sum(rows, "本期_销售额", "销售额_环比")
    curq = ssum(rows, "本期_销量"); priorq, _, _ = prior_sum(rows, "本期_销量", "销量_环比")
    curuv = ssum(rows, "本期_详情页uv"); prioruv, _, _ = prior_sum(rows, "本期_详情页uv", "详情页uv_环比")
    curret = ssum(rows, "本期_退货数量"); priorret, _, _ = prior_sum(rows, "本期_退货数量", "退货数量_环比")
    curclv = ssum(rows, "本期_商列浏览uv"); priorclv, _, _ = prior_sum(rows, "本期_商列浏览uv", "商列浏览uv_环比")
    skc = ssum(rows, "本期_在架skc")
    bigs = sorted(set(r["big_category"] for r in rows))
    sec_rows.append(dict(sec=sec, big="/".join(bigs), cur=cur, prior=pri, curq=curq, priorq=priorq,
                         curuv=curuv, prioruv=prioruv, curret=curret, priorret=priorret,
                         curclv=curclv, priorclv=priorclv, skc=skc, n_as=n_as))
sec_rows.sort(key=lambda x: -x["cur"])
w_sum(f"二级品类数={len(sec_rows)}")
for x in sec_rows:
    share = x["cur"]/tot_cur_sales if tot_cur_sales else None
    pshare = x["prior"]/tot_prior_sales if tot_prior_sales else None
    w_sum(f"{x['sec']} [{x['big']}]: 销售={money(x['cur'])} 环比={rel(rr(x['cur'],x['prior']))} 占比={pct(share)}(环比期占比={pct(pshare)}, 变化={ppt((share-pshare) if share is not None and pshare is not None else None)}) 销量={intr(x['curq'])}(环比={rel(rr(x['curq'],x['priorq']))}) UV={intr(x['curuv'])}(环比={rel(rr(x['curuv'],x['prioruv']))}) CVR={pct(x['curq']/x['curuv'] if x['curuv'] else None,2)}(环比期={pct(x['priorq']/x['prioruv'] if x['prioruv'] else None,2)}) 商列UV={intr(x['curclv'])}(环比={rel(rr(x['curclv'],x['priorclv']))}) 退件率={pct(x['curret']/x['curq'] if x['curq'] else None,2)} 在架SKC={intr(x['skc'])} 假设0行={x['n_as']}")

# 表A markdown（>30 行时 Top20+其它）
def fmt_tableA(rows):
    if len(rows) > 30:
        top, rest = rows[:20], rows[20:]
        o = rest[0]["cur"] + sum(r["cur"] for r in rest[1:]) if rest else 0
        oq = rest[0]["curq"] + sum(r["curq"] for r in rest[1:]) if rest else 0
        ouv = rest[0]["curuv"] + sum(r["curuv"] for r in rest[1:]) if rest else 0
        lines = [r for r in top] + [dict(sec="其它（合并）", big="-", cur=o, prior=None, curq=oq, priorq=None, curuv=ouv, prioruv=None)]
        note = f"维度=二级品类（S2 明细加总）；共 {len(rows)} 行，按销售额降序取 Top20，其余合并为「其它」"
    else:
        lines = rows
        note = f"维度=二级品类（S2 明细加总）；共 {len(rows)} 行，全量展示"
    t = [note, "", "| 二级品类 | 大类 | 销售额(USD) | 销售额环比 | 销售额占比 | 销量 | 销量环比 | 详情页UV | UV环比 | CVR |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in lines:
        share = r["cur"]/tot_cur_sales if tot_cur_sales else None
        t.append(f"| {r['sec']} | {r['big']} | {money(r['cur'])} | {rel(rr(r['cur'],r['prior']))} | {pct(share)} | {intr(r['curq'])} | {rel(rr(r['curq'],r['priorq']))} | {intr(r['curuv'])} | {rel(rr(r['curuv'],r['prioruv']))} | {pct(r['curq']/r['curuv'] if r['curuv'] else None,2)} |")
    return "\n".join(t)

w_tab("### 表A 二级品类拆解（窗口 2026-10-01~10-20）")
w_tab(fmt_tableA(sec_rows))
w_tab()

# ================= S2-L3 =================
l3 = load("S2_品类拆解L3.csv")
w_sum()
w_sum(f"## 表B 三级品类汇总（L3 明细加总，行数输入={len(l3)}）")
byl3 = {}
for r in l3:
    byl3.setdefault((r["big_category"], r["second_category"], r["third_category"]), []).append(r)
l3_rows = []
for k, rows in byl3.items():
    cur = ssum(rows, "本期_销售额"); pri, n_as, _ = prior_sum(rows, "本期_销售额", "销售额_环比")
    curq = ssum(rows, "本期_销量"); priorq, _, _ = prior_sum(rows, "本期_销量", "销量_环比")
    curuv = ssum(rows, "本期_详情页uv"); prioruv, _, _ = prior_sum(rows, "本期_详情页uv", "详情页uv_环比")
    l3_rows.append(dict(big=k[0], sec=k[1], third=k[2], cur=cur, prior=pri, curq=curq, priorq=priorq, curuv=curuv, prioruv=prioruv, n_as=n_as))
l3_rows.sort(key=lambda x: -x["cur"])
w_sum(f"三级品类数={len(l3_rows)}")
tot_l3_cur = sum(r["cur"] for r in l3_rows)
top_incr = sorted([r for r in l3_rows if r["prior"] is not None], key=lambda r: (r["cur"]-r["prior"]))[-5:]
top_decl = sorted([r for r in l3_rows if r["prior"] and r["cur"] > 1000], key=lambda r: (r["prior"]-r["cur"]), reverse=True)[:8]
w_sum("三级品类·销售额增量 Top5（cur-prior）:")
for r in reversed(top_incr):
    w_sum(f"  {r['sec']}/{r['third']}: 本期={money(r['cur'])} 环比期={money(r['prior'])} 增量={money(r['cur']-r['prior'])} 环比={rel(rr(r['cur'],r['prior']))}")
w_sum("三级品类·拖累候选（prior-cur 最大，本期>1000）:")
for r in top_decl:
    w_sum(f"  {r['sec']}/{r['third']}: 本期={money(r['cur'])} 环比期={money(r['prior'])} 缩减={money(r['prior']-r['cur'])} 环比={rel(rr(r['cur'],r['prior']))}")

w_tab("### 表B 三级品类拆解（窗口 2026-10-01~10-20）")
if len(l3_rows) > 30:
    top20, rest = l3_rows[:20], l3_rows[20:]
    o = sum(r["cur"] for r in rest); oq = sum(r["curq"] for r in rest); ouv = sum(r["curuv"] for r in rest)
    lines = [dict(sec="-", third="其它（合并）", big="-", cur=o, prior=None, curq=oq, priorq=None, curuv=ouv, prioruv=None)] 
    lines = top20 + lines
    note = f"维度=三级品类（L3 明细加总）；共 {len(l3_rows)} 行，按销售额降序取 Top20，其余合并为「其它」"
else:
    lines = l3_rows
    note = f"维度=三级品类（L3 明细加总）；共 {len(l3_rows)} 行，全量展示"
w_tab(note)
w_tab()
w_tab("| 大类 | 二级品类 | 三级品类 | 销售额(USD) | 销售额环比 | 销售额占比 | 销量 | 销量环比 | 详情页UV | CVR |")
w_tab("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
for r in lines:
    share = r["cur"]/tot_l3_cur if tot_l3_cur else None
    w_tab(f"| {r['big']} | {r['sec']} | {r['third']} | {money(r['cur'])} | {rel(rr(r['cur'],r['prior']))} | {pct(share)} | {intr(r['curq'])} | {rel(rr(r['curq'],r['priorq']))} | {intr(r['curuv'])} | {pct(r['curq']/r['curuv'] if r['curuv'] else None,2)} |")
w_tab()

# ================= S3 =================
s3 = load("S3_新老品业务部门.csv")
w_sum()
w_sum(f"## S3 新老品×业务部门（行数={len(s3)}，窗口同 S2）")
for r in s3:
    w_sum(f"{r['大类']}/{r['业务部门']}/{r['是否当月新品']}: 销售额={money(num(r['本期_销售额']))} 环比={rel(num(r['销售额_环比']))} 占比={pct(num(r['本期_销售额占比']))} 在架SKC={intr(num(r['本期_在架skc']))}(环比={rel(num(r['在架skc_环比']))}) 详情页UV={intr(num(r['本期_详情页uv']))}(环比={rel(num(r['详情页uv_环比']))}) CVR={pct(num(r['本期_cvr']),2)}(环比={rel(num(r['cvr_环比']))}) 退件率={pct(num(r['本期_退件率']),2)}(环比={rel(num(r['退件率_环比']))}) 款效={money(num(r['本期_款效']))}(环比={rel(num(r['款效_环比']))})")
# 部门内新品占比
w_sum("部门内新品销售额占比（由 S3 行加总）:")
dept_agg = {}
for r in s3:
    dept_agg.setdefault(r["业务部门"], {})[r["是否当月新品"]] = num(r["本期_销售额"]) or 0.0
for d, m in dept_agg.items():
    tot = sum(m.values())
    for k in ["当月新品", "当月老品", "当月未上架"]:
        if k in m or tot:
            w_sum(f"  {d}: {k}={money(m.get(k))} 占比={pct((m.get(k) or 0)/tot if tot else None)}")

w_tab("### 表3 新老品 × 业务部门（S3，窗口 2026-10-01~10-20）")
w_tab("| 大类 | 业务部门 | 是否当月新品 | 销售额(USD) | 销售额环比 | 销售额占比 | 在架SKC | 在架SKC环比 | 详情页UV | CVR | 款效 |")
w_tab("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for r in s3:
    w_tab(f"| {r['大类']} | {r['业务部门']} | {r['是否当月新品']} | {money(num(r['本期_销售额']))} | {rel(num(r['销售额_环比']))} | {pct(num(r['本期_销售额占比']))} | {intr(num(r['本期_在架skc']))} | {rel(num(r['在架skc_环比']))} | {intr(num(r['本期_详情页uv']))} | {pct(num(r['本期_cvr']),2)} | {money(num(r['本期_款效']))} |")
w_tab()

# ================= 图表 =================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
C_BLUE, C_ORANGE, C_GREEN, C_RED = "#0072B2", "#E69F00", "#009E73", "#D55E00"

# 图1：部门 GMV 达成率
labels, vals = [], []
for d in DEPTS:
    if d == "全品类":
        continue
    t = num(g[dkey(d, "目标")])
    if not t:
        continue
    labels.append(DEPT_LABEL.get(d, d))
    vals.append(num(g[dkey(d, "达成率")]) * 100)
order = sorted(range(len(vals)), key=lambda i: -vals[i])
labels = [labels[i] for i in order]; vals = [vals[i] for i in order]
all_rate = num(g["全品类达成率"]) * 100
fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
colors = [C_BLUE if v >= all_rate else C_ORANGE for v in vals]
bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1])
ax.axvline(all_rate, color=C_RED, ls="--", lw=1.2)
ax.text(all_rate + 1, len(vals) - 0.4, f"全品类 {all_rate:.1f}%", color=C_RED, fontsize=10)
for b, v in zip(bars, vals[::-1]):
    ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=10)
ax.set_xlim(0, max(vals) * 1.18)
ax.set_xlabel("GMV 达成率（%）")
ax.set_title("图1 各业务部门 GMV 目标达成率（2026-10，月度口径）")
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "chart1_dept_achievement.png")); plt.close(fig)

# 图2：二级品类销售额 Top10 及环比
top10 = sec_rows[:10]
fig, ax = plt.subplots(figsize=(9.5, 5.8), dpi=150)
names = [x["sec"] for x in top10][::-1]
sales = [x["cur"] for x in top10][::-1]
momv = [rr(x["cur"], x["prior"]) * 100 if x["prior"] else None for x in top10][::-1]
bars = ax.barh(names, [s / 10000 for s in sales], color=C_BLUE)
for b, s, m in zip(bars, sales, momv):
    tag = f"{s/10000:,.1f}万" + (f"（环比{m:+.1f}%）" if m is not None else "")
    ax.text(b.get_width() * 1.01, b.get_y() + b.get_height() / 2, tag, va="center", fontsize=9)
ax.set_xlabel("本期销售额（万 USD）")
ax.set_title("图2 二级品类销售额 Top10 及环比（2026-10-01~10-20）")
ax.set_xlim(0, max(sales) / 10000 * 1.35)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "chart2_l2_top10.png")); plt.close(fig)

# 图3：新老品结构（当期 vs 环比）
keys = [k for k in ["当月新品", "当月老品", "当月未上架"] if k in bym]
cur_sh = [bym.get(k, {}).get("share", 0) or 0 for k in keys]
pri_sh = [bym.get(k, {}).get("pshare", 0) or 0 for k in keys]
x = range(len(keys)); w_ = 0.36
fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
b1 = ax.bar([i - w_/2 for i in x], [v*100 for v in cur_sh], w_, label="本期(10-01~10-20)", color=C_BLUE)
b2 = ax.bar([i + w_/2 for i in x], [v*100 for v in pri_sh], w_, label="环比期(09-01~09-20)", color=C_ORANGE)
for bs in (b1, b2):
    for b in bs:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.6, f"{b.get_height():.1f}%", ha="center", fontsize=10)
ax.set_xticks(list(x)); ax.set_xticklabels(keys)
ax.set_ylabel("销售额占比（%）"); ax.set_ylim(0, max(cur_sh + pri_sh) * 118)
ax.set_title("图3 新老品销售额结构：本期 vs 环比（S2）")
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "chart3_newold_mix.png")); plt.close(fig)

# 图4：三级品类拖累 Top5
decl5 = top_decl[:5]
fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
names4 = [f"{r['sec']}/{r['third']}" for r in decl5][::-1]
drop = [(r["prior"] - r["cur"]) / 10000 for r in decl5][::-1]
mom4 = [rr(r["cur"], r["prior"]) * 100 for r in decl5][::-1]
bars = ax.barh(names4, drop, color=C_RED)
for b, d_, m in zip(bars, drop, mom4):
    ax.text(b.get_width() * 1.01, b.get_y() + b.get_height()/2, f"-{d_:,.1f}万（{m:+.1f}%）", va="center", fontsize=9)
ax.set_xlabel("环比销售额缩减（万 USD）")
ax.set_title("图4 三级品类环比拖累 Top5（本期>1000USD）")
ax.set_xlim(0, max(drop) * 1.4)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "chart4_l3_decline.png")); plt.close(fig)

with io.open(os.path.join(OUT, "analysis_summary.md"), "w", encoding="utf-8") as f:
    f.write(SUM.getvalue())
with io.open(os.path.join(OUT, "report_tables.md"), "w", encoding="utf-8") as f:
    f.write(TAB.getvalue())
print("DONE. summary=", len(SUM.getvalue()), "tables=", len(TAB.getvalue()))
