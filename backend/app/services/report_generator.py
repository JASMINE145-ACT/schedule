"""Report generator for business trip plans"""

from typing import Dict, Any, List
from datetime import datetime


class ReportGenerator:
    """Generate business trip markdown reports from plan data"""
    
    def __init__(self):
        pass
    
    def generate_markdown(
        self,
        plan_data: Dict[str, Any],
        include_details: bool = True
    ) -> str:
        """
        Generate business trip markdown report from plan data
        
        Args:
            plan_data: Complete plan data
            include_details: Whether to include detailed information
            
        Returns:
            Markdown formatted business trip report
        """
        request = plan_data.get("request", {})
        days = plan_data.get("days", [])
        summary = plan_data.get("summary", {})
        
        report = []
        
        # Title - 商务接待行程规划
        city = request.get('city', '商务接待')
        total_days = request.get('total_days', 1)
        report.append(f"# {city}{total_days}天商务接待行程规划")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Executive Summary - 执行摘要
        report.append("## 执行摘要")
        report.append("")
        report.append("本行程规划基于Google Maps API获取的实际地理数据和路线信息，为商务拜访、客户接待等商务活动提供优化路线建议。")
        report.append("")
        report.append("**关键数据：**")
        if summary:
            report.append(f"- **总行程天数**: {total_days}天")
            report.append(f"- **团队规模**: {request.get('team_size', 1)}人")
            transportation_mode = request.get('transportation_mode', 'driving')
            transportation_name = {
                'driving': '包车/自驾',
                'transit': '公共交通',
                'walking': '步行'
            }.get(transportation_mode, transportation_mode)
            report.append(f"- **交通方式**: {transportation_name}")
            if summary.get("total_distance_km"):
                report.append(f"- **总距离**: {summary['total_distance_km']:.1f}公里")
            if summary.get("total_duration_hours"):
                report.append(f"- **总行程时间**: {summary['total_duration_hours']:.1f}小时（不含活动时间）")
            if days:
                # 提取关键路线数据
                key_distances = []
                for day in days:
                    segments = day.get("segments", [])
                    for seg in segments:
                        if seg.get("distance_text"):
                            key_distances.append(seg["distance_text"])
                if key_distances:
                    report.append(f"- **关键路线**: 最长单程约 {max([float(d.replace('km', '').replace('公里', '').strip()) for d in key_distances if 'km' in d or '公里' in d], default=0):.1f} 公里")
            report.append("")
        
        report.append("---")
        report.append("")
        
        # Daily Plans - 参考 jakarta_business_trip/itinerary.md 的详细格式
        for day_plan in days:
            day_num = day_plan.get("day", 1)
            report.append(f"## 第{day_num}天：{day_plan.get('theme', day_plan.get('region', '商务行程'))}")
            report.append("")
            
            # 住宿/起终点
            start_location = day_plan.get("start_location") or day_plan.get("accommodation")
            if start_location:
                report.append("### 住宿/起终点")
                report.append(f"**{start_location.get('name', '起点')}**")
                if start_location.get("address"):
                    report.append(f"- 地址：{start_location['address']}")
                if start_location.get("coordinates"):
                    coord = start_location['coordinates']
                    report.append(f"- 坐标：{coord.get('lat', '')}, {coord.get('lng', '')}")
                report.append("")
            
            if day_plan.get("date"):
                report.append(f"**日期**: {day_plan['date']}")
                report.append("")
            
            # 上午行程
            morning_segments = [s for s in day_plan.get("segments", []) if s.get("time_period") == "morning" or (s.get("departure_time") and "08" <= s.get("departure_time", "")[:2] <= "12")]
            if morning_segments:
                report.append("### 上午行程（08:00-12:00）")
                report.append("")
                
                for i, segment in enumerate(morning_segments, 1):
                    from_loc = segment.get("from_location", "")
                    to_loc = segment.get("to_location", "")
                    departure = segment.get("departure_time", "")
                    arrival = segment.get("arrival_time", "")
                    
                    # 必去点标识
                    is_required = segment.get("is_required", False)
                    required_marker = "**必去**" if is_required else "**可选**"
                    
                    report.append(f"**{departure or '08:00'}-{arrival or '12:00'} {to_loc or from_loc}**")
                    report.append(f"- {required_marker}：{segment.get('activity_description', segment.get('description', ''))}")
                    
                    if segment.get("coordinates"):
                        coord = segment['coordinates']
                        report.append(f"- **坐标**：{coord.get('lat', '')}, {coord.get('lng', '')}")
                    
                    if segment.get("address"):
                        report.append(f"- **地址**：{segment['address']}")
                    
                    if segment.get("distance_text"):
                        distance_km = segment.get("distance_meters", 0) / 1000 if segment.get("distance_meters") else None
                        distance_str = segment['distance_text']
                        if distance_km:
                            report.append(f"- **距离{from_loc or '起点'}**：{distance_km:.1f}km，{segment.get('duration_text', '约' + str(segment.get('duration_seconds', 0) // 60) + '分钟')}")
                        else:
                            report.append(f"- **距离**：{distance_str}")
                    
                    if segment.get("duration_text"):
                        duration_text = segment['duration_text']
                        if segment.get("is_rush_hour"):
                            non_rush_duration = segment.get("non_rush_duration_text")
                            if non_rush_duration:
                                report.append(f"- **预计时间**：{non_rush_duration}（非高峰），**高峰时可能{duration_text}**")
                            else:
                                report.append(f"- **预计时间**：{duration_text}（非高峰），**高峰时可能延长**")
                        else:
                            report.append(f"- **预计时间**：{duration_text}")
                    
                    if segment.get("route_description"):
                        report.append(f"- **路线逻辑**：{segment['route_description']}")
                    
                    report.append("")
            
            # 中午行程
            lunch_segments = [s for s in day_plan.get("segments", []) if s.get("time_period") == "lunch" or "午餐" in str(s.get("activity_description", ""))]
            if lunch_segments:
                report.append("### 中午行程（12:00-13:30）")
                report.append("")
                
                for segment in lunch_segments:
                    to_loc = segment.get("to_location", "")
                    report.append(f"**12:00-13:30 商务午餐**")
                    if to_loc:
                        report.append(f"- **推荐区域**：{to_loc}")
                    if segment.get("distance_text"):
                        report.append(f"- **距离上午地点**：{segment['distance_text']}")
                    report.append("")
            
            # 下午行程
            afternoon_segments = [s for s in day_plan.get("segments", []) if s.get("time_period") == "afternoon" or (s.get("departure_time") and "13" <= s.get("departure_time", "")[:2] <= "18")]
            if afternoon_segments:
                report.append("### 下午行程（13:30-18:00）")
                report.append("")
                report.append("**推荐路线顺序：**")
                report.append("")
                
                for i, segment in enumerate(afternoon_segments, 1):
                    from_loc = segment.get("from_location", "")
                    to_loc = segment.get("to_location", "")
                    departure = segment.get("departure_time", "")
                    arrival = segment.get("arrival_time", "")
                    
                    report.append(f"{i}. **{to_loc or segment.get('activity_description', '地点' + str(i))}**（{departure or '13:30'}-{arrival or '18:00'}）")
                    
                    if from_loc:
                        report.append(f"   - 距离{from_loc}：{segment.get('distance_text', '')}，{segment.get('duration_text', '')}")
                    
                    if segment.get("activity_description"):
                        report.append(f"   - **活动**：{segment['activity_description']}")
                    
                    if segment.get("advantages"):
                        report.append(f"   - **优势**：{segment['advantages']}")
                    
                    if segment.get("notes"):
                        report.append(f"   - **注意**：{segment['notes']}")
                    
                    report.append("")
                
                # 机动缓冲时段
                buffer_segment = day_plan.get("buffer_segment")
                if buffer_segment:
                    report.append("**机动缓冲时段**")
                    report.append(f"- **建议地点**：{buffer_segment.get('location', '')}")
                    report.append(f"- **用途**：应对堵车/加会/临时改点")
                    report.append("")
            
            # 返回酒店或下一站
            return_segment = day_plan.get("return_segment")
            if return_segment:
                report.append("### 返回酒店")
                report.append("")
                report.append(f"**{return_segment.get('departure_time', '18:00')}-{return_segment.get('arrival_time', '18:30')} 返回{return_segment.get('to_location', '酒店')}**")
                if return_segment.get("distance_text"):
                    report.append(f"- 从任何下午点返回：{return_segment['distance_text']}")
                report.append(f"- **建议**：{return_segment.get('departure_time', '18:00')}前出发，避开晚高峰（16:30-18:30）的尾段")
                report.append("")
            
            # 交通风险评估 - 详细格式
            risks = day_plan.get("risks", [])
            if risks:
                report.append(f"### 第{day_num}天交通风险评估")
                report.append("")
                
                high_risks = [r for r in risks if r.get("level") == "high"]
                medium_risks = [r for r in risks if r.get("level") == "medium"]
                low_risks = [r for r in risks if r.get("level") == "low"]
                
                if high_risks:
                    report.append("**高风险时段：**")
                    for risk in high_risks:
                        report.append(f"- **{risk.get('time', risk.get('type', '时段'))}**：{risk.get('description', '')}")
                        if risk.get("cause"):
                            report.append(f"  - **原因**：{risk['cause']}")
                        if risk.get("mitigation"):
                            report.append(f"  - **缓解措施**：{risk['mitigation']}")
                    report.append("")
                
                if medium_risks:
                    report.append("**中风险路段/时段：**")
                    for risk in medium_risks:
                        report.append(f"- **{risk.get('location', risk.get('type', '路段'))}**：{risk.get('description', '')}")
                        if risk.get("cause"):
                            report.append(f"  - **原因**：{risk['cause']}")
                        if risk.get("mitigation"):
                            report.append(f"  - **缓解措施**：{risk['mitigation']}")
                    report.append("")
                
                if low_risks:
                    report.append("**低风险路段/时段：**")
                    for risk in low_risks:
                        report.append(f"- **{risk.get('location', risk.get('type', '路段'))}**：{risk.get('description', '')}")
                    report.append("")
            
            # 替代方案 - 详细格式
            alternative_plan = day_plan.get("alternative_plan")
            if alternative_plan:
                report.append(f"### 第{day_num}天替代方案（时间紧张时）")
                report.append("")
                
                if isinstance(alternative_plan, dict):
                    if alternative_plan.get("description"):
                        report.append(alternative_plan["description"])
                        report.append("")
                    if alternative_plan.get("simplified_route"):
                        report.append("精简方案：")
                        for i, step in enumerate(alternative_plan["simplified_route"], 1):
                            report.append(f"{i}. {step}")
                        report.append("")
                    if alternative_plan.get("removed_points"):
                        report.append("**砍掉的点：**")
                        for point in alternative_plan["removed_points"]:
                            report.append(f"- ❌ {point}")
                        report.append("")
                else:
                    report.append(str(alternative_plan))
                    report.append("")
            
            report.append("---")
            report.append("")
        
        # 整体交通风险评估总结 - 参考 jakarta_business_trip/itinerary.md
        all_risks = []
        for day in days:
            day_risks = day.get("risks", [])
            for risk in day_risks:
                risk['day'] = day.get("day", 0)
            all_risks.extend(day_risks)
        
        if all_risks:
            report.append("## 整体交通风险评估总结")
            report.append("")
            
            high_risks = [r for r in all_risks if r.get("level") == "high"]
            medium_risks = [r for r in all_risks if r.get("level") == "medium"]
            
            if high_risks:
                report.append("### 最高风险路段/时段")
                report.append("")
                for i, risk in enumerate(high_risks, 1):
                    day_num = risk.get('day', 0)
                    report.append(f"{i}. **第{day_num}天{risk.get('time', risk.get('type', '高风险'))}**")
                    report.append(f"   - **风险等级**：高")
                    if risk.get("cause"):
                        report.append(f"   - **原因**：{risk['cause']}")
                    if risk.get("mitigation"):
                        report.append(f"   - **缓解措施**：{risk['mitigation']}")
                    report.append("")
            
            if medium_risks:
                report.append("### 中风险路段/时段")
                report.append("")
                for i, risk in enumerate(medium_risks, 1):
                    day_num = risk.get('day', 0)
                    report.append(f"{i}. **第{day_num}天{risk.get('location', risk.get('type', '中风险'))}**")
                    report.append(f"   - **风险等级**：中")
                    if risk.get("cause"):
                        report.append(f"   - **原因**：{risk['cause']}")
                    if risk.get("mitigation"):
                        report.append(f"   - **缓解措施**：{risk['mitigation']}")
                    report.append("")
            
            if not high_risks and not medium_risks:
                report.append("✅ 整体交通风险较低，路线规划合理。")
                report.append("")
        
        # 替代方案总结
        alternative_plans = [d.get("alternative_plan") for d in days if d.get("alternative_plan")]
        if alternative_plans:
            report.append("## 替代方案")
            report.append("")
            for i, day in enumerate(days, 1):
                alt = day.get("alternative_plan")
                if alt:
                    report.append(f"### 第{i}天替代方案")
                    report.append("")
                    if isinstance(alt, dict):
                        if alt.get("description"):
                            report.append(alt["description"])
                    else:
                        report.append(str(alt))
                    report.append("")
            report.append("---")
            report.append("")
        
        # 每日时间表建议 - 参考 jakarta_business_trip/itinerary.md
        report.append("## 每日时间表建议")
        report.append("")
        
        for day_plan in days:
            day_num = day_plan.get("day", 1)
            report.append(f"### 第{day_num}天时间表")
            report.append("")
            report.append("| 时间 | 活动 | 地点 | 备注 |")
            report.append("|------|------|------|------|")
            
            # 上午
            morning_segments = [s for s in day_plan.get("segments", []) if s.get("time_period") == "morning" or (s.get("departure_time") and "08" <= s.get("departure_time", "")[:2] <= "12")]
            for seg in morning_segments:
                time_range = f"{seg.get('departure_time', '08:00')}-{seg.get('arrival_time', '12:00')}"
                activity = seg.get("activity_description", seg.get("to_location", "商务活动"))
                location = seg.get("to_location", "")
                notes = ""
                if seg.get("is_rush_hour"):
                    notes += "避开早高峰 "
                if seg.get("is_required"):
                    notes += "必去"
                report.append(f"| {time_range} | {activity} | {location} | {notes} |")
            
            # 中午
            lunch_segments = [s for s in day_plan.get("segments", []) if s.get("time_period") == "lunch" or "午餐" in str(s.get("activity_description", ""))]
            for seg in lunch_segments:
                report.append(f"| 12:00-13:30 | 商务午餐 | {seg.get('to_location', '')} | {seg.get('distance_text', '')} |")
            
            # 下午
            afternoon_segments = [s for s in day_plan.get("segments", []) if s.get("time_period") == "afternoon" or (s.get("departure_time") and "13" <= s.get("departure_time", "")[:2] <= "18")]
            for seg in afternoon_segments:
                time_range = f"{seg.get('departure_time', '13:30')}-{seg.get('arrival_time', '18:00')}"
                activity = seg.get("activity_description", seg.get("to_location", "商务活动"))
                location = seg.get("to_location", "")
                notes = ""
                if seg.get("departure_time") and "16:30" <= seg.get("departure_time", "") <= "18:00":
                    notes += "避开晚高峰 "
                report.append(f"| {time_range} | {activity} | {location} | {notes} |")
            
            # 返回
            return_seg = day_plan.get("return_segment")
            if return_seg:
                report.append(f"| {return_seg.get('departure_time', '18:00')}-{return_seg.get('arrival_time', '18:30')} | 返回酒店 | {return_seg.get('to_location', '')} | 避开晚高峰尾段 |")
            
            report.append("")
        
        # 关键建议总结 - 参考 jakarta_business_trip/itinerary.md
        report.append("## 关键建议总结")
        report.append("")
        
        # 出发时间建议
        report.append("### 出发时间")
        for day_plan in days:
            day_num = day_plan.get("day", 1)
            segments = day_plan.get("segments", [])
            morning_seg = next((s for s in segments if s.get("time_period") == "morning" or (s.get("departure_time") and "08" <= s.get("departure_time", "")[:2] <= "09")), None)
            if morning_seg:
                dep_time = morning_seg.get("departure_time", "")
                is_rush = morning_seg.get("is_rush_hour", False)
                if is_rush:
                    report.append(f"- **第{day_num}天**：**{dep_time}前出发**（关键！避开早高峰）")
                else:
                    report.append(f"- **第{day_num}天**：{dep_time or '08:30'}后出发（避开早高峰）")
        report.append("")
        
        # 机动缓冲
        report.append("### 机动缓冲")
        for day_plan in days:
            day_num = day_plan.get("day", 1)
            buffer_seg = day_plan.get("buffer_segment")
            if buffer_seg:
                report.append(f"- **第{day_num}天**：{buffer_seg.get('time', '16:30-17:00')} {buffer_seg.get('location', '机动缓冲')}")
        report.append("")
        
        # 交通风险规避
        report.append("### 交通风险规避")
        report.append("1. **避开高峰时段**：07:00-09:00，16:30-18:30")
        report.append("2. **早出发**：建议在高峰前或高峰后出发")
        report.append("3. **预留缓冲**：每天至少1小时机动时间")
        report.append("4. **选择最优路线**：优先选择避开拥堵的路线")
        report.append("")
        
        report.append("---")
        report.append("")
        
        # Data Source
        report.append("## 数据来源")
        report.append("")
        report.append("- **地理编码**：Google Maps Geocoding API")
        report.append("- **路线规划**：Google Maps Directions API")
        report.append("- **距离矩阵**：Google Maps Distance Matrix API")
        report.append("- **地点搜索**：Google Maps Places API")
        report.append("")
        report.append(f"**生成时间**：基于实时API数据")
        report.append(f"**坐标系统**：WGS84（Google Maps标准）")
        report.append("")
        report.append("---")
        report.append("")
        
        # 注意事项
        report.append("## 注意事项")
        report.append("")
        report.append("1. **实际交通时间可能因拥堵而延长**：建议预留20-30%额外时间")
        report.append("2. **商务会面可能延长时间**：机动缓冲时段很重要")
        report.append("3. **天气因素**：雨季可能影响交通，建议关注天气预报")
        report.append("4. **司机熟悉路况**：包车司机应能提供实时路线调整建议")
        report.append("5. **收费公路**：部分路线需经过收费公路，准备现金或电子支付")
        report.append("")
        
        if request.get("notes"):
            report.append("## 其他备注")
            report.append("")
            report.append(request["notes"])
            report.append("")
        
        report.append("---")
        report.append("")
        report.append(f"**文档版本**：v1.0  ")
        report.append(f"**最后更新**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        report.append("")
        
        return "\n".join(report)
    
    def generate_summary(self, days: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics
        
        Args:
            days: List of daily plans
            
        Returns:
            Summary dictionary
        """
        total_distance = 0
        total_duration = 0
        total_segments = 0
        high_risk_count = 0
        
        for day in days:
            segments = day.get("segments", [])
            total_segments += len(segments)
            
            for segment in segments:
                total_distance += segment.get("distance_meters", 0)
                total_duration += segment.get("duration_seconds", 0)
                
                if segment.get("risk_level") == "high":
                    high_risk_count += 1
        
        return {
            "total_distance_meters": total_distance,
            "total_distance_km": total_distance / 1000,
            "total_duration_seconds": total_duration,
            "total_duration_hours": total_duration / 3600,
            "total_segments": total_segments,
            "high_risk_segments": high_risk_count,
            "total_days": len(days)
        }

