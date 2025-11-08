# 🥗 KAI - AI-Powered Nutrition Intelligence for Nigerians

**KAI** is an intelligent nutrition assistant designed specifically for Nigerians, combining camera-first meal logging with culturally-adapted nutrition guidance. Built with a multi-agent AI architecture, KAI helps users track nutrition, understand dietary patterns, and receive personalized coaching tailored to Nigerian cuisine and health needs.

## 🌟 Key Features

### 📸 Camera-First Meal Logging
- **Instant Food Recognition**: Simply take a photo of your meal and KAI identifies Nigerian dishes
- **Portion Estimation**: Uses MiDaS depth estimation to accurately estimate portion sizes
- **Automatic Nutrition Tracking**: Logs calories, macronutrients, and micronutrients automatically

### 🇳🇬 Culturally-Aware Nutrition
- **Nigerian Food Database**: Recognizes popular dishes like Jollof rice, Eba, Fufu, Egusi soup, Suya, Plantain, and more
- **Cultural Context**: Understands food pairings, preparation methods, and cultural significance
- **Budget-Conscious Recommendations**: Provides meal suggestions based on price tiers (budget, mid, premium)

### 👩‍⚕️ Personalized Health Coaching
- **Pregnancy & Maternal Health**: Specialized guidance for pregnant and lactating women
- **Deficiency Prevention**: Focuses on common deficiencies in Nigerian women (iron, calcium, vitamin D, zinc)
- **Anemia Support**: Tailored advice for managing and preventing iron deficiency anemia
- **14-Day Rolling Averages**: Tracks nutrition patterns over time for better insights

### 🤖 Multi-Agent AI Architecture
KAI uses a sophisticated 7-agent workflow to provide intelligent, context-aware responses:

1. **Router Agent** 🧭 - Classifies user requests and routes to appropriate workflows
2. **Vision Agent** 👁️ - Analyzes food images using GPT-4o vision capabilities
3. **Knowledge Agent** 📚 - Retrieves nutrition data from Nigerian food knowledge base (ChromaDB RAG)
4. **Fusion Engine** 🔄 - Classifies meals and analyzes dietary patterns
5. **Uncertainty Agent** 📊 - Calculates confidence scores and rolling averages
6. **Coaching Agent** 💬 - Provides personalized, empathetic nutrition guidance
7. **End Node** ✅ - Formats and delivers final responses

## 🏗️ Architecture & Workflows

### Workflow Routes

#### 1. Food Logging Pipeline 📷
```
User uploads image → Router → Vision Agent → Knowledge Agent → Fusion Engine → 
Uncertainty Agent → Coaching Agent → End Node
```
- Detects foods from images
- Estimates portions using MiDaS depth estimation
- Retrieves nutrition data from knowledge base
- Analyzes meal patterns
- Provides personalized coaching

#### 2. Nutrition Query Pipeline ❓
```
User asks question → Router → Knowledge Agent → Coaching Agent → End Node
```
- Answers questions about Nigerian foods
- Provides nutrition information
- Offers meal suggestions

#### 3. Health Check Pipeline 🏥
```
User asks health question → Router → Uncertainty Agent → Coaching Agent → End Node
```
- Analyzes nutrition history
- Identifies deficiencies
- Provides health recommendations

#### 4. General Chat Pipeline 💬
```
User message → Router → Coaching Agent → End Node
```
- Handles greetings and general conversation
- Provides empathetic support

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **OpenAI Agents SDK** - Multi-agent orchestration
- **GPT-4o** - Vision analysis and coaching
- **GPT-4o-mini** - Cost-efficient routing
- **ChromaDB** - Vector database for RAG
- **SQLite/PostgreSQL** - User data and meal history
- **JWT Authentication** - Secure user sessions

### AI & ML
- **LangChain** - RAG pipeline orchestration
- **Sentence Transformers** - Semantic search
- **MiDaS** - Depth estimation for portion sizing
- **Tavily** - Web search for real-time nutrition data

### Frontend (Mobile App)
- **React + TypeScript** - Modern UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library

## 📦 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ (for mobile app)
- PostgreSQL (optional, SQLite works for development)

### Backend Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd KAI
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
JWT_SECRET_KEY=your_jwt_secret
DATABASE_URL=sqlite:///kai_database.db  # or PostgreSQL URL
```

4. **Initialize the database**
```bash
python -m kai.database.db_setup
```

5. **Set up ChromaDB knowledge base**
```bash
# The knowledge base will be initialized on first run
# Or run ingestion scripts in knowledge-base/ingestion/
```

6. **Run the API server**
```bash
uvicorn kai.api.server:app --reload
```

The API will be available at `http://localhost:8000`

### Mobile App Setup

1. **Navigate to mobile app directory**
```bash
cd "Mobile App Development (2)"
```

2. **Install dependencies**
```bash
npm install
```

3. **Run development server**
```bash
npm run dev
```

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Create new user account
- `POST /api/v1/auth/login` - Login and get JWT token

### Food Logging
- `POST /api/v1/food-logging-upload` - Upload meal image and get nutrition analysis

### Chat
- `POST /api/v1/chat` - Chat with KAI coaching agent

### Meals
- `POST /api/v1/meals/log` - Manually log a meal
- `GET /api/v1/meals/history` - Get meal history (requires JWT)

### Users
- `GET /api/v1/users/profile` - Get user profile and health data
- `PUT /api/v1/users/profile` - Update user profile
- `GET /api/v1/users/stats` - Get daily nutrition statistics

### Health
- `GET /health` - Service health check

## 🍲 Recognized Nigerian Foods

KAI recognizes and provides detailed nutrition information for:

- **Staples**: Jollof rice, Fried rice, White rice, Eba, Fufu, Pounded yam, Amala
- **Soups**: Egusi soup, Bitterleaf soup, Ogbono soup, Okro soup, Vegetable soup
- **Proteins**: Suya, Grilled fish, Fried chicken, Beef stew, Goat meat, Peppered snail
- **Sides**: Plantain (fried/boiled), Yam, Potatoes, Beans, Moin moin, Akara
- **Snacks**: Chin chin, Puff puff, Buns, Doughnuts
- **Beverages**: Zobo, Kunu, Palm wine, Fresh juice

## 🎯 Health Focus Areas

### Common Deficiencies Addressed
- **Iron** (18mg/day for non-pregnant, 27mg/day for pregnant women)
- **Calcium** (1000mg/day)
- **Vitamin D** (supplementation guidance)
- **Zinc** (8mg/day)

### Special Populations
- **Pregnant Women**: Increased iron and folate requirements
- **Lactating Mothers**: Higher calorie and nutrient needs
- **Anemia Management**: Iron-rich meal planning and absorption tips
- **Budget-Conscious Users**: Affordable nutrition recommendations

## 🔄 Agent Communication Flow

All agents communicate using structured Pydantic models:

- `TriageResult` - Routing decision
- `VisionResult` - Detected foods from image
- `KnowledgeResult` - Nutrition data from RAG
- `CoachingResult` - Personalized guidance

## 📊 Data Models

### User Profile
- Demographics (age, gender)
- Health status (pregnancy, lactation, anemia)
- Custom RDV (Recommended Daily Values)
- Meal history

### Meal Record
- Foods consumed with portions
- Total nutrition breakdown
- Image URL
- Timestamp
- Confidence scores

## 🚀 Deployment

### Railway Deployment
KAI includes a `railway.toml` configuration for easy deployment on Railway.

### Docker
A `Dockerfile` is included for containerized deployment.

## 📝 Development Status

### ✅ Completed
- Router/Triage agent with strict JSON schemas
- Vision agent with GPT-4o
- Knowledge agent with ChromaDB RAG
- Coaching agent with personalized guidance
- Database setup and meal logging
- JWT authentication
- FastAPI server with all endpoints

### 🚧 In Progress
- Fusion Engine configuration
- Uncertainty Agent with 14-day rolling averages
- Enhanced portion estimation accuracy
- Mobile app UI polish


## 🙏 Acknowledgments

- Nigerian nutrition data sources
- OpenAI for GPT-4o vision capabilities
- ChromaDB for vector storage
- Tavily for web search integration

---

**Built with ❤️ for Nigerians** 🇳🇬

