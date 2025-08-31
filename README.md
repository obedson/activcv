# 🚀 Activ CV - AI-Powered Career Intelligence

**Smarter CV for Smart People**

An intelligent career companion that automatically tailors your CV and matches your skills with the right opportunities—so you apply smarter, faster, and with confidence.

## Project Structure

```
├── web/                    # Next.js frontend application
├── agent/                  # FastAPI backend with CrewAI agents
├── infra/                  # Infrastructure configuration (Supabase, etc.)
├── gce-deploy.yaml        # Google Cloud Engine deployment config
├── build-gce.sh           # GCE deployment script
├── DEPLOY_GCE.md          # GCE deployment guide
└── temporal/              # Development files and cleanup
```

## ✨ Features

### 🎯 **Core Capabilities**
- **AI-Powered CV Generation** - CrewAI agents create tailored CVs based on job requirements
- **Intelligent Cover Letter Writing** - Personalized cover letters with company research
- **Real-time Job Processing** - Background job queue with live progress tracking
- **Advanced Job Analysis** - Extract requirements, skills, and ATS keywords from job descriptions
- **Document Vault** - Secure document storage with sharing and version control

### 🔧 **Technical Features**
- **Production Ready** - Optimized Docker containers for GCE deployment
- **Scalable Architecture** - Kubernetes deployment with auto-scaling
- **Security First** - Non-root containers, health checks, resource limits
- **Real-time Updates** - WebSocket connections for live job progress

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

### Infrastructure
- Google Cloud Engine (GKE)
- Supabase (Database, Auth, Storage)
- Docker containers

## Quick Start

### Local Development

1. **Clone and setup backend**
   ```bash
   git clone <repository-url>
   cd agent
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   python main.py
   ```

2. **Setup frontend**
   ```bash
   cd web
   npm install
   npm run dev
   ```

### MVP Testing (Cloud Run) - Recommended

```bash
# Set your GCP project ID
export PROJECT_ID="your-gcp-project-id"

# Deploy to Cloud Run (pay-per-request, scales to zero)
./deploy-cloudrun.sh $PROJECT_ID
```

See [DEPLOY_CLOUDRUN.md](DEPLOY_CLOUDRUN.md) for detailed instructions.

### Production Deployment (GKE)

```bash
# For production with high traffic
./build-gce.sh $PROJECT_ID
```

See [DEPLOY_GCE.md](DEPLOY_GCE.md) for Kubernetes deployment.

## Configuration

### Environment Variables

Backend (`agent/.env`):
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anon key
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `JWT_SECRET`: Random secret for JWT signing

Frontend (`web/.env.local`):
- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anon key
- `NEXT_PUBLIC_API_URL`: Backend API URL

## Development

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Security

- Non-root Docker containers
- Row-level security (RLS) for all user data
- JWT-based authentication
- Resource limits and health checks
- Input validation and sanitization

## License

MIT License - see LICENSE file for details
