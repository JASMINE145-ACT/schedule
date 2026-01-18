"""Workflow module - Business trip planning workflow nodes (inspired by SQL_LLM)

This module defines workflow nodes for the business trip planner,
similar to SQL_LLM's workflow structure with nodes and state management.

Architecture:
- Workflow Nodes: Define stages of planning process
- State Management: Track planning state and progress
- Context Management: Prepare context for LLM processing
- Error Handling: Automatic retry and error correction

Workflow Stages:
1. understand_requirements: Extract business trip requirements
2. geocode_locations: Geocode all locations
3. calculate_distances: Calculate distance matrix (with traffic)
4. search_business_places: Search restaurants/hotels
5. optimize_route: Optimize route order
6. assess_traffic_risks: Assess traffic risks
7. generate_alternatives: Generate alternative routes
8. generate_report: Generate final report
"""

from .nodes import (
    understand_requirements_node,
    geocode_locations_node,
    calculate_distances_node,
    search_business_places_node,
    optimize_route_node,
    assess_traffic_risks_node,
    generate_alternatives_node,
    generate_report_node
)

__all__ = [
    "understand_requirements_node",
    "geocode_locations_node",
    "calculate_distances_node",
    "search_business_places_node",
    "optimize_route_node",
    "assess_traffic_risks_node",
    "generate_alternatives_node",
    "generate_report_node"
]

