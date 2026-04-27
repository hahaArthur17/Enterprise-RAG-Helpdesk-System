Enterprise RAG Helpdesk System

An AI-empowered full-stack knowledge base assistant designed for enterprise internal use.
This project demonstrates a modern microservices architecture, integrating a React frontend, a robust .NET Web API for business logic, and a Python FastAPI service for AI/RAG capabilities.

🏗 Architecture Diagram

The system follows a standard Backend-for-Frontend (BFF) microservices architecture.

Diagram
graph LR
    User([User])
    UI[Frontend \n React + TypeScript]
    NET_API[Backend API \n .NET Core]
    PY_API[AI Microservice \n Python FastAPI]
    
    DB[(PostgreSQL + pgvector)]
    LLM((Azure OpenAI))

    User -- Interacts with --> UI
    UI -- HTTP POST /api/chat --> NET_API
    NET_API -- HTTP POST /ask --> PY_API
    
    PY_API -. Embeddings & Search .-> DB
    PY_API -. Prompt & Generate .-> LLM
    
    classDef frontend fill:#61dafb,stroke:#333,stroke-width:2px,color:#000;
    classDef dotnet fill:#512bd4,stroke:#333,stroke-width:2px,color:#fff;
    classDef python fill:#ffd43b,stroke:#333,stroke-width:2px,color:#000;
    classDef future fill:#e9ecef,stroke:#999,stroke-width:2px,stroke-dasharray: 5 5,color:#666;

    class UI frontend;
    class NET_API dotnet;
    class PY_API python;
    class DB,LLM future;

🛠 Tech Stack
Frontend (User Interface)
React 18 – Component-based UI rendering
TypeScript – Strong typing for stability and maintainability
Vite – Fast development and build tooling
Backend (.NET BFF - Backend for Frontend)
C# & ASP.NET Core Web API – Handles routing, validation, and orchestration
IHttpClientFactory – Manages resilient HTTP connections
ILogger (Structured Logging) – Tracks request flows and errors
AI Microservice (Python)
Python 3 – Core language for AI and data processing
FastAPI – High-performance asynchronous framework
Pydantic – Data validation and configuration management
🚀 Getting Started (Local Development)

Run the three services in separate terminals:

1. Start the AI Service (Python)
cd ai-service

# Activate your virtual environment first
# Example:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000

2. Start the Backend API (.NET)
cd backend-dotnet/BackendApi
dotnet run


Runs on: http://localhost:5263

(Check console output to confirm)

3. Start the Frontend (React)
cd frontend
npm install
npm run dev


Visit: http://localhost:5173

📌 Notes
Ensure all services are running simultaneously
Backend depends on the AI service being available
Planned future enhancements:
PostgreSQL + pgvector integration
Azure OpenAI for LLM-based responses