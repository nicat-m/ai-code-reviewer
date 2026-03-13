# 🤖 AI Code Review

Automated AI-powered code review service for GitLab merge requests. Analyzes code changes for security vulnerabilities, logic bugs, logging risks, and code quality issues using OpenAI or local Ollama models.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [How It Works](#-how-it-works)
- [Features](#-features)
- [Local Setup](#-local-setup)
  - [Ollama Installation](#-ollama-installation-guide)
- [Deployment](#-deployment)
- [API Documentation](#-api-documentation)
- [Configuration](#-configuration)

---

## 📖 Overview

This service automatically reviews code changes in GitLab merge requests using AI models. When a merge request is opened, reopened, or updated, the service:

1. Fetches the code changes (diff) from GitLab
2. Analyzes them using AI (OpenAI GPT or Ollama)
3. Posts detailed review comments back to the merge request
4. Adds an "AI-reviewed" label

**Supports two AI backends:**

- **OpenAI**: Cloud-based GPT models (requires API key)
- **Ollama**: Local models (self-hosted, free)

---

## ⚙️ How It Works

### Architecture Flow

```
GitLab MR Event
    ↓
Webhook Endpoint (/webhook)
    ↓
Background Task Processor
    ↓
Fetch MR Diff ← GitLab API
    ↓
Filter Files (Java, Python, JS, TS, XML, YAML)
    ↓
Chunk Large Diffs (5000 chars per chunk)
    ↓
Analyze with AI Model
    ↓
Post Comments to MR ← GitLab API
    ↓
Add "AI-reviewed" Label
```

### Review Criteria

The AI reviewer checks for:

- **🔐 Security Issues**: SQL injection risks, auth errors, validation problems
- **🧠 Logic Bugs**: Logic errors, risky patterns, syntax issues
- **🪵 Logging Risks**: Excessive logging, sensitive data exposure, debug logs in production
- **🎯 Code Quality**: Best practices, maintainability, performance

---

## ✨ Features

✅ Automatic code review on merge requests  
✅ Supports multiple programming languages (Java, Python, JavaScript, TypeScript, XML, YAML)  
✅ Two AI backends (OpenAI + Ollama)  
✅ Chunks large diffs for accurate analysis  
✅ Prevents duplicate reviews  
✅ Background task processing  
✅ Kubernetes-ready deployment

---

## 🚀 Local Setup

### Prerequisites

- Python 3.11+
- pip
- GitLab account with API token
- OpenAI API key OR Ollama instance

### 🦙 Ollama Installation Guide

If you want to use **local AI models** with Ollama (free, self-hosted):

#### macOS

```bash
# Method 1: Using Homebrew (recommended)
brew install ollama

# Method 2: Direct download
# Download from https://ollama.ai/download
# Or use curl
curl https://ollama.ai/install.sh | sh
```

#### Linux (Ubuntu/Debian)

```bash
# Install
curl https://ollama.ai/install.sh | sh

# Start service
sudo systemctl start ollama
sudo systemctl enable ollama  # Auto-start on boot
```

#### Windows

```bash
# Download installer from https://ollama.ai/download/windows
# Or use Chocolatey
choco install ollama
```

#### Docker

```bash
# Run Ollama in container
docker run -d -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama
```

#### Verify Installation

```bash
ollama --version
# Start Ollama service (if not auto-running)
ollama serve
```

#### Pull Models

Pull the code review models:

```bash
# Recommended for code review
ollama pull deepseek-coder:6.7b

# Or other models
ollama pull mistral
ollama pull neural-chat
ollama pull codellama
```

List available models:

```bash
ollama list
```

#### Test Ollama API

```bash
# Check if Ollama API is running
curl http://localhost:11434/api/tags

# Test a simple request
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-coder:6.7b",
    "prompt": "write hello world in python",
    "stream": false
  }'
```

---

### Installation

1. **Clone the repository**

```bash
git clone <repo-url>
cd ai-code-review
```

2. **Create virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies**

```bash
pip install -r src/requirements.txt
```

4. **Create .env file**

**For OpenAI:**

```bash
export GITLAB_URL="https://gitlab.e-taxes.gov.az"
export GITLAB_TOKEN="your-gitlab-token"
export OPENAI_API_KEY="your-openai-api-key"
export AI_MODEL="gpt-5.2" 
```

**For Ollama:**

```bash
export GITLAB_URL="https://gitlab.e-taxes.gov.az"
export GITLAB_TOKEN="your-gitlab-token"
export OLLAMA_URL="http://localhost:11434/api/generate"
export OLLAMA_MODEL="deepseek-coder:6.7b"  # or other Ollama model
```

5. **Run the service**

**OpenAI version:**

```bash
cd src
python gitlab_openai.py
```

**Ollama version:**

```bash
cd src
python gitlab_ollama.py
```

The service starts on `http://localhost:5000`

6. **Test locally**

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"object_kind": "merge_request", "object_attributes": {"action": "open"}}'
```

---

## 📦 Deployment

### Docker

#### Building Images

The Dockerfile supports both OpenAI and Ollama backends using build arguments.

**For OpenAI (default):**

```bash
docker build -t ai-code-review:openai ./src
```

**For Ollama:**

```bash
docker build --build-arg APP_MODULE=gitlab_ollama -t ai-code-review:ollama ./src
```

#### Running Containers

**OpenAI version:**

```bash
docker run -p 5000:5000 \
  -e GITLAB_URL="https://gitlab.e-taxes.gov.az" \
  -e GITLAB_TOKEN="your-token" \
  -e OPENAI_API_KEY="your-key" \
  ai-code-review:openai
```

**Ollama version (with local Ollama service):**

```bash
docker run -p 5000:5000 \
  -e GITLAB_URL="https://gitlab.e-taxes.gov.az" \
  -e GITLAB_TOKEN="your-token" \
  -e OLLAMA_URL="http://host.docker.internal:11434/api/generate" \
  -e OLLAMA_MODEL="deepseek-coder:6.7b" \
  ai-code-review:ollama
```

> **Note:** Use `host.docker.internal` (Docker Desktop) or actual host IP to reach local Ollama from container.

### Kubernetes

Use the provided manifests:

```bash
# Deploy to cluster
kubectl apply -f k8s/

# Check deployment
kubectl get pods -l app=ai-code-review
kubectl logs -f deployment/ai-code-review
```

**k8s/Deployment.yaml** includes:

- Resource limits (CPU: 500m, Memory: 512Mi)
- Health checks (readiness/liveness probes)
- Security context (non-root user)
- Environment variables from ConfigMap

**k8s/Ingress.yaml** provides:

- Ingress routing
- SSL termination
- Webhook endpoint exposure

### Configuration for Kubernetes

Create a secret for sensitive data:

```bash
kubectl create secret generic ai-code-review-secrets \
  --from-literal=GITLAB_TOKEN=your-token \
  --from-literal=OPENAI_API_KEY=your-key \
  --from-literal=AI_MODEL=gpt.5.2 \
  --from-literal=GITLAB_URL=gitlab-url \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Setting up GitLab Webhook

1. Go to **GitLab Project → Settings → Integrations → Webhooks**
2. Add webhook URL: `https://your-domain.com/webhook`
3. Trigger events: **Merge request events**
4. Secret token (optional): Add random string for security

---

## 📡 API Documentation

### Webhook Endpoint

**POST** `/webhook`

Receives GitLab merge request events and triggers automated code review.

#### Request Headers

```
Content-Type: application/json
X-Gitlab-Token: <secret-token> (optional)
```

#### Request Body (GitLab webhook payload)

```json
{
  "object_kind": "merge_request",
  "object_attributes": {
    "iid": 123,
    "action": "open|reopen|update"
  },
  "project": {
    "id": 456
  }
}
```

#### Triggering Actions

Review runs automatically when:

- MR is **opened** (`action: "open"`)
- MR is **reopened** (`action: "reopen"`)
- MR is **updated** with new commits (`action: "update"`)

#### Response

```json
{
  "status": "AI review started"
}
```

or

```json
{
  "status": "ignored"
}
```

#### Response Codes

- `200 OK` - Event processed or ignored
- `400 Bad Request` - Invalid webhook format
- `500 Internal Server Error` - Processing error

### Example Webhook Events

**When MR is opened:**

```json
{
  "object_kind": "merge_request",
  "action": "open",
  "object_attributes": {
    "iid": 1,
    "action": "open",
    "target_branch": "main",
    "source_branch": "feature/new-api"
  },
  "project": {
    "id": 123,
    "name": "my-project"
  }
}
```

### Review Comment Format

The AI posts comments in this format:

```markdown
🤖 **AI Code Review**
Model: `gpt-5.2`

🔐 **Security Issues:**

- SQL injection risk in query building
- Missing input validation on user_id parameter

🧠 **Logic Issues:**

- Loop index not incremented, potential infinite loop
- Unreachable code after return statement

🪵 **Logging Risks:**

- Sensitive data (password) logged on line 45
- Debug log level in production code
```

If no issues found:

```markdown
🤖 **AI Code Review**
Model: `gpt-5.2`

Kritik problem tapılmadı ✅
```

---

## ⚙️ Configuration

### Environment Variables

| Variable         | Required   | Default                               | Description                  |
| ---------------- | ---------- | ------------------------------------- | ---------------------------- |
| `GITLAB_URL`     | Yes        | -                                     | GitLab instance URL          |
| `GITLAB_TOKEN`   | Yes        | -                                     | GitLab personal access token |
| `OPENAI_API_KEY` | For OpenAI | -                                     | OpenAI API key               |
| `AI_MODEL`       | For OpenAI | `gpt-5.2`                          | OpenAI model name            |
| `OLLAMA_URL`     | For Ollama | `http://localhost:11434/api/generate` | Ollama API endpoint          |
| `OLLAMA_MODEL`   | For Ollama | `deepseek-coder:6.7b`                 | Ollama model name            |

### Processing Limits

| Parameter        | Value                                                         | Purpose                          |
| ---------------- | ------------------------------------------------------------- | -------------------------------- |
| `MAX_TOTAL_DIFF` | 20000 chars                                                   | Maximum diff size to analyze     |
| `CHUNK_SIZE`     | 5000 chars                                                    | Size of diff chunks              |
| `MAX_CHUNKS`     | 5                                                             | Maximum chunks to analyze per MR |
| `ALLOWED_EXT`    | `.java`, `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.xml`, `.yaml` | File types to review             |

---

## 🔒 Security Considerations

- ✅ Non-root container user
- ✅ Environment-based secrets (no hardcoded tokens)
- ✅ GitLab webhook secret verification (recommended)
- ✅ Background task processing (non-blocking)
- ✅ Sensitive data filtered from logs
- ✅ Rate limiting (5 chunks max per MR)

---

## 📊 Example Use Cases

### Catch Security Issues

```diff
- password = request.args.get('pwd')  # UNSAFE
+ password = request.args.get('pwd')  # ✅ Validates and escapes input
```

→ AI detects missing validation

### Detect Logic Bugs

```diff
for i in range(len(items)):
  print(items[i])
  # Missing i += 1 in original code
```

→ AI flags infinite loop risk

### Prevent Logging Risks

```diff
- logger.info(f"User token: {token}")  # ❌ Exposes sensitive data
+ logger.info("User authentication successful")  # ✅ Safe logging
```

→ AI warns about credential exposure

---

## 🆘 Troubleshooting

**Review not posting?**

- Check GitLab token validity: `curl -H "PRIVATE-TOKEN: $TOKEN" $GITLAB_URL/api/v4/user`
- Verify webhook URL is accessible
- Check service logs

**Ollama not connecting?**

- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Check `OLLAMA_URL` environment variable
- Pull model: `ollama pull deepseek-coder:6.7b`

**OpenAI errors?**

- Verify API key: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $KEY"`
- Check account has credits
- Ensure model name is correct

**Large diffs not analyzed?**

- Increase `MAX_TOTAL_DIFF` and `MAX_CHUNKS` limits
- Diffs over 20KB are truncated by default
