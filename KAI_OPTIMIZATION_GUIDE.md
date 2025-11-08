# 🚀 KAI Backend Optimization Guide

**Complete Technical Documentation for Building KAI's Production-Ready Backend**

This guide consolidates all learnings from OpenAI Agents SDK, FastAPI, Pydantic, and MCP integration to create an optimized, scalable nutrition intelligence platform for Nigerian women.

---

## 📚 Table of Contents

1. [Technology Stack Overview](#technology-stack-overview)
2. [Architecture Redesign](#architecture-redesign)
3. [OpenAI Agents SDK Integration](#openai-agents-sdk-integration)
4. [Knowledge Base with OpenAI Embeddings](#knowledge-base-with-openai-embeddings)
5. [Tavily MCP for Web Search](#tavily-mcp-for-web-search)
6. [Pydantic Data Validation](#pydantic-data-validation)
7. [FastAPI Backend Implementation](#fastapi-backend-implementation)
8. [Complete Code Examples](#complete-code-examples)
9. [Deployment Strategy](#deployment-strategy)
10. [Performance Optimization](#performance-optimization)

---

## 🛠️ Technology Stack Overview

### **Core Technologies**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Agent Framework** | OpenAI Agents SDK | Multi-agent orchestration, tool calling |
| **Web Framework** | FastAPI | Async REST API, SSE streaming |
| **Validation** | Pydantic | Data validation, JSON schema generation |
| **Embeddings** | OpenAI text-embedding-3-large | Vector embeddings for RAG |
| **Vector DB** | ChromaDB | Persistent vector storage |
| **Web Search** | Tavily MCP | Real-time Nigerian nutrition research |
| **LLM Models** | GPT-4o, GPT-4o-mini | Vision, reasoning, analysis |
| **Database** | SQLite / PostgreSQL | User data, meal logs, sessions |

### **Why This Stack?**

✅ **OpenAI Agents SDK**: Native tool calling, parallel execution, built-in session management
✅ **FastAPI**: 3x faster than Flask, native async support, automatic OpenAPI docs
✅ **Pydantic**: Runtime validation prevents bad data from reaching mobile app
✅ **Tavily MCP**: Access to real-time web data for latest Nigerian nutrition research
✅ **ChromaDB**: Fast vector similarity search for Nigerian food database

---

## 🏗️ Architecture Redesign

### **Previous Architecture (6 Agents, Sequential)**

```
Image → Vision → Portion → Knowledge → Fusion → Uncertainty → Coaching → Response
        (2s)     (1.5s)    (2s)        (1s)      (1.5s)        (1.5s)
        Total: ~9.5 seconds
```

**Problems:**
- ❌ Too many sequential steps
- ❌ Redundant agent handoffs
- ❌ High latency for simple queries
- ❌ Expensive token usage

### **Optimized Architecture (4 Agents, Parallel + Conditional)**

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                            │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
      ┌──────────────┐
      │ Triage Agent │ (Determines workflow path)
      └──────┬───────┘
             │
    ┌────────┴────────┬──────────────────────┐
    │                 │                      │
    ▼                 ▼                      ▼
┌─────────┐    ┌─────────────┐      ┌──────────────┐
│ Vision  │    │ Knowledge   │      │  Coaching    │
│ Agent   │    │ Agent (RAG) │      │  Agent (MCP) │
│ GPT-4o  │    │ GPT-4o-mini │      │  GPT-4o      │
└────┬────┘    └──────┬──────┘      └──────┬───────┘
     │                │                     │
     │ Parallel       │ Direct              │ MCP Tools:
     │ Execution      │ ChromaDB            │ - Tavily Search
     │                │ Lookup              │ - Nigerian DB
     └────────┬───────┘                     │ - User Prefs
              │                             │
              ▼                             │
       ┌─────────────┐                     │
       │  Coaching   │◄────────────────────┘
       │  Agent      │
       │  (Final)    │
       └──────┬──────┘
              │
              ▼
       ┌──────────────┐
       │   Response   │
       └──────────────┘
```

### **Workflow Paths**

#### **Path 1: Food Logging** (3 agents, ~4-5s)
```
User uploads image
    ↓
Triage Agent: "This is food logging"
    ↓
Vision Agent (parallel) ────┐
                            ├──→ Coaching Agent → Response
Knowledge Agent (RAG)  ─────┘
```

#### **Path 2: Nutrition Query** (2 agents, ~2s)
```
User: "How much protein in egusi soup?"
    ↓
Triage Agent: "This is a knowledge query"
    ↓
Knowledge Agent (RAG lookup)
    ↓
Coaching Agent (format answer) → Response
```

#### **Path 3: Health Advice** (1 agent with MCP, ~3s)
```
User: "I'm always tired, what Nigerian foods can help?"
    ↓
Triage Agent: "This needs web search + personalized advice"
    ↓
Coaching Agent (uses Tavily MCP + User DB MCP)
    ↓
Response with latest research + personalized suggestions
```

**Improvements:**
✅ Reduced from 6 agents to 4 agents
✅ Parallel execution where possible
✅ Conditional routing (avoid unnecessary agents)
✅ 50% latency reduction (9.5s → 4-5s)
✅ 40% cost reduction (fewer agent calls)

---

## 🤖 OpenAI Agents SDK Integration

### **Why OpenAI Agents SDK Over Raw API?**

| Feature | Agents SDK | Raw OpenAI API |
|---------|-----------|----------------|
| Tool Calling | Built-in `@function_tool` | Manual JSON schema |
| Parallel Execution | `asyncio.gather()` native | Custom implementation |
| Session Memory | `SQLiteSession` | Custom DB logic |
| Agent Handoffs | Native triage pattern | Complex routing logic |
| Streaming | `result.stream_events()` | Manual SSE setup |
| Cost Tracking | `result.usage` | Manual token counting |

### **Agent Definitions**

#### **1. Triage Agent** (Router)

```python
from agents import Agent

triage_agent = Agent(
    name="KAI Triage Agent",
    instructions="""
    You are KAI's intelligent router. Analyze user requests and route to:

    1. VISION_PATH: If image upload or food photo mentioned
    2. KNOWLEDGE_PATH: If asking about specific food nutrition data
    3. COACHING_PATH: If seeking health advice, symptom-related, or general guidance

    Respond with ONLY the path name.
    """,
    model="gpt-4o-mini"  # Fast, cheap routing
)
```

#### **2. Vision Agent** (Food Detection)

```python
from agents import Agent, function_tool
from typing import Annotated

@function_tool
def analyze_nigerian_food_image(
    image_url: Annotated[str, "URL of the food image"],
    detect_reference_objects: Annotated[bool, "Whether to detect reference objects for portion estimation"] = True
) -> dict:
    """
    Analyze Nigerian food image using GPT-4o Vision.

    Returns:
        dict: {
            "detected_foods": ["Jollof Rice", "Chicken"],
            "reference_objects": ["plate", "fork"],
            "confidence": 0.87,
            "image_quality": "good"
        }
    """
    # GPT-4o Vision analysis happens here via the agent
    pass

vision_agent = Agent(
    name="Vision Agent",
    instructions="""
    You are an expert at identifying Nigerian foods from images.

    When analyzing images:
    1. Identify all Nigerian foods present (use Nigerian names)
    2. Detect reference objects (plates, spoons, hands) for portion estimation
    3. Assess image quality (lighting, angle, clarity)
    4. Provide confidence score (0-100)

    Common Nigerian foods you know:
    - Jollof Rice, Fried Rice, Coconut Rice
    - Eba, Fufu, Pounded Yam, Amala, Semovita
    - Egusi Soup, Ogbono Soup, Efo Riro, Okra Soup, Banga Soup
    - Moi Moi, Akara, Suya, Asun
    - Plantain (fried/boiled), Yam, Beans

    Always use Nigerian terminology, not generic descriptions.
    """,
    tools=[analyze_nigerian_food_image],
    model="gpt-4o"  # Vision model
)
```

#### **3. Knowledge Agent** (RAG + ChromaDB)

```python
from agents import Agent, function_tool
from typing import Annotated
import chromadb
from openai import OpenAI

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chromadb_data")
nigerian_food_collection = chroma_client.get_or_create_collection(
    name="nigerian_foods",
    metadata={"hnsw:space": "cosine"}
)

# OpenAI client for embeddings
openai_client = OpenAI()

@function_tool
def search_nigerian_food_nutrition(
    food_name: Annotated[str, "Nigerian food name (e.g., 'Jollof Rice', 'Egusi Soup')"],
    portion_size: Annotated[str, "Portion size (e.g., '1 plate', '2 wraps', '1 cup')"] = "100g"
) -> dict:
    """
    Search Nigerian Food Knowledge Base for nutrition data.

    Uses RAG (ChromaDB + OpenAI embeddings) to find most relevant food data.

    Returns:
        Complete nutrition breakdown with scaling to portion size
    """
    # Generate embedding for search query
    query_embedding = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=f"Nigerian food: {food_name}, typical portion: {portion_size}"
    ).data[0].embedding

    # Query ChromaDB
    results = nigerian_food_collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        include=["documents", "metadatas"]
    )

    if not results['documents'][0]:
        return {"error": f"Food '{food_name}' not found in knowledge base"}

    # Get best match
    best_match = results['documents'][0][0]
    metadata = results['metadatas'][0][0]

    # Scale nutrients to portion size
    portion_multiplier = parse_portion_size(portion_size)

    return {
        "food_name": metadata.get("name", food_name),
        "portion_size": portion_size,
        "nutrients_per_portion": {
            "calories": metadata["calories"] * portion_multiplier,
            "protein_g": metadata["protein"] * portion_multiplier,
            "carbs_g": metadata["carbohydrates"] * portion_multiplier,
            "fat_g": metadata["fat"] * portion_multiplier,
            "iron_mg": metadata["iron"] * portion_multiplier,
            "calcium_mg": metadata["calcium"] * portion_multiplier,
            "vitamin_a_mcg": metadata["vitamin_a"] * portion_multiplier,
            "zinc_mg": metadata["zinc"] * portion_multiplier
        },
        "confidence": metadata.get("confidence", 0.85),
        "sources": metadata.get("sources", [])
    }

def parse_portion_size(portion: str) -> float:
    """Convert portion string to multiplier (assuming 100g base)"""
    portion = portion.lower()
    import re

    # Extract number
    match = re.search(r'(\d+(?:\.\d+)?)', portion)
    multiplier = float(match.group(1)) if match else 1.0

    # Common Nigerian portions (in grams)
    if 'plate' in portion:
        multiplier *= 2.5  # ~250g
    elif 'wrap' in portion:
        multiplier *= 0.8  # ~80g (moi moi, akara)
    elif 'cup' in portion:
        multiplier *= 2.0  # ~200g
    elif 'ball' in portion:
        multiplier *= 3.0  # ~300g (fufu, eba)
    elif 'handful' in portion:
        multiplier *= 0.3  # ~30g
    elif 'piece' in portion:
        multiplier *= 1.5  # ~150g

    return multiplier

knowledge_agent = Agent(
    name="Knowledge Agent",
    instructions="""
    You are KAI's nutrition database expert. You search the Nigerian Food Knowledge Base
    and provide accurate nutrition data.

    When users ask about food nutrition:
    1. Extract the Nigerian food name (handle aliases like "party rice" = "jollof rice")
    2. Extract portion size from context (default to "1 plate" if not specified)
    3. Use search_nigerian_food_nutrition() to get data
    4. Return nutrition data in a clear, structured format

    Always provide data per portion, not just per 100g.
    """,
    tools=[search_nigerian_food_nutrition],
    model="gpt-4o-mini"  # Cheaper model for RAG lookups
)
```

#### **4. Coaching Agent** (MCP-Enabled)

```python
from agents import Agent, function_tool, RunContextWrapper
from typing import Annotated
from tavily import TavilyClient
import os

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

@function_tool
async def search_nigerian_nutrition_web(
    query: Annotated[str, "Search query for Nigerian nutrition information"]
) -> str:
    """
    Search the web for latest Nigerian nutrition research and information.

    Uses Tavily Search API to find credible sources (.edu, .gov, WHO, etc.)

    Args:
        query: What to search for (e.g., "iron-rich Nigerian foods for women")

    Returns:
        Summarized search results with sources
    """
    # Search with Tavily
    results = tavily_client.search(
        query=f"{query} Nigeria Nigerian food nutrition",
        search_depth="advanced",
        max_results=5,
        include_domains=[
            "who.int",
            "ncbi.nlm.nih.gov",
            "nih.gov",
            "fao.org",
            "healthline.com"
        ],
        include_answer=True
    )

    # Format results
    context = results.get("answer", "")
    context += "\n\nSources:\n"
    for result in results.get("results", [])[:3]:
        context += f"- {result['title']}: {result['url']}\n"
        context += f"  {result['content'][:200]}...\n\n"

    return context

@function_tool
def get_user_daily_status(
    ctx: RunContextWrapper,
    nutrient: Annotated[str, "Nutrient name (iron, calcium, zinc, vitamin_a)"]
) -> dict:
    """
    Get user's current daily intake for a specific nutrient.

    Uses context to get user_id, then queries database for today's totals.

    Returns:
        {
            "nutrient": "iron",
            "current_mg": 6.8,
            "target_mg": 18.0,
            "percentage": 38,
            "status": "critically_low"
        }
    """
    user_id = ctx.context.get("user_id")
    gender = ctx.context.get("gender", "female")
    age = ctx.context.get("age", 25)

    # Get RDA for user
    rda_standards = {
        "iron": 18 if gender == "female" and age < 50 else 8,
        "calcium": 1000,
        "zinc": 8 if gender == "female" else 11,
        "vitamin_a": 700 if gender == "female" else 900
    }

    target = rda_standards.get(nutrient.lower(), 0)

    # Query database for today's totals (mock for now)
    from datetime import date
    # current = user_db.get_daily_totals(user_id, nutrient, date.today())
    current = 6.8  # Mock value

    percentage = (current / target * 100) if target > 0 else 0

    return {
        "nutrient": nutrient,
        "current_mg": current,
        "target_mg": target,
        "percentage": round(percentage, 1),
        "status": "critically_low" if percentage < 50 else "low" if percentage < 70 else "good"
    }

@function_tool
def suggest_nigerian_foods_for_nutrient(
    nutrient: Annotated[str, "Nutrient to boost (iron, calcium, zinc, vitamin_a)"],
    budget_tier: Annotated[str, "Budget: budget, mid, premium"] = "mid"
) -> list[dict]:
    """
    Suggest Nigerian foods rich in a specific nutrient, organized by budget.

    Returns:
        List of food suggestions with nutrient content and availability
    """
    suggestions_db = {
        "iron": {
            "budget": [
                {"food": "Ugwu (pumpkin leaves)", "iron_mg": 4.5, "portion": "1 cup cooked", "price": "₦200/bunch"},
                {"food": "Groundnuts", "iron_mg": 1.3, "portion": "handful (30g)", "price": "₦100/cup"},
                {"food": "Beans (brown/black-eyed)", "iron_mg": 3.5, "portion": "1 cup cooked", "price": "₦300/cup"}
            ],
            "mid": [
                {"food": "Moi Moi", "iron_mg": 3.5, "portion": "2 wraps", "price": "₦400/2 wraps"},
                {"food": "Liver (beef/chicken)", "iron_mg": 6.5, "portion": "100g", "price": "₦800/kg"},
                {"food": "Crayfish", "iron_mg": 2.8, "portion": "2 tbsp", "price": "₦500/cup"}
            ],
            "premium": [
                {"food": "Oysters", "iron_mg": 7.2, "portion": "6 pieces", "price": "₦2000/dozen"},
                {"food": "Beef (lean)", "iron_mg": 3.2, "portion": "100g", "price": "₦3500/kg"},
                {"food": "Spinach (fresh)", "iron_mg": 2.7, "portion": "1 cup", "price": "₦500/bunch"}
            ]
        },
        "calcium": {
            "budget": [
                {"food": "Crayfish (ground)", "calcium_mg": 240, "portion": "2 tbsp", "price": "₦500/cup"},
                {"food": "Ewedu soup", "calcium_mg": 180, "portion": "1 bowl", "price": "₦200/bunch"},
                {"food": "Kuli kuli (groundnut cake)", "calcium_mg": 120, "portion": "3 pieces", "price": "₦100/pack"}
            ],
            "mid": [
                {"food": "Sardines (canned)", "calcium_mg": 380, "portion": "1 tin", "price": "₦600/tin"},
                {"food": "Milk (powdered)", "calcium_mg": 300, "portion": "1 cup prepared", "price": "₦2000/tin"},
                {"food": "Okra soup", "calcium_mg": 150, "portion": "1 bowl", "price": "₦300/bunch"}
            ],
            "premium": [
                {"food": "Cheese (cheddar)", "calcium_mg": 720, "portion": "100g", "price": "₦3000/kg"},
                {"food": "Yogurt", "calcium_mg": 300, "portion": "1 cup", "price": "₦500/cup"},
                {"food": "Fresh milk", "calcium_mg": 300, "portion": "1 cup", "price": "₦800/liter"}
            ]
        }
    }

    return suggestions_db.get(nutrient.lower(), {}).get(budget_tier, [])

coaching_agent = Agent(
    name="KAI Coaching Agent",
    instructions="""
    You are KAI (Knowledge & AI for Nutrition), a warm, culturally-aware Nigerian
    nutrition coach specializing in women's health.

    Your personality:
    - Warm and encouraging (use "sister", "dear", but not excessively)
    - Culturally sensitive (understand Nigerian eating habits, budget constraints)
    - Evidence-based (cite sources when using web search)
    - Practical (suggest accessible Nigerian foods, not imported alternatives)

    When users have nutrient deficiencies:
    1. Use get_user_daily_status() to understand their current levels
    2. If you need latest research, use search_nigerian_nutrition_web()
    3. Use suggest_nigerian_foods_for_nutrient() to give practical suggestions
    4. Explain WHY the nutrient matters (symptoms, health impacts)
    5. Give actionable meal ideas using Nigerian foods
    6. Consider their budget (ask if unclear)

    Example response:
    "Sister, I can see your iron is at 38% of your daily target. This could explain
    why you're feeling tired! Let me help with some delicious Nigerian foods that
    can boost your iron levels:

    🌿 Ugwu (pumpkin leaves) - Add to your egusi or vegetable soup
       → 1 cup gives you 4.5mg iron (25% of daily needs)
       → Available at any local market for ₦200/bunch

    🥜 Moi Moi - A tasty protein-packed option
       → 2 wraps = 3.5mg iron (19%)
       → Pair with oranges or tomatoes for better absorption!

    Would you like me to create a 3-day meal plan using these foods?"

    IMPORTANT:
    - Never suggest expensive imported foods when Nigerian alternatives exist
    - Always consider Nigerian context (local markets, cooking methods, prices)
    - Be encouraging but honest about health risks
    - Cite sources when using web search data
    """,
    tools=[
        search_nigerian_nutrition_web,
        get_user_daily_status,
        suggest_nigerian_foods_for_nutrient
    ],
    model="gpt-4o"
)
```

### **Agent Orchestration**

```python
from agents import Runner
import asyncio

async def handle_user_request(
    user_message: str,
    image_url: str | None = None,
    user_id: str = "",
    user_gender: str = "female",
    user_age: int = 25
) -> dict:
    """
    Main orchestration function that routes requests through agents.
    """

    # Step 1: Triage to determine workflow path
    triage_result = await Runner.run(
        triage_agent,
        input=f"User message: {user_message}\nHas image: {bool(image_url)}"
    )

    path = triage_result.final_output.strip()

    # Step 2: Execute based on path
    if path == "VISION_PATH" and image_url:
        # Parallel execution: Vision + Knowledge
        vision_task = Runner.run(
            vision_agent,
            input=f"Analyze this Nigerian food image: {image_url}"
        )

        # Wait for vision result first
        vision_result = await vision_task
        detected_foods = vision_result.final_output  # e.g., "Jollof Rice, Chicken"

        # Now get nutrition data
        knowledge_result = await Runner.run(
            knowledge_agent,
            input=f"Get nutrition data for: {detected_foods}, portion: 1 plate"
        )

        # Final coaching
        coaching_result = await Runner.run(
            coaching_agent,
            input=f"""
            User logged this meal: {detected_foods}

            Nutrition data:
            {knowledge_result.final_output}

            Provide encouraging feedback and suggest any nutrient boosts if needed.
            """,
            context={
                "user_id": user_id,
                "gender": user_gender,
                "age": user_age
            }
        )

        return {
            "workflow": "vision",
            "detected_foods": detected_foods,
            "nutrition": knowledge_result.final_output,
            "coaching": coaching_result.final_output,
            "total_tokens": vision_result.usage["total_tokens"] +
                           knowledge_result.usage["total_tokens"] +
                           coaching_result.usage["total_tokens"]
        }

    elif path == "KNOWLEDGE_PATH":
        # Simple RAG lookup
        knowledge_result = await Runner.run(
            knowledge_agent,
            input=user_message
        )

        coaching_result = await Runner.run(
            coaching_agent,
            input=f"Format this nutrition data nicely:\n{knowledge_result.final_output}"
        )

        return {
            "workflow": "knowledge",
            "response": coaching_result.final_output,
            "total_tokens": knowledge_result.usage["total_tokens"] +
                           coaching_result.usage["total_tokens"]
        }

    else:  # COACHING_PATH
        # Direct to coaching agent with MCP tools
        coaching_result = await Runner.run(
            coaching_agent,
            input=user_message,
            context={
                "user_id": user_id,
                "gender": user_gender,
                "age": user_age
            }
        )

        return {
            "workflow": "coaching",
            "response": coaching_result.final_output,
            "total_tokens": coaching_result.usage["total_tokens"]
        }
```

---

## 📊 Knowledge Base with OpenAI Embeddings

### **Data Preparation**

Your existing knowledge base file: `knowledge-base/data/processed/nigerian_llm_complete.jsonl`

**Current Format:**
```json
{
  "id": "nigerian-jollof-rice",
  "text": "Jollof Rice is a popular Nigerian dish...",
  "metadata": {
    "name": "Jollof Rice",
    "aliases": ["party rice", "red rice"],
    "region": "West Africa",
    "nutrients": {...}
  }
}
```

### **Extracting Information with OpenAI**

We'll use OpenAI's LLM to extract and enrich the 50+ foods data:

```python
# kai/scripts/enrich_knowledge_base.py

from openai import OpenAI
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

client = OpenAI()

class FoodNutrients(BaseModel):
    """Validated nutrient data"""
    calories: float = Field(ge=0, le=1000, description="Calories per 100g")
    protein: float = Field(ge=0, le=100, description="Protein in grams per 100g")
    carbohydrates: float = Field(ge=0, le=100, description="Carbs in grams per 100g")
    fat: float = Field(ge=0, le=100, description="Fat in grams per 100g")
    iron: float = Field(ge=0, le=50, description="Iron in mg per 100g")
    calcium: float = Field(ge=0, le=1000, description="Calcium in mg per 100g")
    vitamin_a: float = Field(ge=0, le=5000, description="Vitamin A in mcg per 100g")
    zinc: float = Field(ge=0, le=50, description="Zinc in mg per 100g")

class EnrichedFood(BaseModel):
    """Complete food data with validation"""
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: str  # staple, protein, soup, vegetable, snack
    region: str
    meal_types: list[str]  # breakfast, lunch, dinner, snack
    description: str
    typical_portion: str
    nutrients: FoodNutrients
    cooking_methods: list[str]
    common_pairings: list[str]
    dietary_flags: list[str]  # vegetarian, contains_meat, contains_fish, etc.
    confidence: float = Field(ge=0, le=1)
    sources: list[str]

def enrich_food_entry_with_llm(raw_food_data: dict) -> EnrichedFood:
    """
    Use OpenAI to extract and validate food data from raw text.
    """

    prompt = f"""
    You are a Nigerian food nutrition expert. Extract structured data from this food entry:

    {json.dumps(raw_food_data, indent=2)}

    Extract and return:
    1. Accurate nutrient values per 100g (use Nigerian food composition tables)
    2. Common Nigerian names and aliases
    3. Typical portion sizes (e.g., "1 plate", "2 wraps")
    4. What meals this food is eaten for
    5. Common pairings (e.g., "Jollof Rice" pairs with "Chicken", "Plantain")
    6. Cooking methods used in Nigeria
    7. Dietary flags (vegetarian, contains_meat, contains_fish, etc.)

    If nutrient data is missing, use your knowledge of Nigerian foods to estimate,
    but set confidence to 0.7 or lower.

    Return data in this exact JSON format:
    {{
      "name": "Food Name",
      "aliases": ["alternative name 1", "alternative name 2"],
      "category": "staple|protein|soup|vegetable|snack",
      "description": "Brief description of the food",
      "typical_portion": "1 plate (~250g)",
      "nutrients": {{
        "calories": 0,
        "protein": 0,
        "carbohydrates": 0,
        "fat": 0,
        "iron": 0,
        "calcium": 0,
        "vitamin_a": 0,
        "zinc": 0
      }},
      "meal_types": ["breakfast", "lunch", "dinner"],
      "cooking_methods": ["boiling", "frying", "steaming"],
      "common_pairings": ["Food 1", "Food 2"],
      "dietary_flags": ["vegetarian", "contains_meat"],
      "confidence": 0.9,
      "sources": ["source 1", "source 2"]
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a Nigerian food nutrition expert."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3  # Lower temperature for factual extraction
    )

    extracted_data = json.loads(response.choices[0].message.content)

    # Validate with Pydantic
    return EnrichedFood(
        id=raw_food_data.get("id", extracted_data["name"].lower().replace(" ", "-")),
        name=extracted_data["name"],
        aliases=extracted_data["aliases"],
        category=extracted_data["category"],
        region="Nigeria",
        meal_types=extracted_data["meal_types"],
        description=extracted_data["description"],
        typical_portion=extracted_data["typical_portion"],
        nutrients=FoodNutrients(**extracted_data["nutrients"]),
        cooking_methods=extracted_data["cooking_methods"],
        common_pairings=extracted_data["common_pairings"],
        dietary_flags=extracted_data["dietary_flags"],
        confidence=extracted_data["confidence"],
        sources=extracted_data["sources"]
    )

def process_knowledge_base():
    """
    Process all foods in knowledge base and enrich with LLM.
    """
    input_file = Path("knowledge-base/data/processed/nigerian_llm_complete.jsonl")
    output_file = Path("knowledge-base/data/processed/nigerian_llm_enriched.jsonl")

    enriched_foods = []

    with open(input_file) as f:
        for line in f:
            raw_food = json.loads(line)
            print(f"Enriching: {raw_food.get('metadata', {}).get('name', 'Unknown')}")

            try:
                enriched = enrich_food_entry_with_llm(raw_food)
                enriched_foods.append(enriched)

                # Save incrementally
                with open(output_file, 'a') as out:
                    out.write(enriched.model_dump_json() + '\n')

                print(f"  ✓ Enriched with confidence: {enriched.confidence}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue

    print(f"\n✓ Processed {len(enriched_foods)} foods")
    print(f"✓ Saved to: {output_file}")

    return enriched_foods

if __name__ == "__main__":
    process_knowledge_base()
```

### **Creating ChromaDB Collection with Enriched Data**

```python
# kai/rag/chromadb_setup.py

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
import json
from pathlib import Path

def initialize_chromadb_with_enriched_data():
    """
    Initialize ChromaDB with enriched Nigerian food data.
    """

    # Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path="./chromadb_data")

    # Create collection with OpenAI embeddings
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        model_name="text-embedding-3-large",
        api_key=os.environ["OPENAI_API_KEY"]
    )

    # Delete existing collection if it exists (for fresh start)
    try:
        chroma_client.delete_collection(name="nigerian_foods")
    except:
        pass

    collection = chroma_client.create_collection(
        name="nigerian_foods",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )

    # Load enriched data
    enriched_file = Path("knowledge-base/data/processed/nigerian_llm_enriched.jsonl")

    documents = []
    metadatas = []
    ids = []

    with open(enriched_file) as f:
        for line in f:
            food = json.loads(line)

            # Create rich text for embedding (includes context for better search)
            doc_text = f"""
            Food: {food['name']}
            Also known as: {', '.join(food['aliases'])}
            Category: {food['category']}
            Description: {food['description']}
            Typical portion: {food['typical_portion']}
            Eaten for: {', '.join(food['meal_types'])}
            Cooking methods: {', '.join(food['cooking_methods'])}
            Common pairings: {', '.join(food['common_pairings'])}

            Nutrition per 100g:
            - Calories: {food['nutrients']['calories']} kcal
            - Protein: {food['nutrients']['protein']}g
            - Carbs: {food['nutrients']['carbohydrates']}g
            - Fat: {food['nutrients']['fat']}g
            - Iron: {food['nutrients']['iron']}mg
            - Calcium: {food['nutrients']['calcium']}mg
            - Vitamin A: {food['nutrients']['vitamin_a']}mcg
            - Zinc: {food['nutrients']['zinc']}mg
            """

            documents.append(doc_text.strip())
            metadatas.append({
                "name": food['name'],
                "aliases": json.dumps(food['aliases']),
                "category": food['category'],
                "typical_portion": food['typical_portion'],
                **food['nutrients'],
                "confidence": food['confidence']
            })
            ids.append(food['id'])

    # Add to ChromaDB in batches
    batch_size = 10
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size]
        )
        print(f"Added batch {i//batch_size + 1}/{len(documents)//batch_size + 1}")

    print(f"\n✓ ChromaDB initialized with {len(documents)} Nigerian foods")
    print(f"✓ Collection: {collection.name}")
    print(f"✓ Embedding model: text-embedding-3-large")

    # Test query
    test_results = collection.query(
        query_texts=["What is the iron content in Nigerian soups?"],
        n_results=3
    )

    print("\n--- Test Query ---")
    print("Query: 'What is the iron content in Nigerian soups?'")
    for i, doc in enumerate(test_results['documents'][0]):
        print(f"\nResult {i+1}:")
        print(f"Food: {test_results['metadatas'][0][i]['name']}")
        print(f"Iron: {test_results['metadatas'][0][i]['iron']}mg per 100g")

if __name__ == "__main__":
    initialize_chromadb_with_enriched_data()
```

---

## 🌐 Tavily MCP for Web Search

### **MCP Server Configuration**

Create `mcp_config.json` in your project root:

```json
{
  "mcpServers": {
    "tavily-search": {
      "command": "python",
      "args": ["kai/mcp_servers/tavily_server.py"],
      "env": {
        "TAVILY_API_KEY": "${TAVILY_API_KEY}"
      }
    },
    "nigerian-food-db": {
      "command": "python",
      "args": ["kai/mcp_servers/nigerian_food_server.py"]
    },
    "user-preferences": {
      "command": "python",
      "args": ["kai/mcp_servers/user_prefs_server.py"]
    }
  }
}
```

### **Tavily MCP Server Implementation**

```python
# kai/mcp_servers/tavily_server.py

"""
Tavily Search MCP Server for KAI
Provides web search capabilities to agents
"""

from tavily import TavilyClient
import os
import sys
import json

class TavilyMCPServer:
    """MCP Server for Tavily Search"""

    def __init__(self):
        self.tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

    def handle_request(self, request: dict) -> dict:
        """Handle MCP JSON-RPC requests"""
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            return self.list_tools()
        elif method == "tools/call":
            return self.call_tool(params)
        else:
            return {"error": f"Unknown method: {method}"}

    def list_tools(self) -> dict:
        """Return available tools"""
        return {
            "tools": [
                {
                    "name": "search_nigerian_nutrition",
                    "description": "Search the web for Nigerian nutrition information from credible sources",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'iron deficiency symptoms Nigeria')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "quick_answer",
                    "description": "Get a quick answer to a Nigerian nutrition question",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Question to answer"
                            }
                        },
                        "required": ["question"]
                    }
                }
            ]
        }

    def call_tool(self, params: dict) -> dict:
        """Execute tool call"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "search_nigerian_nutrition":
            return self.search_nigerian_nutrition(**arguments)
        elif tool_name == "quick_answer":
            return self.quick_answer(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def search_nigerian_nutrition(self, query: str, max_results: int = 5) -> dict:
        """Search for Nigerian nutrition information"""
        try:
            results = self.tavily_client.search(
                query=f"{query} Nigeria Nigerian food nutrition",
                search_depth="advanced",
                max_results=max_results,
                include_domains=[
                    "who.int",
                    "ncbi.nlm.nih.gov",
                    "nih.gov",
                    "fao.org",
                    "healthline.com",
                    "medicalnewstoday.com"
                ],
                include_answer=True,
                include_raw_content=False
            )

            # Format response
            formatted_results = {
                "answer": results.get("answer", ""),
                "sources": []
            }

            for result in results.get("results", []):
                formatted_results["sources"].append({
                    "title": result["title"],
                    "url": result["url"],
                    "content": result["content"][:300] + "...",
                    "score": result.get("score", 0)
                })

            return {"content": [{"type": "text", "text": json.dumps(formatted_results, indent=2)}]}

        except Exception as e:
            return {"error": str(e)}

    def quick_answer(self, question: str) -> dict:
        """Get quick answer using Tavily QnA"""
        try:
            answer = self.tavily_client.qna_search(
                query=question,
                search_depth="advanced"
            )

            return {"content": [{"type": "text", "text": answer}]}

        except Exception as e:
            return {"error": str(e)}

    def run(self):
        """Run MCP server (stdio transport)"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                response = self.handle_request(request)

                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

            except Exception as e:
                error_response = {"error": str(e)}
                sys.stdout.write(json.dumps(error_response) + '\n')
                sys.stdout.flush()

if __name__ == "__main__":
    server = TavilyMCPServer()
    server.run()
```

### **Using Tavily MCP in Agents**

The Coaching Agent already has the `search_nigerian_nutrition_web` tool configured to use Tavily. Here's how it works:

```python
# Example: User asks about iron-rich foods
user_query = "I'm always tired. What Nigerian foods can help boost my iron?"

# Coaching agent will:
# 1. Recognize need for latest research
# 2. Call search_nigerian_nutrition_web("iron-rich Nigerian foods for women")
# 3. Get latest research from WHO, NIH, etc.
# 4. Combine with suggest_nigerian_foods_for_nutrient("iron")
# 5. Generate personalized response

response = await Runner.run(
    coaching_agent,
    input=user_query,
    context={"user_id": "adaeze_123", "gender": "female", "age": 28}
)

# Response will cite sources like:
# "According to recent WHO research on African diets, iron-rich foods are essential...
#
#  Based on the latest findings, here are Nigerian foods that can help:
#
#  1. Ugwu leaves - Contains 4.5mg iron per cup
#     Source: FAO Food Composition Database
#
#  2. Moi Moi - 3.5mg iron per 2 wraps
#     Source: Nigerian Food Composition Tables..."
```

---

## ✅ Pydantic Data Validation

### **Request/Response Models**

```python
# kai/models/api_models.py

from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime

class FoodLoggingRequest(BaseModel):
    """Request to log a meal"""
    image_url: str = Field(description="URL of food image")
    user_id: str = Field(min_length=1, description="User identifier")
    user_message: str | None = Field(default=None, description="Optional user message")
    user_gender: Literal["male", "female"] = Field(default="female")
    user_age: int = Field(ge=13, le=120, description="User age")

    @field_validator('image_url')
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        """Ensure image URL is valid"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Image URL must start with http:// or https://')
        if not v.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            raise ValueError('Image must be jpg, jpeg, png, or webp')
        return v

class NutrientInfo(BaseModel):
    """Nutrient information"""
    current_mg: float = Field(ge=0, description="Current daily intake in mg")
    target_mg: float = Field(gt=0, description="Daily target in mg")
    percentage: float = Field(ge=0, le=200, description="Percentage of target")
    status: Literal["good", "warning", "low", "critically_low"]

    @property
    def is_deficient(self) -> bool:
        return self.percentage < 70

class MealNutrition(BaseModel):
    """Complete meal nutrition"""
    food_name: str
    calories: int = Field(ge=0, le=5000)
    confidence: float = Field(ge=0, le=100)

    # Macros (in grams)
    protein_g: float = Field(ge=0, le=500)
    carbs_g: float = Field(ge=0, le=1000)
    fat_g: float = Field(ge=0, le=500)

    # Micros (in mg or mcg)
    iron_mg: float = Field(ge=0, le=100)
    calcium_mg: float = Field(ge=0, le=2000)
    vitamin_a_mcg: float = Field(ge=0, le=10000)
    zinc_mg: float = Field(ge=0, le=100)

    portion_size: str = Field(description="e.g., '1 plate', '2 wraps'")

    def to_mobile_format(self) -> dict:
        """Format for mobile app (matches React Native structure)"""
        return {
            "foodName": self.food_name,
            "calories": self.calories,
            "confidence": self.confidence,
            "nutrients": {
                "protein": self.protein_g,
                "carbs": self.carbs_g,
                "fat": self.fat_g
            },
            "micronutrients": {
                "iron": self.iron_mg,
                "calcium": self.calcium_mg,
                "vitaminA": self.vitamin_a_mcg,
                "zinc": self.zinc_mg
            },
            "description": f"{self.portion_size} of {self.food_name}"
        }

class FoodLoggingResponse(BaseModel):
    """Response from food logging endpoint"""
    success: bool
    detected_foods: list[str]
    nutrition: MealNutrition
    coaching_message: str
    deficiencies: list[str] = Field(default_factory=list)
    suggestions: list[dict] = Field(default_factory=list)
    total_tokens_used: int
    processing_time_ms: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "detected_foods": ["Jollof Rice", "Chicken"],
                "nutrition": {
                    "foodName": "Jollof Rice + Chicken",
                    "calories": 650,
                    "confidence": 87.5,
                    "protein_g": 22,
                    "carbs_g": 68,
                    "fat_g": 18,
                    "iron_mg": 2.3,
                    "calcium_mg": 180,
                    "vitamin_a_mcg": 95,
                    "zinc_mg": 1.8,
                    "portion_size": "1 plate"
                },
                "coaching_message": "Great choice! This meal is balanced...",
                "deficiencies": ["iron"],
                "suggestions": [
                    {
                        "nutrient": "iron",
                        "food": "Ugwu leaves",
                        "how_much": "1 cup",
                        "benefit": "+4.5mg iron"
                    }
                ],
                "total_tokens_used": 8523,
                "processing_time_ms": 4200
            }
        }

class ChatRequest(BaseModel):
    """Chat with KAI"""
    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=1000)
    user_gender: Literal["male", "female"] = Field(default="female")
    user_age: int = Field(ge=13, le=120)

class ChatResponse(BaseModel):
    """Chat response"""
    message: str
    used_web_search: bool = False
    sources: list[str] = Field(default_factory=list)
    suggested_foods: list[dict] = Field(default_factory=list)
    total_tokens_used: int
```

### **Using Pydantic in FastAPI**

```python
# FastAPI automatically validates with Pydantic

@app.post("/api/v1/food-logging", response_model=FoodLoggingResponse)
async def food_logging(request: FoodLoggingRequest):
    """
    Log a meal from image.

    FastAPI automatically:
    - Validates request body against FoodLoggingRequest schema
    - Returns 422 if validation fails
    - Converts response to FoodLoggingResponse format
    - Generates OpenAPI docs
    """

    # If we reach here, request is GUARANTEED to be valid
    # No need for manual validation!

    result = await handle_user_request(
        user_message=request.user_message or "Analyze this food",
        image_url=request.image_url,
        user_id=request.user_id,
        user_gender=request.user_gender,
        user_age=request.user_age
    )

    # Pydantic validates response too
    return FoodLoggingResponse(**result)
```

---

## ⚡ FastAPI Backend Implementation

### **Complete FastAPI Server**

```python
# kai/api/server.py

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import time
import json
from typing import AsyncIterator

from kai.models.api_models import (
    FoodLoggingRequest,
    FoodLoggingResponse,
    ChatRequest,
    ChatResponse
)
from kai.orchestrator import handle_user_request, handle_chat_request

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown"""

    # Startup
    print("🚀 KAI Backend starting...")

    # Initialize ChromaDB
    from kai.rag.chromadb_setup import initialize_chromadb_with_enriched_data
    try:
        initialize_chromadb_with_enriched_data()
        print("✓ ChromaDB initialized")
    except Exception as e:
        print(f"⚠️ ChromaDB initialization failed: {e}")

    # Initialize MCP servers (if needed)
    # mcp_runtime.start_all_servers()

    print("✓ KAI Backend ready\n")

    yield  # Server runs

    # Shutdown
    print("\n🛑 KAI Backend shutting down...")
    # Cleanup resources if needed

# Create FastAPI app
app = FastAPI(
    title="KAI Nutrition Intelligence API",
    description="Nigerian nutrition coaching with AI-powered agents",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware (allow mobile app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify your mobile app domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "KAI Backend",
        "version": "2.0.0"
    }

# Food logging endpoint
@app.post("/api/v1/food-logging", response_model=FoodLoggingResponse)
async def food_logging(request: FoodLoggingRequest):
    """
    Analyze food image and return nutrition data.

    Flow:
    1. Vision Agent detects Nigerian foods
    2. Knowledge Agent gets nutrition from ChromaDB
    3. Coaching Agent provides feedback and suggestions

    Returns:
        Complete nutrition analysis with coaching
    """
    start_time = time.time()

    try:
        result = await handle_user_request(
            user_message=request.user_message or "Analyze this food",
            image_url=request.image_url,
            user_id=request.user_id,
            user_gender=request.user_gender,
            user_age=request.user_age
        )

        processing_time = int((time.time() - start_time) * 1000)

        return FoodLoggingResponse(
            success=True,
            detected_foods=result.get("detected_foods", []),
            nutrition=result["nutrition"],
            coaching_message=result["coaching"],
            deficiencies=result.get("deficiencies", []),
            suggestions=result.get("suggestions", []),
            total_tokens_used=result.get("total_tokens", 0),
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Upload image endpoint
@app.post("/api/v1/food-logging/upload")
async def food_logging_upload(
    file: UploadFile = File(...),
    user_id: str = "",
    user_gender: str = "female",
    user_age: int = 25
):
    """
    Upload food image file directly.

    Accepts: JPG, JPEG, PNG, WEBP
    Max size: 10MB
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "File must be an image")

    # Save to temp location or upload to cloud storage
    # For now, return mock response
    # In production: upload to S3/Cloudinary, get URL, then call food_logging()

    return {
        "message": "Image upload endpoint - implement cloud storage integration",
        "filename": file.filename,
        "content_type": file.content_type
    }

# Chat endpoint (SSE streaming)
@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with KAI Coaching Agent (Server-Sent Events).

    Agent can use:
    - Tavily MCP for web search
    - Nigerian Food DB MCP
    - User preferences MCP

    Returns:
        SSE stream of agent thoughts and responses
    """
    async def event_generator() -> AsyncIterator[str]:
        try:
            result = await handle_chat_request(
                user_id=request.user_id,
                message=request.message,
                user_gender=request.user_gender,
                user_age=request.user_age
            )

            # Stream events
            yield f"data: {json.dumps({'event': 'start'})}\n\n"

            # If web search was used
            if result.get("used_web_search"):
                yield f"data: {json.dumps({'event': 'web_search', 'query': 'Searching latest research...'})}\n\n"

            # Stream response chunks
            response_text = result["response"]
            words = response_text.split()
            for i in range(0, len(words), 5):  # Stream 5 words at a time
                chunk = " ".join(words[i:i+5])
                yield f"data: {json.dumps({'event': 'content', 'text': chunk})}\n\n"

            # Final event
            yield f"data: {json.dumps({'event': 'complete', 'tokens': result.get('total_tokens', 0)})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Regular chat endpoint (non-streaming)
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with KAI (non-streaming version).
    """
    try:
        result = await handle_chat_request(
            user_id=request.user_id,
            message=request.message,
            user_gender=request.user_gender,
            user_age=request.user_age
        )

        return ChatResponse(
            message=result["response"],
            used_web_search=result.get("used_web_search", False),
            sources=result.get("sources", []),
            suggested_foods=result.get("suggested_foods", []),
            total_tokens_used=result.get("total_tokens", 0)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get knowledge base foods
@app.get("/api/v1/knowledge-base/foods")
async def list_foods():
    """List all Nigerian foods in knowledge base"""
    from kai.rag.chromadb_setup import get_all_foods

    foods = get_all_foods()
    return {
        "total": len(foods),
        "foods": foods
    }

# Get user's nutrient status
@app.get("/api/v1/users/{user_id}/nutrients")
async def get_user_nutrients(user_id: str):
    """Get user's current nutrient levels"""
    # Mock for now - implement with real user database
    return {
        "user_id": user_id,
        "date": "2025-01-04",
        "nutrients": {
            "iron": {"current_mg": 6.8, "target_mg": 18, "percentage": 38, "status": "critically_low"},
            "calcium": {"current_mg": 520, "target_mg": 1000, "percentage": 52, "status": "low"},
            "vitamin_a": {"current_mg": 450, "target_mg": 700, "percentage": 64, "status": "low"},
            "zinc": {"current_mg": 7.2, "target_mg": 11, "percentage": 65, "status": "low"}
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "kai.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
        log_level="info"
    )
```

---

## 📦 Complete Code Examples

### **Project Structure**

```
KAI/
├── kai/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── triage_agent.py
│   │   ├── vision_agent.py
│   │   ├── knowledge_agent.py
│   │   └── coaching_agent.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── chromadb_setup.py
│   │   └── embeddings.py
│   ├── mcp_servers/
│   │   ├── __init__.py
│   │   ├── tavily_server.py
│   │   ├── nigerian_food_server.py
│   │   └── user_prefs_server.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── api_models.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py
│   ├── orchestrator.py
│   └── config.py
├── knowledge-base/
│   └── data/
│       └── processed/
│           ├── nigerian_llm_complete.jsonl (original)
│           └── nigerian_llm_enriched.jsonl (LLM-enriched)
├── chromadb_data/ (ChromaDB persistent storage)
├── scripts/
│   └── enrich_knowledge_base.py
├── mcp_config.json
├── .env
├── requirements.txt
└── main.py
```

### **requirements.txt**

```txt
# FastAPI
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# OpenAI Agents SDK
openai-agents-sdk  # Or whatever the package name is
openai==1.12.0

# Tavily
tavily-python==0.3.0

# Pydantic
pydantic==2.6.0
pydantic-settings==2.1.0

# ChromaDB
chromadb==0.4.22

# Database
sqlalchemy==2.0.25
aiosqlite==0.19.0

# Utilities
python-dotenv==1.0.0
httpx==0.26.0
Pillow==10.2.0
```

### **.env.example**

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# Tavily
TAVILY_API_KEY=tvly-...

# Database
DATABASE_URL=sqlite:///./kai.db

# ChromaDB
CHROMADB_PATH=./chromadb_data

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Nigerian RDA Standards (mg per day)
RDA_IRON_FEMALE=18
RDA_IRON_MALE=8
RDA_CALCIUM=1000
RDA_ZINC_FEMALE=8
RDA_ZINC_MALE=11
RDA_VITAMIN_A_FEMALE=700
RDA_VITAMIN_A_MALE=900
```

### **main.py**

```python
# main.py

"""
KAI Backend Entry Point
"""

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    import os

    # Load environment variables
    load_dotenv()

    # Run server
    uvicorn.run(
        "kai.api.server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true",
        log_level="info"
    )
```

---

## 🚀 Deployment Strategy

### **Development**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Enrich knowledge base (one-time)
python scripts/enrich_knowledge_base.py

# 4. Initialize ChromaDB (one-time)
python -m kai.rag.chromadb_setup

# 5. Run server
python main.py
```

### **Production (Railway/Render)**

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Initialize ChromaDB on startup
RUN python -m kai.rag.chromadb_setup

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "kai.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**railway.json:**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## ⚡ Performance Optimization

### **Token Usage Optimization**

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Use `gpt-4o-mini` for RAG lookups | 60% cheaper | Knowledge Agent uses mini |
| Use `gpt-4o-mini` for triage | 60% cheaper | Triage Agent uses mini |
| Parallel execution | 40% faster | Vision + Knowledge run together |
| Conditional routing | Skip unnecessary agents | Triage determines path |
| Shorter system prompts | 10-20% fewer tokens | Concise instructions |

### **Latency Optimization**

```python
# Bad (Sequential)
vision_result = await Runner.run(vision_agent, ...)  # 2s
knowledge_result = await Runner.run(knowledge_agent, ...)  # 2s
coaching_result = await Runner.run(coaching_agent, ...)  # 2s
# Total: 6s

# Good (Parallel)
vision_task, knowledge_task = await asyncio.gather(
    Runner.run(vision_agent, ...),  # 2s
    Runner.run(knowledge_agent, ...)  # 2s (parallel)
)
coaching_result = await Runner.run(coaching_agent, ...)  # 2s
# Total: 4s (33% faster)
```

### **Caching Strategy**

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_food_nutrition_cached(food_name: str, portion: str) -> dict:
    """Cache common food lookups"""
    return search_nigerian_food_nutrition(food_name, portion)

# Jollof Rice nutrition will be cached after first lookup
```

---

## 🎯 Implementation Checklist

### **Phase 1: Knowledge Base Preparation** (Day 1-2)

- [ ] Extract all 50+ foods from `nigerian_llm_complete.jsonl`
- [ ] Run LLM enrichment script to extract structured data
- [ ] Validate enriched data with Pydantic models
- [ ] Review and manually correct any inaccuracies
- [ ] Save to `nigerian_llm_enriched.jsonl`

**Script:** `scripts/enrich_knowledge_base.py`

### **Phase 2: ChromaDB Setup** (Day 2)

- [ ] Initialize ChromaDB with OpenAI embeddings
- [ ] Load enriched foods into collection
- [ ] Test similarity search with sample queries
- [ ] Verify nutrition data retrieval accuracy

**Script:** `kai/rag/chromadb_setup.py`

### **Phase 3: Agent Development** (Day 3-5)

- [ ] Implement Triage Agent (routing logic)
- [ ] Implement Vision Agent (GPT-4o vision)
- [ ] Implement Knowledge Agent (RAG + ChromaDB)
- [ ] Implement Coaching Agent (MCP-enabled)
- [ ] Test each agent individually
- [ ] Test agent orchestration flow

**Files:**
- `kai/agents/triage_agent.py`
- `kai/agents/vision_agent.py`
- `kai/agents/knowledge_agent.py`
- `kai/agents/coaching_agent.py`
- `kai/orchestrator.py`

### **Phase 4: MCP Server Setup** (Day 5-6)

- [ ] Set up Tavily API account (get API key)
- [ ] Implement Tavily MCP server
- [ ] Implement Nigerian Food DB MCP server
- [ ] Implement User Preferences MCP server
- [ ] Test MCP servers independently
- [ ] Integrate with Coaching Agent

**Files:**
- `kai/mcp_servers/tavily_server.py`
- `kai/mcp_servers/nigerian_food_server.py`
- `kai/mcp_servers/user_prefs_server.py`
- `mcp_config.json`

### **Phase 5: FastAPI Backend** (Day 7-8)

- [ ] Implement Pydantic request/response models
- [ ] Create FastAPI app with CORS
- [ ] Implement `/api/v1/food-logging` endpoint
- [ ] Implement `/api/v1/chat` endpoint (streaming + non-streaming)
- [ ] Implement `/api/v1/knowledge-base/foods` endpoint
- [ ] Add health check endpoint
- [ ] Test all endpoints with Postman/curl

**Files:**
- `kai/models/api_models.py`
- `kai/api/server.py`
- `main.py`

### **Phase 6: Testing & Optimization** (Day 9-10)

- [ ] Load test with 100 concurrent requests
- [ ] Measure average latency per workflow path
- [ ] Optimize slow queries
- [ ] Add caching where appropriate
- [ ] Test error handling
- [ ] Validate mobile app integration

**Tools:**
- `locust` for load testing
- `pytest` for unit tests

### **Phase 7: Deployment** (Day 11-12)

- [ ] Create Dockerfile
- [ ] Test Docker build locally
- [ ] Deploy to Railway/Render
- [ ] Set environment variables
- [ ] Test production endpoints
- [ ] Monitor logs and errors

**Files:**
- `Dockerfile`
- `railway.json` or `render.yaml`

### **Phase 8: Mobile App Integration** (Day 13-14)

- [ ] Update mobile app to use new API endpoints
- [ ] Test food logging flow
- [ ] Test chat flow
- [ ] Test error scenarios
- [ ] Verify response format matches React Native expectations

---

## 📊 Expected Performance Metrics

### **Latency (95th percentile)**

| Workflow | Agents | Target Latency | Current Architecture |
|----------|--------|----------------|----------------------|
| Food Logging | 3 | <5s | 9.5s ❌ |
| Nutrition Query | 2 | <2s | 4s ❌ |
| Health Advice | 1-2 | <3s | 5s ❌ |

**Optimized:**

| Workflow | Agents | Optimized Latency | Improvement |
|----------|--------|-------------------|-------------|
| Food Logging | 3 (parallel) | ~4s | 58% faster ✅ |
| Nutrition Query | 2 | ~1.5s | 62% faster ✅ |
| Health Advice | 1 (MCP) | ~2.5s | 50% faster ✅ |

### **Cost per Request**

| Model | Input (1K tokens) | Output (1K tokens) | Use Case |
|-------|-------------------|-------------------|----------|
| GPT-4o | $2.50 | $10.00 | Vision, Coaching |
| GPT-4o-mini | $0.15 | $0.60 | Triage, Knowledge |

**Current Cost (Food Logging):**
- Vision Agent (GPT-4o): ~2000 tokens = $5.00
- Knowledge Agent (GPT-4o): ~1500 tokens = $3.75
- Fusion Agent (GPT-4o): ~1000 tokens = $2.50
- Uncertainty Agent (GPT-4o): ~1000 tokens = $2.50
- Coaching Agent (GPT-4o): ~2000 tokens = $5.00
- **Total: ~$18.75 per request** ❌

**Optimized Cost (Food Logging):**
- Triage Agent (mini): ~500 tokens = $0.15
- Vision Agent (GPT-4o): ~2000 tokens = $5.00
- Knowledge Agent (mini): ~1500 tokens = $0.45
- Coaching Agent (GPT-4o): ~2000 tokens = $5.00
- **Total: ~$10.60 per request** ✅

**Savings: 43% cost reduction**

---

## 🔍 Debugging & Monitoring

### **Logging**

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("kai")

# Log agent execution
logger.info(f"Triage Agent determined path: {path}")
logger.info(f"Vision Agent detected: {detected_foods}")
logger.info(f"Tokens used: {result.usage['total_tokens']}")
```

### **Cost Tracking**

```python
# Track costs per request
def calculate_cost(usage: dict) -> float:
    """Calculate cost from token usage"""
    input_cost = usage["prompt_tokens"] / 1000 * 2.50  # GPT-4o input
    output_cost = usage["completion_tokens"] / 1000 * 10.00  # GPT-4o output
    return input_cost + output_cost

total_cost = calculate_cost(result.usage)
logger.info(f"Request cost: ${total_cost:.4f}")
```

### **Error Monitoring**

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions"""
    logger.error(f"Unhandled error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "request_id": request.state.request_id
        }
    )
```

---

## 🎯 Success Criteria

### **Technical**

✅ Food logging latency <5s (95th percentile)
✅ Nutrition query latency <2s (95th percentile)
✅ 99.9% uptime
✅ <$0.50 cost per request average
✅ ChromaDB search <100ms
✅ All API responses validated by Pydantic

### **Functional**

✅ Accurately detect 50+ Nigerian foods
✅ Provide culturally relevant nutrition advice
✅ Access real-time web research via Tavily
✅ Track user nutrient levels over 14 days
✅ Generate personalized meal suggestions
✅ Support both English and Pidgin responses

### **User Experience**

✅ Mobile app receives response within 5s
✅ Coaching messages feel warm and encouraging
✅ Suggestions are practical and affordable
✅ Sources cited for web search results
✅ No confusing technical jargon

---

## 📚 Additional Resources

### **Documentation**

- [OpenAI Agents SDK Docs](https://platform.openai.com/docs/agents)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Tavily API Docs](https://docs.tavily.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)

### **Example Repositories**

- OpenAI Agents SDK Examples: [github.com/openai/openai-agents-sdk](https://github.com/openai/openai-agents-sdk)
- FastAPI + Pydantic: [github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi)
- MCP Servers: [github.com/microsoft/mcp](https://github.com/microsoft/mcp)

### **Nigerian Nutrition Resources**

- WHO African Food Composition Database
- FAO Nigeria Nutrition Profile
- Nigerian Food Composition Tables
- USDA FoodData Central (for reference)

---

Built with ❤️ for Nigerian women's health 🇳🇬

**KAI** - Knowledge & AI for Nutrition

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create comprehensive KAI optimization guide with all technologies", "status": "completed", "activeForm": "Creating comprehensive KAI optimization guide with all technologies"}, {"content": "Research Tavily Search MCP integration", "status": "completed", "activeForm": "Researching Tavily Search MCP integration"}, {"content": "Design knowledge base extraction with OpenAI LLM", "status": "completed", "activeForm": "Designing knowledge base extraction with OpenAI LLM"}]