# AI Commissioner - Fantasy Sports AI Agent

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://python.org)

A comprehensive SaaS platform that seamlessly integrates with fantasy sports leagues to provide automated AI-powered recaps, power rankings, and engaging content generation throughout the season. Transform your league's communication with intelligent, personalized, and timely updates.

## Features

### Core Functionality
- **Multi-Provider Support**: Integrates with Yahoo Fantasy and Sleeper
- **OAuth Authentication**: Secure Yahoo OAuth flow + simple Sleeper league ID entry
- **Automated Scheduling**: Celery-based task scheduling for weekly recaps
- **AI-Powered Content**: Both deterministic and LLM-powered text generation
- **GroupMe Integration**: Automatic publishing to GroupMe group chats

### Scheduled Content
- **Tuesday 9 AM CT**: Prior-week review + power rankings
- **Wednesday 9 AM CT**: Waiver wire recap (adds/drops/FAAB)
- **Configurable**: Per-league customization of schedule and content

### Data Integration
- **Sleeper**: Complete league data ingestion (leagues/users/rosters/matchups/transactions)
- **Yahoo**: OAuth-based data access with token refresh
- **Canonical Schema**: Provider-agnostic normalized data model
- **Real-time Sync**: Webhook support + scheduled synchronization

### AI Content Generation
- **Deterministic Rendering**: Fast, zero-cost formatted recaps
- **LLM Rendering**: Optional AI-powered content with customizable personas
- **Multiple Styles**: Standard, emoji, formal, casual formatting options
- **Persona Support**: Witty, professional, roastmaster, hype, analyst personas

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Ingestors     │    │   AI/Text       │
│                 │    │                 │    │                 │
│ • OAuth Routes  │───▶│ • Sleeper API   │───▶│ • Summary Gen   │
│ • Admin Panel   │    │ • Yahoo API     │    │ • Text Format   │
│ • Webhooks      │    │ • Normalization │    │ • LLM Integration│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   Scheduler     │    │   Publisher     │
│                 │    │                 │    │                 │
│ • PostgreSQL    │    │ • Celery Beat   │    │ • GroupMe API   │
│ • Canonical     │    │ • Redis         │    │ • Message Queue │
│ • Normalized    │    │ • Cron Jobs     │    │ • Retry Logic   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Project Structure

```
aicommissioner/
├── main.py                 # FastAPI application entry point
├── config.py              # Application configuration
├── requirements.txt       # Python dependencies
├── api/
│   └── routes/
│       ├── auth.py        # Authentication endpoints
│       ├── admin.py       # League management
│       └── webhooks.py    # Webhook handlers
├── database/
│   └── connection.py      # Database setup
├── models/                # SQLAlchemy models
│   ├── user.py
│   ├── league.py
│   ├── roster.py
│   ├── matchup.py
│   └── transaction.py
├── ingestors/             # Data ingestion
│   ├── sleeper_ingestor.py
│   └── yahoo_ingestor.py
├── ai_text/               # AI content generation
│   ├── summary_generator.py
│   └── text_formatter.py
├── publishers/            # Content publishing
│   └── groupme_publisher.py
├── services/              # Business logic
│   └── recap_service.py
└── schedulers/            # Task scheduling
    ├── celery_app.py
    └── tasks.py
```

## Setup & Installation

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd aicommissioner

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Required Configuration

Create a `.env` file with:

```env
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost/aicommissioner

# Redis (for Celery)
REDIS_URL=redis://localhost:6379

# Yahoo OAuth
YAHOO_CLIENT_ID=your_yahoo_client_id
YAHOO_CLIENT_SECRET=your_yahoo_client_secret
YAHOO_REDIRECT_URI=http://localhost:8000/auth/yahoo/callback

# AI Services (optional)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# GroupMe
GROUPME_ACCESS_TOKEN=your_groupme_access_token

# Security
SECRET_KEY=your_secret_key_here
```

### 3. Database Setup

```bash
# Start PostgreSQL and Redis
# Create database
createdb aicommissioner

# Run migrations (tables will be created automatically)
python main.py
```

### 4. Start Services

```bash
# Terminal 1: Start FastAPI app
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Celery worker
celery -A schedulers.celery_app worker --loglevel=info

# Terminal 3: Start Celery beat scheduler
celery -A schedulers.celery_app beat --loglevel=info
```

## Usage

### 1. User Authentication

**Yahoo OAuth:**
```bash
# Navigate to
GET /auth/yahoo/login
# Complete OAuth flow
```

**Sleeper Integration:**
```bash
# Add Sleeper league IDs
POST /auth/sleeper/leagues
{
  "league_ids": ["league_id_1", "league_id_2"]
}
```

### 2. League Management

```bash
# Create league
POST /admin/leagues
{
  "provider": "sleeper",
  "provider_league_id": "your_league_id",
  "name": "My League",
  "season": 2024,
  "groupme_bot_id": "bot_id",
  "enable_power_rankings": true,
  "enable_waiver_recaps": true
}

# Update league settings
PATCH /admin/leagues/{league_id}
{
  "enable_llm_rendering": true,
  "ai_persona_style": "witty"
}
```

### 3. Manual Recaps

```bash
# Trigger power rankings
POST /admin/recaps/power-rankings
{
  "league_id": 1,
  "week": 5
}

# Trigger waiver recap
POST /admin/recaps/waiver-recap
{
  "league_id": 1,
  "week": 5
}
```

### 4. Webhooks

```bash
# Sleeper webhook endpoint
POST /webhooks/sleeper/{league_id}

# Test webhook
POST /webhooks/test/{league_id}
```

## API Documentation

Once running, view interactive API docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Scheduled Tasks

### Default Schedule (Central Time)

- **Tuesday 9:00 AM**: Power Rankings recap for previous week
- **Wednesday 9:00 AM**: Waiver wire activity recap
- **Daily 6:00 AM**: League data synchronization
- **Daily 6:00 PM**: Evening league sync (during season)
- **Sunday/Monday every 2 hours**: Game day rapid sync
- **Sunday 2:00 AM**: Weekly data cleanup

### Customization

Each league can customize:
- Schedule days/times
- Content types (power rankings, waiver recaps)
- AI rendering (deterministic vs LLM)
- Persona styles
- GroupMe integration

## AI Content Features

### Deterministic Rendering (Free)
- **Standard**: Clean, professional format
- **Emoji**: Fun, emoji-heavy style
- **Formal**: Professional sports journalism
- **Casual**: Conversational group chat style

### LLM Rendering (Optional)
- **Providers**: OpenAI GPT-3.5/4, Anthropic Claude
- **Personas**: 
  - Witty (humor and puns)
  - Professional (sports analysis)
  - Roastmaster (savage trash talk)
  - Hype (maximum energy)
  - Analyst (deep insights)

## Monitoring & Health

```bash
# Health check
GET /health

# Webhook health
GET /webhooks/health

# Check active tasks
celery -A schedulers.celery_app inspect active
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]
