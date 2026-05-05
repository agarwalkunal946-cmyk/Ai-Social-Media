# Synapse AI Social Media Analytics

Synapse is a full-stack AI-powered social media analytics platform for Instagram, YouTube, and X / Twitter. It combines real-time dashboard metrics, sentiment and emotion analysis, toxicity detection, predictive signals, AI recommendations, crisis alerts, chatbot-style insight support, and automated HTML reports.

## 1. Project Overview

### Core outcomes in the current build

- Real-time analytics from connected Instagram, YouTube, and X / Twitter sources
- Multi-platform dashboard with audience, interaction, and trend summaries
- Sentiment analysis, emotion detection, and toxicity detection
- Audience insights and explainable AI summaries
- Predictive analysis for best day, best posting window, and momentum direction
- Trending hashtag extraction from indexed content
- Crisis alert generation based on negative sentiment, toxicity, and trend cooling
- Chatbot assistant for dashboard Q&A
- Floating analytics assistant with connected-media and public-trend prompts
- Automated weekly and monthly HTML reports
- User and admin workspaces
- Firebase authentication with Email, Google, GitHub, and Facebook

## 2. Architecture

### High-level flow

```text
Frontend (React + Vite)
        |
        v
Backend API (FastAPI)
        |
        +--> MongoDB        -> users, connections, alerts, reports, OAuth state
        +--> Redis/Memurai  -> connected preview cache + dashboard snapshot cache
        +--> Firebase Auth  -> login identity
        +--> Google APIs    -> YouTube account + analytics
        +--> Meta APIs      -> Instagram business account + insights
        +--> X live source  -> public profile, timeline, search, trends
```

### Request flow

```text
User connects platform
    -> backend stores account connection
    -> backend fetches platform preview data
    -> dashboard snapshot aggregates metrics
    -> AI layers derive mood, risk, prediction, recommendations
    -> frontend renders charts, cards, alerts, chatbot, and reports
```

## 3. Main Features

### User dashboard

- Connected account overview
- Platform rollups for Instagram, YouTube, and X / Twitter
- Sentiment and emotion charts
- Toxicity and moderation watchlist
- Audience insights
- Predictive analysis
- Explainable AI
- Trending hashtags
- Top content viewer
- AI recommendations
- Crisis alerts
- Floating chatbot assistant
- Reports workspace

### Admin workspace

- Managed user list
- Search, sort, edit, activate, deactivate, and delete users
- User-specific analytics inspection
- Latest connections and reports
- Manual system alert creation
- Connection removal
- Report removal

## 4. Tech Stack

### Frontend

- React 18
- Vite
- Tailwind CSS
- TanStack Query
- Axios
- Recharts
- Framer Motion
- Firebase Web SDK

### Backend

- FastAPI
- Python 3.11
- Motor
- MongoDB
- Redis or Memurai
- httpx
- Google Auth

## 5. Windows Prerequisites

Install these on the client system before setup:

1. Git
2. Node.js 20+ and npm
3. Python 3.11
4. MongoDB Community Server
5. Redis for Windows or Memurai
6. Google Chrome or Microsoft Edge
7. Optional: `ngrok` or any HTTPS tunnel for OAuth callback testing

## 6. Accounts and Services Required

### Firebase

Create one Firebase project and enable:

- Email/Password
- Google
- GitHub
- Facebook

### Google / YouTube

Create one Google Cloud project and enable:

- YouTube Data API v3
- YouTube Analytics API
- OAuth consent screen
- OAuth web client credentials

### Meta / Instagram

Create one Meta app with:

- Facebook Login product
- App in Live mode, or add testers while in Development mode
- Instagram Professional account
- Connected Facebook Page
- Required Instagram permissions approved or available for the app

### X / Twitter

This project uses a handle-based live X / Twitter source for public profile, search, trend, and post-detail reads.

Client handoff requires:

- one working X live source token
- one actor or source identifier compatible with the backend

In this repo those are configured through `X_LIVE_SOURCE_TOKEN` and `X_LIVE_SOURCE_ACTOR_ID`.

## 7. Environment Variables

### Backend: `backend/.env`

```env
APP_NAME=Ai Social Media
API_PREFIX=/api
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173
DEMO_MODE=true
FIRST_ADMIN_EMAIL=admin@gmail.com
ADMIN_EMAILS=admin@gmail.com
AUTH_FALLBACK_ENABLED=true

MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=ai_social_media
REDIS_URL=redis://localhost:6379/0
PREVIEW_CACHE_TTL_SECONDS=300
DASHBOARD_CACHE_TTL_SECONDS=180

FIREBASE_API_KEY=
FIREBASE_AUTH_DOMAIN=
FIREBASE_PROJECT_ID=
FIREBASE_STORAGE_BUCKET=
FIREBASE_MESSAGING_SENDER_ID=
FIREBASE_APP_ID=
FIREBASE_MEASUREMENT_ID=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/providers/youtube/callback

META_APP_ID=
META_APP_SECRET=
META_REDIRECT_URI=http://localhost:8000/api/providers/instagram/callback
META_API_VERSION=v25.0

X_LIVE_SOURCE_TOKEN=
X_LIVE_SOURCE_ACTOR_ID=danek~twitter-scraper-ppr
X_LIVE_TIMELINE_MAX_POSTS=36
X_LIVE_SEARCH_MAX_POSTS=48
X_LIVE_POST_DETAIL_MAX_POSTS=1
X_LIVE_TRENDING_COUNTRY=United States
X_LIVE_TIMEOUT_SECONDS=45

UPLOADS_DIR=F:/Client_Projects/Ai-Social-Media/backend/uploads
REPORTS_DIR=F:/Client_Projects/Ai-Social-Media/backend/app/static/reports
```

### Frontend: `frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_MESSAGING_SENDER_ID=
VITE_FIREBASE_APP_ID=
VITE_FIREBASE_MEASUREMENT_ID=
```

## 8. Local Setup on Windows

### Backend

```powershell
cd F:\Client_Projects\Ai-Social-Media\backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd F:\Client_Projects\Ai-Social-Media\frontend
npm install
npm run dev
```

### Default URLs

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## 9. First Admin Setup

Admin signup is not open from the UI.

Set the admin email in `backend/.env`:

```env
FIRST_ADMIN_EMAIL=admin@gmail.com
ADMIN_EMAILS=admin@gmail.com
```

Then log in through Firebase using the same email or seed the admin manually:

```powershell
cd F:\Client_Projects\Ai-Social-Media\backend
.venv\Scripts\activate
python scripts\seed_admin.py
```

## 10. Platform Connection Requirements

### Instagram

- Instagram Business or Creator account
- Linked Facebook Page
- Meta app credentials in `backend/.env`
- Redirect URI must match the Meta app configuration
- Public Instagram discovery works best after an owned professional account is connected

### YouTube

- Google account that owns the YouTube channel
- YouTube Data API and YouTube Analytics API enabled
- Redirect URI must match Google OAuth settings

### X / Twitter

- Public X handle
- Valid `X_LIVE_SOURCE_TOKEN`
- Valid `X_LIVE_SOURCE_ACTOR_ID`

Current build note:

- X connect is handle-based
- X OAuth is not used in the current implementation

## 11. Cache and Reload Behavior

- React Query is configured to avoid refetch-on-window-focus, so switching browser tabs should not trigger a full loading flash again
- Connected platform previews are cached in Redis or Memurai
- Dashboard snapshots are also cached in Redis or Memurai for faster repeat loads
- Cache TTL is controlled through:
  - `PREVIEW_CACHE_TTL_SECONDS`
  - `DASHBOARD_CACHE_TTL_SECONDS`
- Health check endpoint: `http://localhost:8000/api/health`

## 12. Dashboard Analytics Logic

This section documents exactly how the current project calculates analytics.

### 11.1 Content score

Used for top content ranking and trend strength.

```text
content_score =
  views
  + likes * 15
  + comments * 20
  + replies * 20
  + reposts * 18
  + retweets * 18
  + quotes * 16
  + saves * 18
  + shares * 18
```

### 11.2 Interaction total

```text
interactions =
  likes + comments + replies + reposts + retweets + quotes + saves + shares
```

### 11.3 Sentiment

The current project uses a lightweight heuristic fallback in `backend/app/services/analysis.py`.

- positive keywords increase positive score
- negative keywords increase negative score
- dominant side becomes the sentiment label
- final dashboard mood combines dominant sentiment and dominant emotion

### 11.4 Emotion detection

Emotion labels are mapped from keyword groups such as:

- joy
- excitement
- concern
- frustration
- anger
- surprise

### 11.5 Toxicity detection

Toxicity is estimated from harmful-language keywords.

Text is flagged as toxic when the toxicity score crosses the review threshold used in the analysis service. The dashboard then builds:

- overall toxicity summary
- moderation queue
- crisis alerts when needed

### 11.6 Platform reach and engagement rate

Platform comparison is calculated differently per platform:

- YouTube reach: max of subscribers and visible video views
- Instagram reach: connected follower count
- X / Twitter reach: max of followers, views, and loaded-post proxy

```text
engagement_rate = interactions / reach * 100
```

### 11.7 Trend detection

The engagement trend groups indexed content by day of week using the content score.

- strongest day = highest trend bucket
- best time window = highest score bucket by UTC hour range

Time windows used:

- Early morning
- Morning
- Afternoon
- Evening
- Late night

### 11.8 Predictive analysis

Prediction compares recent trend momentum against the earlier baseline.

```text
predicted_change_pct =
  ((recent_average - baseline_average) / baseline_average) * 100
```

Thresholds in the current build:

- `>= 12%` -> Upward
- `<= -10%` -> Cooling
- otherwise -> Stable

### 11.9 Trending hashtags

Hashtags come from indexed content tags and caption-derived tags.

- recurring tags are counted
- top recurring tags become dashboard trending hashtags
- recommendation cards reuse these tags

### 11.10 Recommendations

Recommendations are built from:

- strongest day
- strongest time window
- top content title and hook pattern
- dominant emotion
- recurring hashtags
- predictive trend direction

### 11.11 Explainable AI

The explainability layer exposes the factors used in recommendations:

- reach weighting
- interaction velocity
- sentiment balance
- moderation risk
- topic recurrence

### 11.12 Crisis alerts

Automatic workspace alerts are generated when:

- negative sentiment percentage becomes high
- toxicity watchlist crosses the risk threshold
- engagement is cooling sharply
- viral opportunity becomes unusually strong

### 11.13 Chatbot assistant

The chatbot is backed by the current dashboard snapshot and answers questions about:

- best posting time
- hashtags
- audience reach
- crisis risk
- top content
- moderation watchlist

## 13. User and Admin Capabilities

### User can

- sign in and manage profile
- upload avatar
- connect and disconnect platforms
- view dashboard analytics
- explore public and connected platform views
- ask the floating assistant
- open alerts
- generate, open, download, and delete reports

### Admin can

- view the operations center
- inspect all managed users
- edit user profile, mode, and status
- remove users
- inspect a selected user's analytics
- remove a selected user's connection
- remove a selected user's report
- create system alerts

## 14. File Guide

### Root

- `README.md` -> main documentation and setup guide
- `Synapse-AI-Social-Media-Presentation.pptx` -> project presentation deck
- `backend/` -> FastAPI backend
- `frontend/` -> React frontend

### Backend key files

- `backend/app/main.py` -> FastAPI app entry point
- `backend/app/api/routes/dashboard.py` -> dashboard and chatbot endpoints
- `backend/app/api/routes/providers.py` -> connect and disconnect flows
- `backend/app/api/routes/auth.py` -> profile and mode endpoints
- `backend/app/api/routes/alerts.py` -> alert APIs
- `backend/app/api/routes/admin.py` -> admin APIs
- `backend/app/api/routes/reports.py` -> report APIs
- `backend/app/services/dashboard_data.py` -> dashboard aggregation logic
- `backend/app/services/analysis.py` -> sentiment, emotion, toxicity heuristics
- `backend/app/services/platform_preview.py` -> connected platform previews
- `backend/app/services/public_platforms.py` -> public search and explore data
- `backend/app/services/reports.py` -> HTML report generation
- `backend/app/services/alerts.py` -> auto and system alert generation
- `backend/app/services/social/instagram.py` -> Instagram API logic
- `backend/app/services/social/youtube.py` -> YouTube API logic
- `backend/app/services/social/x_apify.py` -> X live-source adapter used by the backend
- `backend/scripts/generate_project_presentation.py` -> generates the PPTX presentation deck

### Frontend key files

- `frontend/src/App.jsx` -> routes
- `frontend/src/pages/LandingPage.jsx` -> public landing page
- `frontend/src/pages/LoginPage.jsx` -> login page
- `frontend/src/pages/SignupPage.jsx` -> signup page
- `frontend/src/pages/DashboardPage.jsx` -> user dashboard
- `frontend/src/pages/ConnectPage.jsx` -> platform connection page
- `frontend/src/pages/PublicPlatformPage.jsx` -> public and connected explorer
- `frontend/src/pages/ReportsPage.jsx` -> reports page
- `frontend/src/pages/AdminPage.jsx` -> admin workspace
- `frontend/src/components/layout/AppShell.jsx` -> shared app shell
- `frontend/src/components/ui/PlatformIcon.jsx` -> branded Instagram, YouTube, and X icons
- `frontend/src/contexts/AuthContext.jsx` -> frontend auth state
- `frontend/src/lib/firebase.js` -> Firebase config
- `frontend/src/lib/apiClient.js` -> authenticated API client

## 15. Storage

- MongoDB stores users, social accounts, alerts, reports, and OAuth states
- Redis or Memurai caches connected platform previews and dashboard snapshots
- `backend/uploads/` stores local uploads such as avatars
- `backend/app/static/reports/` stores generated HTML reports

## 16. Client Handoff

Do not hand over your own personal production secrets blindly. Give the client:

1. A clean `backend/.env` template and `frontend/.env` template
2. The exact list of accounts they must create or share access to
3. The redirect URIs they must configure in Firebase, Google, and Meta
4. The Apify token and actor details for the X / Twitter source

Recommended client-owned accounts:

1. One Firebase project owner account
2. One Google Cloud project owner account for YouTube APIs
3. One Meta developer app owner account for Instagram/Facebook Login
4. One Apify account with token access
5. One MongoDB + Redis or Memurai host owner if deployment is separate

What to share with the client:

1. `frontend/.env` values for Firebase web config and backend API URL
2. `backend/.env` values for API credentials, OAuth secrets, Redis, MongoDB, and Apify
3. This `README.md`
4. `Synapse-AI-Social-Media-Presentation.pptx`

Best practice:

- Keep the template in version control
- Keep the real client secret values outside git
- Ask the client to generate or own the Google, Meta, Firebase, and Apify credentials for long-term ownership

## 17. Troubleshooting

### Dashboard shows no analytics

Check:

1. MongoDB is running
2. Redis or Memurai is running
3. platform connection completed successfully
4. correct backend and frontend `.env` values are present

### Instagram connect works but discovery is limited

Check:

1. Instagram account is Professional
2. account is linked to a Facebook Page
3. Meta app has the required scopes
4. redirect URI is configured correctly

### YouTube analytics are missing

Check:

1. Google OAuth client is correct
2. YouTube Data API v3 is enabled
3. YouTube Analytics API is enabled
4. the signed-in Google account owns the target channel

### X / Twitter connect fails

Check:

1. `X_LIVE_SOURCE_TOKEN`
2. `X_LIVE_SOURCE_ACTOR_ID`
3. network access from the backend machine
4. the handle is public and valid

### Facebook login shows "This app isn't available"

Check:

1. Facebook sign-in is enabled in Firebase Authentication
2. the Firebase redirect URI `https://<your-firebase-project>.firebaseapp.com/__/auth/handler` is added under Meta `Facebook Login > Settings > Valid OAuth Redirect URIs`
3. the Meta app is in Development mode with test users / admins / developers only, or in Live mode for public access
4. localhost testing is done only with Facebook test accounts when the app is still in Development mode
5. at least the standard login permissions `public_profile` and `email` are available

## 18. Verification Completed

The current codebase was verified after these changes with:

```powershell
cd backend
.venv\Scripts\python.exe -m compileall app

cd ..\frontend
npm run build
```

Both completed successfully.
