# Git 敏感信息保护指南

## 📋 目录
- [问题说明](#问题说明)
- [解决方案](#解决方案)
- [快速开始](#快速开始)
- [详细步骤](#详细步骤)
- [自动化脚本使用](#自动化脚本使用)
- [常见问题](#常见问题)

---

## 问题说明

在开发过程中，我们经常需要在代码中配置敏感信息（如 API Key、AccessKey、数据库密码等）。如果不小心将这些信息提交到 Git 仓库并推送到远程（如 GitHub），会导致：

1. **安全风险**：密钥泄露，可能被恶意利用
2. **GitHub 阻止推送**：GitHub Secret Scanning 会自动检测并阻止包含密钥的推送
3. **历史污染**：即使后续删除，密钥仍存在于 Git 历史中

### 本项目遇到的问题

```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - GITHUB PUSH PROTECTION
remote:   - Push cannot contain secrets
remote:   - Alibaba Cloud AccessKey ID
remote:   - Alibaba Cloud AccessKey Secret
```

---

## 解决方案

### 核心策略：**分离配置文件与代码**

1. ✅ **本地保留真实配置**：`config.py` 包含真实的 AccessKey，仅本地使用
2. ✅ **Git 忽略敏感文件**：通过 `.gitignore` 防止敏感文件被提交
3. ✅ **提供配置模板**：创建 `config.py.example` 作为配置示例（不含真实密钥）
4. ✅ **清理 Git 历史**：移除历史中的敏感信息

---

## 快速开始

### 方法一：使用自动化脚本（推荐）

```bash
# 1. 初始化项目（首次使用）
python git_security_tool.py --init

# 2. 检查敏感信息状态
python git_security_tool.py --check

# 3. 安全提交代码
python git_security_tool.py --commit "feat: 添加新功能"
```

### 方法二：手动操作

```bash
# 1. 创建 .gitignore（如果不存在）
echo "config.py" >> .gitignore
echo "*.env" >> .gitignore

# 2. 生成配置模板
cp config.py config.py.example
# 编辑 config.py.example，将真实密钥替换为占位符

# 3. 验证配置
git check-ignore config.py  # 应该输出：.gitignore:XX:config.py config.py

# 4. 提交代码
git add .
git commit -m "chore: 添加敏感信息保护"
git push origin main
```

---

## 详细步骤

### 步骤 1：创建 .gitignore 文件

在项目根目录创建或更新 `.gitignore` 文件：

```gitignore
# Configuration files with secrets (重要！)
config.py
*.env
.env.local
.env.production
secrets.py
credentials.py

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Jupyter Notebook
.ipynb_checkpoints
*-checkpoint.ipynb

# Output directories
output/
notebook_output/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
```

### 步骤 2：生成配置模板

对于每个包含敏感信息的配置文件，创建一个对应的 `.example` 模板文件：

**原始文件 (config.py)**：
```python
"""MaxCompute 系统配置文件"""

ODPS_ACCESS_ID = 'YOUR_REAL_ACCESS_KEY_ID'          # AccessKey ID（示例）
ODPS_ACCESS_KEY = 'YOUR_REAL_ACCESS_KEY_SECRET'     # AccessKey Secret（示例）
ODPS_PROJECT = "cupshe_bigdata_ads"
ODPS_ENDPOINT = "https://service.eu-central-1.maxcompute.aliyun.com/api"
```

**模板文件 (config.py.example)**：
```python
"""
注意：此文件是配置模板，不包含真实的密钥信息
请复制此文件为 config.py 并填入你的真实配置
"""

ODPS_ACCESS_ID = 'YOUR_ACCESS_KEY_ID_HERE'          # 替换为你的 AccessKey ID
ODPS_ACCESS_KEY = 'YOUR_ACCESS_KEY_SECRET_HERE'     # 替换为你的 AccessKey Secret
ODPS_PROJECT = "cupshe_bigdata_ads"
ODPS_ENDPOINT = "https://service.eu-central-1.maxcompute.aliyun.com/api"
```

### 步骤 3：验证配置

```bash
# 检查 config.py 是否被忽略
git check-ignore config.py
# 应该输出：.gitignore:XX:config.py config.py

# 检查是否有待提交的敏感文件
git status
# config.py 不应该出现在列表中
```

### 步骤 4：提交代码

```bash
# 添加所有文件（config.py 会被自动忽略）
git add -A

# 查看将要提交的文件
git status

# 提交
git commit -m "chore: 添加敏感信息保护"

# 推送
git push origin main
```

---

## 自动化脚本使用

### 安装

无需安装，直接使用 Python 运行：

```bash
python git_security_tool.py --help
```

### 命令说明

#### 1. 初始化项目（首次使用）

```bash
python git_security_tool.py --init
```

功能：
- 创建/更新 `.gitignore` 文件
- 查找所有 `config.py` 和 `.env` 文件
- 自动生成对应的 `.example` 模板文件
- 验证配置是否正确

输出示例：
```
======================================================================
【初始化 Git 敏感信息保护】
======================================================================

[步骤 1] 创建/更新 .gitignore...
[SUCCESS] .gitignore 已更新，敏感文件将被忽略

[步骤 2] 生成配置模板...
[SUCCESS] 已生成模板: maxcompute_cli/config.py.example
[SUCCESS] 已生成模板: maxcompute_notebook/config.py.example

[步骤 3] 验证配置...
[SUCCESS] 所有检查通过！可以安全提交代码

======================================================================
[SUCCESS] 初始化完成！

下一步操作：
  1. 检查生成的 *.example 文件是否正确
  2. 运行: git add .
  3. 运行: git commit -m "chore: 添加敏感信息保护"
  4. 运行: git push origin main
======================================================================
```

#### 2. 检查敏感信息状态

```bash
python git_security_tool.py --check
```

功能：
- 检查 `.gitignore` 配置
- 检查配置文件是否存在及是否有对应模板
- 检查 Git 历史
- 检查暂存区是否有敏感文件

输出示例：
```
======================================================================
【敏感信息检查】
======================================================================

[1] 检查 .gitignore 配置...
  [OK] config.py 已被忽略

[2] 检查配置文件...
  找到 3 个配置文件:
    - maxcompute_cli/config.py
      ✓ 模板文件存在
    - maxcompute_notebook/config.py
      ✓ 模板文件存在
    - ollma查询/config.py
      ✓ 模板文件存在

[3] 检查 Git 历史...
  共有 2 个提交

[4] 检查暂存区...
  [OK] 工作区干净

======================================================================
[SUCCESS] 所有检查通过！可以安全提交代码
======================================================================
```

#### 3. 仅生成模板文件

```bash
python git_security_tool.py --template
```

功能：
- 只生成 `.example` 模板文件，不修改 `.gitignore`

#### 4. 安全提交代码

```bash
python git_security_tool.py --commit "feat: 添加新功能"
```

功能：
- 先执行敏感信息检查
- 确认无误后提交代码
- 可选推送到远程

---

## 如果已经提交了敏感信息怎么办？

### 情况 1：刚提交，还未推送

```bash
# 撤销最后一次提交（保留工作区文件）
git reset HEAD~1

# 更新 .gitignore
echo "config.py" >> .gitignore

# 重新提交
git add -A
git commit -m "chore: 添加敏感信息保护"
git push origin main
```

### 情况 2：已推送到远程

**方案 A：重写 Git 历史（推荐）**

```bash
# 1. 从干净的提交开始创建新分支
git checkout -b clean-main <clean-commit-hash>

# 2. 复制当前工作区的文件到新分支
git checkout main -- .

# 3. 确保 .gitignore 正确
echo "config.py" >> .gitignore

# 4. 提交
git add -A
git commit -m "chore: 添加敏感信息保护"

# 5. 强制推送（⚠️ 会覆盖远程历史）
git push origin clean-main --force

# 6. 在 GitHub 上设置 clean-main 为默认分支
# 7. 删除旧的 main 分支
```

**方案 B：使用 BFG Repo-Cleaner**

```bash
# 1. 下载 BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# 2. 创建 passwords.txt 文件，列出要删除的密钥
echo "YOUR_REAL_ACCESS_KEY_ID" >> passwords.txt
echo "YOUR_REAL_ACCESS_KEY_SECRET" >> passwords.txt

# 3. 运行 BFG
java -jar bfg.jar --replace-text passwords.txt my-repo.git

# 4. 清理并推送
cd my-repo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin main --force
```

**方案 C：在 GitHub 上允许密钥（仅用于测试环境）**

访问 GitHub 提供的链接，点击 "Allow secret"：
- https://github.com/<user>/<repo>/security/secret-scanning/unblock-secret/<token-id>

⚠️ **警告**：这会永久允许该密钥存在于仓库中，不推荐用于生产环境。

### 情况 3：更换新的 AccessKey（最安全）

1. 登录阿里云控制台
2. 禁用当前泄露的 AccessKey
3. 创建新的 AccessKey
4. 更新本地的 `config.py` 文件
5. 按照上述步骤重新提交

---

## 常见问题

### Q1: 为什么 config.py 还在我的项目中？

A: `.gitignore` 只会阻止文件被 Git 跟踪，不会删除本地文件。你的 `config.py` 仍然在本地，可以正常使用，只是不会被提交到 Git。

### Q2: 团队成员如何获取配置？

A: 团队成员克隆仓库后：
1. 复制 `config.py.example` 为 `config.py`
2. 填入自己的真实配置
3. 开始开发

```bash
cp config.py.example config.py
# 编辑 config.py，填入真实密钥
```

### Q3: 如何检查某个文件是否被 Git 忽略？

```bash
git check-ignore <file-path>
# 如果输出路径，说明被忽略；无输出说明未被忽略
```

### Q4: 如果我需要提交配置文件怎么办？

A: 不要直接提交包含真实密钥的配置文件。可以：
1. 提交 `.example` 模板文件
2. 使用环境变量代替硬编码密钥
3. 使用密钥管理服务（如 AWS Secrets Manager、Azure Key Vault）

### Q5: GitHub 仍然阻止推送怎么办？

A: 可能的原因：
1. Git 历史中仍有敏感信息 → 需要重写历史或使用 BFG 清理
2. 某些文件未被正确忽略 → 检查 `.gitignore` 和 `git status`
3. GitHub 缓存了旧数据 → 等待几分钟或联系 GitHub 支持

---

## 最佳实践

1. ✅ **始终使用 `.gitignore` 保护敏感文件**
2. ✅ **提供配置模板供团队成员参考**
3. ✅ **定期运行 `git_security_tool.py --check` 检查状态**
4. ✅ **使用环境变量管理密钥（生产环境）**
5. ✅ **定期轮换 AccessKey**
6. ❌ **不要在代码中硬编码密钥**
7. ❌ **不要将 `.env`、`config.py` 等文件提交到 Git**
8. ❌ **不要使用 `git add -f` 强制添加被忽略的文件**

---

## 相关资源

- [GitHub Secret Scanning 文档](https://docs.github.com/code-security/secret-scanning)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [Git 官方文档 - .gitignore](https://git-scm.com/docs/gitignore)
- [阿里云 AccessKey 管理](https://ram.console.aliyun.com/manage/ak)

---

## 总结

通过本指南，你已经学会了：
- ✅ 如何使用 `.gitignore` 保护敏感文件
- ✅ 如何生成配置模板
- ✅ 如何使用自动化脚本简化流程
- ✅ 如何处理已泄露的敏感信息

现在你可以安全地管理包含敏感信息的 Git 项目了！
