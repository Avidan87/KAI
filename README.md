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
- **Pixel-perfect segmentation:** SAM 2 (Meta) segments overlapping foods accurately (60% faster than previous system)
- **Smart portion estimation:** Depth Anything V2 AI estimates grams from depth maps
- **Automatic nutrition breakdown:** Tracks 8 nutrients - calories, protein, fat, carbs, iron, calcium, vitamin A, zinc
- **Portion safety caps:** Max 300g/food, 650g/meal (research-backed Nigerian portions)

### 🇳🇬 Culturally-Aware Nigerian Nutrition
- **50+ Nigerian foods recognized:** Jollof Rice, Pounded Yam, Fufu, Egusi Soup, Suya, Moi Moi, Akara, Eba, Efo Riro, Ogbono Soup, Okra Soup, Pepper Soup, Amala, Fried Plantain, and more
- **Regional variations:** Understands local names, cooking methods, and food pairings
- **Budget-adapted options:** Affordable, mid-tier, and premium food choices
- **Cultural context:** Traditional meal combinations and preparation methods

### 👥 Personalized Health Coaching for All Nigerians
- **Gender-specific guidance:** RDV calculations for men and women
- **Age-adjusted recommendations:** Optimized for 19-50 and 51+ age groups
- **Activity-level awareness:** Sedentary to very active lifestyle adjustments
- **Multi-nutrient tracking:** Monitors all 8 key nutrients with gap analysis
- **Learning phase:** First 7 days or 21 meals for baseline establishment
- **Dynamic feedback:** "Great job logging your Jollof Rice and plantain!" with actual food mentions
- **Health goals:** Weight loss, muscle gain, maintenance, general wellness
- **Streaks & trends:** Week-over-week progress tracking

---

## 🏗️ System Architecture & Workflows

### 🤖 Multi-Agent Pipeline (4 Core Agents)

**1. Triage Agent (Router):**
- Model: GPT-4o-mini (cost-efficient)
- Routes user input to: `food_logging`, `nutrition_query`, `health_coaching`, or `general_chat`
- Optimized: Image uploads skip triage and go directly to vision agent

**2. Vision Agent (Food Detection):**
- Model: GPT-4o with vision capabilities
- **NEW (Jan 2026):** Upgraded with SAM 2 segmentation
  - Replaces Florence-2 (450 lines removed)
  - Pixel-perfect food masks (no bbox overlap issues)
  - 60% faster (1-2s vs 3-4s)
  - 40% more accurate (15-20% MAPE vs 25-30%)
- Handles overlapping Nigerian foods on same plate
- Outputs: Food names, portions, confidence scores, ingredients, cooking methods

**3. Knowledge Agent (RAG System):**
- Model: GPT-4o-mini with ChromaDB vector search
- Embeddings: OpenAI text-embedding-3-large (3072 dimensions)
- 50+ enriched Nigerian foods with semantic search
- Retrieves precise nutrition data for all 8 nutrients
- Tools: `search_nigerian_foods`, `get_foods_by_nutrient`

**4. Coaching Agent (Personalization):**
- Model: GPT-4o for dynamic coaching
- Features:
  - Learning phase detection (first 7 days)
  - Week-over-week trend analysis
  - Multi-nutrient gap identification
  - Dynamic meal combo suggestions via RAG
  - Culturally-aware motivational messaging
- Tools: `generate_nutrition_insights`, `suggest_meals`

---

### ⚡ Complete Food Logging Workflow

```
User uploads photo
  ↓
Vision Agent (GPT-4o detects Nigerian foods)
  ↓
SAM 2 (generates pixel-perfect masks for each food)
  ↓
Depth Anything V2 MCP (estimates portions from depth maps)
  ↓
Knowledge Agent (retrieves nutrition via ChromaDB RAG)
  ↓
Coaching Agent (generates personalized feedback)
  ↓
Response: Detected foods + nutrition + coaching + tracking flags
```

**Response includes:**
- Food names with Nigerian aliases
- Portion estimates in grams
- Complete 8-nutrient breakdown
- `depth_estimation_used` flag (tracks MCP server usage)
- Personalized coaching with actual food mentions
- Rolling averages, streaks, actionable next steps

**Other Workflows:**
- **Nutrition Query:** "How much iron in fufu?" → Knowledge Agent → Coaching Agent
- **Health Coaching:** "What should I eat for anemia?" → Coaching Agent (with Tavily web search)
- **General Chat:** Greetings and casual conversation

---

## 🛠️ Technology Stack

### Backend & AI
- **Framework:** Python 3.10+, FastAPI (async), JWT authentication
- **AI Models:**
  - GPT-4o (vision, coaching)
  - GPT-4o-mini (routing, knowledge)
  - OpenAI text-embedding-3-large (3072-dim embeddings)
- **Computer Vision:**
  - **SAM 2** (Meta's Segment Anything Model 2) - small variant (46M params)
  - **Depth Anything V2** (Railway MCP server) - state-of-the-art monocular depth estimation
  - OpenCV, Pillow, NumPy, Torch
- **RAG Pipeline:** ChromaDB, LangChain, sentence-transformers
- **Databases:** SQLite (async via aiosqlite) or PostgreSQL
- **MCP Servers:**
  - Depth estimation (Depth Anything V2)
  - Tavily web search (Nigerian health context)

### Deployment
- **Containerization:** Docker, Railway
- **Configuration:** Environment variables (.env)
- **API:** RESTful with CORS enabled

---

## 🍲 Comprehensive Nigerian Food Coverage

**Staples:** Jollof Rice, Fried Rice, Rice and Stew, Eba, Fufu, Pounded Yam, Amala

**Soups:** Egusi Soup, Ogbono Soup, Okra Soup, Efo Riro, Pepper Soup, Edikang Ikong

**Proteins:** Suya, Fried/Grilled Chicken, Fried/Grilled Fish

**Sides:** Fried Plantain (Dodo), Moi Moi, Akara, Beans and Stew, Ewa Agoyin

**All detected foods shown in personalized feedback!**

---

## 🔬 Advanced Features

### SAM 2 Food Segmentation (January 2026 Upgrade)
- **Pixel-level accuracy:** No more bbox overlap (previous 214% overlap issue eliminated)
- **Automatic mask generation:** No prompts needed
- **Handles overlapping foods:** Jollof rice + stew on same plate perfectly separated
- **Vision Transformer architecture:** 1024+ dimensional features per pixel
- **Model variants available:** tiny (0.5s), small (1-2s, default), base (3-4s), large (8-10s)

### Depth Estimation MCP Server
- **Model:** Depth Anything V2 Small (24.8M params)
- **Features:**
  - Batch processing (multiple foods per API call)
  - Image hash caching (SHA-256, LRU cache with 100 entries)
  - Railway-hosted with 120s timeout for cold starts
  - Reference object detection (plate, spoon, hand)
- **Tracking:** `depth_estimation_used` flag in all responses

### Personalized RDV Calculator
- **Gender-specific:** Different recommendations for men and women
- **Age-adjusted:** 19-50 and 51+ categories
- **Activity multipliers:** Sedentary (1.2x) to Very Active (1.9x)
- **All 8 nutrients:** Calories, protein, fat, carbs, iron, calcium, vitamin A, zinc
- *Future:* Pregnancy, lactation, anemia adjustments

### ChromaDB RAG System
- **Vector search:** Semantic similarity for Nigerian food queries
- **Rich metadata:** All 8 nutrients, portion limits, price tier, dietary flags
- **Comprehensive text:** Name + aliases + description + benefits + cultural significance
- **Persistent storage:** `chromadb_data/` directory

---

## 📦 Installation & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd KAI
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install SAM 2 (Food Segmentation)
```bash
# Windows
cd scripts
install_sam2.bat

# Linux/Mac
cd scripts
chmod +x install_sam2.sh
./install_sam2.sh
```

This will:
- Install SAM 2 package from GitHub
- Download sam2_hiera_small.pt checkpoint (~176MB)
- Verify installation

### 4. Environment Variables
Create `.env` file:
```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Web Search (optional)
TAVILY_API_KEY=your_tavily_api_key

# Authentication
JWT_SECRET_KEY=your_jwt_secret_key

# Database
DATABASE_URL=sqlite:///kai_database.db  # Or PostgreSQL URL

# MCP Servers (optional - fallback enabled)
DEPTH_ESTIMATION_URL=your_railway_depth_server_url
```

### 5. Initialize Database
```bash
python -m kai.database.db_setup
# ChromaDB knowledge base initializes automatically
```

### 6. Run API Server
```bash
uvicorn kai.api.server:app --reload
# API available at http://localhost:8000
```

### 7. API Documentation
Visit http://localhost:8000/docs for interactive API documentation (Swagger UI)

---

## 🚀 API Endpoints

**Base URL:** `/api/v1`

### Authentication
- `POST /auth/signup` - Create account (email, name, gender, age)
- `POST /auth/login` - Login with email

### Food Logging
- `POST /food-logging-upload` - Upload meal photo (multipart/form-data)
  - Returns: detected_foods, nutrition (8 nutrients), coaching, depth_estimation_used

### Chat & Queries
- `POST /chat` - Ask nutrition questions or get coaching
  - Returns: coaching_message, nutrition_data, follow_up_suggestions, tavily_used

### Meal Management
- `POST /meals/log` - Save meal to database
- `GET /meals/history` - Retrieve meal history (paginated)

### User Profile
- `GET /users/profile` - Get profile + health info + RDV
- `PUT /users/profile` - Update profile/health settings
- `GET /users/stats` - Daily nutrition statistics

### Health Check
- `GET /health` - Service health status

**Authentication:** All endpoints require `Authorization: Bearer <jwt_token>` header

---

## 📊 Database Schema

### Tables
1. **users** - User accounts (UUID, email, name, gender, age)
2. **user_health** - Health profile (weight, height, activity level, goals, BMR, TDEE)
3. **meals** - Meal records (type, date, time, image_url, description)
4. **meal_foods** - Per-food nutrition breakdown (portion_grams, 8 nutrients)
5. **daily_nutrients** - Daily aggregated nutrition totals

### ChromaDB Collection
- **nigerian_foods** - 50+ foods with embeddings and metadata

---

## 📚 Documentation

- **Migration Guide:** `/docs/FOODSAM_MIGRATION.md` - SAM 2 upgrade details
- **Coaching Design:** `/docs/COACHING_API_GUIDE.md` - Personalization features
- **Dynamic Coaching:** `/docs/DYNAMIC_COACHING_DESIGN.md` - Architecture overview

---

## 🎯 Recent Updates (January 2026)

### SAM 2 Migration ✅
- Replaced Florence-2 bounding boxes with SAM 2 pixel-perfect segmentation
- **Performance:** 60% faster, 40% more accurate
- **Code:** 450 lines simpler (removed K-Means workarounds)
- **Result:** No more bbox overlap issues on Nigerian plates

### Depth Anything V2 Integration ✅
- State-of-the-art monocular depth estimation
- 10x faster than ZoeDepth
- Batch processing for multiple foods
- Image hash caching for efficiency

### Enhanced Coaching Agent ✅
- Multi-nutrient tracking (all 8 nutrients)
- Learning phase coaching (first 7 days)
- Week-over-week trend analysis
- Gender-neutral, inclusive messaging

---

## 🔮 Future Enhancements

- **Phase 2:** Update MCP server to accept pixel masks directly (skip bbox conversion)
- **Phase 3:** Fine-tune SAM 2 on Nigerian food dataset (FoodSAM approach)
- Pregnancy/lactation/anemia-specific nutrition guidance
- Cost optimization (nutrient per Naira tracking)
- Historical health trend visualization
- Offline mode with local SAM 2 inference

---

## 🙏 Credits & Acknowledgments

- **Nigerian Nutrition Researchers** - Cultural food knowledge and portion data
- **OpenAI** - GPT-4o vision, embeddings, and API
- **Meta AI** - SAM 2 (Segment Anything Model 2)
- **Depth Anything Team** - State-of-the-art depth estimation
- **ChromaDB, LangChain, Tavily** - RAG infrastructure
- **Nigerian Women & Health Advocates** - Feedback and use case validation

---

## 📄 License

[Your License Here]

---

**Built with ❤️ for Nigerians** 🇳🇬

*Empowering healthy eating through AI-powered nutrition intelligence tailored to Nigerian foods, culture, and health needs.*

---

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests.

## 📧 Contact

For questions, feedback, or support, please open an issue on GitHub.

---

**Version:** 2.0.0 (SAM 2 Integration)
**Last Updated:** January 2026
