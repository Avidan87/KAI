# KAI - Architecture Documentation

> **Nigerian Nutrition Intelligence System**
> AI-powered food logging, nutrition tracking, and personalized coaching

## 🏗️ System Overview

KAI is a multi-agent AI system that analyzes Nigerian food images, calculates nutrition, and provides personalized coaching. The system uses GPT-4o Vision, SAM 2 segmentation, depth estimation, and RAG-based nutrition retrieval.

```
┌─────────────────────────────────────────────────────────────┐
│                      USER REQUEST                            │
│              (Image Upload + Optional Message)               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    KAI API (FastAPI)                         │
│                   kai/api/server.py                          │
│                  localhost:8000 / Railway                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                               │
│                 kai/orchestrator.py                          │
│        Coordinates multi-agent workflow execution            │
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
         │                   ├──► MCP Server     │
         │                   └──► GPT-4o Vision  │
         │                                       │
         │                                       └──► ChromaDB
         │                                       └──► OpenAI Embeddings
         │
         └─────────────────────────────────────────┐
                                                   ▼
                                          ┌─────────────┐
                                          │  COACHING   │
                                          │    AGENT    │
                                          └─────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────┐
                                          │  RESPONSE   │
                                          └─────────────┘
```

---

## 📦 Core Components

### 1. **API Layer** (`kai/api/server.py`)

FastAPI server exposing REST endpoints:

- **POST /api/v1/food-logging-upload** - Full pipeline (Vision → Knowledge → Coaching)
- **POST /api/v1/chat** - Chat with coaching agent
- **POST /api/v1/auth/signup** - User registration
- **POST /api/v1/auth/login** - User authentication
- **GET /api/v1/users/profile** - User profile + health data
- **GET /api/v1/meals/history** - Meal history

**Key Features:**
- JWT authentication
- CORS middleware for cross-origin requests
- Lifespan management (startup/shutdown hooks)
- Railway keepalive service (prevents cold starts)

---

### 2. **Orchestrator** (`kai/orchestrator.py`)

Central coordination layer that routes requests through appropriate agents.

**Workflows:**

#### **Food Logging Workflow** (with image):
```
1. Triage Agent → Classifies request type
2. Vision Agent → Detects foods, estimates portions
3. Knowledge Agent → Retrieves nutrition data
4. Coaching Agent → Provides personalized feedback
```

#### **Chat Workflow** (no image):
```
1. Chat Agent receives user message
2. Intelligent tool selection based on query type:
   - "How was my last meal?" → analyze_last_meal (Database + RDV analysis)
   - "What's in jollof rice?" → search_foods (ChromaDB)
   - "How am I doing?" → get_user_progress (Database)
   - "My meal history" → get_meal_history (Database)
3. GPT-4o generates engaging response with emojis and coaching
4. Returns personalized feedback with suggestions
```

**Key Intelligence:**
- Distinguishes between general food queries (ChromaDB) and logged meal analysis (Database)
- Adapts coaching style based on learning phase (first 21 meals)
- Provides RDV-based nutrient gap analysis
- Celebrates streaks and progress with emoji-rich responses

**Timeout Configuration:**
- Triage: 30s
- Vision: 200s (SAM 2 + Railway cold start)
- Knowledge: 45s
- Coaching: 45s

---

### 3. **Agents**

#### **Triage Agent** (`kai/agents/triage.py`)
- **Purpose:** Route requests to appropriate workflow
- **Model:** GPT-4o
- **Outputs:** Workflow type, confidence score, extracted food names

#### **Vision Agent** (`kai/agents/vision_agent.py`)
- **Purpose:** Detect foods and estimate portions from images
- **Components:**
  - GPT-4o Vision (food detection)
  - SAM 2 (segmentation for 3+ foods)
  - MCP Depth Server (portion estimation)
- **Optimization:** Uses SAM 2 only for complex plates (3+ foods)

**Vision Pipeline:**
```
Image → GPT-4o Vision → Detected Foods → SAM 2 Segmentation (if 3+ foods)
  → Masks to Bboxes → MCP Batch API → Portion Estimates → Scaled Portions
```

#### **Knowledge Agent** (`kai/agents/knowledge.py`)
- **Purpose:** Retrieve nutrition data for detected foods
- **Components:**
  - ChromaDB (vector database)
  - OpenAI embeddings (text-embedding-3-large)
  - JSONL data (48 Nigerian foods)
- **Features:** Semantic search, portion scaling, macro/micro nutrient retrieval

#### **Chat Agent** (`kai/agents/chat_agent.py`)
- **Purpose:** Handle all user conversations and provide personalized coaching
- **Model:** GPT-4o with function calling
- **Features:**
  - **Intelligent Tool Routing:** Automatically chooses between ChromaDB (general food info) and Database (logged meals)
  - **Meal Analysis:** RDV-based analysis of logged meals with nutrient gap detection
  - **Learning Phase Detection:** Adapts coaching based on user progress (first 21 meals)
  - **Emoji-Rich Responses:** Engaging, friendly communication style
  - **Multi-nutrient Coaching:** Tracks all 8 nutrients (calories, protein, carbs, fat, iron, calcium, potassium, zinc)
  - **Progress Tracking:** Daily totals, streaks, weekly trends
  - **Nigerian Food Context:** Culturally-aware recommendations

**Tools Available:**
1. `search_foods` - ChromaDB search for general Nigerian food nutrition info
2. `analyze_last_meal` - Analyze most recent logged meal with RDV-based coaching
3. `get_user_progress` - Fetch daily/weekly nutrition stats and trends
4. `get_meal_history` - Retrieve recent meals
5. `web_search` - Tavily fallback for foods not in database

---

### 4. **SAM 2 Segmentation** (`kai/agents/sam_segmentation.py`)

Segments food items for accurate portion estimation.

**Key Details:**
- **Model:** SAM 2 Hiera Small (46M params)
- **Mode:** Automatic mask generation
- **Optimization:** `points_per_side=12` (144 points, ~60s on CPU)
- **Usage:** Only for complex plates (3+ foods)
- **Device:** CPU (no GPU available on Railway)

**Performance:**
- 1-2 foods: Skips SAM 2 (simple division) → 0s
- 3+ foods: Uses SAM 2 → 60s

---

### 5. **MCP Depth Server** (External Service)

**Location:** Railway (`https://midas-mcp.up.railway.app`)

**Purpose:** Estimate food volumes and portions using depth estimation.

**Model:** Depth Anything V2 Small (24.8M params)

**Endpoints:**
- `POST /api/v1/depth/portions/batch` - Batch portion estimation
- `GET /health` - Health check (used by keepalive)

**Client:** `kai/mcp_servers/depth_estimation_client.py`

---

### 6. **Railway Keepalive Service** (`kai/services/railway_keepalive.py`)

**Purpose:** Prevent Railway cold starts (60-90s delays)

**How it works:**
- Pings Railway `/health` endpoint every 5 minutes
- Keeps MCP server warm
- Reduces response time from 60-90s to 5-10s

**Configuration:**
- Interval: 300s (5 minutes)
- Auto-starts on FastAPI startup
- Auto-stops on shutdown

---

### 7. **ChromaDB + RAG** (`kai/rag/chromadb_setup.py`)

**Purpose:** Store and retrieve Nigerian food nutrition data.

**Components:**
- **Collection:** `nigerian_foods`
- **Embeddings:** OpenAI text-embedding-3-large (3072 dimensions)
- **Data:** 48 Nigerian dishes (from `nigerian_foods_v2_improved.jsonl`)
- **Storage:** `chromadb_data/` directory

**Key Features:**
- Semantic search (handles spelling variations)
- Nutrition scaling by portion size
- Density-based weight estimation

**Initialization:** `reinitialize_chromadb.py`

---

### 8. **Database** (`kai/database.py`)

**Type:** SQLite (development) / PostgreSQL (production)

**Tables:**
- **users** - User profiles (email, password, JWT)
- **user_health** - Health data (age, weight, BMI, activity level)
- **meals** - Logged meals (foods, portions, nutrition)

**ORM:** Raw SQL with async SQLite support

---

## 🔄 Complete Food Logging Flow

```
1. User uploads image via /api/v1/food-logging-upload
   ↓
2. Orchestrator receives request
   ↓
3. Triage Agent: "This is a food logging request with image"
   ↓
4. Vision Agent:
   a. GPT-4o Vision detects: ["Jollof Rice", "Fried Plantain", "Chicken"]
   b. 3 foods detected → Use SAM 2 segmentation (~60s)
   c. SAM 2 generates pixel masks for each food
   d. Convert masks to bounding boxes
   e. Call MCP batch API with all bboxes
   f. MCP returns: [Jollof: 250g, Plantain: 80g, Chicken: 120g]
   g. Scale portions if total exceeds 650g (realistic meal size)
   ↓
5. Knowledge Agent:
   a. Semantic search in ChromaDB for each food
   b. Retrieve nutrition per 100g
   c. Scale by actual portions
   d. Aggregate macros + 8 micronutrients
   ↓
6. Coaching Agent:
   a. Analyze nutrition vs user's RDV
   b. Check for deficiencies (< 70% RDV)
   c. Generate culturally-aware feedback
   ↓
7. Save meal to database
   ↓
8. Return response: {
     foods: [...],
     nutrition: {...},
     coaching_message: "..."
   }
```

---

## ⚙️ Configuration

### **Environment Variables** (`.env`)

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_VISION_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Database
DATABASE_URL=sqlite:///./kai.db

# MCP Server (Railway)
MIDAS_MCP_URL=https://midas-mcp.up.railway.app
MIDAS_MCP_ENABLED=true

# JWT
JWT_SECRET_KEY=...

# Nigerian RDV Standards
IRON_RDA_MALE=10
IRON_RDA_FEMALE=20
CALCIUM_RDA=1000
ZINC_RDA=15
# ... etc
```

---

## 🚀 Performance Optimizations

### **1. SAM 2 Optimization**
- **Before:** `points_per_side=32` (1024 points) → 5-10 minutes
- **After:** `points_per_side=12` (144 points) → 60 seconds
- **Speedup:** 10x faster

### **2. Hybrid SAM 2 Usage**
- **Before:** SAM 2 for ALL plates (1+ foods)
- **After:** SAM 2 only for complex plates (3+ foods)
- **Result:** 60% of meals skip SAM 2 (~60s saved)

### **3. Railway Keepalive**
- **Before:** First request after idle → 60-90s cold start
- **After:** Keepalive pings every 5 min → 5-10s warm start
- **Result:** 60-90s saved on cold starts

### **4. Batch Processing**
- MCP server processes all foods in single API call
- Reduces N requests to 1 request
- Saves network overhead

---

## 📊 Performance Summary

| **Scenario** | **# Foods** | **Time (Before)** | **Time (After)** | **Savings** |
|-------------|------------|------------------|------------------|-------------|
| Single dish (1 food) | 1 | 120-150s | 15-20s | **100-130s** |
| Simple plate (2 foods) | 2 | 120-150s | 15-20s | **100-130s** |
| Complex plate (3+ foods) | 3+ | 120-150s | 70-80s | **40-70s** |

**Average speedup:** 60-100 seconds per request

---

## 🔧 Key Technical Decisions

### **Why SAM 2 over Florence-2?**
- Pixel-perfect segmentation (vs crude bboxes)
- Handles overlapping foods
- No bbox overlap issues (214% overlap bug fixed)
- 60% faster than Florence-2 + K-Means

### **Why ChromaDB over SQL?**
- Semantic search (handles spelling variations)
- Embedding-based similarity (no exact matches needed)
- Fast retrieval (<100ms for 48 foods)

### **Why Hybrid SAM 2 Usage?**
- Simple plates (1-2 foods) don't need segmentation
- Division method is accurate enough (±10%)
- Saves 60s for 60% of meals

### **Why Railway Keepalive?**
- Prevents serverless cold starts
- Simple background task (5-line integration)
- Saves 60-90s per cold start

---

## 🗂️ Project Structure

```
KAI/
├── kai/
│   ├── agents/
│   │   ├── triage.py              # Request routing
│   │   ├── vision_agent.py        # Food detection + portions
│   │   ├── knowledge.py           # Nutrition retrieval
│   │   ├── coaching.py            # Personalized advice
│   │   └── sam_segmentation.py    # SAM 2 wrapper
│   ├── api/
│   │   └── server.py              # FastAPI endpoints
│   ├── services/
│   │   └── railway_keepalive.py   # MCP keepalive
│   ├── mcp_servers/
│   │   └── depth_estimation_client.py  # MCP client
│   ├── rag/
│   │   └── chromadb_setup.py      # Vector DB setup
│   ├── database.py                # SQLite/PostgreSQL
│   ├── orchestrator.py            # Multi-agent coordinator
│   └── auth.py                    # JWT authentication
├── MCP SERVER/                    # Separate Railway deployment
│   ├── server.py                  # Depth Anything V2 API
│   ├── depth_anything_v2.py       # Model wrapper
│   └── portion_calculator.py      # Volume → weight
├── knowledge-base/
│   └── data/processed/
│       └── nigerian_foods_v2_improved.jsonl  # 48 foods
├── models/
│   └── sam2/
│       └── sam2_hiera_small.pt    # SAM 2 checkpoint
├── chromadb_data/                 # ChromaDB storage
├── .env                           # Environment config
├── claude.md                      # Development guidelines
└── ARCHITECTURE.md               # This file
```

---

## 🐛 Known Issues & Solutions

### **Issue #1: SAM 2 Timeout**
- **Cause:** `points_per_side=32` → 5-10 minutes
- **Solution:** Reduced to 12 → 60 seconds ✅

### **Issue #2: Railway Cold Start**
- **Cause:** Railway sleeps after 10min inactivity
- **Solution:** Keepalive service pings every 5min ✅

### **Issue #3: SAM 2 Config Path**
- **Cause:** Hydra can't find relative paths
- **Solution:** Use absolute paths to configs ✅

### **Issue #4: Checkpoint Not Found**
- **Cause:** Path missing `models/sam2/` prefix
- **Solution:** Join with proper directory ✅

### **Issue #5: ChromaDB Corruption**
- **Cause:** Bad state after interrupted initialization
- **Solution:** Delete `chromadb_data/` and reinitialize ✅

---

## 🔮 Future Improvements

1. **GPU Inference** - Deploy SAM 2 on GPU (60s → 3s)
2. **Mask-based Depth** - Pass masks directly to MCP (not bboxes)
3. **Meal Recommendations** - ML-based personalized suggestions
4. **Micronutrient Tracking** - Track 8 micronutrients over time
5. **Food Search** - Add manual food search endpoint
6. **Image Preprocessing** - Auto-crop and enhance images
7. **Multi-language** - Support Yoruba, Igbo, Hausa

---

## 📚 Related Files

- **Development Guidelines:** [claude.md](claude.md)
- **README:** [README.md](README.md)
- **API Documentation:** [OpenAPI Schema](http://localhost:8000/docs)
- **Knowledge Base:** [knowledge-base/](knowledge-base/)

---

**Last Updated:** January 2026
**Maintainer:** Avidan (KAI Project)
