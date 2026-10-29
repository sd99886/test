# -*- coding: utf-8 -*-
"""
退货原因分析 — 7 大板块分析引擎
输入: CSV 数据文件
输出: analysis_result.json

用法: python analysis.py <csv_path> <output_json_path>
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

def run_analysis(csv_path, output_path):
    df = pd.read_csv(csv_path)
    df.rename(columns={c: 'GMV' for c in df.columns if c.lower() == 'gmv'}, inplace=True)
    for c in ['sku级别一级原因', 'sku级别二级原因', 'sku级别三级原因']:
        df[c] = df[c].fillna('').replace('', '无退货原因')

    # ── 板块一：整体退货概况 ──
    total_sales = int(df['销量'].sum())
    total_refund_qty = int(df['退款数量'].sum())
    total_gmv = df['GMV'].sum()
    total_refund_amt = df['退款金额'].sum()
    total_coupon_amt = df['退券金额'].sum()
    total_refund_total = df['退款总额'].sum()
    overall_return_qty_rate = total_refund_qty / total_sales * 100 if total_sales > 0 else 0
    overall_return_amt_rate = total_refund_total / total_gmv * 100 if total_gmv > 0 else 0

    section1 = {
        '总销量': total_sales, '总退款数量': total_refund_qty,
        '总GMV(USD)': round(total_gmv, 2), '总退款金额(USD)': round(total_refund_amt, 2),
        '总退券金额(USD)': round(total_coupon_amt, 2), '总退款总额(USD)': round(total_refund_total, 2),
        '退件率': round(overall_return_qty_rate, 2), '退货率': round(overall_return_amt_rate, 2),
    }

    # ── 板块二：退货原因分布 ──
    df_ret = df[df['一级原因'] != '无退货原因'] if '一级原因' in df.columns else df[df['sku级别一级原因'] != '无退货原因']
    reason_col = '一级原因' if '一级原因' in df.columns else 'sku级别一级原因'
    sub_col = '二级原因' if '二级原因' in df.columns else 'sku级别二级原因'

    reason_agg = df_ret.groupby(reason_col).agg(退款数量=('退款数量','sum'),退款金额=('退款金额','sum'),销量=('销量','sum'),GMV=('GMV','sum')).reset_index()
    reason_agg['占比'] = (reason_agg['退款数量'] / reason_agg['退款数量'].sum() * 100).round(2)
    reason_agg = reason_agg.sort_values('退款数量', ascending=False)

    core_reasons = reason_agg[reason_agg['占比'] >= 20][reason_col].tolist()
    if not core_reasons:
        core_reasons = reason_agg.head(2)[reason_col].tolist()

    sub_reason_details = {}
    for r1 in core_reasons:
        sub = df_ret[df_ret[reason_col] == r1].groupby(sub_col).agg(退款数量=('退款数量','sum')).reset_index()
        sub['占比'] = (sub['退款数量'] / sub['退款数量'].sum() * 100).round(2)
        sub = sub.sort_values('退款数量', ascending=False).head(3)
        sub_reason_details[r1] = sub.to_dict('records')

    # ── 板块三：分月趋势 ──
    month_col = '销售月' if '销售月' in df.columns else df.columns[0]
    monthly = df.groupby(month_col).agg(销量=('销量','sum'),GMV=('GMV','sum'),退款数量=('退款数量','sum'),退款金额=('退款金额','sum'),退款总额=('退款总额','sum')).reset_index()
    monthly['退件率'] = (monthly['退款数量'] / monthly['销量'] * 100).round(2)
    monthly['退货率'] = (monthly['退款总额'] / monthly['GMV'] * 100).round(2)
    monthly = monthly.sort_values(month_col)
    monthly['标注'] = ''
    max_idx = monthly['退件率'].idxmax()
    monthly.loc[max_idx, '标注'] = '🔴 峰值'
    for i in range(1, len(monthly)):
        if monthly.iloc[i]['退件率'] < monthly.iloc[i-1]['退件率']:
            monthly.iloc[i, monthly.columns.get_loc('标注')] = '🟢 改善'
        elif monthly.iloc[i]['退件率'] > monthly.iloc[i-1]['退件率']:
            monthly.iloc[i, monthly.columns.get_loc('标注')] = '🟡 恶化'

    # ── 板块四：分月原因明细 ──
    mr = df_ret.groupby([month_col, reason_col]).agg(销量=('销量','sum'),退款数量=('退款数量','sum'),退款金额=('退款金额','sum'),退款总额=('退款总额','sum')).reset_index()
    mr['退件率'] = (mr['退款数量'] / mr['销量'] * 100).round(2)
    mr = mr.sort_values([month_col, '退款数量'], ascending=[True, False])
    mr['标注'] = ''
    mr.loc[mr['退件率'] > 50, '标注'] = '🔴 高风险'

    # ── 板块五：深层诊断 ──
    top2 = reason_agg.head(2)[reason_col].tolist()
    diagnosis = {}
    for r1 in top2:
        r1d = df_ret[df_ret[reason_col] == r1]
        r1_refund = int(r1d['退款数量'].sum()); r1_sales = int(r1d['销量'].sum())
        r1_rate = r1_refund / r1_sales * 100 if r1_sales > 0 else 0
        r1_share = r1_refund / total_refund_qty * 100 if total_refund_qty > 0 else 0
        severity = '🔴 高' if (r1_share > 30 or r1_rate > 50) else ('🟡 中' if r1_share >= 15 else '🟢 低')
        sub = r1d.groupby(sub_col).agg(退款数量=('退款数量','sum')).reset_index()
        sub['占比'] = (sub['退款数量'] / sub['退款数量'].sum() * 100).round(2)
        sub = sub.sort_values('退款数量', ascending=False)
        diagnosis[r1] = {'退款数量': r1_refund, '涉及销量': r1_sales, '退件率': round(r1_rate, 2),
                         '占总退款比': round(r1_share, 2), '严重度': severity, '二级原因': sub.to_dict('records')}

    # ── 板块六：改善建议 ──
    reason_to_sug = {"Item Doesn't Fit": '尺码类 -> 调整鞋楦/更新尺码表/增加尺码说明',
                     'Dislike the Fabric': '面料类 -> 面料升级/加衬里/改善面料手感',
                     'Arrived Different From Description/Photo': '描述类 -> 更新产品图/增加实物说明',
                     "I Don't Like the Product": '设计类 -> 优化产品款式设计/增加用户评价展示',
                     'Order not shipped, cancelled': '订单类 -> 优化发货时效/改善订单处理流程',
                     'Other': '其他类 -> 进一步收集客户反馈细化原因'}
    suggestions = []
    for r1 in top2:
        d = diagnosis[r1]
        suggestions.append({'原因': r1, '严重度': d['严重度'], '退件率': f"{d['退件率']}%",
                           '占总退款比': f"{d['占总退款比']}%",
                           '建议方向': reason_to_sug.get(r1, '需进一步分析'),
                           '优先级': 'P0' if d['严重度'] == '🔴 高' else 'P1'})

    # ── 板块七：改善目标 ──
    target_rate = round(overall_return_qty_rate * 0.7, 2)
    targets = {'current_rate': round(overall_return_qty_rate, 2), 'target_rate': target_rate,
               'reduce_qty': int(total_refund_qty * 0.3), 'top_actions': suggestions[:3]}

    # ── 输出 JSON ──
    output = {
        'section1_overview': section1,
        'section2_reason_dist': reason_agg.to_dict('records'),
        'section2_sub_reasons': sub_reason_details,
        'section3_monthly_trend': monthly.to_dict('records'),
        'section4_monthly_reason': mr.to_dict('records'),
        'section5_diagnosis': diagnosis,
        'section6_suggestions': suggestions,
        'section7_targets': targets,
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"分析完成 → {output_path}")
    return output

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python analysis.py <csv_path> <output_json_path>")
        sys.exit(1)
    run_analysis(sys.argv[1], sys.argv[2])
