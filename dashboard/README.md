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

2. Start the development server:
```bash
npm run dev
```

3. Make sure your AI Commissioner backend is running on `http://localhost:8000`

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

The dashboard proxies API calls to the backend server running on port 8000:
- `/api/*` → `http://localhost:8000/api/*`
- `/auth/*` → `http://localhost:8000/auth/*` 
- `/connect/*` → `http://localhost:8000/connect/*`
- `/admin/*` → `http://localhost:8000/admin/*`

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **Language**: TypeScript
- **API**: Fetch with proxy to FastAPI backend