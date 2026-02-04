# KAI - Architecture Documentation

> **Nigerian Nutrition Intelligence System**
> AI-powered food logging, nutrition tracking, and personalized coaching

## 🏗️ System Overview

KAI is a multi-agent AI system that analyzes Nigerian food images, calculates nutrition, and provides personalized coaching. The system uses GPT-4o Vision, SAM 2 segmentation, MiDaS depth estimation, and pgvector-based nutrition retrieval — all backed by Supabase PostgreSQL.

```
┌─────────────────────────────────────────────────────────────┐
│                      USER REQUEST                           │
│              (Image Upload + Optional Message)              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    KAI API (FastAPI)                         │
│                   kai/api/server.py                          │
│              HF Spaces (port 7860) / Local (8000)           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                              │
│                 kai/orchestrator.py                          │
│        Coordinates multi-agent workflow execution           │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    ┌─────────┐         ┌─────────┐        ┌─────────┐
    │ TRIAGE  │         │ VISION  │        │KNOWLEDGE│
    │  AGENT  │         │  AGENT  │        │  AGENT  │
    └─────────┘         └─────────┘        └─────────┘
         │                   │                   │
         │                   ├──► SAM 2          │
         │                   ├──► MiDaS MCP      │
         │                   └──► GPT-4o Vision  │
         │                                       │
         │                                       └──► Supabase pgvector
         │                                       └──► OpenAI Embeddings
         │
         └─────────────────────────────────────────┐
                                                   ▼
                                          ┌─────────────┐
                                          │    CHAT     │
                                          │    AGENT    │
                                          └─────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────┐
                                          │  RESPONSE   │
                                          └─────────────┘
```

---

## 🌐 Deployment Architecture

```
📱 Flutter App
     │
     ▼
🤗 HF Spaces ─── Docker (Python 3.11 + SAM 2 + FastAPI)
     │                Port 7860, CPU Basic (2 vCPU, 16GB RAM)
     │
     ├──► 🗄️ Supabase (PostgreSQL + pgvector)
     │        - 9 tables (users, meals, foods, stats, embeddings)
     │        - 75 Nigerian foods with 3072-dim embeddings
     │        - Connected via supabase-py (HTTPS)
     │
     ├──► 🚂 Railway (MiDaS MCP Server)
     │        - Depth Anything V2 Small (24.8M params)
     │        - Batch portion estimation API
     │        - Keepalive ping every 5 minutes
     │
     └──► 🤖 OpenAI API
              - GPT-4o (vision, chat)
              - GPT-4o-mini (triage, knowledge)
              - text-embedding-3-large (3072-dim)
```

All services communicate over **public HTTPS** — no VPNs or private networking required.

---

## 📦 Core Components

### 1. API Layer (`kai/api/server.py`)

FastAPI server exposing REST endpoints:

- **POST /api/v1/food-logging-upload** — Full pipeline (Vision → Knowledge → Save)
- **POST /api/v1/chat** — Chat with KAI (nutrition questions, feedback, progress)
- **POST /api/v1/auth/signup** — User registration
- **POST /api/v1/auth/login** — User authentication
- **GET /api/v1/users/profile** — User profile + health data + RDV
- **PUT /api/v1/users/health-profile** — Update health profile (BMR/TDEE calculation)
- **GET /api/v1/users/nutrition-plan** — Goal-driven nutrition plan with priority nutrients
- **GET /api/v1/users/stats** — Daily nutrition statistics
- **GET /api/v1/meals/history** — Meal history (paginated)
- **GET /health** — Health check

**Key Features:**

- JWT authentication (all endpoints except signup/login/health)
- CORS middleware for cross-origin requests
- Lifespan management (database init, Railway keepalive start/stop)
- Goal-driven food logging response (6-8 priority nutrients per goal)

---

### 2. Orchestrator (`kai/orchestrator.py`)

Central coordination layer that routes requests through appropriate agents.

**Food Logging Workflow** (with image):

```
1. Vision Agent → Detects foods, estimates portions via SAM 2 + MiDaS
2. Knowledge Agent → Retrieves nutrition data via pgvector RAG
3. Save meal to Supabase (meals + meal_foods + daily_nutrients)
4. Update user stats (background task)
5. Return priority nutrients for user's health goal
```

**Chat Workflow** (no image):

```
1. Chat Agent receives user message
2. Intelligent tool selection based on query type:
   - "How was my last meal?" → analyze_last_meal (Database + RDV analysis)
   - "What's in jollof rice?" → search_foods (pgvector)
   - "How am I doing?" → get_user_progress (Database)
   - "Suggest a meal" → suggest_meal (goal-driven, pgvector)
   - "What should I eat for anemia?" → web_search (Tavily)
3. GPT-4o generates personalized response
4. Returns coaching feedback with suggestions
```

**Timeout Configuration:**

- Triage: 30s
- Vision: 200s (SAM 2 + Railway cold start)
- Knowledge: 45s
- Chat: 45s

---

### 3. Agents

#### Triage Agent (`kai/agents/triage_agent.py`)

- **Purpose:** Route requests to appropriate workflow
- **Model:** GPT-4o-mini (cost-efficient)
- **Outputs:** Workflow type, confidence score, extracted food names
- **Optimization:** Image uploads skip triage entirely

#### Vision Agent (`kai/agents/vision_agent.py`)

- **Purpose:** Detect foods and estimate portions from images
- **Components:**
  - GPT-4o Vision (food detection + identification)
  - SAM 2 (segmentation for 3+ foods)
  - MiDaS MCP (depth-based portion estimation)
- **Optimization:** Uses SAM 2 only for complex plates (3+ foods)

**Vision Pipeline:**

```
Image → GPT-4o Vision → Detected Foods
  → SAM 2 Segmentation (if 3+ foods)
  → Masks to Bboxes
  → MiDaS Batch API → Portion Estimates
  → Scale if total exceeds 650g
```

#### Knowledge Agent (`kai/agents/knowledge_agent.py`)

- **Purpose:** Retrieve nutrition data for detected foods
- **Components:**
  - Supabase pgvector (vector database)
  - OpenAI text-embedding-3-large (3072 dimensions)
  - 75 Nigerian foods with 16 nutrients each
- **Features:** Semantic search, portion scaling, 16-nutrient retrieval

#### Chat Agent (`kai/agents/chat_agent.py`)

- **Purpose:** Handle all user conversations and provide personalized coaching
- **Model:** GPT-4o with function calling
- **Features:**
  - Intelligent tool routing (pgvector for food info, database for logged meals)
  - RDV-based meal analysis with nutrient gap detection
  - Goal-driven meal suggestions via pgvector
  - Learning phase detection (first 21 meals)
  - Week-over-week trend analysis
  - 16-nutrient tracking

**Tools Available:**

1. `search_foods` — pgvector search for Nigerian food nutrition info
2. `analyze_last_meal` — Analyze most recent meal with RDV-based coaching
3. `get_user_progress` — Fetch daily/weekly nutrition stats and trends
4. `get_meal_history` — Retrieve recent meals
5. `suggest_meal` — Goal-driven meal suggestions from knowledge base
6. `web_search` — Tavily fallback for foods not in database

---

### 4. SAM 2 Segmentation (`kai/agents/sam_segmentation.py`)

Segments food items for accurate portion estimation.

- **Model:** SAM 2 Hiera Small (46M params)
- **Mode:** Automatic mask generation
- **Optimization:** `points_per_side=12` (144 points vs 1024 default)
- **Usage:** Only for complex plates (3+ foods)
- **Device:** CPU (no GPU on HF Spaces free tier)
- **Config:** Relative Hydra path (`configs/sam2/sam2_hiera_s.yaml`)
- **Checkpoint:** Downloaded at Docker build time via curl (176MB)

**Performance:**

- 1-2 foods: Skips SAM 2 (simple division) → instant
- 3+ foods: Uses SAM 2 → ~60s on CPU

---

### 5. MiDaS MCP Server (External Service)

**Location:** Railway

**Purpose:** Estimate food volumes and portions using depth estimation.

**Model:** Depth Anything V2 Small (24.8M params)

**Endpoints:**

- `POST /api/v1/depth/portions/batch` — Batch portion estimation
- `GET /health` — Health check (used by keepalive)

**Client:** `kai/mcp_servers/depth_estimation_client.py`

**Features:**

- Batch processing (multiple foods per API call)
- Image hash caching (SHA-256, LRU cache)
- 120s timeout for cold starts
- Reference object detection (plate, spoon, hand)

---

### 6. Railway Keepalive Service (`kai/services/railway_keepalive.py`)

- Pings Railway `/health` endpoint every 5 minutes
- Prevents 60-90s cold starts on Railway free tier
- Auto-starts on FastAPI startup, auto-stops on shutdown

---

### 7. Supabase pgvector RAG (`kai/rag/chromadb_setup.py`)

**Purpose:** Store and retrieve Nigerian food nutrition data via vector similarity search.

**Database:** Supabase PostgreSQL with pgvector extension

**Components:**

- **Table:** `nigerian_foods` (pgvector embeddings, 3072 dimensions)
- **Embeddings:** OpenAI text-embedding-3-large
- **Data:** 75 Nigerian dishes from `nigerian_foods_v2_improved.jsonl`
- **Search:** RPC function `match_nigerian_foods` (cosine similarity)
- **Index:** Sequential scan (no index needed for <100 foods)

**Key Features:**

- Semantic search (handles spelling variations and aliases)
- 16 nutrients per food (per 100g)
- Portion scaling based on detected grams
- Density-based weight estimation

**Initialization:** `reinitialize_chromadb.py`

---

### 8. Database (`kai/database/`)

**Type:** Supabase PostgreSQL (cloud)
**Client:** supabase-py (HTTPS, not raw SQL)

**Tables (9):**

| Table | Purpose |
| --- | --- |
| `users` | User profiles (UUID, email, name, gender, age) |
| `user_health` | Health data (weight, height, activity, goals, BMR/TDEE, calorie targets) |
| `meals` | Logged meals (type, date, time, image_url) |
| `meal_foods` | Per-food nutrition (portion_grams + 16 nutrients) |
| `daily_nutrients` | Aggregated daily totals (16 nutrients, auto-updated) |
| `user_nutrition_stats` | Pre-computed stats (streaks, weekly averages, trends) |
| `user_food_frequency` | Food frequency tracking (7-day + total counts) |
| `user_recommendation_responses` | Recommendation follow-through tracking |
| `nigerian_foods` | Vector table with pgvector embeddings (75 foods) |

**Database Module Structure:**

- `db_setup.py` — Supabase client initialization
- `user_operations.py` — User CRUD, health profile
- `meal_operations.py` — Meal logging, food saving, daily totals
- `stats_operations.py` — Stats, food frequency, recommendations

---

### 9. Nutrition Services (`kai/services/`)

#### Goal-Driven Nutrition (`nutrition_priorities.py`)

- **8 Health Goals:** lose_weight, gain_muscle, maintain_weight, general_wellness, pregnancy, heart_health, energy_boost, bone_health
- **16 Nutrients tracked:** calories, protein, carbs, fat, fiber, iron, calcium, zinc, potassium, sodium, magnesium, vitamin_a, vitamin_c, vitamin_d, vitamin_b12, folate
- **6-8 priority nutrients per goal** with goal-specific RDV targets
- **Gender & age-adjusted** RDV calculations

#### RDV Calculator (`kai/utils/nutrition_rdv.py`)

- BMR calculation (Mifflin-St Jeor equation)
- TDEE = BMR × activity multiplier
- Goal-adjusted calorie targets (deficit/surplus)
- Weight projection for weight loss/gain goals

---

### 10. Authentication (`kai/auth/jwt_auth.py`)

- JWT token generation and validation
- `get_current_user_id` dependency for protected endpoints
- Token includes user_id in `sub` claim

---

### 11. Background Jobs (`kai/jobs/update_user_stats.py`)

Runs after every meal log:

- Calculates total meals logged
- Computes logging streaks (current + longest)
- Calculates week-over-week nutrient averages
- Determines nutrient trends (improving/declining/stable)
- Detects learning phase completion (7 days + 21 meals)

---

## 🗂️ Project Structure

```
KAI/
├── kai/
│   ├── agents/
│   │   ├── triage_agent.py          # Request routing (GPT-4o-mini)
│   │   ├── vision_agent.py          # Food detection + portions (GPT-4o)
│   │   ├── knowledge_agent.py       # Nutrition retrieval (pgvector RAG)
│   │   ├── chat_agent.py            # Conversations + coaching (GPT-4o)
│   │   └── sam_segmentation.py      # SAM 2 wrapper
│   ├── api/
│   │   └── server.py                # FastAPI endpoints
│   ├── auth/
│   │   └── jwt_auth.py              # JWT authentication
│   ├── database/
│   │   ├── db_setup.py              # Supabase client init
│   │   ├── user_operations.py       # User CRUD
│   │   ├── meal_operations.py       # Meal logging
│   │   ├── stats_operations.py      # Stats & recommendations
│   │   └── migrations/              # Schema migration scripts
│   ├── jobs/
│   │   └── update_user_stats.py     # Background stats calculation
│   ├── models/
│   │   └── agent_models.py          # Pydantic models (16 nutrients)
│   ├── mcp_servers/
│   │   ├── depth_estimation_client.py  # MiDaS MCP client
│   │   └── tavily_server.py         # Tavily web search
│   ├── rag/
│   │   └── chromadb_setup.py        # pgvector RAG setup
│   ├── services/
│   │   ├── nutrition_priorities.py  # Goal-driven nutrition
│   │   └── railway_keepalive.py     # MCP keepalive
│   ├── utils/
│   │   └── nutrition_rdv.py         # BMR/TDEE/RDV calculator
│   └── orchestrator.py              # Multi-agent coordinator
├── knowledge-base/
│   └── data/processed/
│       └── nigerian_foods_v2_improved.jsonl  # 75 foods
├── models/
│   └── sam2/
│       └── sam2_hiera_small.pt      # SAM 2 checkpoint (gitignored, downloaded in Docker)
├── Dockerfile                       # HF Spaces Docker build
├── .dockerignore
├── requirements.txt
├── reinitialize_chromadb.py         # Load foods into pgvector
├── supabase_migration.sql           # Database schema
├── .env                             # Environment config (gitignored)
├── CLAUDE.md                        # Development guidelines
└── ARCHITECTURE.md                  # This file
```

---

## 🔧 Key Technical Decisions

### Why Supabase pgvector over ChromaDB?

- Cloud-hosted (no local storage needed for deployment)
- PostgreSQL reliability + pgvector for embeddings
- Single database for both relational data and vector search
- Free tier sufficient for <100 foods (sequential scan, no index needed)

### Why HF Spaces over Railway for the backend?

- Free tier with 2 vCPU + 16GB RAM (enough for SAM 2 on CPU)
- Docker support (full control over environment)
- Automatic builds on git push
- Persistent hosting (no sleep/cold starts)

### Why SAM 2 only for 3+ foods?

- Simple plates (1-2 foods) don't need segmentation
- Division method is accurate enough (±10%)
- Saves ~60s for 60% of meals

### Why 16 nutrients?

- Covers macros (calories, protein, carbs, fat, fiber)
- Key minerals for Nigerian diet (iron, calcium, zinc, potassium, sodium, magnesium)
- Essential vitamins (A, C, D, B12, folate)
- Enables goal-specific tracking (e.g., folate for pregnancy, sodium for heart health)

---

## 🐛 Known Issues & Solutions

| Issue | Cause | Solution |
| --- | --- | --- |
| SAM 2 config path error | Hydra needs relative paths, not absolute | Use `configs/sam2/sam2_hiera_s.yaml` (relative) |
| Datetime naive vs aware | Supabase returns timezone-aware timestamps | Use `datetime.now(timezone.utc)` |
| Railway cold start | Railway sleeps after 10min inactivity | Keepalive ping every 5min |
| pgvector index failure | IVFFlat/HNSW don't support 3072 dims on Supabase | Sequential scan (fast enough for <100 foods) |
| HF binary file rejection | Binary files in git history | Clean history with orphan branch |

---

## 🔮 Future Improvements

1. **GPU Inference** — Deploy SAM 2 on GPU (60s → 3s)
2. **Mask-based Depth** — Pass masks directly to MiDaS (skip bbox conversion)
3. **Fine-tune SAM 2** — Nigerian food dataset for better segmentation
4. **Multi-language** — Support Yoruba, Igbo, Hausa
5. **Offline Mode** — Local SAM 2 inference on device
6. **Cost Tracking** — Nutrient per Naira optimization

---

**Last Updated:** February 2026
**Version:** 3.0.0 (Supabase + HF Spaces)
**Maintainer:** Avidan (KAI Project)
