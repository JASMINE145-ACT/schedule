#!/usr/bin/env python3
"""启动新版本前端服务"""

import sys
import os
from pathlib import Path

# 设置路径
frontend_dir = Path(__file__).parent
os.chdir(frontend_dir)

if __name__ == '__main__':
    print("🚀 启动 Travel Planner Frontend V2...")
    print("📍 前端地址: http://localhost:8501")
    print("🤖 智能对话式旅行规划界面")
    print("-" * 50)
    
    # 使用 streamlit 模块启动
    import streamlit.web.cli as stcli
    sys.argv = ["streamlit", "run", "app_v2.py", "--server.port", "8501"]
    sys.exit(stcli.main())
