"""
从 Excel 提取数据并生成 BI Demo 所需的 JSON
"""
import openpyxl
import json
from collections import defaultdict
from datetime import datetime

wb = openpyxl.load_workbook(r"C:\Users\Cupshe\Downloads\Datasets Fusion 2026-09-17 16-30-37.xlsx", read_only=True)
ws = wb['Datasets Fusion']
rows = list(ws.iter_rows(values_only=True))
header = rows[0]

# 转为字典列表
data = []
for row in rows[1:]:
    d = {}
    for i, h in enumerate(header):
        val = row[i]
        if isinstance(val, datetime):
            val = val.strftime('%Y-%m-%d %H:%M:%S')
        d[h] = val
    data.append(d)

# 按异常工单分组
orders = defaultdict(lambda: {'nodes': [], 'info': {}})
for d in data:
    oid = d['异常工单号']
    orders[oid]['info'] = {
        'order_no': d['异常工单号'],
        'create_time': d['创建时间'],
        'supplier': d['供应商'],
        'status': d['状态'],
        'exception_type': d.get('异常类型', ''),
        'exception_desc': d['异常描述'],
        'category': d.get('大类', ''),
        'reason_1': d.get('一级异常原因', ''),
        'reason_2': d.get('二级异常原因', ''),
        'reason_3': d.get('三级异常原因', ''),
        'source': d.get('来源', ''),
        'purchaser': d.get('采购员', ''),
        'process_name': d.get('process_name', ''),
        'process_code': d.get('process_code', ''),
    }
    if d.get('node_id') is not None:
        node_key = (int(float(d['node_id'])), int(float(d['node_seq'])))
        # 检查是否已存在（去重）
        existing = next((n for n in orders[oid]['nodes'] if n['node_id'] == node_key[0] and n['node_seq'] == node_key[1]), None)
        if existing:
            # 追加 field 信息
            if d.get('field_name'):
                existing['fields'].append({
                    'field_name': d['field_name'],
                    'field_value': d.get('field_value', ''),
                    'filed_code': d.get('filed_code', ''),
                })
        else:
            node = {
                'node_id': int(float(d['node_id'])),
                'node_seq': int(float(d['node_seq'])),
                'node_name': d['node_name'],
                'status': int(float(d['status'])) if d['status'] else None,
                'handler_id': d.get('proc_production_exception_order_node handler_id', ''),
                'gmt_create': d.get('gmt_create', ''),
                'gmt_modified': d.get('gmt_modified', ''),
                'is_del': int(float(d['is_del'])) if d['is_del'] else 0,
                'process_name': d.get('process_name', ''),
                'fields': []
            }
            if d.get('field_name'):
                node['fields'].append({
                    'field_name': d['field_name'],
                    'field_value': d.get('field_value', ''),
                    'filed_code': d.get('filed_code', ''),
                })
            orders[oid]['nodes'].append(node)

# 排序节点
for oid in orders:
    orders[oid]['nodes'].sort(key=lambda x: x['node_seq'])

# 统计
status_dist = defaultdict(int)
for d in data:
    status_dist[d['状态']] += 1

process_dist = defaultdict(int)
for oid, v in orders.items():
    pn = v['info'].get('process_name', '') or '未知'
    process_dist[pn] += 1

reason1_dist = defaultdict(int)
for d in data:
    reason1_dist[d.get('一级异常原因', '')] += 1

# 节点名称映射
node_name_map = {
    1: '面料组接收处理异常',
    2: '面料组完成异常处理',
    7: '辅料组接收处理异常',
    8: '辅料组完成异常处理',
    4: '面料组接收处理异常(数量)',
    3: '订单组确认异常处理结果(数量)',
    9: '订单组确认异常处理结果',
    5: '成本部确认价格异常内容',
    6: '辅料组接收处理异常(2)',
    13: '未知节点',
}

# 计算每个工单的节点时效
order_timeliness = []
for oid, v in list(orders.items())[:50]:  # 取前50个
    info = v['info']
    nodes = v['nodes']
    if not nodes:
        continue
    
    # 计算每个节点的处理时长
    node_details = []
    for n in nodes:
        create_dt = datetime.strptime(n['gmt_create'], '%Y-%m-%d %H:%M:%S') if n['gmt_create'] else None
        modify_dt = datetime.strptime(n['gmt_modified'], '%Y-%m-%d %H:%M:%S') if n['gmt_modified'] else None
        duration_hours = None
        if create_dt and modify_dt:
            duration_hours = round((modify_dt - create_dt).total_seconds() / 3600, 1)
        
        node_details.append({
            'node_name': n['node_name'],
            'node_seq': n['node_seq'],
            'status': n['status'],
            'handler_id': n['handler_id'],
            'gmt_create': n['gmt_create'],
            'gmt_modified': n['gmt_modified'],
            'duration_hours': duration_hours,
            'is_del': n['is_del'],
            'fields': n.get('fields', []),
        })
    
    # 计算总时长
    all_creates = [datetime.strptime(n['gmt_create'], '%Y-%m-%d %H:%M:%S') for n in nodes if n['gmt_create']]
    all_modifies = [datetime.strptime(n['gmt_modified'], '%Y-%m-%d %H:%M:%S') for n in nodes if n['gmt_modified']]
    total_hours = None
    if all_creates and all_modifies:
        total_hours = round((max(all_modifies) - min(all_creates)).total_seconds() / 3600, 1)
    
    order_timeliness.append({
        'order_no': info['order_no'],
        'create_time': info['create_time'],
        'supplier': info['supplier'],
        'status': info['status'],
        'exception_desc': info['exception_desc'],
        'reason_1': info['reason_1'],
        'reason_2': info['reason_2'],
        'reason_3': info['reason_3'],
        'process_name': info.get('process_name', ''),
        'purchaser': info.get('purchaser', ''),
        'nodes': node_details,
        'total_hours': total_hours,
    })

# 生成汇总统计
summary = {
    'total_orders': len(orders),
    'status_distribution': dict(status_dist),
    'process_distribution': dict(process_dist),
    'reason1_distribution': dict(reason1_dist),
    'avg_hours': round(sum(o['total_hours'] for o in order_timeliness if o['total_hours']) / max(1, len([o for o in order_timeliness if o['total_hours']])), 1),
    'max_hours': max((o['total_hours'] for o in order_timeliness if o['total_hours']), default=0),
    'min_hours': min((o['total_hours'] for o in order_timeliness if o['total_hours']), default=0),
}

# 节点时效汇总
node_duration_summary = defaultdict(list)
for o in order_timeliness:
    for n in o['nodes']:
        if n['duration_hours'] is not None:
            node_duration_summary[n['node_name']].append(n['duration_hours'])

node_stats = {}
for name, durations in node_duration_summary.items():
    node_stats[name] = {
        'avg': round(sum(durations) / len(durations), 1),
        'max': round(max(durations), 1),
        'min': round(min(durations), 1),
        'count': len(durations),
    }

result = {
    'summary': summary,
    'node_stats': node_stats,
    'orders': order_timeliness,
}

with open('bi_demo_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Generated bi_demo_data.json")
print(f"Total orders: {len(orders)}")
print(f"Orders with timeliness: {len(order_timeliness)}")
print(f"Node stats: {json.dumps(node_stats, ensure_ascii=False, indent=2)}")
print(f"Summary: {json.dumps(summary, ensure_ascii=False, indent=2)}")

wb.close()
