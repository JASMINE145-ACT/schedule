"""新版本的 FastAPI 主应用 - 支持 LLM 驱动的对话式规划"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
from typing import Dict, Any

# 导入新的模型和服务
from app.models_v2 import (
    StartConversationRequest, ContinueConversationRequest, ConversationResponse,
    Conversation, PlanningStage
)
from app.services.maps_service import MapsService
from app.services.llm_service_v2 import LLMService
from app.services.llm_orchestrator import LLMOrchestrator
from app.services.report_generator import ReportGenerator
from app.database import Database


# 全局变量存储服务实例和对话
conversations: Dict[str, Conversation] = {}
maps_service: MapsService = None
llm_service: LLMService = None
orchestrator: LLMOrchestrator = None
report_generator: ReportGenerator = None
database: Database = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global maps_service, llm_service, orchestrator, report_generator, database
    
    # 启动时初始化服务
    try:
        maps_service = MapsService()
        llm_service = LLMService()
        orchestrator = LLMOrchestrator(maps_service, llm_service)
        report_generator = ReportGenerator()
        database = Database()
        print("✅ 所有服务初始化成功")
    except Exception as e:
        print(f"❌ 服务初始化失败: {e}")
        raise
    
    yield
    
    # 关闭时清理资源
    print("🔄 清理资源...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Travel Planner Service V2",
    description="LLM 驱动的智能旅行规划服务",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "maps": maps_service is not None,
            "llm": llm_service is not None,
            "orchestrator": orchestrator is not None,
            "database": database is not None
        },
        "active_conversations": len(conversations)
    }


@app.post("/api/v2/conversation/start", response_model=ConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """开始新的对话式规划"""
    try:
        # 创建新对话
        conversation = await orchestrator.start_conversation(
            user_input=request.user_input,
            user_id=request.user_id
        )
        
        # 存储对话
        conversations[conversation.id] = conversation
        
        # 获取最新的助手消息
        assistant_messages = [
            msg for msg in conversation.messages 
            if msg.role.value == "assistant" and msg.type.value == "text"
        ]
        
        latest_message = assistant_messages[-1].content if assistant_messages else "我来帮您规划旅行！"
        
        # 构建响应
        response = ConversationResponse(
            conversation_id=conversation.id,
            stage=conversation.stage,
            assistant_message=latest_message,
            current_plan=conversation.current_plan,
            suggested_actions=_get_suggested_actions(conversation.stage),
            requires_confirmation=conversation.stage == PlanningStage.FINAL_CONFIRMATION
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"启动对话失败: {str(e)}")


@app.post("/api/v2/conversation/continue", response_model=ConversationResponse)
async def continue_conversation(request: ContinueConversationRequest):
    """继续对话"""
    try:
        # 获取对话
        if request.conversation_id not in conversations:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        conversation = conversations[request.conversation_id]
        
        # 继续对话
        updated_conversation = await orchestrator.continue_conversation(
            conversation=conversation,
            user_input=request.user_input
        )
        
        # 更新存储的对话
        conversations[conversation.id] = updated_conversation
        
        # 获取最新的助手消息
        assistant_messages = [
            msg for msg in updated_conversation.messages 
            if msg.role.value == "assistant" and msg.type.value == "text"
        ]
        
        latest_message = assistant_messages[-1].content if assistant_messages else "请继续..."
        
        # 构建响应
        response = ConversationResponse(
            conversation_id=updated_conversation.id,
            stage=updated_conversation.stage,
            assistant_message=latest_message,
            current_plan=updated_conversation.current_plan,
            suggested_actions=_get_suggested_actions(updated_conversation.stage),
            requires_confirmation=updated_conversation.stage == PlanningStage.FINAL_CONFIRMATION
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"继续对话失败: {str(e)}")


@app.get("/api/v2/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    return conversations[conversation_id]


@app.get("/api/v2/conversation/{conversation_id}/plan")
async def get_plan(conversation_id: str):
    """获取规划详情"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    conversation = conversations[conversation_id]
    
    if not conversation.current_plan:
        raise HTTPException(status_code=404, detail="规划尚未生成")
    
    # 将 TravelPlan 转换为字典格式（包含完整数据）
    plan = conversation.current_plan
    
    # 构建规划数据（包含 days 和 summary）
    plan_data = {
        "id": plan.id,
        "title": plan.title,
        "request": plan.request if hasattr(plan, "request") else {},
        "days": [day.model_dump() if hasattr(day, "model_dump") else day for day in plan.days] if plan.days else [],
        "summary": plan.summary if hasattr(plan, "summary") else {},
        "version": plan.version,
        "created_at": plan.created_at.isoformat() if hasattr(plan.created_at, "isoformat") else str(plan.created_at),
        "updated_at": plan.updated_at.isoformat() if hasattr(plan.updated_at, "isoformat") else str(plan.updated_at)
    }
    
    return plan_data


@app.get("/api/v2/conversation/{conversation_id}/report")
async def get_conversation_report(conversation_id: str):
    """获取指定对话的详细报告（Markdown格式）"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    conversation = conversations[conversation_id]
    if not conversation.current_plan:
        raise HTTPException(status_code=404, detail="规划尚未生成")
    
    # 将 TravelPlan 转换为报告生成器需要的格式
    plan = conversation.current_plan
    requirement = plan.requirement if hasattr(plan, "requirement") else {}
    
    # 转换 days：将 DayPlan.places 转换为 segments 格式
    days_for_report = []
    if plan.days:
        for day in plan.days:
            day_dict = day.model_dump() if hasattr(day, "model_dump") else day
            places = day_dict.get("places", [])
            
            # 将 places 转换为 segments 格式
            segments = []
            for i, place in enumerate(places):
                # 估算时间段（上午、中午、下午）
                if i < len(places) * 0.3:
                    time_period = "morning"
                    departure_time = "09:00"
                    arrival_time = "12:00"
                elif i < len(places) * 0.7:
                    time_period = "afternoon"
                    departure_time = "13:30"
                    arrival_time = "18:00"
                else:
                    time_period = "lunch"
                    departure_time = "12:00"
                    arrival_time = "13:30"
                
                # 构建 segment 字典
                place_dict = place.model_dump() if hasattr(place, "model_dump") else place
                segment = {
                    "time_period": time_period,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "to_location": place_dict.get("name", ""),
                    "from_location": places[i-1].get("name", "") if i > 0 else "",
                    "activity_description": place_dict.get("description", ""),
                    "address": place_dict.get("address", ""),
                    "is_required": i == 0,  # 第一个地点通常是必去的
                    "estimated_duration": place_dict.get("estimated_duration", 180)
                }
                segments.append(segment)
            
            # 构建 day 字典（包含 segments）
            day_dict["segments"] = segments
            days_for_report.append(day_dict)
    
    # 构建规划数据（用于报告生成）
    plan_data = {
        "request": {
            "city": requirement.destination if hasattr(requirement, "destination") else requirement.get("destination", "商务接待"),
            "total_days": requirement.duration_days if hasattr(requirement, "duration_days") else requirement.get("duration_days", 1),
            "team_size": requirement.group_size if hasattr(requirement, "group_size") else requirement.get("group_size", 1),
            "transportation_mode": requirement.transportation_mode if hasattr(requirement, "transportation_mode") else requirement.get("transportation_mode", "driving")
        },
        "days": days_for_report,
        "summary": plan.summary if hasattr(plan, "summary") else {}
    }
    
    # 生成 Markdown 报告
    report_markdown = report_generator.generate_markdown(
        plan_data=plan_data,
        include_details=True
    )
    
    return {
        "conversation_id": conversation_id,
        "plan_id": plan.id,
        "report": report_markdown,
        "format": "markdown"
    }


@app.get("/api/v2/conversations")
async def list_conversations():
    """列出所有对话"""
    return {
        "conversations": [
            {
                "id": conv.id,
                "stage": conv.stage,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "has_plan": conv.current_plan is not None,
                "message_count": len(conv.messages)
            }
            for conv in conversations.values()
        ],
        "total": len(conversations)
    }


@app.delete("/api/v2/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    del conversations[conversation_id]
    return {"message": "对话已删除"}


@app.post("/api/v2/conversation/{conversation_id}/execute")
async def execute_plan(conversation_id: str, background_tasks: BackgroundTasks):
    """执行最终确认的计划"""
    try:
        if conversation_id not in conversations:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        conversation = conversations[conversation_id]
        
        if not conversation.current_plan:
            raise HTTPException(status_code=400, detail="没有可执行的计划")
        
        if conversation.stage != PlanningStage.FINAL_CONFIRMATION:
            raise HTTPException(status_code=400, detail="计划尚未确认，无法执行")
        
        # 在后台执行详细规划
        execution_id = str(uuid.uuid4())
        background_tasks.add_task(
            _execute_detailed_planning,
            conversation.current_plan,
            execution_id
        )
        
        return {
            "message": "计划执行已启动",
            "execution_id": execution_id,
            "plan_id": conversation.current_plan.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"执行计划失败: {str(e)}")


def _get_suggested_actions(stage: PlanningStage) -> list[str]:
    """根据阶段获取建议操作"""
    suggestions = {
        PlanningStage.UNDERSTANDING: [
            "请提供更多详细信息",
            "确认旅行需求",
            "开始规划"
        ],
        PlanningStage.INITIAL_PLANNING: [
            "查看推荐景点",
            "调整行程安排",
            "继续优化"
        ],
        PlanningStage.INTERACTIVE_OPTIMIZATION: [
            "修改某个景点",
            "调整时间安排",
            "确认当前计划",
            "重新规划"
        ],
        PlanningStage.FINAL_CONFIRMATION: [
            "确认并执行计划",
            "再次修改",
            "保存计划"
        ],
        PlanningStage.EXECUTION: [
            "查看执行进度",
            "下载计划报告"
        ]
    }
    
    return suggestions.get(stage, ["继续对话"])


async def _execute_detailed_planning(plan, execution_id: str):
    """执行详细规划（后台任务）"""
    try:
        # 这里实现详细的路线规划、时间安排、风险评估等
        # 调用原有的规划逻辑
        
        # 更新计划状态
        plan.stage = PlanningStage.EXECUTION
        
        print(f"✅ 计划 {plan.id} 执行完成 (执行ID: {execution_id})")
        
    except Exception as e:
        print(f"❌ 计划执行失败: {e}")


# 移除重复的健康检查端点，避免冲突


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
