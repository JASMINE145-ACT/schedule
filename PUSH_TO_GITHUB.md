# 推送到 GitHub 指南

本指南帮助你将 Travel Planner Service 项目安全地推送到 GitHub。

## ✅ 安全检查清单

在推送前，请确认：

- [x] 已创建 `.gitignore` 文件（忽略 `.env`、`*.db`、`__pycache__` 等）
- [x] 代码中没有硬编码的 API keys
- [x] 已创建 `.env.example` 作为模板
- [x] 数据库文件已被忽略

## 📝 推送步骤

### 1. 初始化 Git 仓库（如果还没有）

```powershell
cd D:\Projects\agent-jk\analysis\travel_planner_service

# 检查是否已经是 git 仓库
git status

# 如果不是，初始化仓库
git init
```

### 2. 检查 .gitignore 是否生效

```powershell
# 查看会被忽略的文件
git status --ignored

# 确认 .env 和 .db 文件被忽略
```

### 3. 添加文件到 Git

```powershell
# 添加所有文件（.gitignore 会自动排除敏感文件）
git add .

# 查看将要提交的文件（确认没有敏感信息）
git status
```

### 4. 创建初始提交

```powershell
git commit -m "Initial commit: Travel Planner Service V2

- FastAPI backend with LLM-driven conversational planning
- Streamlit frontend with chat interface
- Google Maps integration
- Anthropic Claude integration
- SQLite database for history"
```

### 5. 在 GitHub 上创建新仓库

1. 登录 GitHub
2. 点击右上角 "+" → "New repository"
3. 填写仓库信息：
   - Repository name: `travel-planner-service`（或你喜欢的名称）
   - Description: `智能旅行规划服务 - 基于 FastAPI 和 Streamlit`
   - Visibility: Public 或 Private（根据你的选择）
   - **不要**勾选 "Initialize with README"（因为我们已经有了）
4. 点击 "Create repository"

### 6. 连接本地仓库到 GitHub

```powershell
# 替换 YOUR_USERNAME 和 YOUR_REPO_NAME 为实际值
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 或使用 SSH（如果你配置了 SSH key）
# git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git

# 验证远程仓库
git remote -v
```

### 7. 推送代码到 GitHub

```powershell
# 推送主分支
git branch -M main
git push -u origin main
```

### 8. 验证推送结果

1. 访问你的 GitHub 仓库页面
2. 确认所有文件都已上传
3. **重要**：确认没有 `.env` 文件
4. **重要**：确认没有数据库文件（`*.db`）
5. 确认 `.env.example` 文件存在

## 🔒 安全最佳实践

### 在 GitHub 仓库中添加 README 说明

在 `README.md` 中已经有环境变量配置说明，确保用户知道：

1. 需要创建 `.env` 文件
2. 需要获取 API keys
3. 参考 `.env.example` 模板

### 如果意外推送了敏感信息

如果发现意外推送了 `.env` 或 API keys：

```powershell
# 1. 立即从 git 历史中删除敏感文件
git rm --cached .env
git commit -m "Remove sensitive .env file"

# 2. 强制推送（警告：这会重写历史）
git push --force origin main

# 3. 在 GitHub 上重新生成 API keys（重要！）
```

### 设置 GitHub Secrets（如果使用 Actions）

如果将来要使用 GitHub Actions，在仓库设置中配置 Secrets：

1. Settings → Secrets and variables → Actions
2. 添加 `ANTHROPIC_API_KEY`
3. 添加 `GOOGLE_MAPS_API_KEY`

## 📋 推送后检查清单

- [ ] 代码已成功推送到 GitHub
- [ ] `.env` 文件**不在**仓库中
- [ ] 数据库文件**不在**仓库中
- [ ] `.env.example` 文件存在
- [ ] `README.md` 包含配置说明
- [ ] `.gitignore` 文件正确配置

## 🎉 完成！

你的代码现在已经安全地推送到 GitHub 了！

## 📚 后续步骤

1. **添加 License**（可选）
   - 在 GitHub 仓库设置中添加 License

2. **添加 Topics**（可选）
   - 在仓库页面点击 ⚙️ → Topics
   - 添加标签如：`python`, `fastapi`, `streamlit`, `travel-planner`, `llm`

3. **添加 README badge**（可选）
   - 在 README.md 顶部添加状态徽章

4. **设置分支保护**（可选）
   - Settings → Branches → Add rule

