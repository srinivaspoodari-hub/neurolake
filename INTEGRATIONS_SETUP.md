# External Integrations Setup Guide

**Date**: 2025-11-09
**Status**: ✅ COMPLETE

---

## Overview

NeuroLake now supports external integrations with:
1. **Google APIs** - Drive, Sheets, Authentication
2. **Groq LLM** - AI-powered SQL generation and chat

All integrations are accessible via `/api/v1/integrations` endpoints.

---

## Google API Integration

### Features
- ✅ OAuth 2.0 authentication
- ✅ List and download Google Drive files
- ✅ Read Google Sheets data
- ✅ Import Sheets directly to NeuroLake tables
- ✅ Auto-import Drive files to catalog

### Setup Instructions

#### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable APIs:
   - Google Drive API
   - Google Sheets API
   - Google OAuth 2.0

#### 2. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Choose **Web application**
4. Add authorized redirect URIs:
   ```
   http://localhost:3000/auth/google/callback
   http://localhost:8000/auth/google/callback
   ```
5. Copy your **Client ID** and **Client Secret**

#### 3. Set Environment Variables

Add to your `.env` file or export:

```bash
# Google API Configuration
export GOOGLE_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

**Docker Compose**: Add to `docker-compose.yml`:
```yaml
environment:
  - GOOGLE_CLIENT_ID=your-client-id
  - GOOGLE_CLIENT_SECRET=your-client-secret
```

#### 4. Verify Integration

```bash
# Check integration status
curl http://localhost:8000/api/v1/integrations/status
```

Should return:
```json
{
  "integrations": {
    "google": {
      "configured": true,
      "status": "operational"
    }
  }
}
```

### Available Endpoints

#### OAuth Authentication
```http
POST /api/v1/integrations/google/auth
Content-Type: application/json

{
  "code": "oauth_authorization_code",
  "redirect_uri": "http://localhost:3000/auth/google/callback"
}
```

#### List Google Drive Files
```http
GET /api/v1/integrations/google/drive/files?access_token=YOUR_TOKEN&max_results=100
```

#### Download and Import Drive File
```http
GET /api/v1/integrations/google/drive/files/{file_id}/download?access_token=YOUR_TOKEN
```

#### Get Google Sheet Data
```http
GET /api/v1/integrations/google/sheets/{spreadsheet_id}?access_token=YOUR_TOKEN&range=Sheet1!A1:Z1000
```

#### Import Sheet to NeuroLake
```http
POST /api/v1/integrations/google/sheets/{spreadsheet_id}/import
Content-Type: application/json

{
  "access_token": "YOUR_TOKEN",
  "table_name": "imported_data",
  "schema": "imports",
  "range": "Sheet1!A1:Z1000"
}
```

---

## Groq LLM Integration

### Features
- ✅ Ultra-fast LLM inference (Groq LPU)
- ✅ Natural language to SQL conversion
- ✅ SQL query explanation
- ✅ Chat completion
- ✅ Multiple model support (Llama 3, Mixtral, Gemma)

### Setup Instructions

#### 1. Get Groq API Key

1. Go to [Groq Console](https://console.groq.com/)
2. Sign up for an account (free tier available)
3. Navigate to **API Keys**
4. Click **Create API Key**
5. Copy your API key

#### 2. Set Environment Variable

Add to your `.env` file or export:

```bash
# Groq API Configuration
export GROQ_API_KEY="gsk_your_api_key_here"
```

**Docker Compose**: Add to `docker-compose.yml`:
```yaml
environment:
  - GROQ_API_KEY=gsk_your_key_here
```

#### 3. Verify Integration

```bash
# Check integration status
curl http://localhost:8000/api/v1/integrations/status
```

Should return:
```json
{
  "integrations": {
    "groq": {
      "configured": true,
      "status": "operational"
    }
  }
}
```

### Available Endpoints

#### Chat Completion
```http
POST /api/v1/integrations/groq/chat
Content-Type: application/json

{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain neural networks."}
  ],
  "model": "llama3-70b-8192",
  "temperature": 0.7,
  "max_tokens": 1024
}
```

#### Generate SQL from Natural Language
```http
POST /api/v1/integrations/groq/sql/generate
Content-Type: application/json

{
  "question": "Show me the top 10 customers by revenue",
  "schema_context": "Table: customers (id, name, revenue, city)",
  "model": "llama3-70b-8192"
}
```

Response:
```json
{
  "question": "Show me the top 10 customers by revenue",
  "sql": "SELECT * FROM customers ORDER BY revenue DESC LIMIT 10",
  "confidence": 0.95,
  "explanation": "Retrieves top 10 customers sorted by revenue"
}
```

#### Explain SQL Query
```http
POST /api/v1/integrations/groq/sql/explain
Content-Type: application/json

{
  "sql": "SELECT * FROM customers ORDER BY revenue DESC LIMIT 10",
  "model": "llama3-70b-8192"
}
```

#### List Available Models
```http
GET /api/v1/integrations/groq/models
```

Response:
```json
{
  "models": [
    {
      "id": "llama3-70b-8192",
      "name": "Llama 3 70B",
      "context_window": 8192,
      "capabilities": ["chat", "completion", "code"]
    },
    {
      "id": "mixtral-8x7b-32768",
      "name": "Mixtral 8x7B",
      "context_window": 32768,
      "capabilities": ["chat", "completion", "multilingual"]
    }
  ]
}
```

---

## Environment Variables Summary

### Required for Google Integration
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Required for Groq Integration
```bash
GROQ_API_KEY=gsk_your_api_key_here
```

### Complete .env File Example
```bash
# NeuroLake Core
DATABASE_URL=postgresql://user:pass@localhost:5432/neurolake
REDIS_URL=redis://localhost:6379
API_PORT=8000

# Google APIs
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Groq LLM
GROQ_API_KEY=gsk_your_api_key_here
```

---

## Frontend Integration

### Using Google API from Frontend

```typescript
import { integrationsService } from '@/services/integrationsService'

// Authenticate
const auth = await integrationsService.googleAuth(code, redirectUri)

// List Drive files
const files = await integrationsService.listDriveFiles(auth.access_token)

// Import Google Sheet
const result = await integrationsService.importGoogleSheet(
  spreadsheetId,
  auth.access_token,
  'my_table',
  'imports'
)
```

### Using Groq API from Frontend

```typescript
import { integrationsService } from '@/services/integrationsService'

// Generate SQL from natural language
const result = await integrationsService.generateSQL(
  "Show me top 10 customers",
  schemaContext
)

console.log(result.sql) // Generated SQL query

// Execute the generated SQL
await queryService.executeQuery({ sql: result.sql })
```

---

## Use Cases

### Google Integration Use Cases

1. **Data Import**: Import Google Sheets directly to NeuroLake tables
2. **Drive Sync**: Automatically sync Drive folders to catalog
3. **Collaboration**: Share NeuroLake query results to Google Sheets
4. **Backup**: Export tables to Google Drive

### Groq Integration Use Cases

1. **Natural Language Queries**: Convert questions to SQL
2. **Query Assistance**: Explain complex SQL queries
3. **SQL Generation**: Auto-generate queries from requirements
4. **Data Insights**: Get AI-powered insights from data

---

## Security Best Practices

### Google API
- ✅ **Never** commit credentials to git
- ✅ Use environment variables only
- ✅ Rotate OAuth tokens regularly
- ✅ Restrict OAuth scopes to minimum required
- ✅ Use HTTPS in production

### Groq API
- ✅ **Never** expose API key in frontend
- ✅ Always call from backend
- ✅ Monitor usage and set limits
- ✅ Rotate API keys periodically

---

## Troubleshooting

### Google Integration Issues

**Error**: "Google API credentials not configured"
```bash
# Check environment variables
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# Restart server after setting
```

**Error**: "Invalid OAuth code"
- OAuth codes expire after 10 minutes
- Generate new code and try again
- Verify redirect URI matches exactly

### Groq Integration Issues

**Error**: "Groq API key not configured"
```bash
# Check environment variable
echo $GROQ_API_KEY

# Should start with 'gsk_'
```

**Error**: "Rate limit exceeded"
- Free tier: 30 requests/minute
- Implement request queuing
- Upgrade to paid tier for higher limits

---

## API Documentation

All integration endpoints are documented in the interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Navigate to **Integrations v1** section for complete documentation.

---

## Testing

### Test Google Integration

```bash
# Test OAuth (with real code from Google)
curl -X POST http://localhost:8000/api/v1/integrations/google/auth \
  -H "Content-Type: application/json" \
  -d '{
    "code": "your_oauth_code",
    "redirect_uri": "http://localhost:3000/auth/google/callback"
  }'

# Test Drive files listing
curl "http://localhost:8000/api/v1/integrations/google/drive/files?access_token=YOUR_TOKEN"
```

### Test Groq Integration

```bash
# Generate SQL
curl -X POST http://localhost:8000/api/v1/integrations/groq/sql/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me top 10 customers by revenue",
    "model": "llama3-70b-8192"
  }'

# Chat completion
curl -X POST http://localhost:8000/api/v1/integrations/groq/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain SQL joins"}
    ],
    "model": "llama3-70b-8192"
  }'
```

---

## Conclusion

Both Google API and Groq integrations are now **fully operational** in NeuroLake. Follow the setup instructions above to configure your API keys and start using these powerful integrations.

**Next Steps**:
1. Set up environment variables
2. Test endpoints using curl or Swagger UI
3. Integrate with frontend applications
4. Build custom workflows using these APIs

**Status**: ✅ READY FOR USE
