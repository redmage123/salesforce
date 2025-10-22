# Research Agent Walkthrough - Real Example

## Example: "Add OAuth Authentication with Google and GitHub"

This walkthrough shows how the Research Agent works in TWO modes:
1. **Autonomous Research** - Agent decides what to research
2. **User-Prompted Research** - User tells agent what to focus on

---

## Task Details

```json
{
  "card_id": "card-20251022160000",
  "title": "Add OAuth authentication with Google and GitHub",
  "description": "Allow users to sign in using their Google or GitHub accounts. Store user profile information (name, email, avatar) after authentication. Maintain user sessions across page reloads.",
  "priority": "high",
  "points": 13,
  "acceptance_criteria": [
    "Users can click 'Sign in with Google' button",
    "Users can click 'Sign in with GitHub' button",
    "After auth, user profile displayed (name, email, avatar)",
    "Sessions persist across page reloads",
    "Users can sign out"
  ],
  "user_research_prompts": [
    "Compare authlib vs python-social-auth vs oauthlib libraries",
    "Research security implications of storing OAuth tokens",
    "Find out if we need to encrypt user data in database"
  ]
}
```

**Key Points:**
- Priority: HIGH → Research will run
- Points: 13 (COMPLEX) → Research will run
- User provided 3 specific research prompts → Research MUST address these

---

## Pipeline Start (T+0:00)

### Orchestrator Analyzes Task

```python
# Workflow Planner analyzes the task
planner = WorkflowPlanner(card)
workflow_plan = planner.create_workflow_plan()

# Analysis Results:
{
  "complexity": "complex",  # 13 points → complex
  "task_type": "feature",
  "parallel_developers": 3,  # Complex task = 3 devs
  "stages": ["architecture", "dependencies", "validation", "arbitration", "integration", "testing"]
}

# Check if research should run
should_run_research(card, workflow_plan)

# Evaluation:
user_research_prompts? YES (3 prompts)  → RUN RESEARCH
complexity == complex? YES              → RUN RESEARCH
priority == high? YES                   → RUN RESEARCH

# Decision: RUN RESEARCH STAGE
```

**Console Output:**
```
[14:00:00] 📊 RESEARCH STAGE ACTIVATED
[14:00:00] ℹ️ Reason: User requested research
[14:00:00] ℹ️ Task: Add OAuth authentication with Google and GitHub
[14:00:00] ℹ️ User-requested topics: 3
[14:00:00] ℹ️   - Compare authlib vs python-social-auth vs oauthlib libraries
[14:00:00] ℹ️   - Research security implications of storing OAuth tokens
[14:00:00] ℹ️   - Find out if we need to encrypt user data in database
```

---

## Research Stage Execution (T+0:01 - T+0:03)

### Step 1: Research Agent Receives Task

**Message from Orchestrator:**
```json
{
  "from_agent": "pipeline-orchestrator",
  "to_agent": "research-agent",
  "message_type": "data_update",
  "card_id": "card-20251022160000",
  "priority": "high",
  "data": {
    "update_type": "research_requested",
    "task": {
      "title": "Add OAuth authentication with Google and GitHub",
      "description": "...",
      "priority": "high",
      "points": 13
    },
    "user_research_prompts": [
      "Compare authlib vs python-social-auth vs oauthlib libraries",
      "Research security implications of storing OAuth tokens",
      "Find out if we need to encrypt user data in database"
    ]
  }
}
```

### Step 2: Autonomous Topic Identification

**Research Agent Analysis:**

```
🔍 Analyzing task: "Add OAuth authentication with Google and GitHub"

Keywords Detected:
- "OAuth" → authentication protocol
- "Google", "GitHub" → multiple OAuth providers
- "sign in" → user authentication
- "sessions" → session management
- "profile information" → user data storage

Technology Decision Points Identified:
1. OAuth Library Selection (multiple options exist)
2. OAuth Flow Type (authorization code vs implicit)
3. Session Storage (where to store sessions?)
4. User Data Storage (how to store profile info?)
5. Security Implementation (token security, encryption)

Security Keywords Found:
- "authentication" → security critical
- "sessions" → security critical
- "profile information" → user data = security concern

Autonomous Research Topics Generated:
1. OAuth library comparison
2. OAuth 2.0 flow types
3. Google OAuth setup and best practices
4. GitHub OAuth setup and best practices
5. Session management strategies
6. User data storage patterns
7. Token security best practices
8. Multi-provider OAuth integration
```

### Step 3: Research Execution

#### User-Prompted Research (Priority 1)

**User Prompt 1:** "Compare authlib vs python-social-auth vs oauthlib libraries"

**Research Conducted:**
- Web search: "authlib vs python-social-auth vs oauthlib comparison"
- GitHub stars and maintenance status
- Documentation quality check
- Community adoption

**Findings:**
```markdown
## User-Requested Research

### 1. OAuth Library Comparison: authlib vs python-social-auth vs oauthlib

**authlib:**
- GitHub: 4.3k stars
- Maintained: ✅ Active (last commit: 3 days ago)
- Documentation: ✅ Excellent (comprehensive guides)
- Features: OAuth 1.0, OAuth 2.0, OpenID Connect
- Python versions: 3.7+
- Multi-provider: ✅ Built-in support for Google, GitHub, etc.
- Pros:
  - Modern, actively maintained
  - Excellent documentation
  - Supports latest OAuth specs
  - Clean API
- Cons:
  - Smaller community than python-social-auth

**python-social-auth:**
- GitHub: 2.8k stars
- Maintained: ⚠️ Less active (last commit: 6 months ago)
- Documentation: ⚠️ Moderate
- Features: 50+ providers built-in
- Python versions: 2.7, 3.4+
- Multi-provider: ✅ Excellent (50+ providers)
- Pros:
  - Many providers out-of-the-box
  - Large community
- Cons:
  - Less actively maintained
  - Older codebase
  - Python 2.7 legacy support

**oauthlib:**
- GitHub: 2.7k stars
- Maintained: ✅ Active
- Documentation: ⚠️ Technical (low-level)
- Features: OAuth 1.0, OAuth 2.0 (low-level)
- Python versions: 3.6+
- Multi-provider: ❌ Low-level library (you build provider support)
- Pros:
  - Very flexible
  - Used by requests-oauthlib
- Cons:
  - Low-level (more code needed)
  - Steeper learning curve

**RECOMMENDATION: authlib**

**Reasoning:**
1. Most actively maintained (commits within days)
2. Best documentation for quick implementation
3. Built-in multi-provider support (Google + GitHub)
4. Modern codebase (no Python 2.7 legacy)
5. Clean API reduces development time

**Trade-off:** Smaller community than python-social-auth, but better
maintenance and documentation outweigh this.

**Confidence:** HIGH (based on GitHub metrics + documentation review)
```

**User Prompt 2:** "Research security implications of storing OAuth tokens"

**Research Conducted:**
- OAuth 2.0 security best practices (OWASP)
- Token storage recommendations
- Token encryption standards
- NIST guidelines

**Findings:**
```markdown
### 2. Security Implications of Storing OAuth Tokens

**Critical Findings:**

**Access Tokens:**
- ⚠️ **NEVER store in localStorage** (vulnerable to XSS attacks)
- ⚠️ **NEVER store in cookies without HttpOnly flag**
- ✅ **DO store in server-side sessions** (safest)
- ⚠️ **DO encrypt if storing in database** (required!)

**Refresh Tokens:**
- ⚠️ **CRITICAL**: More sensitive than access tokens
- ✅ **MUST encrypt in database** (non-negotiable)
- ✅ **MUST use HTTPS only**
- ✅ **SHOULD implement token rotation** (refresh token changes on use)

**Attack Vectors:**
1. **XSS (Cross-Site Scripting)**
   - Risk: If tokens in localStorage, XSS can steal them
   - Mitigation: Server-side sessions only

2. **CSRF (Cross-Site Request Forgery)**
   - Risk: Attacker tricks user into making requests
   - Mitigation: CSRF tokens + SameSite cookies

3. **Token Leakage**
   - Risk: Tokens exposed in logs, URLs, or error messages
   - Mitigation: Never log tokens, never pass in URL

4. **Database Breach**
   - Risk: If database compromised, unencrypted tokens stolen
   - Mitigation: Encrypt tokens at rest (AES-256)

**Security Recommendations:**

1. **Access Tokens (short-lived, 1 hour):**
   ```python
   # Store in encrypted server-side session
   session['access_token'] = encrypt_token(access_token)
   ```

2. **Refresh Tokens (long-lived, 30 days):**
   ```python
   # Encrypt before storing in database
   encrypted_token = AES_encrypt(refresh_token, secret_key)
   db.store(user_id, encrypted_token)
   ```

3. **Session Security:**
   - Use secure, HttpOnly cookies
   - Set SameSite=Lax or Strict
   - Short session timeout (30 min inactive)

4. **Token Transmission:**
   - HTTPS only (enforce!)
   - Never in URL parameters
   - Never in logs

**CRITICAL ACTION REQUIRED:**
- Implement token encryption in database
- Use server-side sessions (not localStorage)
- Enable HTTPS in production

**Compliance:**
- GDPR: Token encryption = good practice
- SOC 2: Token encryption = requirement
- PCI DSS: Not applicable (unless payment data)

**Confidence:** HIGH (OWASP + NIST guidelines)
```

**User Prompt 3:** "Find out if we need to encrypt user data in database"

**Research Conducted:**
- GDPR requirements for user data
- Database encryption best practices
- Field-level vs full-database encryption

**Findings:**
```markdown
### 3. User Data Encryption in Database

**User Data in This Task:**
- Name (public info)
- Email (semi-sensitive)
- Avatar URL (public info)
- OAuth tokens (highly sensitive)

**Encryption Requirements:**

**What MUST be encrypted:**
1. ✅ **OAuth access tokens** (CRITICAL)
2. ✅ **OAuth refresh tokens** (CRITICAL)
3. ⚠️ **Email addresses** (RECOMMENDED)

**What CAN remain unencrypted:**
4. ❌ **Names** (public info)
5. ❌ **Avatar URLs** (public info)

**Encryption Approaches:**

**Option A: Field-Level Encryption (RECOMMENDED)**
```python
# Encrypt sensitive fields only
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # Plain text
    email = db.Column(db.LargeBinary)  # Encrypted
    avatar_url = db.Column(db.String(200))  # Plain text
    access_token = db.Column(db.LargeBinary)  # Encrypted
    refresh_token = db.Column(db.LargeBinary)  # Encrypted

def encrypt_field(value, key):
    return AES.encrypt(value, key)

def decrypt_field(encrypted_value, key):
    return AES.decrypt(encrypted_value, key)
```

**Option B: Full Database Encryption**
- Pros: Everything encrypted
- Cons: Performance overhead, harder to search/index
- Use case: Highly regulated industries

**Recommendation for This Task: Field-Level Encryption**

**Encrypt:**
- access_token (required)
- refresh_token (required)
- email (recommended for privacy)

**Don't Encrypt:**
- name (no benefit, public info)
- avatar_url (public URL anyway)

**Encryption Library:**
- Use `cryptography` library (Python)
- Algorithm: AES-256-GCM (authenticated encryption)
- Key management: Environment variable (never commit!)

**GDPR Compliance:**
- Encryption = "appropriate technical measures" (GDPR Article 32)
- Not strictly required for all data
- Required for "sensitive" data (tokens = sensitive)

**Answer:** **YES, encrypt tokens and email. No need for name/avatar.**

**Confidence:** HIGH (GDPR + security best practices)
```

#### Autonomous Research (Supplements User Prompts)

**Topic 1: OAuth 2.0 Flow Types**

**Research:**
```markdown
## Autonomous Research: OAuth 2.0 Flow Types

**Authorization Code Flow (Server-Side):**
- ✅ Most secure
- ✅ Refresh tokens supported
- ✅ Recommended for server apps
- Flow: User → Auth Server → Callback with code → Exchange code for token

**Implicit Flow (Client-Side - DEPRECATED):**
- ❌ Less secure (tokens in URL)
- ❌ No refresh tokens
- ❌ Deprecated by OAuth 2.1
- Use case: SPAs (but use PKCE instead)

**PKCE (Proof Key for Code Exchange):**
- ✅ Secure for mobile/SPA
- ✅ Prevents authorization code interception
- ✅ Recommended for public clients

**RECOMMENDATION: Authorization Code Flow**

For server-side Flask app, use standard Authorization Code Flow.
Google and GitHub both support this flow.
```

**Topic 2: Session Management**

**Research:**
```markdown
## Autonomous Research: Session Management

**Flask-Login vs Flask-Session vs Custom:**

**Flask-Login:**
- Purpose: User session management
- ✅ Integrates with Flask
- ✅ "Remember me" functionality
- ✅ Login decorators (@login_required)
- Use case: Perfect for OAuth

**Flask-Session:**
- Purpose: Server-side session storage
- ✅ Store sessions in Redis/database
- ✅ More secure than client-side
- Use case: Large session data

**Recommendation:**
- Use Flask-Login for user management
- Store OAuth tokens in encrypted database
- Use Flask's built-in session for temporary data
```

### Step 4: Generate Research Report

**Research Report Created:** `/tmp/research/research_report_card-20251022160000.md`

**Executive Summary:**
```markdown
# Research Report: Add OAuth authentication with Google and GitHub

**Generated:** 2025-10-22 14:00:03 UTC
**Card ID:** card-20251022160000
**Priority:** HIGH
**Complexity:** 13 points (COMPLEX)
**Research Mode:** User-Prompted + Autonomous

---

## Executive Summary

**Primary Recommendation:** Use authlib + Flask-Login + field-level encryption

**Critical Findings:**
1. authlib is best OAuth library (actively maintained, great docs)
2. MUST encrypt OAuth tokens in database (security requirement)
3. MUST encrypt email addresses (GDPR best practice)
4. Use Authorization Code Flow (most secure)
5. Never store tokens in localStorage (XSS vulnerability)

**Critical Actions:**
1. Install authlib library
2. Implement AES-256 encryption for tokens and email
3. Use server-side sessions only
4. Enable HTTPS in production
5. Implement token rotation for refresh tokens

**Security Risk Level:** HIGH (OAuth tokens + user data)
**GDPR Compliance:** Encryption required for tokens
**Estimated Implementation:** 2-3 days for 3 developers
```

### Step 5: Send to Architecture Agent

**Message Sent:**
```json
{
  "from_agent": "research-agent",
  "to_agent": "architecture-agent",
  "message_type": "data_update",
  "priority": "high",
  "data": {
    "update_type": "research_complete",
    "research_report_file": "/tmp/research/research_report_card-20251022160000.md",
    "executive_summary": {
      "primary_recommendation": "authlib + Flask-Login + field-level encryption",
      "critical_findings": [
        "authlib is best OAuth library (most maintained)",
        "MUST encrypt tokens in database",
        "Never store tokens in localStorage",
        "Use Authorization Code Flow"
      ],
      "user_prompts_answered": 3,
      "autonomous_topics_researched": 4,
      "confidence_level": "HIGH"
    },
    "recommendations": {
      "oauth_library": "authlib",
      "session_library": "Flask-Login",
      "encryption": "AES-256-GCM",
      "oauth_flow": "authorization_code",
      "token_storage": "encrypted_database"
    }
  }
}
```

**Shared State Updated:**
```json
{
  "card_id": "card-20251022160000",
  "shared_data": {
    "current_stage": "research_complete",
    "research_report": "/tmp/research/research_report_card-20251022160000.md",
    "research_status": "COMPLETE",
    "user_research_prompts_count": 3,
    "recommendations": {
      "oauth_library": "authlib",
      "encryption_required": true
    }
  }
}
```

**Console Output:**
```
[14:00:03] ✅ Research complete - report at /tmp/research/research_report_card-20251022160000.md
[14:00:03] ℹ️ User prompts answered: 3/3
[14:00:03] ℹ️ Autonomous topics researched: 4
[14:00:03] ℹ️ Confidence level: HIGH
```

---

## Architecture Stage Uses Research (T+0:04)

**Architecture Agent reads research report from shared state:**

```python
# Architecture Agent receives research message
state = messenger.get_shared_state(card_id="card-20251022160000")
research_report_path = state["shared_data"]["research_report"]

# Reads research report
with open(research_report_path) as f:
    research = f.read()

# Uses research recommendations in ADR
recommendations = state["shared_data"]["recommendations"]
# {
#   "oauth_library": "authlib",
#   "session_library": "Flask-Login",
#   "encryption": "AES-256-GCM"
# }
```

**ADR Created (informed by research):**

```markdown
# ADR-004: OAuth Authentication with Google and GitHub

**Status:** Accepted
**Date:** 2025-10-22
**Research Informed:** YES (/tmp/research/research_report_card-20251022160000.md)

## Decision

### OAuth Library: authlib

**Chosen because** (from research):
- Most actively maintained (commits within last week)
- Excellent documentation
- Built-in Google + GitHub support
- Modern codebase (Python 3.7+)

**Research showed:**
- authlib: 4.3k stars, active maintenance
- python-social-auth: less active, legacy code
- oauthlib: too low-level for our needs

### OAuth Flow: Authorization Code Flow

**Chosen because** (from research):
- Most secure flow
- Supports refresh tokens
- Recommended by OWASP
- Both Google and GitHub support it

### Session Management: Flask-Login

**Chosen because** (from research):
- Integrates with Flask
- Provides @login_required decorator
- "Remember me" functionality
- Industry standard

### Security Implementation:

**Token Encryption (REQUIRED by research):**
```python
# Encrypt tokens before storing
from cryptography.fernet import Fernet

access_token_encrypted = encrypt_token(access_token)
refresh_token_encrypted = encrypt_token(refresh_token)
```

**User Data Encryption (research recommendation):**
- Encrypt: access_token, refresh_token, email
- Plain: name, avatar_url

**Session Security (research requirement):**
- Server-side sessions only
- HttpOnly cookies
- SameSite=Lax
- HTTPS only in production

## Research Citations

All technical decisions above are backed by research findings:
- OAuth library comparison (user request #1)
- Token security implications (user request #2)
- Data encryption requirements (user request #3)
- OAuth flow types (autonomous research)
- Session management (autonomous research)

**Research Confidence:** HIGH
**Research Report:** /tmp/research/research_report_card-20251022160000.md
```

---

## Summary: How Research Agent Helped

### Without Research Agent:
❌ Architecture Agent guesses "let's use python-social-auth" (older, less maintained)
❌ Doesn't encrypt tokens (security vulnerability!)
❌ Stores tokens in localStorage (XSS attack vector!)
❌ No clear security implementation
❌ Developers have to research during implementation (slows down)

### With Research Agent:
✅ Data-driven choice: authlib (most maintained, best docs)
✅ Critical security finding: MUST encrypt tokens
✅ Critical security finding: Never use localStorage
✅ Clear security implementation guide
✅ Developers get research upfront (faster implementation)
✅ User's specific questions answered (authlib vs others, encryption needs)

---

## Research Impact on Pipeline

**Before Research:**
```
Task → Architecture (guesses) → 3 Developers (research individually) → Quality issues
```

**After Research:**
```
Task → Research (data) → Architecture (informed) → 3 Developers (use research) → Higher quality
```

**Time Savings:**
- Research Agent: 2 minutes
- Without it: Each of 3 developers researches = 15 minutes × 3 = 45 minutes
- **Net savings: 43 minutes + better quality**

**Quality Improvements:**
- Security vulnerabilities caught BEFORE coding
- Best library chosen (not just first Google result)
- Critical requirements identified (encryption)
- User questions answered with citations

---

## Key Features Demonstrated

### 1. Autonomous Topic Identification ✅
Research Agent analyzed the task and identified:
- OAuth library selection
- OAuth flow types
- Session management
- Security implications

**Without user telling it!**

### 2. User-Prompted Research ✅
Research Agent prioritized and answered ALL 3 user prompts:
1. Library comparison (with metrics!)
2. Token security (with specific recommendations)
3. Encryption needs (with code examples)

### 3. Data-Driven Recommendations ✅
Every recommendation backed by data:
- GitHub stars
- Maintenance status
- OWASP guidelines
- GDPR requirements

### 4. Communication Protocol ✅
Research Agent:
- Sent findings to Architecture Agent
- Updated shared state
- Used high-priority messaging
- Provided executive summary

### 5. Influence on Architecture ✅
Architecture Agent cited research in ADR:
- "Chosen because (from research): ..."
- "Research showed: ..."
- Included research report path for traceability

---

## Research Agent Value Proposition

**Cost:** 2-3 minutes research time
**Value:**
- ✅ Prevents security vulnerabilities
- ✅ Data-driven technology choices
- ✅ Answers user questions specifically
- ✅ Saves developer time (no individual research)
- ✅ Higher quality architecture decisions
- ✅ Better code quality (informed by best practices)

**ROI:** Time saved (45 min) + quality improvement = **VERY HIGH VALUE**

This is why the Research Agent is a critical addition to the pipeline! 🔍
