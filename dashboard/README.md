# AI Commissioner Dashboard

A simple Next.js micro-dashboard for managing fantasy football leagues with AI-powered recaps.

## Features

- **Connect Page** (`/connect`): Connect Yahoo Fantasy or Sleeper leagues
- **Settings Page** (`/settings/[leagueId]`): Configure league settings, recap schedules, and AI personalities  
- **Preview Page** (`/preview`): Generate and preview recaps without publishing

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. (Optional) Set backend URL environment variable:
```bash
# For development (default)
export BACKEND_URL=http://localhost:8000

# For production
export BACKEND_URL=https://your-api-domain.com
```

3. Start the development server:
```bash
npm run dev
```

4. Make sure your AI Commissioner backend is running on the configured URL (default: `http://localhost:8000`)

## Pages

### `/connect`
- **Yahoo**: "Connect Yahoo" button → redirects to `/auth/yahoo/start`
- **Sleeper**: Form with league_id and optional groupme_bot_id → POST to `/connect/sleeper`

### `/settings/[leagueId]` 
- **Toggles**: Tuesday Review (power rankings), Wednesday Waivers (waiver recaps)
- **Style**: Select from balanced/snark/hype/nerd
- **Use LLM**: Checkbox to enable AI rendering
- **Send Test Post**: Button → POST to `/admin/run/tuesday/{league_uuid}`

### `/preview`
- Form to generate recap text without publishing
- Calls backend API to generate content for preview
- Copy to clipboard functionality

## API Integration

The dashboard proxies API calls to the backend server. The backend URL is configurable via the `BACKEND_URL` environment variable (defaults to `http://localhost:8000`):
- `/api/*` → `${BACKEND_URL}/api/*`
- `/auth/*` → `${BACKEND_URL}/auth/*` 
- `/connect/*` → `${BACKEND_URL}/connect/*`
- `/admin/*` → `${BACKEND_URL}/admin/*`

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **Language**: TypeScript
- **Configuration**: TypeScript-based Next.js config with environment-driven rewrites
- **API**: Fetch with proxy to FastAPI backend