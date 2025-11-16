# 🥗 KAI - AI-Powered Nutrition Intelligence for Nigerians

**KAI** is an advanced nutrition assistant tailored for Nigerians. It combines **camera-first meal logging, culturally-aware food recognition, and fully personalized AI nutrition coaching**—powered by a robust multi-agent architecture understanding both local foods and health needs.

---

## 🌟 Key Features

### 📸 Camera-First Meal Logging  
- **Instant food recognition:** Snap a meal photo, get Nigerian dishes detected
- **Smart portion estimation:** Uses MiDaS depth-AI and fallback logic for grams (tracks if depth server was used)
- **Automatic nutrition breakdown:** Calculates calories, protein, fat, iron, and more

### 🇳🇬 Culturally-Aware Nutrition
- **Nigerian food expertise:** Recognizes all major local dishes—eba, jollof, fufu, egusi, suya, plantain, moin moin, etc.
- **Cultural context:** Understands food pairings, prep methods, local dietary habits
- **Budget-adapted options:** Advice adapts to affordable, mid, or premium Nigerian food choices

### 👩‍⚕️ Personalized Health Coaching
- **Dynamic, user-specific feedback:** Coaching message always includes the foods recognized (“Great job logging your bread and beans!”)
- **Multi-nutrient tracking:** Monitors carbs, fats, protein, iron, calcium, vitamin A, zinc, and energy
- **Streaks, patterns, and learning phase:** Encourages consistent healthy eating, tracks personalized rolling averages
- **Local wellness focus:** Emphasizes iron, calcium, and other nutrients for Nigerian women and moms

---

## 🏗️ System Architecture & Workflows

### 🔁 Agent-Based Multi-Stage Pipeline

**KAI leverages four primary active agents:**

1. **Triage Agent (Router):**  
   Classifies every user input (image, question, or text) into workflows: food logging, nutrition query, health coaching, or chat.

2. **Vision Agent:**  
   Detects Nigerian foods and portion sizes from images. Uses MiDaS depth-AI if available; falls back otherwise (with a backend flag `midas_used` to record server usage).

3. **Knowledge Agent:**  
   Retrieves precise nutrition info from a custom, vectorized Nigerian food knowledge base (via ChromaDB).

4. **Coaching Agent:**  
   Synthesizes user history, detected foods, and nutrition gaps into **fully customized, empathetic advice**—always mentioning the actual foods detected/logged.

#### ⚡ Workflow Example: Food Logging

`User uploads photo → Triage → Vision Agent → Knowledge Agent → Coaching Agent → Response`
- **Response includes:**  
  - Recognized food names (“bread and beans”)
  - Portion estimation, full nutrient breakdown
  - “midas_used”: tracks if MiDaS server or fallback logic handled portions
  - Personalized advice with food mention (“Great job logging your jollof rice and plantain!”)
  - Rolling averages, streaks, and actionable next steps

#### Other routes:
- **Nutrition Query:** “How much iron in fufu?” → Triage → Knowledge Agent → Coaching Agent → Answer
- **Health Coaching / Chat:** “What should I eat for anemia?” → Triage → Coaching Agent

---

## 🛠️ Technology Stack

- **Backend:** Python, FastAPI, OpenAI (GPT-4o), ChromaDB, SQLite/PostgreSQL, JWT
- **AI/ML:** MiDaS portion estimation, RAG pipeline, culture-specific heuristic logic, OpenAI Agent SDK
- **Frontend:** React + TypeScript mobile app (Vite, Tailwind, shadcn/ui)
- **DevOps:** Docker, Railway, .env-based config

---

## 🍲 Recognized Nigerian Foods

KAI covers all key meal groups—staples (eba, amala, fufu, jollof), soups (egusi, ogbono), proteins (suya, fish, chicken), and more.  
**Food detected is always shown in feedback, so users know exactly what was understood.**

---

## 💬 Agent Communication Flow

- **TriageResult:** Classifies and routes
- **VisionResult:** Detected foods from image (+ midas_used flag for depth server usage)
- **KnowledgeResult:** Nutrition totals, food-specific data
- **CoachingResult:** Personalized, food-inclusive feedback with next steps and tips

---

## 📦 Installation

1. **Clone and set up:**
   ```bash
   git clone <repository-url>
   cd KAI
   pip install -r requirements.txt
   ```

2. **Set up environment variables** (`.env`):
   ```
   OPENAI_API_KEY=your_openai_api_key
   TAVILY_API_KEY=your_tavily_api_key
   JWT_SECRET_KEY=your_jwt_secret
   DATABASE_URL=sqlite:///kai_database.db  # Or your Postgres URL
   ```

3. **Initialize database and knowledge base**  
   ```bash
   python -m kai.database.db_setup
   # Knowledge base (ChromaDB) initializes automatically or via scripts in knowledge-base/ingestion/
   ```

4. **Run the API server:**  
   ```bash
   uvicorn kai.api.server:app --reload
   # API at http://localhost:8000
   ```

5. **Mobile App:**  
   ```
   cd "Mobile App Development (2)"
   npm install
   npm run dev
   ```

---

## 🚀 Deployment & Development

- **Docker** and **Railway** supported (`Dockerfile`, `railway.toml`)
- `*.egg-info` and other build artifacts are ignored (not needed for runtime!)

---

## 🙏 Credits

- Nigerian nutrition researchers and open-source food databases
- OpenAI (GPT-4o vision, RAG)
- ChromaDB, Tavily, LangChain

---

**Built with ❤️ for Nigerians** 🇳🇬

