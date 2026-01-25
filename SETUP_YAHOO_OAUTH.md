# Yahoo OAuth Setup Guide

## The Issue
You're getting an "Internal Server Error" when trying to connect to Yahoo because the OAuth credentials are not configured.

## Quick Fix

### Step 1: Set Environment Variables
Create a `.env` file in the project root with your Yahoo OAuth credentials:

```bash
# Copy the template
cp env.template .env

# Edit the .env file and add your Yahoo credentials
```

### Step 2: Get Yahoo OAuth Credentials

1. Go to https://developer.yahoo.com/apps/
2. Sign in with your Yahoo account
3. Click "Create an App"
4. Fill out the form:
   - **Application Name**: AI Commissioner
   - **Application Type**: Web Application
   - **Description**: Fantasy league automation tool
   - **Home Page URL**: http://localhost:3000
   - **Redirect URI(s)**: http://localhost:8000/auth/yahoo/callback

5. After creating the app, you'll get:
   - **Client ID** (Consumer Key)
   - **Client Secret** (Consumer Secret)

### Step 3: Configure Environment Variables

Edit your `.env` file:

```bash
# Required for Yahoo OAuth
YAHOO_CLIENT_ID=your_client_id_from_yahoo
YAHOO_CLIENT_SECRET=your_client_secret_from_yahoo
YAHOO_REDIRECT_URI=http://localhost:8000/auth/yahoo/callback

# Required for the app
SECRET_KEY=some_random_secret_key_here
FRONTEND_URL=http://localhost:3000

# Optional but recommended
DATABASE_URL=postgresql+asyncpg://username:password@localhost/aicommissioner
```

### Step 4: Restart the Server

After setting up the environment variables:

```bash
# Restart your backend server
uvicorn main:app --reload --port 8000
```

## Testing the Connection

1. Navigate to `http://localhost:3000/connect`
2. Click "Connect with Yahoo"
3. You should be redirected to Yahoo for authorization
4. After authorizing, you'll be redirected back to your app

## Troubleshooting

### Still getting errors?
- Check that your `.env` file is in the project root
- Verify the Yahoo app redirect URI matches exactly: `http://localhost:8000/auth/yahoo/callback`
- Make sure your Yahoo app is set to "Web Application" type
- Check server logs for specific error messages

### Can't create Yahoo app?
- Make sure you're signed into a Yahoo account
- Some Yahoo accounts may need to verify phone numbers first
- Try using a different browser or clearing cookies

### OAuth scope issues?
The app requests these Yahoo permissions:
- `openid` - Basic identity
- `email` - Email address  
- `profile` - Profile information
- `fspt-r` - Fantasy Sports Read access

Make sure your Yahoo app allows these scopes.
