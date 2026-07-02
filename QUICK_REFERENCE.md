# Git 敏感信息保护 - 快速参考卡片

## 🚀 快速开始（30秒）

```bash
# 1. 检查当前状态
python git_security_tool.py --check

# 2. 如果未初始化，运行
python git_security_tool.py --init

# 3. 安全提交代码
python git_security_tool.py --commit "feat: 你的修改"
```

---

##  常用命令速查

### 检查与验证

```bash
# 检查敏感信息状态
python git_security_tool.py --check

# 手动检查文件是否被忽略
git check-ignore config.py
# 输出: .gitignore:35:config.py  config.py  ✓ 已忽略
# 无输出  ✗ 未忽略（危险！）

# 查看待提交的文件
git status
# 确认 config.py 不在列表中
```

### 配置文件管理

```bash
# 生成配置模板（首次使用）
python git_security_tool.py --template

# 团队成员获取配置
cp config.py.example config.py
# 编辑 config.py，填入真实密钥
```

### Git 操作

```bash
# ✅ 正确的提交流程
git add -A              # 添加所有文件（config.py 会被自动忽略）
git commit -m "message" # 提交
git push origin main    # 推送

# ❌ 错误的做法（绝对不要做！）
git add config.py       # 不要直接添加敏感文件
git add -f config.py    # 不要强制添加！

# 撤销错误提交
git reset HEAD~1        # 撤销最后一次提交
git rm --cached config.py  # 从暂存区移除
echo "config.py" >> .gitignore  # 添加到忽略列表
```

---

## 🔍 故障排查

### 问题 1: GitHub 阻止推送

**症状:**
```
remote: error: GH013: Repository rule violations found
remote: - Push cannot contain secrets
```

**解决方案:**

方案 A - 在 GitHub 上允许（仅测试环境）:
1. 访问错误信息中的链接
2. 点击 "Allow secret"
3. 重新推送

方案 B - 清理历史（推荐）:
```bash
# 从干净提交创建新分支
git checkout -b clean-main <clean-commit-hash>
git checkout main -- .
git push origin clean-main --force
```

方案 C - 更换密钥（最安全）:
1. 登录阿里云控制台
2. 禁用旧 AccessKey
3. 创建新 AccessKey
4. 更新本地 config.py

### 问题 2: config.py 出现在 git status 中

**原因:** .gitignore 配置不正确

**解决:**
```bash
# 检查 .gitignore 是否存在
cat .gitignore | grep config.py

# 如果没有，添加规则
echo "config.py" >> .gitignore
echo "*.env" >> .gitignore

# 验证
git check-ignore config.py
```

### 问题 3: Jupyter Notebook 仍显示旧代码

**原因:** Jupyter 缓存了旧版本

**解决:**
1. 关闭 Jupyter Notebook/Lab
2. 删除 `.ipynb_checkpoints` 目录
3. 重新打开 notebook

```bash
rm -rf .ipynb_checkpoints
```

---

## 📁 项目结构

```
project/
── .gitignore                    # ← 忽略敏感文件
├── git_security_tool.py          # ← 自动化脚本
├── GIT_SECURITY_GUIDE.md         # ← 详细文档
├── demo_git_security.py          # ← 演示脚本
│
├── maxcompute_cli/
│   ├── config.py                 # ️ 本地文件（不提交）
│   ├── config.py.example         # ✓ 模板文件（提交）
│   ├── main.py                   # ✓ 业务代码（提交）
│   └── sql/query.sql             # ✓ SQL 文件（提交）
│
├── maxcompute_notebook/
│   ├── config.py                 # ⚠️ 本地文件（不提交）
│   ├── config.py.example         # ✓ 模板文件（提交）
│   └── query.ipynb               # ✓ Notebook（提交）
│
└── ollma查询/
    ├── config.py                 # ⚠️ 本地文件（不提交）
    └── config.py.example         # ✓ 模板文件（提交）
```

---

## 🛡️ 最佳实践清单

- [ ] 每个新项目首先运行 `python git_security_tool.py --init`
- [ ] 每次提交前运行 `python git_security_tool.py --check`
- [ ] 定期审查 `.gitignore` 文件
- [ ] 不要使用 `git add -f` 强制添加被忽略的文件
- [ ] 提供清晰的 README 说明配置步骤
- [ ] 使用环境变量管理生产环境密钥
- [ ] 定期轮换 AccessKey

---

## 📞 获取帮助

### 文档
- 详细指南: [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md)
- 演示脚本: `python demo_git_security.py`

### 命令帮助
```bash
python git_security_tool.py --help
```

### 常见问题
1. **Q:** 我的 config.py 还在本地吗？  
   **A:** 是的，`.gitignore` 只是防止它被提交到 Git，不影响本地使用。

2. **Q:** 团队成员如何获取配置？  
   **A:** 复制 `config.py.example` 为 `config.py`，然后填入自己的密钥。

3. **Q:** 如何检查文件是否被忽略？  
   **A:** 运行 `git check-ignore <file-path>`，有输出表示已忽略。

4. **Q:** GitHub 仍然阻止推送怎么办？  
   **A:** 检查 Git 历史中是否有敏感信息，可能需要重写历史或联系 GitHub 支持。

---

## 🔐 安全提示

⚠️ **重要提醒:**

1. **永远不要**在代码中硬编码真实的密钥
2. **永远不要**使用 `git add -f` 强制添加被忽略的文件
3. **定期检查** Git 历史中是否有泄露的密钥
4. **立即轮换**已泄露的 AccessKey
5. **使用环境变量**管理生产环境的敏感信息

---

## 🎯 一分钟教程

**场景:** 你刚克隆了一个项目，需要开始开发

```bash
# 1. 查看项目结构
ls -la

# 2. 检查是否有配置模板
ls config.py.example  # 或 find . -name "config.py.example"

# 3. 复制模板并配置
cp config.py.example config.py
vim config.py  # 填入你的真实 AccessKey

# 4. 验证配置
python git_security_tool.py --check

# 5. 开始开发
python main.py

# 6. 完成后提交
git add -A
git commit -m "feat: 完成功能开发"
git push origin main
```

**完成！** 

---

*最后更新: 2026-07-02*  
*版本: 1.0.0*
