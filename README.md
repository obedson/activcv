# 🚀 Activ CV - AI-Powered Career Intelligence

**Smarter CV for Smart People**

An intelligent career companion that automatically tailors your CV and matches your skills with the right opportunities—so you apply smarter, faster, and with confidence.

## Project Structure

```
├── web/          # Next.js frontend application
├── agent/        # FastAPI backend with CrewAI agents
├── infra/        # Infrastructure configuration (Supabase, etc.)
└── .kiro/        # Kiro specifications and documentation
```

## ✨ Features

### 🎯 **Core Capabilities**
- **AI-Powered CV Generation** - CrewAI agents create tailored CVs based on job requirements
- **Intelligent Cover Letter Writing** - Personalized cover letters with company research
- **Real-time Job Processing** - Background job queue with live progress tracking
- **Advanced Job Analysis** - Extract requirements, skills, and ATS keywords from job descriptions
- **Document Vault** - Secure document storage with sharing and version control
- **Job Site Monitoring** - Automated crawling and intelligent job matching

### 🔧 **Technical Features**
- **Real-time Updates** - WebSocket connections for live job progress
- **Comprehensive Testing** - Unit, integration, and E2E test coverage
- **Production Monitoring** - Prometheus metrics, Grafana dashboards, log aggregation
- **Scalable Architecture** - Docker containers, Redis queue, background workers
- **Security First** - Row-level security, input validation, audit logging

## Tech Stack

### Frontend (web/)
- Next.js 14 with App Router
- TypeScript
- Tailwind CSS
- shadcn/ui components
- Supabase Auth

### Backend (agent/)
- FastAPI
- CrewAI for agent orchestration
- Google Gemini for AI processing
- Supabase for data persistence
- PDF generation with WeasyPrint

### Infrastructure (infra/)
- Supabase (Database, Auth, Storage)
- Vercel (Frontend deployment)
- Fly.io/Railway (Backend deployment)

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Supabase account
- Google Gemini API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-cv-agent
   ```

2. **Set up the frontend**
   ```bash
   cd web
   npm install
   npm run dev
   ```

3. **Set up the backend**
   ```bash
   cd agent
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   python main.py
   ```

4. **Configure Supabase**
   - Create a new Supabase project
   - Run the migrations in `infra/supabase/migrations/`
   - Configure authentication and storage buckets
   - Update environment variables

## Development

- Frontend runs on http://localhost:3000
- Backend API runs on http://localhost:8000
- API documentation available at http://localhost:8000/docs

## Security

- Row-level security (RLS) for all user data
- JWT-based authentication
- PII redaction in logs
- Secure file storage with signed URLs
- Input validation and sanitization

## License

MIT License - see LICENSE file for details