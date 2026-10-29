"""
分析 proc_production_exception_order_node 数据，评估拉链表可行性
"""
import csv
from collections import defaultdict
from datetime import datetime

# 解析数据
rows = []
with open('pasted-text.txt', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')
    header = next(reader)
    for row in reader:
        if len(row) >= 12:
            rows.append({
                'id': int(row[0]),
                'exception_order_id': int(row[1]),
                'node_id': int(row[2]),
                'node_seq': int(row[3]),
                'node_name': row[4],
                'handler_id': int(row[5]),
                'status': int(row[6]),
                'gmt_create': row[7].strip(),
                'gmt_modified': row[8].strip(),
                'creator_id': int(row[9]) if row[9].strip() else None,
                'modifier_id': int(row[10]) if row[10].strip() else None,
                'is_del': int(row[11]),
            })

print(f"总记录数: {len(rows)}")
print(f"字段列表: {header}")
print()

# 1. status 分布
status_dist = defaultdict(int)
for r in rows:
    status_dist[r['status']] += 1
print("=== status 分布 ===")
for s, c in sorted(status_dist.items()):
    print(f"  status={s}: {c} 条")
print()

# 2. is_del 分布
del_dist = defaultdict(int)
for r in rows:
    del_dist[r['is_del']] += 1
print("=== is_del 分布 ===")
for d, c in sorted(del_dist.items()):
    print(f"  is_del={d}: {c} 条")
print()

# 3. status=4 与 is_del=1 的关系
print("=== status=4 与 is_del=1 交叉分析 ===")
s4_d1 = sum(1 for r in rows if r['status'] == 4 and r['is_del'] == 1)
s4_d0 = sum(1 for r in rows if r['status'] == 4 and r['is_del'] == 0)
s1_d1 = sum(1 for r in rows if r['status'] == 1 and r['is_del'] == 1)
print(f"  status=4 且 is_del=1: {s4_d1} 条")
print(f"  status=4 且 is_del=0: {s4_d0} 条")
print(f"  status=1 且 is_del=1: {s1_d1} 条")
print()

# 4. 每个 exception_order 的节点数
order_nodes = defaultdict(list)
for r in rows:
    order_nodes[r['exception_order_id']].append(r)
node_counts = [len(v) for v in order_nodes.values()]
print(f"=== 异常单节点链路 ===")
print(f"  异常单总数: {len(order_nodes)}")
print(f"  每单节点数: min={min(node_counts)}, max={max(node_counts)}, avg={sum(node_counts)/len(node_counts):.1f}")
print()

# 5. 同一 node_id 是否有多条记录（关键！）
node_records = defaultdict(list)
for r in rows:
    node_records[r['node_id']].append(r)
multi = {k: v for k, v in node_records.items() if len(v) > 1}
print(f"=== 同一 node_id 多条记录分析 ===")
print(f"  唯一 node_id 数: {len(node_records)}")
print(f"  有多条记录的 node_id: {len(multi)} 个")
if multi:
    print("  示例（前3个）:")
    for nid in sorted(multi.keys())[:3]:
        recs = sorted(multi[nid], key=lambda x: x['id'])
        print(f"    node_id={nid}:")
        for rec in recs:
            print(f"      id={rec['id']}, status={rec['status']}, "
                  f"handler={rec['handler_id']}, create={rec['gmt_create']}, "
                  f"modified={rec['gmt_modified']}, is_del={rec['is_del']}")
print()

# 6. 时间字段完整性
no_create = sum(1 for r in rows if not r['gmt_create'])
no_modified = sum(1 for r in rows if not r['gmt_modified'])
print(f"=== 时间字段完整性 ===")
print(f"  gmt_create 为空: {no_create} 条")
print(f"  gmt_modified 为空: {no_modified} 条")
print()

# 7. 节点名称种类
names = set(r['node_name'] for r in rows)
print(f"=== 节点名称种类 ({len(names)} 种) ===")
for n in sorted(names):
    cnt = sum(1 for r in rows if r['node_name'] == n)
    print(f"  {n}: {cnt} 条")
print()

# 8. 示例异常单完整链路
print("=== 示例异常单完整链路 ===")
for oid in [28, 71, 85, 470]:
    if oid in order_nodes:
        nodes = sorted(order_nodes[oid], key=lambda x: x['node_seq'])
        print(f"\n  exception_order_id={oid}:")
        for n in nodes:
            print(f"    seq={n['node_seq']}, name={n['node_name']}, "
                  f"status={n['status']}, handler={n['handler_id']}, "
                  f"create={n['gmt_create']}, modified={n['gmt_modified']}, "
                  f"is_del={n['is_del']}")

# 9. handler_id 变更分析
print("\n=== handler_id 变更分析 ===")
handler_changes = 0
for nid, recs in node_records.items():
    if len(recs) > 1:
        handlers = set(r['handler_id'] for r in recs)
        if len(handlers) > 1:
            handler_changes += 1
print(f"  handler_id 发生变化的 node_id: {handler_changes} 个")
