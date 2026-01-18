"""新版本的 Pydantic 模型 - LLM 驱动的交互式规划"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ConversationRole(str, Enum):
    """对话角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """消息类型"""
    TEXT = "text"
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class PlanningStage(str, Enum):
    """规划阶段"""
    UNDERSTANDING = "understanding"  # 理解需求
    INITIAL_PLANNING = "initial_planning"  # 初始规划
    INTERACTIVE_OPTIMIZATION = "interactive_optimization"  # 交互优化
    FINAL_CONFIRMATION = "final_confirmation"  # 最终确认
    EXECUTION = "execution"  # 执行规划


class Message(BaseModel):
    """对话消息"""
    id: str = Field(..., description="消息 ID")
    role: ConversationRole = Field(..., description="消息角色")
    type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    content: str = Field(..., description="消息内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class TravelRequirement(BaseModel):
    """从自然语言提取的旅行需求"""
    destination: str = Field(..., description="目的地")
    duration_days: int = Field(..., description="行程天数")
    group_size: int = Field(..., description="团队人数")
    preferences: List[str] = Field(default_factory=list, description="偏好列表")
    constraints: List[str] = Field(default_factory=list, description="约束条件")
    budget_range: Optional[str] = Field(None, description="预算范围")
    transportation_mode: str = Field(default="driving", description="交通方式")
    special_notes: List[str] = Field(default_factory=list, description="特殊注意事项")


class PlaceRecommendation(BaseModel):
    """地点推荐"""
    name: str = Field(..., description="地点名称")
    address: str = Field(..., description="地址")
    category: str = Field(..., description="类别")
    rating: Optional[float] = Field(None, description="评分")
    description: str = Field(..., description="描述")
    estimated_duration: int = Field(..., description="建议游玩时长（分钟）")
    reasons: List[str] = Field(..., description="推荐理由")


class DayPlan(BaseModel):
    """单日计划"""
    day: int = Field(..., description="第几天")
    theme: str = Field(..., description="当日主题")
    places: List[PlaceRecommendation] = Field(..., description="地点列表")
    route_summary: str = Field(..., description="路线摘要")
    estimated_total_time: int = Field(..., description="预计总时长（分钟）")
    notes: List[str] = Field(default_factory=list, description="注意事项")


class TravelPlan(BaseModel):
    """完整旅行计划"""
    id: str = Field(..., description="计划 ID")
    title: str = Field(..., description="计划标题")
    requirement: TravelRequirement = Field(..., description="原始需求")
    days: List[DayPlan] = Field(..., description="每日计划")
    overall_summary: str = Field(..., description="总体摘要")
    total_estimated_cost: Optional[str] = Field(None, description="预计总费用")
    important_notes: List[str] = Field(default_factory=list, description="重要提醒")
    version: int = Field(default=1, description="计划版本")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class Conversation(BaseModel):
    """对话会话"""
    id: str = Field(..., description="会话 ID")
    user_id: Optional[str] = Field(None, description="用户 ID")
    stage: PlanningStage = Field(default=PlanningStage.UNDERSTANDING, description="当前阶段")
    messages: List[Message] = Field(default_factory=list, description="消息列表")
    current_requirement: Optional[TravelRequirement] = Field(None, description="当前需求")
    current_plan: Optional[TravelPlan] = Field(None, description="当前计划")
    plan_versions: List[TravelPlan] = Field(default_factory=list, description="计划版本历史")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


# API 请求/响应模型

class StartConversationRequest(BaseModel):
    """开始对话请求"""
    user_input: str = Field(..., description="用户自然语言输入")
    user_id: Optional[str] = Field(None, description="用户 ID")


class ContinueConversationRequest(BaseModel):
    """继续对话请求"""
    conversation_id: str = Field(..., description="会话 ID")
    user_input: str = Field(..., description="用户输入")


class ConversationResponse(BaseModel):
    """对话响应"""
    conversation_id: str = Field(..., description="会话 ID")
    stage: PlanningStage = Field(..., description="当前阶段")
    assistant_message: str = Field(..., description="助手回复")
    current_plan: Optional[TravelPlan] = Field(None, description="当前计划")
    suggested_actions: List[str] = Field(default_factory=list, description="建议操作")
    requires_confirmation: bool = Field(default=False, description="是否需要确认")


class ToolCall(BaseModel):
    """工具调用"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(..., description="工具参数")
    call_id: str = Field(..., description="调用 ID")


class ToolResult(BaseModel):
    """工具结果"""
    call_id: str = Field(..., description="调用 ID")
    success: bool = Field(..., description="是否成功")
    result: Any = Field(..., description="结果数据")
    error: Optional[str] = Field(None, description="错误信息")
