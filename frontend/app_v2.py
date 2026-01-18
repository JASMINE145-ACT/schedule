"""新版本的 Streamlit 前端 - 对话式旅行规划界面"""

import streamlit as st
import requests
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="智能旅行规划助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 配置
API_BASE_URL = st.sidebar.text_input(
    "后端 API 地址",
    value="http://localhost:8000",
    help="后端 FastAPI 服务的地址"
)

# 自定义 CSS
st.markdown("""
<style>
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background-color: #fafafa;
        margin-bottom: 1rem;
    }
    
    .user-message {
        background-color: #e3f2fd;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-left: 2rem;
        border-left: 4px solid #2196f3;
    }
    
    .assistant-message {
        background-color: #f1f8e9;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-right: 2rem;
        border-left: 4px solid #4caf50;
    }
    
    .system-message {
        background-color: #fff3e0;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #ff9800;
        font-style: italic;
    }
    
    .stage-indicator {
        background: linear-gradient(90deg, #4caf50, #2196f3);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        text-align: center;
        margin: 1rem 0;
    }
    
    .plan-card {
        border: 2px solid #4caf50;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #f8fff8;
    }
    
    .action-button {
        background-color: #2196f3;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin: 0.2rem;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health() -> bool:
    """检查 API 健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def start_conversation(user_input: str) -> Optional[Dict[str, Any]]:
    """开始新对话"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v2/conversation/start",
            json={"user_input": user_input},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"启动对话失败: {str(e)}")
        return None


def continue_conversation(conversation_id: str, user_input: str) -> Optional[Dict[str, Any]]:
    """继续对话"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v2/conversation/continue",
            json={
                "conversation_id": conversation_id,
                "user_input": user_input
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"继续对话失败: {str(e)}")
        return None


def get_conversation_details(conversation_id: str) -> Optional[Dict[str, Any]]:
    """获取对话详情"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v2/conversation/{conversation_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"获取对话详情失败: {str(e)}")
        return None


def render_stage_indicator(stage: str):
    """渲染阶段指示器"""
    stage_names = {
        "understanding": "🤔 理解需求",
        "initial_planning": "📋 初始规划",
        "interactive_optimization": "🔄 交互优化",
        "final_confirmation": "✅ 最终确认",
        "execution": "🚀 执行中"
    }
    
    stage_name = stage_names.get(stage, stage)
    st.markdown(f'<div class="stage-indicator">{stage_name}</div>', unsafe_allow_html=True)


def render_message(role: str, content: str, timestamp: Optional[str] = None):
    """渲染消息"""
    time_str = ""
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = f" ({dt.strftime('%H:%M')})"
        except:
            pass
    
    if role == "user":
        st.markdown(f'''
        <div class="user-message">
            <strong>您{time_str}:</strong><br>
            {content}
        </div>
        ''', unsafe_allow_html=True)
    elif role == "assistant":
        st.markdown(f'''
        <div class="assistant-message">
            <strong>助手{time_str}:</strong><br>
            {content}
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
        <div class="system-message">
            <strong>系统{time_str}:</strong><br>
            {content}
        </div>
        ''', unsafe_allow_html=True)


def get_conversation_report(conversation_id: str) -> Optional[str]:
    """获取对话的详细报告（Markdown格式）"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v2/conversation/{conversation_id}/report",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("report", "")
    except Exception as e:
        st.error(f"获取报告失败: {str(e)}")
        return None


def render_travel_plan(plan: Dict[str, Any], conversation_id: Optional[str] = None):
    """渲染旅行计划 - 使用详细报告（与参考文档风格一致）"""
    if not plan:
        return
    
    st.markdown('<div class="plan-card">', unsafe_allow_html=True)
    
    # 尝试获取详细报告
    report_markdown = None
    if conversation_id:
        with st.spinner("正在生成详细报告..."):
            report_markdown = get_conversation_report(conversation_id)
    
    if report_markdown:
        # 显示完整的 Markdown 报告（与参考文档一致）
        st.markdown(report_markdown)
    else:
        # 降级显示：显示基本信息（向后兼容）
        st.markdown(f"### 📋 {plan.get('title', '旅行计划')}")
        
        # 基本信息
        requirement = plan.get('requirement', {})
        if requirement:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("目的地", requirement.get('destination', 'N/A'))
            with col2:
                st.metric("天数", f"{requirement.get('duration_days', 0)} 天")
            with col3:
                st.metric("人数", f"{requirement.get('group_size', 0)} 人")
        
        # 每日计划
        days = plan.get('days', [])
        if days:
            st.markdown("#### 📅 每日行程")
            for day in days:
                with st.expander(f"第 {day.get('day', 0)} 天 - {day.get('theme', '未定义主题')}"):
                    st.markdown(f"**路线摘要**: {day.get('route_summary', '暂无')}")
                    st.markdown(f"**预计时长**: {day.get('estimated_total_time', 0)} 分钟")
                    
                    places = day.get('places', [])
                    if places:
                        st.markdown("**推荐地点**:")
                        for i, place in enumerate(places, 1):
                            st.markdown(f"{i}. **{place.get('name', 'Unknown')}** - {place.get('description', '')}")
        
        # 总体摘要
        summary = plan.get('overall_summary', '')
        if summary:
            st.markdown("#### 📝 总体摘要")
            st.markdown(summary)
        
        # 重要提醒
        notes = plan.get('important_notes', [])
        if notes:
            st.markdown("#### ⚠️ 重要提醒")
            for note in notes:
                st.warning(note)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_suggested_actions(actions: List[str], conversation_id: str):
    """渲染建议操作"""
    if not actions:
        return
    
    st.markdown("#### 💡 建议操作")
    cols = st.columns(min(len(actions), 3))
    
    for i, action in enumerate(actions):
        with cols[i % 3]:
            if st.button(action, key=f"action_{i}_{conversation_id}"):
                # 将建议操作作为用户输入
                st.session_state.user_input = action
                st.rerun()


def main():
    """主应用"""
    st.title("🤖 智能旅行规划助手")
    st.markdown("---")
    
    # 检查 API 连接
    if not check_api_health():
        st.error("⚠️ 无法连接到后端服务，请确保后端正在运行")
        st.info(f"后端地址: {API_BASE_URL}")
        if st.button("重试连接"):
            st.rerun()
        return
    
    st.success("✅ 已连接到后端服务")
    
    # 初始化 session state
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "conversation_data" not in st.session_state:
        st.session_state.conversation_data = None
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    
    # 侧边栏 - 对话管理
    with st.sidebar:
        st.header("🗂️ 对话管理")
        
        if st.button("🆕 开始新对话", type="primary"):
            st.session_state.conversation_id = None
            st.session_state.conversation_data = None
            st.session_state.user_input = ""
            st.rerun()
        
        # 显示当前对话信息
        if st.session_state.conversation_id:
            st.info(f"当前对话 ID: {st.session_state.conversation_id[:8]}...")
            
            if st.button("🔄 刷新对话"):
                conversation_details = get_conversation_details(st.session_state.conversation_id)
                if conversation_details:
                    st.session_state.conversation_data = conversation_details
                st.rerun()
    
    # 主界面
    if not st.session_state.conversation_id:
        # 新对话界面
        st.markdown("### 🚀 开始您的旅行规划")
        st.markdown("请用自然语言描述您的旅行计划，例如：")
        
        examples = [
            "我想和朋友3个人去雅加达玩3天，喜欢文化景点和美食",
            "计划家庭旅行，4个人去巴厘岛5天，有老人和小孩",
            "商务出差顺便旅游，2天时间在新加坡，预算有限"
        ]
        
        for example in examples:
            if st.button(f"💡 {example}", key=f"example_{hash(example)}"):
                st.session_state.user_input = example
        
        st.markdown("---")
        
        # 用户输入
        user_input = st.text_area(
            "请描述您的旅行需求：",
            value=st.session_state.user_input,
            height=100,
            placeholder="例如：我想和家人去日本旅游7天，喜欢温泉和美食，预算中等..."
        )
        
        if st.button("🚀 开始规划", type="primary", disabled=not user_input.strip()):
            with st.spinner("正在理解您的需求..."):
                result = start_conversation(user_input)
                if result:
                    st.session_state.conversation_id = result["conversation_id"]
                    st.session_state.conversation_data = result
                    st.session_state.user_input = ""
                    st.rerun()
    
    else:
        # 对话界面
        conversation_data = st.session_state.conversation_data
        
        if conversation_data:
            # 显示当前阶段
            render_stage_indicator(conversation_data.get("stage", "unknown"))
            
            # 获取完整对话历史
            conversation_details = get_conversation_details(st.session_state.conversation_id)
            
            if conversation_details:
                # 显示对话历史
                st.markdown("### 💬 对话历史")
                
                messages = conversation_details.get("messages", [])
                text_messages = [msg for msg in messages if msg.get("type") == "text"]
                
                # 创建聊天容器
                chat_container = st.container()
                
                with chat_container:
                    for msg in text_messages:
                        render_message(
                            msg.get("role", "unknown"),
                            msg.get("content", ""),
                            msg.get("timestamp")
                        )
                
                # 显示当前计划（使用详细报告）
                current_plan = conversation_details.get("current_plan")
                if current_plan:
                    st.markdown("---")
                    render_travel_plan(current_plan, conversation_id=st.session_state.conversation_id)
                
                # 建议操作
                suggested_actions = conversation_data.get("suggested_actions", [])
                if suggested_actions:
                    st.markdown("---")
                    render_suggested_actions(suggested_actions, st.session_state.conversation_id)
                
                # 用户输入区域
                st.markdown("---")
                st.markdown("### ✍️ 继续对话")
                
                # 检查是否需要确认
                requires_confirmation = conversation_data.get("requires_confirmation", False)
                if requires_confirmation:
                    st.info("🎯 计划已准备就绪，请确认是否执行或提出修改建议")
                
                user_input = st.text_area(
                    "您的回复：",
                    value=st.session_state.user_input,
                    height=80,
                    placeholder="请输入您的问题、建议或确认..."
                )
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if st.button("💬 发送", type="primary", disabled=not user_input.strip()):
                        with st.spinner("正在处理您的回复..."):
                            result = continue_conversation(st.session_state.conversation_id, user_input)
                            if result:
                                st.session_state.conversation_data = result
                                st.session_state.user_input = ""
                                st.rerun()
                
                with col2:
                    if requires_confirmation and current_plan:
                        if st.button("✅ 确认执行", type="secondary"):
                            try:
                                response = requests.post(
                                    f"{API_BASE_URL}/api/v2/conversation/{st.session_state.conversation_id}/execute",
                                    timeout=10
                                )
                                if response.status_code == 200:
                                    st.success("🎉 计划已开始执行！")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("执行失败，请重试")
                            except Exception as e:
                                st.error(f"执行失败: {str(e)}")


if __name__ == "__main__":
    main()
