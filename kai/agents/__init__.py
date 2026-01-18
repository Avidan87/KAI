"""
KAI Agents Package

Multi-agent system for Nigerian food nutrition tracking.

Agents:
- VisionAgent: Detects Nigerian foods from images
- KnowledgeAgent: Retrieves nutrition data via ChromaDB RAG
- ChatAgent: Handles all conversations (questions, feedback, progress)
"""

from .vision_agent import VisionAgent, detect_nigerian_foods
from .knowledge_agent import KnowledgeAgent, retrieve_food_nutrition
from .chat_agent import ChatAgent, get_chat_agent

__all__ = [
    # Agent Classes
    "VisionAgent",
    "KnowledgeAgent",
    "ChatAgent",

    # Convenience Functions
    "detect_nigerian_foods",
    "retrieve_food_nutrition",
    "get_chat_agent",
]
