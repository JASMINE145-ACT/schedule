"""V2 版本的 LLM 服务 - 支持工具调用和对话"""

import os
import json
from typing import List, Dict, Any, Optional
import anthropic


class LLMService:
    """V2 版本的 LLM 服务"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 LLM 服务
        
        Args:
            api_key: Anthropic API key
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. "
                "Please set it in environment variables or pass as parameter."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "claude-3-haiku-20240307",
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        与 LLM 对话并支持工具调用
        
        Args:
            messages: 对话消息列表
            tools: 可用工具列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            LLM 响应，包含可能的工具调用
        """
        try:
            # 从 messages 中提取 system 消息
            system_prompt = None
            filtered_messages = []
            
            for msg in messages:
                if msg.get("role") == "system":
                    # 提取 system 消息作为顶层参数
                    system_prompt = msg.get("content", "")
                else:
                    # 保留其他消息（user 和 assistant）
                    filtered_messages.append(msg)
            
            # 准备请求参数
            request_params = {
                "model": model,
                "messages": filtered_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # 如果有 system 消息，作为顶层参数添加
            if system_prompt:
                request_params["system"] = system_prompt
            
            # 添加工具（如果提供）
            if tools:
                request_params["tools"] = tools
            
            # 调用 Claude API
            response = self.client.messages.create(**request_params)
            
            # 解析响应
            result = {
                "content": "",
                "tool_calls": []
            }
            
            # 处理响应内容
            for content_block in response.content:
                if content_block.type == "text":
                    result["content"] += content_block.text
                elif content_block.type == "tool_use":
                    result["tool_calls"].append({
                        "id": content_block.id,
                        "function": {
                            "name": content_block.name,
                            "arguments": json.dumps(content_block.input)
                        }
                    })
            
            return result
            
        except Exception as e:
            raise ValueError(f"LLM chat error: {str(e)}")
    
    async def extract_travel_requirements(
        self,
        user_input: str
    ) -> Dict[str, Any]:
        """
        从自然语言中提取商务接待需求
        
        Args:
            user_input: 用户的自然语言描述
            
        Returns:
            提取的需求信息
        """
        system_prompt = """你是一个专业的商务接待行程需求分析师。请从用户的自然语言描述中提取结构化的商务接待行程信息。

本系统专注于商务接待规划（而非旅游规划），重点考虑：
- 商务会面地点选择（写字楼、商务区、工业园等）
- 交通高峰时段规避（避免延误商务会面）
- 住宿策略优化（权衡通勤时间和成本）
- 替代方案设计（应对突发情况）

请提取以下信息：
1. 目的地（城市/国家）
2. 行程天数
3. 团队人数
4. 交通方式（包车、自驾、公共交通等）
5. 商务活动类型（商务拜访、客户接待、会议、工厂参观等）
6. 必去地点（固定锚点，如会议中心、工业园等）
7. 候选地点（可选地点，如商务会面区、供应商拜访点等）
8. 约束条件（交通高峰限制、时间限制、单程车程限制等）
9. 住宿策略要求（是否需要换酒店、住宿区域偏好等）
10. 特殊要求或注意事项（硬约束，如某天必须到达某地点）

如果某些信息不明确或缺失，请在响应中标注。

请以JSON格式返回结果，格式如下：
{
  "destination": "目的地",
  "duration_days": 天数,
  "group_size": 人数,
  "transportation_mode": "交通方式（包车/自驾/公共交通）",
  "business_activities": ["商务活动1", "商务活动2"],
  "required_locations": ["必去地点1", "必去地点2"],
  "candidate_locations": ["候选地点1", "候选地点2"],
  "constraints": ["约束1", "约束2"],
  "accommodation_strategy": "住宿策略要求",
  "special_notes": ["注意事项1"],
  "missing_info": ["缺失信息1"],
  "confidence": 0.8
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response = await self.chat_with_tools(messages, temperature=0.3)
            
            # 尝试从响应中解析 JSON
            content = response.get("content", "")
            
            # 提取 JSON（简单方法）
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # 如果没有找到有效的 JSON，返回结构化响应
            return {
                "raw_analysis": content,
                "needs_clarification": True,
                "confidence": 0.3
            }
            
        except Exception as e:
            raise ValueError(f"Requirements extraction error: {str(e)}")
    
    async def generate_plan_suggestions(
        self,
        requirement: Dict[str, Any],
        places_data: List[Dict[str, Any]],
        distance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        基于需求和地点数据生成商务接待计划建议
        
        Args:
            requirement: 商务接待需求
            places_data: 地点数据（商务地点）
            distance_data: 距离数据
            
        Returns:
            商务接待计划建议
        """
        system_prompt = """你是一个专业的商务接待行程规划师。基于用户需求、商务地点和距离信息，生成详细的商务接待行程计划。

本系统专注于商务接待规划（而非旅游规划），重点考虑：
- 商务会面地点选择（写字楼、商务区、工业园等）
- 交通高峰时段规避（避免延误商务会面）
- 路线逻辑清晰，减少折返
- 住宿策略优化（权衡通勤时间和成本）

请考虑以下因素：
1. **地理位置优化**：减少往返，形成闭环路线
2. **交通高峰规避**：避开早晚高峰（07:00-09:00，16:30-18:30）
3. **时间安排合理**：预留机动缓冲时段，避免过于紧张
4. **必去地点优先**：确保必去地点安排在合适的时间
5. **单程车程限制**：确保单程车程不超过2小时
6. **商务活动适配**：根据商务活动类型安排合适的地点

生成的计划应包含：
- 每日主题和区域（如：市区商务区、工业园、港口区等）
- 上午、中午、下午的行程安排
- 必去地点和候选地点的选择
- 路线逻辑说明（为什么这样串、如何减少折返）
- 时间安排建议（避开高峰、预留缓冲）
- 交通风险评估（识别高风险路段和时间段）
- 替代方案（精简版路线、提前出发策略）"""

        user_prompt = f"""请基于以下信息生成商务接待行程计划：

商务接待需求：
{json.dumps(requirement, ensure_ascii=False, indent=2)}

商务地点（推荐地点）：
{json.dumps(places_data[:10], ensure_ascii=False, indent=2)}

距离信息（地点间距离和时间）：
{json.dumps(distance_data[:20], ensure_ascii=False, indent=2)}

请生成详细的每日商务接待行程安排，包含：
1. 每日必去地点和候选地点的选择
2. 路线逻辑说明（形成闭环，减少折返）
3. 时间安排（避开高峰，预留缓冲）
4. 交通风险评估（高风险/中风险/低风险路段和时段）
5. 替代方案（精简版路线）

特别注意：
- 这是商务接待规划，不是旅游规划
- 重点考虑交通高峰规避和路线优化
- 预留机动缓冲时段应对商务会面可能延长的情况"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.chat_with_tools(messages, temperature=0.6)
            return {
                "suggestions": response.get("content", ""),
                "model": model,
                "timestamp": "now"
            }
        except Exception as e:
            raise ValueError(f"Plan generation error: {str(e)}")
    
    async def analyze_user_feedback(
        self,
        current_plan: Dict[str, Any],
        user_feedback: str
    ) -> Dict[str, Any]:
        """
        分析用户反馈并提供修改建议
        
        Args:
            current_plan: 当前计划
            user_feedback: 用户反馈
            
        Returns:
            分析结果和修改建议
        """
        system_prompt = """你是一个专业的旅行规划顾问。用户对当前的旅行计划提出了反馈，请分析反馈内容并提供具体的修改建议。

请分析：
1. 用户的具体需求或不满
2. 需要修改的计划部分
3. 具体的修改方案
4. 修改的影响和权衡

提供清晰的修改建议和解释。"""

        user_prompt = f"""当前计划：
{json.dumps(current_plan, ensure_ascii=False, indent=2)}

用户反馈：
{user_feedback}

请分析用户反馈并提供修改建议。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.chat_with_tools(messages, temperature=0.5)
            return {
                "analysis": response.get("content", ""),
                "requires_tools": "search_places" in response.get("content", "").lower(),
                "modification_type": "content_change"  # 可以是 content_change, route_change, time_change 等
            }
        except Exception as e:
            raise ValueError(f"Feedback analysis error: {str(e)}")
    
    async def validate_plan_feasibility(
        self,
        plan: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证计划的可行性
        
        Args:
            plan: 旅行计划
            constraints: 约束条件
            
        Returns:
            验证结果
        """
        system_prompt = """你是一个旅行计划验证专家。请检查计划的可行性，包括时间安排、交通连接、预算估算等。

检查要点：
1. 时间安排是否合理
2. 地点间交通是否可行
3. 活动时长是否适当
4. 是否有冲突或遗漏
5. 预算是否现实

提供具体的问题和建议。"""

        user_prompt = f"""请验证以下旅行计划：

计划：
{json.dumps(plan, ensure_ascii=False, indent=2)}

约束条件：
{json.dumps(constraints, ensure_ascii=False, indent=2)}

请提供验证结果和改进建议。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.chat_with_tools(messages, temperature=0.3)
            content = response.get("content", "")
            
            # 简单的可行性判断
            is_feasible = "可行" in content or "合理" in content
            has_issues = "问题" in content or "建议" in content
            
            return {
                "feasible": is_feasible and not has_issues,
                "analysis": content,
                "issues": [],  # 可以进一步解析具体问题
                "suggestions": []  # 可以进一步解析具体建议
            }
        except Exception as e:
            raise ValueError(f"Plan validation error: {str(e)}")
