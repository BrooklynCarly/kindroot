# KindRoot

An AI-powered patient report generation system for autism screening questionnaires. Analyzes parent-submitted data and generates comprehensive, personalized reports with safety triage, developmental hypotheses, and local resource recommendations.

## Tech Stack

**Backend (Python/FastAPI)**
- FastAPI web framework
- Google Sheets/Docs/Drive integration
- OpenAI GPT-4 via AutoGen agents
- Google OAuth 2.0 + JWT authentication

**Frontend (React/TypeScript)**
- Admin portal: Patient management and report generation
- Consumer portal: Parent quiz intake (links to Typeform)
- Vite build system + TailwindCSS

**AI Agents (AutoGen)**
- Triage Agent: Safety assessment
- Parser Agent: Extract structured data
- Lead Investigator Agent: Generate developmental hypotheses
- Resource Agent: Find local autism resources

## Project Structure

```
kindroot/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── routers/           # API route handlers
│   │   │   ├── auth.py        # OAuth endpoints
│   │   │   ├── patients.py    # Patient endpoints
│   │   │   └── reports.py     # Report generation
│   │   ├── services/          # Business logic
│   │   │   ├── auth.py        # JWT & OAuth
│   │   │   ├── google_sheets.py
│   │   │   ├── google_docs.py
│   │   │   └── knowledge_base.py
│   │   └── middleware/        # Auth middleware
│   ├── requirements.txt
│   └── .env                   # Environment variables (gitignored)
├── frontend/                  # React admin frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── contexts/          # AuthContext
│   │   └── pages/            # Page components
│   └── package.json
├── consumer_frontend/         # React consumer frontend (quiz intake)
│   ├── src/
│   │   └── components/
│   └── package.json
├── agents/                    # AutoGen agent implementations
│   └── autogen/
│       └── agents.py          # Triage, Parser, Investigator agents
├── tests/                     # Test files
├── start_local.sh            # Start all dev servers
├── stop_local.sh             # Stop all dev servers
└── README.md
```

## Local Development

### Prerequisites

- Python 3.8+
- Node.js 16+
- Google Cloud Platform account with:
  - Google Sheets API enabled
  - Google Docs API enabled
  - Google Drive API enabled
  - OAuth 2.0 credentials configured
- OpenAI API key

### Quick Start

**Start all servers:**
```bash
./start_local.sh
```

This starts:
- Backend API → http://localhost:8000
- Admin Frontend → http://localhost:3000
- Consumer Frontend → http://localhost:3001

**Stop servers:**
```bash
./stop_local.sh
```

### Manual Setup (First Time)

1. **Backend Setup:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create `.env` file in `backend/` directory:**
   ```bash
   # Required environment variables
   GOOGLE_SHEETS_ID=your_spreadsheet_id
   GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
   OPENAI_API_KEY=your_openai_key
   GOOGLE_CLIENT_ID=your_google_oauth_client_id
   GOOGLE_CLIENT_SECRET=your_google_oauth_secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback
   JWT_SECRET_KEY=generate_random_32char_string
   SESSION_SECRET=generate_random_32char_string
   FRONTEND_URL=http://localhost:3000
   CONSUMER_FRONTEND_URL=http://localhost:3001
   
   # Optional: Archive old reports when generating new ones
   ARCHIVE_FOLDER_ID=your_archive_folder_id
   ```

3. **Place Google credentials:**
   - Download service account credentials from Google Cloud Console
   - Save as `backend/credentials.json`

4. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   
   cd ../consumer_frontend
   npm install
   ```

5. **Run with the startup script:**
   ```bash
   ./start_local.sh
   ```

## How It Works

### Patient Data Flow

1. **Intake**: Parents complete Typeform questionnaire
2. **Storage**: Responses stored in Google Sheets
3. **Processing**: Admin triggers report generation
4. **AI Analysis**: AutoGen agents analyze responses
   - Safety triage (urgent concerns)
   - Structured data extraction
   - Developmental hypotheses
   - Local resource matching
5. **Report**: Generated as Google Doc
6. **Delivery**: Emailed to parent

### AutoGen Agents

Built with [Microsoft AutoGen](https://microsoft.github.io/autogen/) for multi-agent AI workflows:

**Triage Agent (`gpt-4o-mini`)**
- Assesses safety concerns
- Identifies urgent issues
- Categorizes developmental areas

**Parser Agent (`gpt-4o-mini`)**
- Extracts structured patient info
- Normalizes free-text responses
- Creates timeline of milestones

**Lead Investigator Agent (`gpt-4o`)**
- Generates developmental hypotheses
- Cross-references knowledge base
- Prioritizes next steps

**Resource Agent**
- Finds local autism resources by zipcode
- Matches to patient needs

## Development Workflow

### Branch Strategy

- `main` - Production branch (auto-deploys)
- `dev` - Development branch (test features here first)

### Making Changes

```bash
# Work in dev branch
git checkout dev
./start_local.sh

# Make changes, test at http://localhost:3000

# Commit to dev
git add .
git commit -m "Description of changes"
git push origin dev

# When tested and ready:
git checkout main
git merge dev
git push origin main
git checkout dev
```

### Testing Locally

**View logs if something goes wrong:**
```bash
tail -f /tmp/kindroot_backend.log
tail -f /tmp/kindroot_frontend.log
tail -f /tmp/kindroot_consumer.log
```

**Test specific endpoints:**
```bash
# Health check
curl http://localhost:8000/health

# Get patients (requires auth token)
curl http://localhost:8000/api/patients \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Deployment

**Backend**: Deployed on Render (Python)
- Auto-deploys from `main` branch
- Uses `GOOGLE_CREDENTIALS_BASE64` env var (base64 encoded service account)

**Frontends**: Deployed on Vercel
- Auto-deploy from `main` branch
- Admin frontend needs `VITE_API_URL` env var
- Consumer frontend is static (no env vars)

**Google Cloud Setup Required:**
- Enable Google Sheets, Docs, Drive APIs
- Create service account for API access
- Create OAuth 2.0 credentials for user login
- Add redirect URIs for both local and production

## Key Features

**Authentication**
- Google OAuth 2.0 for admin login
- JWT tokens with 24-hour expiration
- Protected API endpoints

**Data Management**
- Google Sheets as database
- One spreadsheet row = one patient
- Columns for raw data, summaries, triage results, hypotheses, resources

**AI Processing**
- Multi-agent workflow using AutoGen
- GPT-4o for complex reasoning (hypotheses)
- GPT-4o-mini for structured extraction (triage, parsing)
- Knowledge base for autism development patterns

**Report Generation**
- Google Docs for formatted reports
- Automatic sections: Safety, Development, Resources, Next Steps
- Stored in shared Google Drive folder
- Email delivery to parents

## Current Status

**Working:**
- ✅ Admin authentication with Google OAuth
- ✅ Patient list from Google Sheets
- ✅ AI-powered triage and analysis
- ✅ Report generation with AutoGen agents
- ✅ Google Docs report creation
- ✅ Email delivery
- ✅ Consumer website with Typeform intake

**Planned:**
- 🚧 Replace Google Sheets with PostgreSQL database
- 🚧 Automated report scheduling
- 🚧 Custom report templates
- 🚧 Admin analytics dashboard

## License

MIT
