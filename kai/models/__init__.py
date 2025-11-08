"""
KAI Models Package

Pydantic models for API requests/responses and agent communication.
"""

from .agent_models import (
    # Request Models
    ChatRequest,
    NutritionQueryRequest,

    # Agent Result Models
    TriageResult,
    DetectedFood,
    VisionResult,
    NutrientInfo,
    FoodNutritionData,
    KnowledgeResult,
    NutrientInsight,
    MealSuggestion,
    CoachingResult,

    # Response Models
    FoodLoggingResponse,
    ChatResponse,

    # Shared Context
    AgentContext,
)

__all__ = [
    # Requests
    "ChatRequest",
    "NutritionQueryRequest",

    # Agent Results
    "TriageResult",
    "DetectedFood",
    "VisionResult",
    "NutrientInfo",
    "FoodNutritionData",
    "KnowledgeResult",
    "NutrientInsight",
    "MealSuggestion",
    "CoachingResult",

    # Responses
    "FoodLoggingResponse",
    "ChatResponse",

    # Context
    "AgentContext",
]
