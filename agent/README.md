# AI CV Agent - Backend

FastAPI backend application with CrewAI agents for intelligent CV generation and job tailoring.

## Features

- FastAPI with automatic OpenAPI documentation
- CrewAI agent orchestration
- Google Gemini integration for AI processing
- Supabase integration for data persistence
- PDF generation and processing
- Background job processing
- Comprehensive logging with PII redaction
- Row-level security enforcement

## Getting Started

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run the development server**
   ```bash
   python main.py
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Project Structure

```
app/
├── api/             # API routes and endpoints
├── core/            # Core configuration and utilities
├── models/          # Pydantic models and schemas
├── services/        # Business logic and external integrations
├── agents/          # CrewAI agent definitions
└── utils/           # Utility functions
```

## Environment Variables

Required environment variables (see `.env.example`):

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `GOOGLE_API_KEY` - Google Gemini API key
- `SECRET_KEY` - JWT secret key

## Development

- The API automatically reloads on code changes
- Access interactive API docs at `/docs`
- Health check endpoint at `/health`
- Structured logging with PII redaction