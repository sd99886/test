"""
将 JSON 数据嵌入 HTML 模板
"""
import json

with open('bi_demo_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 只取前30个工单用于demo
data['orders'] = data['orders'][:30]

json_str = json.dumps(data, ensure_ascii=False)

with open('bi_dashboard_demo.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('DEMO_DATA_PLACEHOLDER', json_str)

with open('bi_dashboard_demo.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done! HTML file size: {len(html)} chars")
print(f"Orders embedded: {len(data['orders'])}")
