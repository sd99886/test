"""
飞书 API 读取表格数据模板
使用前请先安装依赖：pip install lark-oapi requests
然后在下方填入你的 APP_ID 和 APP_SECRET
"""

import requests
import json

# ==================== 配置区（必填） ====================
APP_ID = "cli_xxxxxxxxxxxxxx"           # 替换为你的 App ID
APP_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxx"  # 替换为你的 App Secret
# =======================================================


def get_tenant_access_token():
    """获取 tenant_access_token（有效期2小时）"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    resp = requests.post(url, json=payload)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"获取token失败: {data}")
    return data["tenant_access_token"]


def read_sheet(spreadsheet_token, sheet_range):
    """
    读取飞书电子表格
    :param spreadsheet_token: 表格URL中的token，例如：
        https://xxx.feishu.cn/sheets/shtcnABC123  ->  token = "shtcnABC123"
    :param sheet_range: 读取范围，格式为 "工作表ID!范围"，例如 "0!A1:Z100"
    :return: 二维数组，每行一个列表
    """
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_range}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"读取失败: {data}")
    return data["data"]["valueRange"]["values"]


def read_bitable(app_token, table_id, page_size=100):
    """
    读取飞书多维表格
    :param app_token: 多维表格URL中的token，例如：
        https://xxx.feishu.cn/base/bascnABC123  ->  token = "bascnABC123"
    :param table_id: 数据表ID，例如 "tblcnABC123"
    :param page_size: 每页记录数，最大500
    :return: 记录列表，每条记录的 fields 字段为字典
    """
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    all_records = []
    page_token = None

    while True:
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"读取失败: {data}")

        items = data["data"].get("items", [])
        all_records.extend(items)

        if not data["data"].get("has_more"):
            break
        page_token = data["data"].get("page_token")

    return all_records


# ==================== 使用示例 ====================
if __name__ == "__main__":

    # --- 示例1：读取电子表格 ---
    # spreadsheet_token = "shtcnXXXXXXXXXXXXXX"   # 从表格URL中获取
    # sheet_range = "0!A1:Z100"                    # 工作表ID!范围
    # rows = read_sheet(spreadsheet_token, sheet_range)
    # for row in rows:
    #     print(row)

    # --- 示例2：读取多维表格 ---
    # app_token = "bascnXXXXXXXXXXXXXX"            # 从多维表格URL中获取
    # table_id = "tblcnXXXXXXXXXXXXXX"             # 数据表ID
    # records = read_bitable(app_token, table_id)
    # for record in records:
    #     print(record["fields"])

    print("请先填入 APP_ID 和 APP_SECRET，然后取消注释对应的示例代码")
