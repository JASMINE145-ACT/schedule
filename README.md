# 商务行程规划服务

基于 Google Maps API 和 Claude Haiku 3.5 的智能商务行程规划服务，提供后端 FastAPI 和 Streamlit 前端界面。

## 功能特性

- ✅ **真实地理数据**: 集成 Google Maps API 获取准确的距离和时间数据
- ✅ **智能路线优化**: 使用 Claude Haiku 3.5 进行路线优化和风险评估
- ✅ **交通高峰考虑**: 自动识别和避开交通高峰时段
- ✅ **风险评估**: 识别高风险路段并提供缓解建议
- ✅ **替代方案**: 为每 day 生成精简版替代方案
- ✅ **历史记录**: 保存和查看历史规划记录
- ✅ **美观界面**: Streamlit 提供友好的交互界面

## 项目结构

```
travel_planner_service/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── main.py      # FastAPI 主应用
│   │   ├── models.py    # Pydantic 模型
│   │   ├── database.py  # 数据库模型
│   │   ├── services/    # 核心服务
│   │   │   ├── maps_service.py      # Google Maps 封装
│   │   │   ├── llm_service.py       # Claude LLM 调用
│   │   │   ├── route_optimizer.py   # 路线优化逻辑
│   │   │   └── report_generator.py  # 报告生成
│   │   └── routers/     # API 路由
│   ├── requirements.txt
│   └── run_server.py
├── frontend/            # Streamlit 前端
│   ├── app.py          # 主应用
│   └── requirements.txt
├── tests/              # 测试代码
├── docs/               # 文档
└── start_all.bat       # 一键启动脚本
```

## 快速开始

### 1. 环境准备

**必需的环境变量：**
- `ANTHROPIC_API_KEY`: Claude API Key
- `GOOGLE_MAPS_API_KEY`: Google Maps API Key

**获取 API Keys：**
- Anthropic: https://console.anthropic.com/
- Google Maps: https://console.cloud.google.com/

### 2. 安装依赖

```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
pip install -r requirements.txt
```

### 3. 配置环境变量

在 `backend` 目录下创建 `.env` 文件：

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./travel_planner.db
```

### 4. 启动服务

**方式 1: 使用一键启动脚本（推荐）**

```bash
# Windows
start_all.bat
```

**方式 2: 手动启动**

```bash
# 终端 1: 启动后端
cd backend
python run_server.py

# 终端 2: 启动前端
cd frontend
streamlit run app.py
```

### 5. 访问服务

- **前端界面**: http://localhost:8501
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## 使用指南

### 创建行程规划

1. 在 Streamlit 界面填写基本信息（团队人数、交通方式、天数）
2. 配置每天的行程：
   - 起点/住宿
   - 必去地点
   - 候选地点
   - 约束条件（最大行程时间、高峰时段、缓冲时间等）
3. 点击"开始规划"
4. 等待规划完成（通常在 30-60 秒内）
5. 查看规划结果，包括：
   - 每日详细路线
   - 时间安排
   - 风险评估
   - 替代方案
6. 下载 Markdown 格式报告

### 查看历史记录

在 Streamlit 界面选择"查看历史记录"页面，可以：
- 查看所有历史规划
- 重新查看已完成的规划详情
- 下载历史报告

## API 端点

### 健康检查
- `GET /api/health` - 服务健康状态

### 地理编码和路线
- `POST /api/geocode` - 地址转坐标
- `POST /api/directions` - 获取路线规划
- `POST /api/distance-matrix` - 计算距离矩阵
- `POST /api/search-places` - 搜索地点

### 行程规划
- `POST /api/plan` - 创建行程规划（异步）
- `GET /api/plan/{plan_id}/status` - 查询规划状态
- `GET /api/plan/{plan_id}` - 获取规划结果

### 历史记录
- `GET /api/history` - 获取历史记录列表
- `GET /api/history/{plan_id}` - 获取特定规划详情
- `DELETE /api/history/{plan_id}` - 删除规划

详细 API 文档请访问: http://localhost:8000/docs

## 测试

```bash
# 运行后端测试
cd backend
pytest ../tests/test_backend.py -v

# 或从项目根目录
pytest tests/ -v
```

## 部署到 Streamlit Cloud

1. 将代码推送到 GitHub 仓库
2. 在 [Streamlit Cloud](https://streamlit.io/cloud) 创建新应用
3. 配置环境变量：
   - `ANTHROPIC_API_KEY`
   - `GOOGLE_MAPS_API_KEY`
4. 设置启动命令：
   ```bash
   streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
   ```
5. 确保后端 API 地址在 Streamlit Cloud 可访问（可能需要部署后端或使用 API Gateway）

## 故障排查

### 后端无法启动

1. 检查环境变量是否正确设置
2. 检查 API Keys 是否有效
3. 查看后端日志中的错误信息

### 规划失败

1. 检查 Google Maps API Key 是否正确且有足够的配额
2. 检查地址是否可以被正确地理编码
3. 查看后端日志了解详细错误

### 前端无法连接后端

1. 检查后端是否正在运行（访问 http://localhost:8000/api/health）
2. 检查前端配置的 API 地址是否正确
3. 检查防火墙设置

## 技术栈

- **后端**: FastAPI, SQLAlchemy, Google Maps API, LangChain
- **前端**: Streamlit, Folium
- **LLM**: Claude Haiku 3.5 (via LangChain)
- **数据库**: SQLite (via aiosqlite)

## 许可证

本项目仅供学习和研究使用。

