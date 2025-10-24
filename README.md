# KAI: Nigerian Nutrition Intelligence App 🇳🇬🥗

**KAI** is a culturally-adapted nutrition tracking and health guidance platform built for Nigerian users. It combines AI-powered food recognition, portion estimation, and proactive micronutrient intelligence to empower healthier eating habits across Nigeria.

---

## 🌟 Core Mission
**See your food. Know your calories. Understand your habits.**
- Proactive deficiency detection from photos
- Focus on preventive wellness, not just calorie tracking

## 👥 Target Users
- Nigerians seeking culturally relevant nutrition advice
- Users who want fast, camera-first meal logging
- Anyone interested in tracking and improving their dietary health

## 🏆 Key Features
- **Camera-first logging:** Snap a meal, get instant feedback (10 seconds per meal)
- **Nigerian food recognition:** Jollof, eba, moi moi, egusi, and more
- **Micronutrient intelligence:** Tracks 8 key nutrients (3 macros + 5 micros)
- **Deficiency detection:** 14-day rolling average, evidence-based symptom prompts
- **Culturally relevant solutions:** Nigerian food database, local market references, price tiers
- **Zero-friction UX:** Data-light, 4-tab navigation, progressive disclosure, quick onboarding

## 🧠 How It Works
- **Vision Agent:** Detects Nigerian foods from photos
- **Portion Agent:** Estimates food weight/volume using MiDaS depth estimation
- **Knowledge Agent:** Calculates nutrition with Nigerian-specific adjustments
- **Fusion Engine:** Classifies meal types and patterns
- **Uncertainty Agent:** Detects deficiencies, tracks confidence
- **Coaching Agent:** Provides health guidance, symptom tracking, and local food solutions

## 🥑 Tracked Nutrients
- **Macros:** Protein, Carbohydrates, Fat
- **Micros:** Iron, Calcium, Vitamin A, Zinc, Vitamin D

## 📲 Technical Stack
- OpenAI Agent Builder (workflow orchestration)
- FastAPI + MiDaS for portion estimation (MCP server)
- Custom Nigerian food knowledge base (JSONL)
- Event-driven, agentic architecture

## 🚀 Getting Started
1. Clone the repo
2. Deploy agents (MiDaS MCP server, etc.)
3. Set environment variables (see `.env.example`)
4. Run the app or deploy on Railway

## 🤝 Contributing
PRs and issues welcome! See CONTRIBUTING.md.

## 📜 License
MIT License

---
Built for Nigeria. Powered by AI. 🇳🇬✨
