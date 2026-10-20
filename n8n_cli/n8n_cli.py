"""
n8n 远程工作流管理 CLI

通过企业 n8n Public API 管理远程工作流（无需本地安装 n8n）。

用法:
    python n8n_cli.py check                          # 检查连接与鉴权
    python n8n_cli.py list                           # 列出所有工作流
    python n8n_cli.py show <id> [--json]             # 查看工作流详情（节点/连线/配置）
    python n8n_cli.py activate <id>                  # 激活工作流
    python n8n_cli.py deactivate <id>                # 停用工作流
    python n8n_cli.py run <id> [--wait]              # 触发执行（--wait 等待完成）
    python n8n_cli.py executions [--limit N] [--status error|success|waiting]
    python n8n_cli.py execution <id> [--json]        # 查看某次执行详情
    python n8n_cli.py export <id> [file]             # 导出工作流 JSON（默认 out/<id>.json）
    python n8n_cli.py update <id> <file>             # 从 JSON 文件更新工作流
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BASE_URL, API_KEY

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "out")


def resolve_id(client, short_id):
    """将短 ID（前缀）解析为完整工作流 ID"""
    if len(short_id) >= 25:
        return short_id
    matches = [w["id"] for w in client.list_workflows() if w["id"].startswith(short_id)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        print(f"错误: 找不到以 {short_id} 开头的工作流，请用 list 命令确认 ID。")
        sys.exit(1)
    print(f"错误: ID 前缀 {short_id} 匹配到 {len(matches)} 个工作流，请输入更长的前缀。")
    sys.exit(1)

# PUT 更新时只允许提交的字段（服务端 schema 严格校验，多余字段会报 400）
ALLOWED_KEYS = ["name", "nodes", "connections", "settings"]


class N8nClient:
    def __init__(self, base_url, api_key):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "X-N8N-API-KEY": api_key,
            "Accept": "application/json",
        })

    def request(self, method, path, **kwargs):
        url = f"{self.base}{path}"
        resp = self.session.request(method, url, timeout=30, **kwargs)
        if resp.status_code == 401:
            print("错误: 鉴权失败(401)，API Key 无效或已失效，请到 n8n Settings 重新生成。")
            sys.exit(1)
        if resp.status_code == 404:
            print(f"错误: 资源不存在(404): {path}")
            sys.exit(1)
        if resp.status_code >= 400:
            print(f"错误: HTTP {resp.status_code}")
            try:
                print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
            except Exception:
                print(resp.text[:500])
            sys.exit(1)
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def health(self):
        resp = requests.get(f"{self.base}/healthz", timeout=15)
        return resp.status_code == 200

    # ---- 工作流 ----
    def list_workflows(self):
        return self.request("GET", "/api/v1/workflows?limit=100")["data"]

    def get_workflow(self, wid):
        return self.request("GET", f"/api/v1/workflows/{wid}")

    def activate(self, wid, active=True):
        action = "activate" if active else "deactivate"
        return self.request("POST", f"/api/v1/workflows/{wid}/{action}")

    def run_workflow(self, wid):
        return self.request("POST", f"/api/v1/workflows/{wid}/run", json={})

    def update_workflow(self, wid, payload):
        return self.request("PUT", f"/api/v1/workflows/{wid}", json=payload)

    # ---- 执行记录 ----
    def list_executions(self, limit=10, status=None):
        path = f"/api/v1/executions?limit={limit}"
        if status:
            path += f"&status={status}"
        return self.request("GET", path)["data"]

    def get_execution(self, eid):
        return self.request("GET", f"/api/v1/executions/{eid}")


# ==================== 命令实现 ====================

def cmd_check(args):
    c = N8nClient(BASE_URL, API_KEY)
    print(f"实例: {BASE_URL}")
    if not c.health():
        print("失败: /healthz 不可达")
        return
    print("健康检查: OK")
    wfs = c.list_workflows()
    print(f"鉴权检查: OK（可见 {len(wfs)} 个工作流）")


def cmd_list(args):
    c = N8nClient(BASE_URL, API_KEY)
    wfs = c.list_workflows()
    if not wfs:
        print("暂无工作流。")
        return
    print(f"\n工作流列表（共 {len(wfs)} 个）:\n")
    print(f"  {'ID':<10} {'状态':<6} {'节点':<4} 名称")
    print("  " + "-" * 70)
    for w in wfs:
        status = "激活" if w.get("active") else "停用"
        print(f"  {w['id'][:8]:<10} {status:<6} {len(w.get('nodes', [])):<4} {w['name']}")
        print(f"  {'':<10} 更新于 {w.get('updatedAt', '?')}")


def cmd_show(args):
    c = N8nClient(BASE_URL, API_KEY)
    w = c.get_workflow(resolve_id(c, args.id))
    if args.json:
        print(json.dumps(w, ensure_ascii=False, indent=2))
        return
    print(f"名称: {w['name']}")
    print(f"ID: {w['id']}")
    print(f"状态: {'已激活' if w.get('active') else '未激活'}")
    print(f"更新时间: {w.get('updatedAt')}")
    settings = w.get("settings", {}) or {}
    print(f"时区: {settings.get('timezone', '?')}  "
          f"保存失败执行: {settings.get('saveDataErrorExecution', '?')}  "
          f"保存成功执行: {settings.get('saveDataSuccessExecution', '?')}")
    print(f"\n节点（{len(w.get('nodes', []))} 个）:")
    for n in w.get("nodes", []):
        print(f"  - [{n['type']}] {n['name']}  (id={n['id'][:8]}, "
              f"disabled={n.get('disabled', False)})")
    print(f"\n连线关系:")
    for src, targets in (w.get("connections") or {}).items():
        src_name = next((n['name'] for n in w.get('nodes', []) if n['name'] == src), src)
        for conn_list in targets.values():
            for conn in conn_list:
                for tgt in conn:
                    print(f"  {src_name}  ->  {tgt['node']} ({tgt.get('type', '?')})")


def cmd_activate(args):
    c = N8nClient(BASE_URL, API_KEY)
    w = c.activate(resolve_id(c, args.id), active=not args.deactivate)
    print(f"已{'停用' if args.deactivate else '激活'}: {w['name']} ({w['id'][:8]})")


def cmd_run(args):
    c = N8nClient(BASE_URL, API_KEY)
    wid = resolve_id(c, args.id)
    result = c.run_workflow(wid)
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
    if args.wait:
        eid = None
        for k in ("executionId", "id", "data"):
            v = result.get(k) if isinstance(result, dict) else None
            if v:
                eid = v if isinstance(v, str) else v.get("id")
                break
        if eid:
            print(f"\n等待执行 {eid} 完成...")
            for _ in range(60):
                time.sleep(2)
                e = c.get_execution(eid)
                status = e.get("status")
                if status not in ("running", "new", "waiting"):
                    print(f"执行完成: status={status}")
                    _print_execution_summary(e)
                    return
                print(f"  状态: {status} ...")
            print("超时: 120 秒内未完成，可用 execution 命令稍后查看。")


def _print_execution_summary(e):
    print(f"工作流: {e.get('workflowId', '?')}")
    print(f"状态: {e.get('status')}")
    print(f"开始: {e.get('startedAt')}  结束: {e.get('stoppedAt')}")
    if e.get("error"):
        print(f"错误: {e['error']}"[:500])


def cmd_executions(args):
    c = N8nClient(BASE_URL, API_KEY)
    exs = c.list_executions(limit=args.limit, status=args.status)
    if not exs:
        print("暂无执行记录。")
        return
    print(f"\n执行记录（最近 {len(exs)} 条）:\n")
    for e in exs:
        print(f"  [{e['id'][:8]}] {e.get('status', '?'):<10} "
              f"workflow={str(e.get('workflowId'))[:8]}  {e.get('startedAt', '?')}")


def cmd_execution(args):
    c = N8nClient(BASE_URL, API_KEY)
    e = c.get_execution(args.id)
    if args.json:
        print(json.dumps(e, ensure_ascii=False, indent=2))
        return
    _print_execution_summary(e)
    data = (e.get("data") or {}).get("resultData", {})
    run_data = (e.get("data") or {}).get("runData", {})
    if run_data:
        print(f"\n各节点运行结果（{len(run_data)} 个节点）:")
        for node_name, runs in run_data.items():
            last = runs[-1] if runs else {}
            print(f"  - {node_name}: status={last.get('status', '?')} "
                  f"items={len(last.get('data', {}).get('main', []) or [])}")
            err = (last.get('error') or {})
            if err:
                print(f"      错误: {json.dumps(err, ensure_ascii=False)[:300]}")


def cmd_export(args):
    c = N8nClient(BASE_URL, API_KEY)
    wid = resolve_id(c, args.id)
    w = c.get_workflow(wid)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = args.file or os.path.join(OUT_DIR, f"{wid[:8]}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=2)
    print(f"已导出 {w['name']} -> {path}")


def cmd_update(args):
    c = N8nClient(BASE_URL, API_KEY)
    wid = resolve_id(c, args.id)
    with open(args.file, "r", encoding="utf-8") as f:
        w = json.load(f)
    payload = {k: w[k] for k in ALLOWED_KEYS if k in w}
    if "name" not in payload:
        print("错误: JSON 文件缺少 name 字段（PUT 需要完整工作流结构）")
        return
    result = c.update_workflow(wid, payload)
    print(f"已更新: {result['name']} ({result['id'][:8]})")


def main():
    parser = argparse.ArgumentParser(description="n8n 远程工作流管理 CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="检查连接与鉴权")

    sub.add_parser("list", help="列出所有工作流")

    p_show = sub.add_parser("show", help="查看工作流详情")
    p_show.add_argument("id", help="工作流 ID（前 8 位即可）")
    p_show.add_argument("--json", action="store_true", help="输出完整 JSON")

    p_act = sub.add_parser("activate", help="激活工作流")
    p_act.add_argument("id", help="工作流 ID")
    p_act.add_argument("--deactivate", action="store_true", help="改为停用")

    p_run = sub.add_parser("run", help="触发执行")
    p_run.add_argument("id", help="工作流 ID")
    p_run.add_argument("--wait", action="store_true", help="等待执行完成")

    p_exs = sub.add_parser("executions", help="列出执行记录")
    p_exs.add_argument("--limit", type=int, default=10)
    p_exs.add_argument("--status", choices=["error", "success", "waiting"], default=None)

    p_ex = sub.add_parser("execution", help="查看某次执行详情")
    p_ex.add_argument("id", help="执行 ID")
    p_ex.add_argument("--json", action="store_true")

    p_exp = sub.add_parser("export", help="导出工作流 JSON")
    p_exp.add_argument("id", help="工作流 ID")
    p_exp.add_argument("file", nargs="?", default=None, help="输出文件路径")

    p_upd = sub.add_parser("update", help="从 JSON 文件更新工作流")
    p_upd.add_argument("id", help="工作流 ID")
    p_upd.add_argument("file", help="JSON 文件路径")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmds = {"check": cmd_check, "list": cmd_list, "show": cmd_show,
            "activate": cmd_activate, "run": cmd_run, "executions": cmd_executions,
            "execution": cmd_execution, "export": cmd_export, "update": cmd_update}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
