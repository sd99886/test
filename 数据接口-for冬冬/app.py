"""
数据API服务（纯数据接口，供外部AI平台调用）

功能：
1. 数分编写SQL → 自动封装为REST API
2. 外部AI平台调用接口获取数据 → AI自行分析

部署方式：
- 本地开发：python app.py
- 生产环境：使用 gunicorn/uwsgi + Nginx 反向代理
"""
import sys
import os
import json
import time
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import pandas as pd

from functools import wraps
from config import (
    ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_PROJECT, ODPS_ENDPOINT,
    API_HOST, API_PORT, MAX_RESULT_ROWS, SQL_DIR, API_KEY
)

app = Flask(__name__)
CORS(app)  # 允许跨域，方便外部AI平台调用


# ============ API Key 认证 ============

def require_api_key(f):
    """API Key 验证装饰器
    
    调用方式（二选一）：
    1. Header: X-API-Key: your-key
    2. URL参数: ?api_key=your-key
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 如果 API_KEY 为空，不启用认证
        if not API_KEY:
            return f(*args, **kwargs)
        
        # 从 Header 或 URL 参数获取 key
        key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not key:
            return jsonify({
                'success': False,
                'error': '缺少 API Key，请在 Header 中传入 X-API-Key 或 URL 参数 api_key'
            }), 401
        
        if key != API_KEY:
            return jsonify({
                'success': False,
                'error': 'API Key 无效'
            }), 403
        
        return f(*args, **kwargs)
    return decorated


# ============ MaxCompute 连接 ============
_odps_connection = None

def get_odps():
    """获取 ODPS 连接（懒加载单例）"""
    global _odps_connection
    if _odps_connection is None:
        from odps import ODPS
        _odps_connection = ODPS(
            ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_PROJECT,
            endpoint=ODPS_ENDPOINT
        )
        print(f'[ODPS] 连接成功: {ODPS_PROJECT}')
    return _odps_connection


# ============ SQL 管理 ============

def get_sql_dir():
    """获取 SQL 目录绝对路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), SQL_DIR)


def list_sql_files():
    """列出所有 SQL 文件"""
    sql_dir = get_sql_dir()
    if not os.path.exists(sql_dir):
        return []
    files = [f for f in os.listdir(sql_dir) if f.endswith('.sql')]
    return sorted(files)


def load_sql(filename):
    """加载指定 SQL 文件内容"""
    filepath = os.path.join(get_sql_dir(), filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read().strip()


def execute_sql(sql, max_rows=None):
    """执行 SQL 并返回 DataFrame"""
    if max_rows is None:
        max_rows = MAX_RESULT_ROWS
    
    o = get_odps()
    start = time.time()
    
    # 执行 SQL
    instance = o.execute_sql(sql)
    instance.wait_for_success()
    
    # 读取结果（Instance Tunnel 加速）
    with instance.open_reader(tunnel=True) as reader:
        df = reader.to_pandas()
    
    # 限制行数
    if len(df) > max_rows:
        df = df.head(max_rows)
    
    elapsed = time.time() - start
    return df, elapsed


def df_to_response(df, exec_time):
    """将 DataFrame 转为 API 响应格式"""
    # 处理 NaN/None
    df = df.fillna('')
    
    records = df.to_dict(orient='records')
    
    return {
        'success': True,
        'data': records,
        'columns': list(df.columns),
        'row_count': len(df),
        'exec_time': round(exec_time, 2),
        'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


# ============ 页面路由 ============

@app.route('/')
def index():
    """API 文档首页"""
    return render_template('index.html')


@app.route('/admin')
def admin():
    """SQL 管理后台（数分专用）"""
    return render_template('admin.html')


# ============ 数据API路由 ============

@app.route('/api/queries', methods=['GET'])
@require_api_key
def api_list_queries():
    """
    列出所有可用的数据接口
    
    响应示例：
    {
        "success": true,
        "queries": [
            {
                "name": "sales_report",
                "description": "销售报表查询",
                "api_url": "/api/query/sales_report",
                "full_url": "http://your-server.com/api/query/sales_report"
            }
        ]
    }
    """
    files = list_sql_files()
    queries = []
    base_url = request.host_url.rstrip('/')
    
    for f in files:
        name = f.replace('.sql', '')
        sql = load_sql(f)
        # 提取 SQL 第一行注释作为描述
        desc = ''
        for line in sql.split('\n'):
            if line.strip().startswith('--'):
                desc = line.strip().lstrip('-').strip()
                break
        
        queries.append({
            'name': name,
            'description': desc or '暂无描述',
            'api_url': f'/api/query/{name}',
            'full_url': f'{base_url}/api/query/{name}',
            'sql_preview': sql[:300] if sql else ''
        })
    
    return jsonify({'success': True, 'queries': queries})


@app.route('/api/query/<name>', methods=['GET'])
@require_api_key
def api_execute_query(name):
    """
    执行指定 SQL 查询并返回数据
    
    参数：
    - limit (可选): 最大返回行数，默认 1000
    
    响应示例：
    {
        "success": true,
        "data": [{"字段1": "值1", "字段2": "值2"}, ...],
        "columns": ["字段1", "字段2"],
        "row_count": 100,
        "exec_time": 5.23,
        "query_time": "2026-07-03 16:30:00"
    }
    """
    sql_file = f'{name}.sql'
    sql = load_sql(sql_file)
    
    if sql is None:
        return jsonify({'success': False, 'error': f'查询不存在: {name}'}), 404
    
    # 支持 URL 参数覆盖限制
    max_rows = request.args.get('limit', MAX_RESULT_ROWS, type=int)
    
    try:
        df, exec_time = execute_sql(sql, max_rows)
        return jsonify(df_to_response(df, exec_time))
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/query', methods=['POST'])
@require_api_key
def api_execute_custom_sql():
    """
    执行自定义 SQL（临时测试用，不推荐生产环境使用）
    
    请求体：
    {
        "sql": "SELECT * FROM table LIMIT 10",
        "limit": 100  // 可选
    }
    """
    data = request.get_json()
    if not data or 'sql' not in data:
        return jsonify({'success': False, 'error': '请提供 sql 参数'}), 400
    
    sql = data['sql']
    max_rows = data.get('limit', MAX_RESULT_ROWS)
    
    try:
        df, exec_time = execute_sql(sql, max_rows)
        return jsonify(df_to_response(df, exec_time))
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============ SQL 编辑路由（数分管理后台）============

@app.route('/api/sql/<name>', methods=['GET'])
def api_get_sql(name):
    """读取指定 SQL 文件内容"""
    # 安全检查：防止路径穿越
    if not name.isalnum() and '-' not in name and '_' not in name:
        return jsonify({'success': False, 'error': '文件名不合法'}), 400
    
    filename = f'{name}.sql'
    sql = load_sql(filename)
    
    if sql is None:
        return jsonify({'success': False, 'error': f'SQL文件不存在: {name}'}), 404
    
    return jsonify({'success': True, 'name': name, 'sql': sql})


@app.route('/api/sql/save', methods=['POST'])
def api_save_sql():
    """保存 SQL 文件（数分编写SQL后保存）"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请提供请求参数'}), 400
    
    name = data.get('name', 'query').strip()
    sql_content = data.get('sql', '').strip()
    
    if not sql_content:
        return jsonify({'success': False, 'error': 'SQL内容不能为空'}), 400
    
    # 安全检查：文件名只允许字母数字下划线中划线
    if not all(c.isalnum() or c in '-_' for c in name):
        return jsonify({'success': False, 'error': '文件名只能包含字母、数字、下划线、中划线'}), 400
    
    # 确保 SQL 目录存在
    sql_dir = get_sql_dir()
    os.makedirs(sql_dir, exist_ok=True)
    
    # 保存文件
    filename = f'{name}.sql'
    filepath = os.path.join(sql_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    return jsonify({
        'success': True,
        'name': name,
        'api_url': f'/api/query/{name}',
        'message': f'SQL已保存: {filename}'
    })


# ============ 启动 ============

if __name__ == '__main__':
    print('=' * 60)
    print('  数据API服务（供外部AI平台调用）')
    print('=' * 60)
    print(f'  API文档: http://{API_HOST}:{API_PORT}/')
    print(f'  管理后台: http://{API_HOST}:{API_PORT}/admin')
    print(f'  接口列表: http://{API_HOST}:{API_PORT}/api/queries')
    print('=' * 60)
    print(f'\n⚠️  注意：当前为开发模式，生产环境请使用 gunicorn/uwsgi')
    print('=' * 60)
    
    app.run(
        host=API_HOST,
        port=API_PORT,
        debug=True
    )
