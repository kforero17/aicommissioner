# Security Guidelines

## Critical: Immediate Actions Required

### 1. Regenerate All Credentials

The following credentials MUST be regenerated immediately:

#### Yahoo OAuth Credentials
1. Go to [Yahoo Developer Console](https://developer.yahoo.com/apps/)
2. Delete the current app or create a new one
3. Generate new Client ID and Client Secret
4. Update `.env` file:
   ```bash
   YAHOO_CLIENT_ID=your_new_client_id
   YAHOO_CLIENT_SECRET=your_new_client_secret
   ```

#### JWT Secret Key
Generate a new secure random secret key:
```bash
openssl rand -hex 32
```
Update `.env`:
```bash
SECRET_KEY=<paste_generated_key_here>
```

#### Encryption Key (for OAuth tokens at rest)
Generate a Fernet encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Update `.env`:
```bash
ENCRYPTION_KEY=<paste_generated_key_here>
```

#### Database URL
Ensure your database URL uses strong credentials:
```bash
DATABASE_URL=postgresql+asyncpg://<user>:<strong_password>@<host>/<database>
```

### 2. Update .env File

Your `.env` file should contain (with your actual values):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost/aicommissioner

# Redis
REDIS_URL=redis://localhost:6379

# Yahoo OAuth
YAHOO_CLIENT_ID=<your_yahoo_client_id>
YAHOO_CLIENT_SECRET=<your_yahoo_client_secret>
YAHOO_REDIRECT_URI=https://yourdomain.com/auth/yahoo/callback

# Security (REQUIRED)
SECRET_KEY=<64_character_hex_string>
ENCRYPTION_KEY=<fernet_key_from_above>

# AI Services
OPENAI_API_KEY=<your_openai_key>
ANTHROPIC_API_KEY=<your_anthropic_key>

# GroupMe
GROUPME_ACCESS_TOKEN=<your_groupme_token>

# Email/SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<your_email>
SMTP_PASSWORD=<your_app_password>
SMTP_FROM_EMAIL=<your_email>

# Application
DEBUG=false  # NEVER true in production
HOST=0.0.0.0
PORT=8000
FRONTEND_URL=https://yourdomain.com

# Timezone
DEFAULT_TIMEZONE=America/Chicago
```

### 3. Remove Sensitive Files from Git History

If you've already committed sensitive files, remove them from git history:

```bash
# Install BFG Repo-Cleaner
brew install bfg  # macOS
# or download from: https://rtyley.github.io/bfg-repo-cleaner/

# Remove .env file from history
bfg --delete-files .env

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (WARNING: destructive)
git push --force
```

Alternatively, if you have sensitive data in commits, consider creating a fresh repository.

### 4. Verify .gitignore

Ensure these files are in `.gitignore`:

```
.env
.env.local
.env.production
.env.staging
cert.pem
key.pem
*.pem
cookies.txt
*.crt
*.key
```

---

## Security Features Implemented

### ✅ Phase 1 Complete

1. **Sensitive Files Protected**
   - SSL certificates, keys, and cookies excluded from git
   - Environment variables properly gitignored

2. **SSL Verification Enabled**
   - Removed all `verify=False` from production code
   - Debug files moved to `dev_tools/` directory

3. **Strong JWT Secrets Required**
   - No default values for `SECRET_KEY`
   - Application will fail to start without proper configuration
   - Algorithm hardcoded to HS256 (not configurable)

4. **OAuth Token Encryption**
   - All OAuth tokens encrypted at rest using Fernet
   - Encryption/decryption transparent via SQLAlchemy hybrid properties
   - See `utilities/encryption.py` and `models/user.py`

5. **HTTP-Only Secure Cookies**
   - JWT tokens stored in HTTP-only cookies
   - No token exposure in URLs or localStorage
   - Cookies marked secure in production
   - SameSite=lax protection

6. **CORS Properly Configured**
   - No wildcard origins
   - Specific allowed origins even in development
   - Credentials enabled for cookie support

7. **Frontend Security**
   - Removed localStorage token access
   - All API calls use `credentials: 'include'`
   - Cookies automatically sent with requests

---

## Deployment Checklist

Before deploying to production:

- [ ] Regenerated all credentials (Yahoo, JWT, encryption keys)
- [ ] Updated `.env` with production values
- [ ] Set `DEBUG=false` in production environment
- [ ] Verified `.gitignore` excludes all sensitive files
- [ ] Removed sensitive files from git history (if committed)
- [ ] Updated `FRONTEND_URL` to production domain
- [ ] Updated `YAHOO_REDIRECT_URI` to production callback URL
- [ ] Configured HTTPS/SSL certificates for production
- [ ] Set up proper database with strong password
- [ ] Tested OAuth flow end-to-end
- [ ] Verified cookies work with HTTPS

---

## Additional Security Recommendations

### For Phase 2 (High Priority)

1. **Rate Limiting**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)

   @router.post("/auth/yahoo/login")
   @limiter.limit("5/minute")
   async def yahoo_login(...):
   ```

2. **Token Revocation**
   - Implement Redis-based token blacklist
   - Store revoked tokens with expiration

3. **CSRF Protection**
   - Add CSRF tokens for state-changing operations
   - Use `fastapi-csrf-protect` library

4. **Remove Debug Endpoints**
   - Remove `/auth/yahoo/debug` in production
   - Or protect with admin-only authentication

5. **Input Validation**
   - Add Pydantic validators for league IDs
   - Sanitize all user inputs

### For Phase 3 (Production Hardening)

1. **Logging & Monitoring**
   - Set up structured logging (structlog)
   - Add Sentry for error tracking
   - Monitor failed authentication attempts

2. **Security Headers**
   ```python
   from fastapi.middleware.trustedhost import TrustedHostMiddleware
   from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

   app.add_middleware(HTTPSRedirectMiddleware)
   app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com"])
   ```

3. **Database Migrations**
   - Set up Alembic properly
   - Never use `create_all()` in production

4. **Comprehensive Testing**
   - Unit tests for auth flows
   - Integration tests for API endpoints
   - Security tests (penetration testing)

---

## Security Incident Response

If credentials are compromised:

1. **Immediately** regenerate all affected credentials
2. Revoke all active sessions (clear Redis, rotate keys)
3. Force all users to re-authenticate
4. Review access logs for suspicious activity
5. Notify affected users if data was accessed
6. Document the incident and mitigation steps

---

## Questions?

For security concerns, contact the development team immediately.

**Do not commit any secrets to git, ever.**
