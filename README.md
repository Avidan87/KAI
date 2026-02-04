---
title: KAI
emoji: 🥗
colorFrom: green
colorTo: yellow
sdk: docker
pinned: false
---

# 🥗 KAI - AI-Powered Nutrition Intelligence for Nigerians

**KAI** is an advanced nutrition assistant tailored for Nigerians. It combines **camera-first meal logging, culturally-aware food recognition, and fully personalized AI nutrition coaching**—powered by a robust multi-agent architecture that understands both local foods and health needs.

---

## 🌟 Key Features

### 📸 Camera-First Meal Logging with SAM 2
- **Instant food recognition:** Snap a meal photo, get Nigerian dishes detected instantly
- **Pixel-perfect segmentation:** SAM 2 (Meta) segments overlapping foods accurately
- **Smart portion estimation:** MiDaS depth estimation via Railway MCP server
- **Automatic nutrition breakdown:** Tracks **16 nutrients** — calories, protein, fat, carbs, fiber, iron, calcium, zinc, potassium, sodium, magnesium, vitamin A, vitamin C, vitamin D, vitamin B12, folate
- **Portion safety caps:** Max 300g/food, 650g/meal (research-backed Nigerian portions)

### 🇳🇬 Culturally-Aware Nigerian Nutrition
- **75 Nigerian foods** in the knowledge base with full nutrition data
- **Semantic search:** Handles spelling variations, local names, and aliases via pgvector embeddings
- **Regional variations:** Understands local names, cooking methods, and food pairings
- **Cultural context:** Traditional meal combinations and preparation methods

### 👥 Personalized Health Coaching — 8 Health Goals
- **Goal-driven nutrition plans** with 6-8 priority nutrients per goal:
  - 🏋️ Lose Weight | 💪 Gain Muscle | ⚖️ Maintain Weight | 🌿 General Wellness
  - 🤰 Pregnancy | ❤️ Heart Health | ⚡ Energy Boost | 🦴 Bone Health
- **Gender-specific & age-adjusted** RDV calculations (BMR/TDEE-based)
- **Activity-level awareness:** Sedentary to very active lifestyle adjustments
- **Learning phase:** First 7 days or 21 meals for baseline establishment
- **Streaks & trends:** Week-over-week progress tracking with trend analysis
- **Dynamic feedback:** Personalized coaching with actual food mentions

---

## 🏗️ Deployment Architecture

```
📱 Flutter App (Frontend)
     │
     ▼
🤗 HF Spaces (KAI FastAPI Backend + SAM 2)
     │         │         │
     ▼         ▼         ▼
  🗄️ Supabase   🚂 Railway   🤖 OpenAI
  (PostgreSQL    (MiDaS MCP   (GPT-4o,
   + pgvector)    Depth Est.)   Embeddings)
```

| Service | Platform | Purpose |
|---|---|---|
| 🤗 KAI Backend | HF Spaces (Docker, CPU) | FastAPI + SAM 2 inference |
| 🗄️ Database | Supabase (PostgreSQL + pgvector) | Users, meals, food embeddings |
| 🚂 MiDaS MCP | Railway | Depth estimation for portion sizing |
| 🤖 AI Models | OpenAI API | GPT-4o, text-embedding-3-large |

---

## 🤖 Multi-Agent Pipeline

### Agents

**1. Triage Agent** — Routes user input to the correct workflow
- Model: GPT-4o-mini
- Routes to: `food_logging`, `nutrition_query`, `health_coaching`, or `general_chat`
- Image uploads skip triage and go directly to vision

**2. Vision Agent** — Detects foods and estimates portions from images
- Model: GPT-4o with vision
- SAM 2 segmentation for 3+ foods on a plate
- MiDaS MCP for depth-based portion estimation

**3. Knowledge Agent** — Retrieves nutrition data via RAG
- Model: GPT-4o-mini with Supabase pgvector search
- Embeddings: OpenAI text-embedding-3-large (3072 dimensions)
- 75 Nigerian foods with 16 nutrients each

**4. Chat Agent** — Handles all conversations and personalized coaching
- Model: GPT-4o with function calling
- Tools: `search_foods`, `analyze_last_meal`, `get_user_progress`, `get_meal_history`, `suggest_meal`, `web_search`
- RDV-based nutrient gap analysis
- Learning phase detection (first 21 meals)

### Food Logging Workflow

```
User uploads photo
  ↓
Vision Agent (GPT-4o detects Nigerian foods)
  ↓
SAM 2 (pixel-perfect masks for 3+ foods)
  ↓
MiDaS MCP (depth-based portion estimation)
  ↓
Knowledge Agent (nutrition lookup via pgvector)
  ↓
Save to Supabase (meal + foods + daily totals)
  ↓
Response: Detected foods + priority nutrients
```

---

## 🛠️ Technology Stack

| Category | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **AI Models** | GPT-4o, GPT-4o-mini, text-embedding-3-large |
| **Food Segmentation** | SAM 2 Hiera Small (46M params, CPU) |
| **Depth Estimation** | MiDaS (via Railway MCP server) |
| **Database** | Supabase PostgreSQL + pgvector |
| **Vector Search** | pgvector (3072-dim OpenAI embeddings) |
| **Authentication** | JWT (via supabase-py + custom JWT) |
| **Web Search** | Tavily API (Nigerian health context) |
| **Deployment** | Docker on HF Spaces |
| **Image Processing** | OpenCV, Pillow, NumPy, PyTorch |

---

## 🚀 API Endpoints

**Base URL:** `https://av-idan-k-a-i.hf.space/api/v1`

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Create account (email, name, gender, age) |
| POST | `/auth/login` | Login with email, get JWT |

### Food Logging
| Method | Endpoint | Description |
|---|---|---|
| POST | `/food-logging-upload` | Upload meal photo → detect foods → nutrition → save |

### Chat
| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | Chat with KAI (nutrition questions, feedback, progress) |

### Meals
| Method | Endpoint | Description |
|---|---|---|
| GET | `/meals/history` | Get meal history (paginated) |

### User Profile
| Method | Endpoint | Description |
|---|---|---|
| GET | `/users/profile` | Get profile + health info + RDV |
| PUT | `/users/health-profile` | Update health profile (weight, height, activity, goals) |
| GET | `/users/nutrition-plan` | Get goal-driven nutrition plan with priority nutrients |
| GET | `/users/stats` | Get daily nutrition stats |

### Health Check
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health status |

**Authentication:** All endpoints (except signup/login/health) require `Authorization: Bearer <jwt_token>` header.

---

## 📊 Database Schema (Supabase)

### Tables
1. **users** — User accounts (UUID, email, name, gender, age)
2. **user_health** — Health profile (weight, height, activity, goals, BMR/TDEE calorie calculations)
3. **meals** — Meal records (type, date, time, image, description)
4. **meal_foods** — Per-food nutrition (portion_grams + 16 nutrients)
5. **daily_nutrients** — Daily aggregated totals (16 nutrients)
6. **user_nutrition_stats** — Pre-computed stats (streaks, weekly averages, trends)
7. **user_food_frequency** — Food frequency tracking (7-day + total counts)
8. **user_recommendation_responses** — Meal recommendation tracking
9. **nigerian_foods** — Vector table with pgvector embeddings (75 foods, 3072-dim)

---

## 🍲 Nigerian Food Coverage (75 Foods)

**Staples:** Jollof Rice, Fried Rice, Rice and Stew, Eba, Fufu, Pounded Yam, Amala, Tuwo Shinkafa, Agege Bread

**Soups:** Egusi Soup, Ogbono Soup, Okra Soup, Efo Riro, Pepper Soup, Edikang Ikong, Afang Soup, Banga Soup, Miyan Kuka

**Proteins:** Suya, Goat Meat Stew, Fried/Grilled Chicken, Fried/Grilled Fish, Peppered Snail, Nkwobi

**Sides:** Fried Plantain (Dodo), Moi Moi, Akara, Beans and Stew, Ewa Agoyin, Ojojo, Dundun

**Snacks & Drinks:** Puff Puff, Chin Chin, Boli, Zobo, Kunu, Tiger Nut Milk

---

## 📦 Installation & Setup

### Local Development

```bash
# Clone
git clone https://github.com/Avidan87/KAI.git
cd KAI

# Install dependencies
pip install -r requirements.txt

# Install SAM 2
pip install git+https://github.com/facebookresearch/segment-anything-2.git

# Download SAM 2 model
mkdir -p models/sam2
cd models/sam2
curl -L -O https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_small.pt
cd ../..

# Set environment variables in .env
# OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
# SUPABASE_ANON_KEY, JWT_SECRET_KEY, MIDAS_MCP_URL, TAVILY_API_KEY

# Run server
uvicorn kai.api.server:app --reload --port 8000
```

### Docker (HF Spaces)

The Dockerfile handles everything automatically:
- Installs system deps + Python packages + SAM 2
- Downloads SAM 2 model checkpoint (176MB) at build time
- Runs FastAPI on port 7860

---

## 🔮 Future Enhancements

- GPU inference for SAM 2 (60s → 3s)
- Pass pixel masks directly to MiDaS (skip bbox conversion)
- Fine-tune SAM 2 on Nigerian food dataset
- Cost optimization (nutrient per Naira tracking)
- Offline mode with local inference
- Multi-language support (Yoruba, Igbo, Hausa)

---

## 🙏 Credits

- **OpenAI** — GPT-4o vision, embeddings, and API
- **Meta AI** — SAM 2 (Segment Anything Model 2)
- **MiDaS** — Depth estimation for portion sizing
- **Supabase** — PostgreSQL + pgvector database
- **Hugging Face** — Spaces hosting
- **Railway** — MCP server hosting

---

**Built with ❤️ for Nigerians** 🇳🇬

*Empowering healthy eating through AI-powered nutrition intelligence tailored to Nigerian foods, culture, and health needs.*

---

**Version:** 3.0.0 (Supabase + HF Spaces)
**Last Updated:** February 2026
