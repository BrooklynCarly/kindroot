# Google OAuth Setup Guide

This guide will walk you through setting up Google OAuth authentication for the KindRoot application.

## Prerequisites

- Google Cloud Platform account
- Access to Google Cloud Console
- Backend and frontend applications set up

## Step 1: Create Google OAuth Credentials

### 1.1 Go to Google Cloud Console
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)

### 1.2 Enable Google+ API
1. Navigate to **APIs & Services** > **Library**
2. Search for "Google+ API"
3. Click **Enable**

### 1.3 Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **Internal** (if using Google Workspace) or **External**
3. Fill in the required fields:
   - **App name**: KindRoot Patient Reports
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Click **Save and Continue**
5. On the **Scopes** page, click **Add or Remove Scopes**
6. Add these scopes:
   - `openid`
   - `email`
   - `profile`
7. Click **Save and Continue**
8. Review and click **Back to Dashboard**

### 1.4 Create OAuth Client ID
1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Choose **Web application**
4. Configure:
   - **Name**: KindRoot Web Client
   - **Authorized JavaScript origins**:
     - `http://localhost:8000` (development)
     - Your production backend URL (when deploying)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/api/auth/callback` (development)
     - Your production backend URL + `/api/auth/callback` (when deploying)
5. Click **Create**
6. **Save the Client ID and Client Secret** - you'll need these!

## Step 2: Configure Backend Environment

### 2.1 Update `.env` File
Edit `backend/.env` and add your OAuth credentials:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback

# JWT Configuration (generate random strings)
JWT_SECRET_KEY=your_random_secret_key_here
SESSION_SECRET=your_session_secret_here

# Optional: Restrict to your organization's domain
ALLOWED_EMAIL_DOMAIN=yourcompany.com
```

### 2.2 Generate Secret Keys
You can generate secure random keys using Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run this twice to generate both `JWT_SECRET_KEY` and `SESSION_SECRET`.

## Step 3: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 4: Test Authentication

### 4.1 Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 4.2 Start Frontend
```bash
cd frontend
npm run dev
```

### 4.3 Test Login Flow
1. Open http://localhost:3000
2. You should see the login page
3. Click "Sign in with Google"
4. Complete Google OAuth flow
5. You should be redirected back and see the patient list

## Step 5: Verify Authentication

### Check Auth Status
Visit http://localhost:8000/api/auth/status to verify OAuth is configured:

```json
{
  "oauth_configured": true,
  "google_client_id": "your_client_id..."
}
```

### Test Protected Endpoint
Try accessing a protected endpoint without authentication:

```bash
curl http://localhost:8000/api/patients
```

You should get a 401 Unauthorized response.

## Security Best Practices

### For Development
- Use `http://localhost` URLs
- Keep `.env` file out of version control (already in `.gitignore`)
- Don't share your Client Secret

### For Production
1. **Update Authorized Origins and Redirect URIs**:
   - Add your production domain to Google OAuth settings
   - Update `GOOGLE_REDIRECT_URI` in production `.env`

2. **Use HTTPS**:
   - Always use HTTPS in production
   - Update CORS settings in `backend/app/main.py`

3. **Restrict Email Domain** (Recommended):
   - Set `ALLOWED_EMAIL_DOMAIN` to your organization's domain
   - This ensures only authorized users can access the system

4. **Rotate Secrets**:
   - Generate new `JWT_SECRET_KEY` and `SESSION_SECRET` for production
   - Never use development secrets in production

5. **Enable Additional Security**:
   - Consider adding rate limiting
   - Enable CSRF protection
   - Set up monitoring and logging

## Troubleshooting

### "OAuth not configured" Error
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`
- Restart the backend server after updating `.env`

### "Redirect URI mismatch" Error
- Check that the redirect URI in Google Cloud Console matches exactly
- Ensure you're using the correct protocol (http vs https)
- Verify the port number matches

### "Access denied" Error
- Check if `ALLOWED_EMAIL_DOMAIN` is set and matches your email domain
- Verify your email is authorized in Google OAuth consent screen (if using External)

### Token Expired
- Tokens expire after 24 hours by default
- Users will need to log in again
- Adjust `ACCESS_TOKEN_EXPIRE_MINUTES` in `backend/app/services/auth.py` if needed

## Domain Restriction (Optional but Recommended)

To restrict access to only users from your organization:

1. Set `ALLOWED_EMAIL_DOMAIN` in `.env`:
   ```bash
   ALLOWED_EMAIL_DOMAIN=yourcompany.com
   ```

2. Only users with `@yourcompany.com` emails will be able to log in

3. For multiple domains, you'll need to modify the validation logic in `backend/app/services/auth.py`

## Next Steps

Once authentication is working:
1. Test all protected endpoints
2. Verify token refresh works correctly
3. Test logout functionality
4. Prepare for production deployment
5. Set up monitoring and logging
6. Consider adding role-based access control (RBAC) if needed
