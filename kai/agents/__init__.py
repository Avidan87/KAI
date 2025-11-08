"""
KAI Agents Package

Multi-agent system for Nigerian food nutrition tracking.

Agent Workflow:
1. Triage Agent - Routes requests to appropriate workflow
2. Vision Agent - Detects Nigerian foods from images
3. Knowledge Agent - Retrieves nutrition data via RAG
4. Coaching Agent - Provides personalized health advice
"""

from .triage_agent import TriageAgent, route_request
from .vision_agent import VisionAgent, detect_nigerian_foods
from .knowledge_agent import KnowledgeAgent, retrieve_food_nutrition
from .coaching_agent import CoachingAgent, provide_nutrition_coaching

__all__ = [
    # Agent Classes
    "TriageAgent",
    "VisionAgent",
    "KnowledgeAgent",
    "CoachingAgent",

    # Convenience Functions
    "route_request",
    "detect_nigerian_foods",
    "retrieve_food_nutrition",
    "provide_nutrition_coaching",
]
