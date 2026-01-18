#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动新版本后端服务"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
from pathlib import Path

# 设置路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载 .env 文件: {env_path}")
    else:
        print(f"⚠️  .env 文件不存在: {env_path}")
        print("   将使用系统环境变量")
except ImportError:
    print("⚠️  python-dotenv 未安装，将使用系统环境变量")

# 验证环境变量
required_env_vars = ["GOOGLE_MAPS_API_KEY", "ANTHROPIC_API_KEY"]
missing_vars = []

for var in required_env_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
    print(f"   请在 .env 文件中设置这些变量（文件路径: {backend_dir / '.env'}）")
    print(f"   或者设置系统环境变量")
    sys.exit(1)

print("✅ 环境变量检查通过")

# 启动服务
if __name__ == '__main__':
    import uvicorn
    
    print("🚀 启动 Travel Planner Service V2...")
    print("📍 后端地址: http://localhost:8000")
    print("📖 API 文档: http://localhost:8000/docs")
    print("🔄 自动重载: 已启用")
    print("-" * 50)
    
    uvicorn.run(
        "app.main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
