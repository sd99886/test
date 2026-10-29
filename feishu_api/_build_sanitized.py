# -*- coding: utf-8 -*-
r"""构建脱敏版 skill：skills_local/<skill> -> skills/<skill>

脱敏规则（对照公网仓库推送标准）：
1. config.py 删除，替换为 config.py.example（凭证占位）
2. 真实文档/表格 token、open_id → 占位符
3. 个人路径 c:\Users\Cupshe\Desktop\test → os.getcwd()（BASE 默认值）
4. 企业租户域名 mycupshe.feishu.cn -> <your-tenant>.feishu.cn
5. 数仓 schema cupshe_bigdata_ads -> {{PROJECT_SCHEMA}}（render_sql.py --schema 填充）
6. SKILL.md 中个人路径 -> <workspace 根目录>

构建后自动扫描敏感模式残留，零残留才通过。
"""
import io, os, re, shutil, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="gbk", errors="replace")

ROOT = r"c:\Users\Cupshe\Desktop\test"
SRC = os.path.join(ROOT, "skills_local")
DST = os.path.join(ROOT, "skills")
SKILLS = ["ops-report-full", "ops-category-analysis", "ops-weekly-report"]

CONFIG_EXAMPLE = '''# -*- coding: utf-8 -*-
# 飞书应用凭证模板：复制本文件为 config.py 并填入真实值（config.py 已被 .gitignore 排除，勿提交）
# 在 https://open.feishu.cn/app 创建应用后获取；回调地址需在应用「安全设置」中预先配置
APP_ID = "cli_xxxxxxxxxxxxxxxx"        # 替换为你的 App ID
APP_SECRET = "your_app_secret_here"    # 替换为你的 App Secret

# OAuth2 回调地址（用于获取 user_access_token）
REDIRECT_URI = "http://localhost:8899/callback"

# 本地服务端口（用于接收 OAuth 回调）
LOCAL_PORT = 8899
'''

REPL = [
    # (pattern, replacement, 文件类型过滤 None=全部)
    (r'aA4JAk0Va9AnpmDldbHiqdMppWQMCykR', 'your_app_secret_here', None),
    (r'cli_a8d0369eaa3a100d', 'cli_xxxxxxxxxxxxxxxx', None),
    (r'XqvbsP48PhNZjDtHsggckWdwnsg', '', None),
    (r'ITAadIR23oNBPpxLn18cXTHcn4R', 'YOUR_DOC_ID', None),
    (r'M9TFdMgPBo3hifxXxypcgWNjnDf', 'YOUR_DOC_ID', None),
    (r'ou_9622d8482039cfcdb3cba1d600e0ead9', 'YOUR_APP_OPEN_ID', None),
    (r'ou_95b321ebb637e9740538ce368c051279', 'YOUR_USER_OPEN_ID', None),
    (r'https://mycupshe\.feishu\.cn', 'https://<your-tenant>.feishu.cn', None),
    (r'c:\\Users\\Cupshe\\Desktop\\test', '<workspace根目录>', r'\.md$'),          # 文档中
    (r'or r"c:\\Users\\Cupshe\\Desktop\\test"', 'or os.getcwd()', r'\.py$'),  # 代码 BASE 默认值
    (r'cupshe_bigdata_cdm', '{{CDM_SCHEMA}}', None),
    (r'CUPSHE_BIGDATA_ADS_dev', '{{ADS_DEV_SCHEMA}}', None),
    (r'cupshe_bigdata_ads', '{{PROJECT_SCHEMA}}', None),
]

# 敏感残留扫描（构建后必须全零）
SCAN = {
    'APP_SECRET': r'aA4JAk0Va9AnpmDldbHiqdMppWQMCykR',
    'APP_ID': r'cli_a8d0369eaa3a100d',
    'sheet_token': r'XqvbsP48PhNZjDtHsggckWdwnsg',
    'doc_id': r'\b[A-Za-z0-9]{25,}\b.*(docx|sheets)|ITAadIR|M9TFdMg',
    'open_id': r'ou_[0-9a-f]{20,}',
    'tenant_domain': r'mycupshe\.feishu\.cn',
    'user_path': r'Cupshe',
    'real_schema': r'(?i)cupshe_bigdata',
}

for skill in SKILLS:
    src_dir = os.path.join(SRC, skill)
    dst_dir = os.path.join(DST, skill)
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir)
    print(f"== {skill} ==")

    # 1) config.py -> config.py.example
    for sub in ("", os.path.join("scripts", "")):
        cfg = os.path.join(dst_dir, sub, "config.py")
        if os.path.exists(cfg):
            os.remove(cfg)
            with io.open(os.path.join(dst_dir, sub, "config.py.example"), "w", encoding="utf-8") as f:
                f.write(CONFIG_EXAMPLE)
            print("   config.py -> config.py.example")

    # 2) 逐文件替换
    for dirpath, _, files in os.walk(dst_dir):
        for fn in files:
            fp = os.path.join(dirpath, fn)
            if not fn.endswith((".py", ".md", ".tpl", ".txt")):
                continue
            src = io.open(fp, encoding="utf-8").read()
            out = src
            for pat, rep, ffilter in REPL:
                if ffilter and not re.search(ffilter, fn):
                    continue
                out = re.sub(pat, rep, out)
            if out != src:
                io.open(fp, "w", encoding="utf-8").write(out)
                print(f"   sanitized: {os.path.relpath(fp, dst_dir)}")

# 3) 敏感残留扫描
print("\n== 残留扫描 ==")
clean = True
for dirpath, _, files in os.walk(DST):
    for fn in files:
        fp = os.path.join(dirpath, fn)
        if not fn.endswith((".py", ".md", ".tpl", ".txt")):
            continue
        src = io.open(fp, encoding="utf-8").read()
        for name, pat in SCAN.items():
            hits = re.findall(pat, src)
            if hits:
                clean = False
                print(f"   [FAIL] {os.path.relpath(fp, DST)} 含 {name} x{len(hits)}")
print("ALL CLEAN" if clean else "HAS SENSITIVE RESIDUE - DO NOT PUSH")
sys.exit(0 if clean else 1)
