"""LLM 编排器 - 管理 LLM 与工具的交互"""

import json
import uuid
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from app.models_v2 import (
    Conversation, Message, TravelRequirement, TravelPlan, 
    ConversationRole, MessageType, PlanningStage, ToolCall, ToolResult
)
from app.services.maps_service import MapsService
from app.services.llm_service_v2 import LLMService


class LLMOrchestrator:
    """LLM 编排器 - 协调 LLM 与各种工具的交互"""
    
    def __init__(self, maps_service: MapsService, llm_service: LLMService):
        self.maps_service = maps_service
        self.llm_service = llm_service
        self.tools = self._register_tools()
        
    def _register_tools(self) -> Dict[str, Callable]:
        """注册可用工具"""
        return {
            "geocode_location": self._tool_geocode_location,
            "search_places": self._tool_search_places,
            "get_distance_matrix": self._tool_get_distance_matrix,
            "get_directions": self._tool_get_directions,
            "extract_travel_requirement": self._tool_extract_travel_requirement,
            "generate_initial_plan": self._tool_generate_initial_plan,
            "modify_plan": self._tool_modify_plan,
            "validate_plan": self._tool_validate_plan,
        }
    
    async def start_conversation(self, user_input: str, user_id: Optional[str] = None) -> Conversation:
        """开始新对话"""
        conversation_id = str(uuid.uuid4())
        
        # 创建新对话
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            stage=PlanningStage.UNDERSTANDING
        )
        
        # 添加用户消息
        user_message = Message(
            id=str(uuid.uuid4()),
            role=ConversationRole.USER,
            content=user_input
        )
        conversation.messages.append(user_message)
        
        # LLM 理解用户需求
        await self._process_understanding_stage(conversation)
        
        return conversation
    
    async def continue_conversation(self, conversation: Conversation, user_input: str) -> Conversation:
        """继续对话"""
        # 添加用户消息
        user_message = Message(
            id=str(uuid.uuid4()),
            role=ConversationRole.USER,
            content=user_input
        )
        conversation.messages.append(user_message)
        conversation.updated_at = datetime.now()
        
        # 检查用户是否明确要求规划（自动转换阶段）
        planning_keywords = ["开始规划", "生成规划", "规划行程", "制定计划", "生成行程", "规划安排"]
        if conversation.stage == PlanningStage.UNDERSTANDING:
            user_input_lower = user_input.lower()
            if any(keyword in user_input_lower for keyword in planning_keywords):
                # 用户明确要求规划，直接进入规划阶段
                conversation.stage = PlanningStage.INITIAL_PLANNING
                print(f"✅ 用户要求规划，自动转换到 INITIAL_PLANNING 阶段")
        
        # 根据当前阶段处理
        if conversation.stage == PlanningStage.UNDERSTANDING:
            await self._process_understanding_stage(conversation)
        elif conversation.stage == PlanningStage.INITIAL_PLANNING:
            await self._process_initial_planning_stage(conversation)
        elif conversation.stage == PlanningStage.INTERACTIVE_OPTIMIZATION:
            await self._process_optimization_stage(conversation)
        elif conversation.stage == PlanningStage.FINAL_CONFIRMATION:
            await self._process_confirmation_stage(conversation)
        
        return conversation
    
    async def _process_understanding_stage(self, conversation: Conversation):
        """处理需求理解阶段"""
        # 构建系统提示 - 商务接待规划
        system_prompt = """你是一个专业的商务接待行程规划助手。你的任务是理解用户的自然语言描述，提取关键的商务接待需求信息。

本系统专注于商务接待规划（而非旅游规划），重点考虑：
- 商务会面地点选择（写字楼、商务区、工业园等）
- 交通高峰时段规避（避免延误商务会面）
- 路线逻辑清晰，减少折返
- 住宿策略优化（权衡通勤时间和成本）

请分析用户的输入，提取以下信息：
1. 目的地（城市/国家）
2. 行程天数
3. 团队人数
4. 交通方式（包车、自驾、公共交通等）
5. 商务活动类型（商务拜访、客户接待、会议、工厂参观等）
6. 必去地点（固定锚点，如会议中心、工业园等）
7. 候选地点（可选地点，如商务会面区、供应商拜访点等）
8. 约束条件（交通高峰限制、时间限制、单程车程限制等）
9. 住宿策略要求（是否需要换酒店、住宿区域偏好等）
10. 特殊注意事项（硬约束，如某天必须到达某地点）

如果信息不完整，请友好地询问缺失的关键信息。
如果信息足够，请继续下一步规划。

请用中文回复，语气友好专业。"""

        # 获取对话历史
        messages = self._build_message_history(conversation, system_prompt)
        
        # 调用 LLM
        # 暂时禁用工具调用，先让基本对话工作
        response = await self.llm_service.chat_with_tools(
            messages=messages,
            tools=None,  # 暂时禁用工具，修复工具格式后再启用
            temperature=0.7
        )
        
        # 处理 LLM 响应
        await self._handle_llm_response(conversation, response)
        
        # 如果没有 current_requirement，尝试从用户消息中提取（手动提取）
        if not conversation.current_requirement:
            # 从最新的用户消息中提取需求信息
            user_messages = [msg for msg in conversation.messages if msg.role == ConversationRole.USER]
            if user_messages:
                latest_user_msg = user_messages[-1].content
                requirement = await self._extract_requirement_from_text(latest_user_msg)
                if requirement:
                    conversation.current_requirement = requirement
                    print(f"✅ 从用户消息中提取需求: {requirement.destination}, {requirement.duration_days}天")
    
    async def _extract_requirement_from_text(self, text: str) -> Optional[TravelRequirement]:
        """从文本中提取需求（简单版本，不依赖工具调用）"""
        try:
            # 使用 LLM 提取需求
            system_prompt = """从用户的文本中提取商务接待需求信息，返回 JSON 格式。

请提取：destination（目的地）、duration_days（天数）、group_size（人数）、transportation_mode（交通方式）。
如果信息不完整，使用默认值。"""
            
            user_prompt = f"请从以下文本中提取商务接待需求，返回 JSON：\n\n{text}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.llm_service.chat_with_tools(messages, tools=None, temperature=0.3)
            content = response.get("content", "")
            
            # 尝试从响应中提取 JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return TravelRequirement(
                        destination=data.get("destination", "未知目的地"),
                        duration_days=int(data.get("duration_days", 1)),
                        group_size=int(data.get("group_size", 1)),
                        transportation_mode=data.get("transportation_mode", "包车"),
                        preferences=data.get("preferences", []),
                        constraints=data.get("constraints", []),
                        special_notes=data.get("special_notes", [])
                    )
                except:
                    pass
            
            # 如果 JSON 解析失败，使用简单规则提取
            # 提取目的地（简单规则：查找"雅加达"、"Jakarta"等）
            destination = "未知目的地"
            if "雅加达" in text or "Jakarta" in text:
                destination = "雅加达"
            
            # 提取天数（查找"3天"、"三天"等）
            import re
            days_match = re.search(r'(\d+)[天日]', text)
            duration_days = int(days_match.group(1)) if days_match else 1
            
            # 提取人数（查找"3人"等）
            people_match = re.search(r'(\d+)人', text)
            group_size = int(people_match.group(1)) if people_match else 1
            
            return TravelRequirement(
                destination=destination,
                duration_days=duration_days,
                group_size=group_size,
                transportation_mode="包车",
                preferences=[],
                constraints=[],
                special_notes=[]
            )
        except Exception as e:
            print(f"⚠️ 提取需求失败: {e}")
            return None
    
    async def _process_initial_planning_stage(self, conversation: Conversation):
        """处理初始规划阶段"""
        # 如果已经有需求，直接生成规划（即使工具调用被禁用）
        if conversation.current_requirement:
            print(f"✅ 检测到需求，直接生成规划...")
            try:
                # 搜索商务地点
                requirement = conversation.current_requirement
                destination = requirement.destination
                
                # 搜索商务地点（优先工业园和商务区）
                print(f"   搜索目的地: {destination}")
                
                # 尝试多个搜索查询以找到商务地点
                places = []
                
                # 1. 搜索工业园
                industrial_parks = self.maps_service.search_places(
                    query=f"industrial park {destination}",
                    location=destination,
                    radius=30000,  # 扩大搜索范围
                    keyword="industrial"
                )
                places.extend(industrial_parks[:3])  # 最多3个
                
                # 2. 搜索商务区
                business_districts = self.maps_service.search_places(
                    query=f"business district {destination}",
                    location=destination,
                    radius=20000,
                    keyword="business"
                )
                places.extend(business_districts[:3])
                
                # 3. 搜索供应商/公司
                companies = self.maps_service.search_places(
                    query=f"supplier company {destination}",
                    location=destination,
                    radius=30000,
                    keyword="company"
                )
                places.extend(companies[:2])
                
                # 去重（按 name）
                seen_names = set()
                unique_places = []
                for place in places:
                    name = place.get("name", "")
                    if name and name not in seen_names:
                        seen_names.add(name)
                        unique_places.append(place)
                places = unique_places[:5]  # 最多5个地点
                
                # 如果没有找到地点，使用默认地点
                if not places or len(places) == 0:
                    print(f"   ⚠️ 未找到商务地点，使用默认地点")
                    places = [
                        {"name": f"{destination}工业园区", "address": f"{destination} 工业园区", "types": ["工业园"]},
                        {"name": f"{destination}商务区", "address": f"{destination} 商务区", "types": ["商务区"]}
                    ]
                else:
                    print(f"   ✅ 找到 {len(places)} 个商务地点")
                
                # 直接调用规划生成工具
                print(f"   生成规划，地点数量: {len(places)}")
                plan = await self._tool_generate_initial_plan(
                    {"requirement": requirement, "places": places},
                    conversation
                )
                
                # 生成规划成功，更新阶段
                conversation.current_plan = plan
                conversation.stage = PlanningStage.INTERACTIVE_OPTIMIZATION
                print(f"✅ 规划生成成功，阶段转换到 INTERACTIVE_OPTIMIZATION")
                
                # 添加助手消息
                assistant_message = Message(
                    id=str(uuid.uuid4()),
                    role=ConversationRole.ASSISTANT,
                    type=MessageType.TEXT,
                    content=f"我已经为您生成了{requirement.duration_days}天的商务接待行程规划。规划包含{len(plan.days)}天的详细安排。"
                )
                conversation.messages.append(assistant_message)
                return
                
            except Exception as e:
                print(f"   ❌ 直接生成规划失败: {e}")
                # 继续使用 LLM 流程
        
        # 使用 LLM 流程生成规划（原有逻辑）
        system_prompt = """你是一个专业的商务接待行程规划助手。基于用户的需求，你需要生成一个详细的商务接待行程计划。

本系统专注于商务接待规划（而非旅游规划），重点考虑：
- 商务会面地点选择（写字楼、商务区、工业园等）
- 交通高峰时段规避（避免延误商务会面）
- 路线逻辑清晰，减少折返
- 住宿策略优化（权衡通勤时间和成本）

请生成每日详细商务行程安排，包括：
- 每日主题和区域（如：市区商务区、工业园、港口区等）
- 上午、中午、下午的行程安排
- 必去地点和候选地点的选择
- 路线逻辑说明（为什么这样串、如何减少折返）
- 时间安排建议（避开高峰、预留缓冲）
- 交通风险评估（识别高风险路段和时间段）
- 替代方案（精简版路线、提前出发策略）

生成的计划应该：
- 考虑地理位置，减少往返，形成闭环路线
- 避开交通高峰（07:00-09:00，16:30-18:30）
- 合理安排时间，预留机动缓冲时段
- 识别交通风险点并提供替代方案
- 确保单程车程不超过2小时

请用中文回复，详细解释你的规划思路和交通风险评估。"""

        messages = self._build_message_history(conversation, system_prompt)
        
        response = await self.llm_service.chat_with_tools(
            messages=messages,
            tools=None,  # 暂时禁用工具，修复工具格式后再启用
            temperature=0.7
        )
        
        await self._handle_llm_response(conversation, response)
    
    async def _process_optimization_stage(self, conversation: Conversation):
        """处理交互优化阶段"""
        system_prompt = """你是一个专业的旅行规划助手。用户正在审视你提供的旅行计划，并可能提出修改建议或疑问。

你需要：
1. 仔细理解用户的反馈和要求
2. 如果需要，调用相关工具获取新信息
3. 修改计划以满足用户需求
4. 清楚地解释修改的原因和影响

可用工具包括搜索地点、计算距离、修改计划等。

请保持专业和耐心，详细解释你的建议。用中文回复。"""

        messages = self._build_message_history(conversation, system_prompt)
        
        response = await self.llm_service.chat_with_tools(
            messages=messages,
            tools=None,  # 暂时禁用工具，修复工具格式后再启用
            temperature=0.6
        )
        
        await self._handle_llm_response(conversation, response)
    
    async def _process_confirmation_stage(self, conversation: Conversation):
        """处理最终确认阶段"""
        system_prompt = """用户已经确认了旅行计划。请进行最终的验证和优化：

1. 验证计划的可行性
2. 检查时间安排是否合理
3. 提供最终的实用建议
4. 生成可执行的详细计划

请确保计划完整、准确、可执行。用中文回复。"""

        messages = self._build_message_history(conversation, system_prompt)
        
        response = await self.llm_service.chat_with_tools(
            messages=messages,
            tools=None,  # 暂时禁用工具，修复工具格式后再启用
            temperature=0.3
        )
        
        await self._handle_llm_response(conversation, response)
    
    def _build_message_history(self, conversation: Conversation, system_prompt: str) -> List[Dict[str, str]]:
        """构建消息历史"""
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in conversation.messages:
            if msg.type == MessageType.TEXT:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        return messages
    
    async def _handle_llm_response(self, conversation: Conversation, response: Dict[str, Any]):
        """处理 LLM 响应"""
        # 添加助手消息
        if "content" in response:
            assistant_message = Message(
                id=str(uuid.uuid4()),
                role=ConversationRole.ASSISTANT,
                content=response["content"]
            )
            conversation.messages.append(assistant_message)
        
        # 处理工具调用
        if "tool_calls" in response:
            for tool_call in response["tool_calls"]:
                await self._execute_tool_call(conversation, tool_call)
    
    async def _execute_tool_call(self, conversation: Conversation, tool_call: Dict[str, Any]):
        """执行工具调用"""
        tool_name = tool_call.get("function", {}).get("name")
        parameters = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
        call_id = tool_call.get("id", str(uuid.uuid4()))
        
        # 记录工具调用
        call_message = Message(
            id=str(uuid.uuid4()),
            role=ConversationRole.ASSISTANT,
            type=MessageType.TOOL_CALL,
            content=f"调用工具: {tool_name}",
            metadata={"tool_name": tool_name, "parameters": parameters, "call_id": call_id}
        )
        conversation.messages.append(call_message)
        
        # 执行工具
        try:
            if tool_name in self.tools:
                result = await self.tools[tool_name](parameters, conversation)
                
                # 记录工具结果
                result_message = Message(
                    id=str(uuid.uuid4()),
                    role=ConversationRole.ASSISTANT,
                    type=MessageType.TOOL_RESULT,
                    content=f"工具执行成功: {tool_name}",
                    metadata={"call_id": call_id, "result": result, "success": True}
                )
                conversation.messages.append(result_message)
                
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
                
        except Exception as e:
            # 记录错误
            error_message = Message(
                id=str(uuid.uuid4()),
                role=ConversationRole.ASSISTANT,
                type=MessageType.TOOL_RESULT,
                content=f"工具执行失败: {tool_name} - {str(e)}",
                metadata={"call_id": call_id, "error": str(e), "success": False}
            )
            conversation.messages.append(error_message)
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "extract_travel_requirement",
                    "description": "从用户输入中提取结构化的旅行需求",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string", "description": "目的地"},
                            "duration_days": {"type": "integer", "description": "行程天数"},
                            "group_size": {"type": "integer", "description": "团队人数"},
                            "preferences": {"type": "array", "items": {"type": "string"}, "description": "偏好列表"},
                            "constraints": {"type": "array", "items": {"type": "string"}, "description": "约束条件"},
                            "transportation_mode": {"type": "string", "description": "交通方式"},
                            "special_notes": {"type": "array", "items": {"type": "string"}, "description": "特殊注意事项"}
                        },
                        "required": ["destination", "duration_days", "group_size"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_places",
                    "description": "搜索目的地的景点和活动",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "location": {"type": "string", "description": "搜索位置"},
                            "category": {"type": "string", "description": "类别筛选"}
                        },
                        "required": ["query", "location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_distance_matrix",
                    "description": "计算多个地点之间的距离和时间",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "origins": {"type": "array", "items": {"type": "string"}, "description": "起点列表"},
                            "destinations": {"type": "array", "items": {"type": "string"}, "description": "终点列表"},
                            "mode": {"type": "string", "description": "交通方式"}
                        },
                        "required": ["origins", "destinations"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_initial_plan",
                    "description": "生成初始旅行计划",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "requirement": {"type": "object", "description": "旅行需求"},
                            "places": {"type": "array", "description": "推荐地点列表"},
                            "distances": {"type": "array", "description": "距离信息"}
                        },
                        "required": ["requirement", "places"]
                    }
                }
            }
        ]
    
    # 工具实现方法
    async def _tool_geocode_location(self, params: Dict[str, Any], conversation: Conversation) -> Dict[str, Any]:
        """地理编码工具"""
        address = params.get("address")
        result = self.maps_service.geocode(address)
        return result
    
    async def _tool_search_places(self, params: Dict[str, Any], conversation: Conversation) -> List[Dict[str, Any]]:
        """搜索地点工具"""
        query = params.get("query")
        location = params.get("location")
        radius = params.get("radius", 5000)
        
        results = self.maps_service.search_places(query, location, radius)
        return results
    
    async def _tool_get_distance_matrix(self, params: Dict[str, Any], conversation: Conversation) -> List[Dict[str, Any]]:
        """距离矩阵工具"""
        origins = params.get("origins", [])
        destinations = params.get("destinations", [])
        mode = params.get("mode", "driving")
        
        results = self.maps_service.get_distance_matrix(origins, destinations, mode)
        return results
    
    async def _tool_get_directions(self, params: Dict[str, Any], conversation: Conversation) -> Dict[str, Any]:
        """路线规划工具"""
        origin = params.get("origin")
        destination = params.get("destination")
        mode = params.get("mode", "driving")
        
        result = self.maps_service.get_directions(origin, destination, mode)
        return result
    
    async def _tool_extract_travel_requirement(self, params: Dict[str, Any], conversation: Conversation) -> TravelRequirement:
        """提取旅行需求工具"""
        try:
            requirement = TravelRequirement(**params)
            conversation.current_requirement = requirement
            conversation.stage = PlanningStage.INITIAL_PLANNING
            return requirement
        except Exception as e:
            # 如果参数不完整，保持在理解阶段
            partial_requirement = TravelRequirement(
                destination=params.get('destination', ''),
                duration_days=params.get('duration_days', 1),
                group_size=params.get('group_size', 1),
                preferences=params.get('preferences', []),
                constraints=params.get('constraints', []),
                transportation_mode=params.get('transportation_mode', 'driving'),
                special_notes=params.get('special_notes', [])
            )
            conversation.current_requirement = partial_requirement
            return partial_requirement
    
    async def _tool_generate_initial_plan(self, params: Dict[str, Any], conversation: Conversation) -> TravelPlan:
        """生成初始计划工具"""
        from app.models_v2 import DayPlan, PlaceRecommendation
        
        requirement = params.get("requirement") or conversation.current_requirement
        places = params.get("places", [])
        
        if not requirement:
            raise ValueError("No travel requirement available")
        
        # 生成每日计划
        days_plans = []
        places_per_day = max(1, len(places) // requirement.duration_days) if places else 2
        
        for day_num in range(1, requirement.duration_days + 1):
            # 为每天分配地点
            start_idx = (day_num - 1) * places_per_day
            end_idx = min(start_idx + places_per_day, len(places))
            day_places = places[start_idx:end_idx] if places else []
            
            # 转换为 PlaceRecommendation 格式
            place_recommendations = []
            for place in day_places:
                place_rec = PlaceRecommendation(
                    name=place.get('name', f'地点 {len(place_recommendations) + 1}'),
                    address=place.get('address', ''),
                    category=place.get('category', '景点'),
                    rating=place.get('rating'),
                    description=place.get('description', '推荐地点'),
                    estimated_duration=120,  # 默认2小时
                    reasons=['符合您的偏好', '位置便利']
                )
                place_recommendations.append(place_rec)
            
            # 如果没有具体地点，生成默认建议
            if not place_recommendations:
                default_places = [
                    PlaceRecommendation(
                        name=f"{requirement.destination}市中心",
                        address="市中心区域",
                        category="城市观光",
                        description="探索城市核心区域",
                        estimated_duration=180,
                        reasons=['了解当地文化', '交通便利']
                    )
                ]
                place_recommendations = default_places
            
            day_plan = DayPlan(
                day=day_num,
                theme=f"第{day_num}天 - 探索{requirement.destination}",
                places=place_recommendations,
                route_summary=f"游览 {len(place_recommendations)} 个精选地点",
                estimated_total_time=sum(p.estimated_duration for p in place_recommendations),
                notes=[f"建议{requirement.transportation_mode}出行"]
            )
            days_plans.append(day_plan)
        
        # 创建完整计划
        plan = TravelPlan(
            id=str(uuid.uuid4()),
            title=f"{requirement.destination} {requirement.duration_days}日游",
            requirement=requirement,
            days=days_plans,
            overall_summary=f"为您精心规划的{requirement.destination} {requirement.duration_days}天行程，包含{sum(len(d.places) for d in days_plans)}个推荐地点",
            important_notes=[
                f"建议使用{requirement.transportation_mode}方式出行",
                "请根据实际情况调整时间安排",
                "建议提前预订热门景点门票"
            ]
        )
        
        conversation.current_plan = plan
        conversation.plan_versions.append(plan)
        conversation.stage = PlanningStage.INTERACTIVE_OPTIMIZATION
        
        return plan
    
    async def _tool_modify_plan(self, params: Dict[str, Any], conversation: Conversation) -> TravelPlan:
        """修改计划工具"""
        from app.models_v2 import DayPlan, PlaceRecommendation
        
        if not conversation.current_plan:
            raise ValueError("No current plan to modify")
        
        # 获取修改参数
        modification_type = params.get("type", "general")  # general, add_place, remove_place, change_day
        target_day = params.get("day")
        place_info = params.get("place_info", {})
        new_places = params.get("new_places", [])
        
        # 创建新版本
        new_plan = conversation.current_plan.model_copy(deep=True)
        new_plan.version += 1
        new_plan.updated_at = datetime.now()
        
        # 根据修改类型执行不同操作
        if modification_type == "add_place" and target_day and place_info:
            # 添加地点到指定天
            for day_plan in new_plan.days:
                if day_plan.day == target_day:
                    new_place = PlaceRecommendation(
                        name=place_info.get('name', '新地点'),
                        address=place_info.get('address', ''),
                        category=place_info.get('category', '景点'),
                        description=place_info.get('description', '用户添加的地点'),
                        estimated_duration=place_info.get('duration', 120),
                        reasons=['用户指定']
                    )
                    day_plan.places.append(new_place)
                    day_plan.estimated_total_time += new_place.estimated_duration
                    day_plan.route_summary = f"游览 {len(day_plan.places)} 个地点"
                    break
        
        elif modification_type == "remove_place" and target_day and place_info:
            # 从指定天移除地点
            place_name = place_info.get('name', '')
            for day_plan in new_plan.days:
                if day_plan.day == target_day:
                    original_places = day_plan.places[:]
                    day_plan.places = [p for p in day_plan.places if p.name != place_name]
                    if len(day_plan.places) < len(original_places):
                        day_plan.estimated_total_time = sum(p.estimated_duration for p in day_plan.places)
                        day_plan.route_summary = f"游览 {len(day_plan.places)} 个地点"
                    break
        
        elif modification_type == "change_theme" and target_day:
            # 修改某天的主题
            new_theme = params.get("theme", "")
            for day_plan in new_plan.days:
                if day_plan.day == target_day:
                    day_plan.theme = new_theme
                    break
        
        elif modification_type == "replace_places" and new_places:
            # 替换推荐地点
            for i, place_data in enumerate(new_places):
                if i < len(new_plan.days):
                    day_plan = new_plan.days[i]
                    new_place_recs = []
                    for place in place_data:
                        place_rec = PlaceRecommendation(
                            name=place.get('name', f'地点 {len(new_place_recs) + 1}'),
                            address=place.get('address', ''),
                            category=place.get('category', '景点'),
                            description=place.get('description', '推荐地点'),
                            estimated_duration=place.get('duration', 120),
                            reasons=place.get('reasons', ['符合需求'])
                        )
                        new_place_recs.append(place_rec)
                    
                    day_plan.places = new_place_recs
                    day_plan.estimated_total_time = sum(p.estimated_duration for p in new_place_recs)
                    day_plan.route_summary = f"游览 {len(new_place_recs)} 个精选地点"
        
        # 更新总体摘要
        total_places = sum(len(d.places) for d in new_plan.days)
        new_plan.overall_summary = f"已更新的{new_plan.requirement.destination} {new_plan.requirement.duration_days}天行程，包含{total_places}个地点"
        
        # 添加修改说明
        modification_note = f"根据您的反馈进行了调整 (版本 {new_plan.version})"
        if modification_note not in new_plan.important_notes:
            new_plan.important_notes.append(modification_note)
        
        conversation.current_plan = new_plan
        conversation.plan_versions.append(new_plan)
        
        return new_plan
    
    async def _tool_validate_plan(self, params: Dict[str, Any], conversation: Conversation) -> Dict[str, Any]:
        """验证计划工具"""
        if not conversation.current_plan:
            raise ValueError("No plan to validate")
        
        # 实现计划验证逻辑
        validation_result = {
            "valid": True,
            "issues": [],
            "suggestions": []
        }
        
        if validation_result["valid"]:
            conversation.stage = PlanningStage.FINAL_CONFIRMATION
        
        return validation_result
