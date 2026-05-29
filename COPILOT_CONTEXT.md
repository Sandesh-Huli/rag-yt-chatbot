# YouTube RAG Chatbot - DevSecOps Project Context

## Project Overview
A multi-mode agentic AI chatbot that processes YouTube videos.
Users can ask questions about videos, request summaries, or get 
translations. Built with LangChain, LangGraph, and FastAPI.

**Tech Stack**: Python (FastAPI backend), JavaScript/React (frontend), 
MongoDB (database), Node.js/Express (API gateway)

---

## Architecture

### High-Level Flow
User Query → React Frontend (3000)
→ Node.js Backend (5000)
→ Python FastAPI Chatbot (8000)
→ LangGraph Agent → {
- Fetch YouTube Transcript
- Embed with HuggingFace (sentence-transformers/all-mpnet-base-v2)
- Route with Orchestrator (Gemini LLM decision)
- Execute Mode: QA / Summarize / Translate
- Retrieve Context from FAISS + Chat History
- Generate Response with Gemini
- Store in MongoDB + FAISS
}
→ Response back to Frontend

### Three AI Modes
1. **QA Mode** — answers questions using transcript + web search fallback
2. **Summarize Mode** — creates video summary
3. **Translate Mode** — translates content to target language

---

## Folder Structure
yt-chatbot/
├── backend/                    # Node.js/Express API gateway
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── server.js               # Entry point, port 5000
│   └── src/
│       ├── app.js              # Express config, /metrics endpoint
│       ├── controllers/
│       │   ├── chatController.js
│       │   └── userController.js
│       ├── services/
│       ├── models/
│       │   └── userModel.js
│       ├── routes/
│       │   ├── chatRoutes.js
│       │   └── userRoutes.js
│       ├── middlewares/
│       │   └── authenticateUser.js  # JWT auth
│       └── config/
│           └── mongodb.js
│
├── chatbot/                    # Python FastAPI AI service
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── chatbot_service.py      # FastAPI app, port 8000
│   ├── config.py               # Environment config
│   ├── logging_config.py       # Structured JSON logging
│   └── services/
│       ├── yt_agent_graph.py   # LangGraph orchestrator (MAIN)
│       ├── rag_service.py      # FAISS vector store
│       ├── transcript_service.py # YouTube transcript fetcher
│       ├── db_service.py       # MongoDB interface
│       └── cache_manager.py    # Session + video cache
│
├── frontend/                   # React + Vite UI
│   ├── Dockerfile
│   ├── .dockerignore
│   └── src/
│       ├── components/
│       │   ├── Chat.jsx        # Main chat interface
│       │   ├── Auth.jsx        # Login/Register
│       │   ├── Sidebar.jsx     # Session navigation
│       │   └── ErrorBoundary.jsx
│       ├── context/
│       │   ├── ChatContext.jsx
│       │   └── AppContext.jsx
│       └── services/
│           ├── api.js
│           └── fetchVideoId.js
│
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml          # namespace: rag-chatbot
│   ├── configmap.yaml          # Non-secret config
│   ├── secrets.yaml            # Secret values (never commit real values)
│   ├── network-policy.yaml     # Zero-trust networking
│   ├── alerting-rules.yaml     # Prometheus alert rules
│   ├── prometheus-config.yaml  # Prometheus scrape config
│   ├── prometheus-deploy.yaml  # Prometheus deployment
│   ├── grafana-deploy.yaml     # Grafana deployment
│   ├── backend/
│   │   ├── deployment.yaml     # 2 replicas, RollingUpdate
│   │   └── service.yaml        # ClusterIP, port 5000
│   ├── chatbot/
│   │   ├── deployment.yaml     # 1 replica (FAISS not concurrent-safe)
│   │   └── service.yaml        # ClusterIP, port 8000
│   ├── frontend/
│   │   ├── deployment.yaml     # 2 replicas
│   │   └── service.yaml        # ClusterIP, port 3000
│   └── mongodb/
│       ├── statefulset.yaml    # 1 replica, PVC 5Gi
│       └── service.yaml        # Headless service
│
├── monitoring/                 # Docker Compose monitoring config
│   ├── prometheus.yml          # Scrape configs
│   └── grafana/
│       └── provisioning/
│           └── datasources/
│               └── datasource.yml  # Auto-provision Prometheus
│
├── .github/
│   └── workflows/
│       ├── ci.yml              # Build + lint + security scan
│       ├── cd.yml              # Build images + deploy to K8s
│       └── rollback.yml        # Manual rollback
│
├── docker-compose.yml          # Full stack + monitoring
├── requirements.txt            # Python dependencies
├── .env                        # Local env vars (never commit)
├── .env.example                # Template for env vars
├── SECURITY.md                 # Security documentation
├── MONITORING.md               # Monitoring documentation
├── ALERTS.md                   # Alert rules documentation
├── CI_CD.md                    # CI/CD pipeline documentation
└── DEPLOYMENT.md               # Deployment guide

---

## Member Contributions

### Member 1 — Docker + Kubernetes
**Files created:**
- `backend/Dockerfile` — Node 18 alpine, non-root user (appuser)
- `chatbot/Dockerfile` — Python 3.11 slim, non-root user (appuser uid 1001), CPU-only torch
- `frontend/Dockerfile` — Multi-stage build, Node 18 alpine, serve static
- All `.dockerignore` files
- `docker-compose.yml` — All 6 services with health checks
- All `k8s/` manifest files (namespace, configmap, secrets, deployments, services, statefulset)

**Key decisions:**
- MongoDB uses StatefulSet with PVC (5Gi) for persistence
- All deployments use RollingUpdate strategy
- All sensitive values (MONGO_URI, JWT_SECRET, API keys) use K8s Secrets
- Resource limits set on all containers
- Liveness and readiness probes on all services

### Member 2 — CI/CD Pipeline
**Files created:**
- `.github/workflows/ci.yml` — Lint + build + Gitleaks security scan
- `.github/workflows/cd.yml` — Build + push Docker images + deploy to K8s
- `.github/workflows/rollback.yml` — Manual rollback via workflow_dispatch
- `CI_CD.md` — Pipeline documentation
- `DEPLOYMENT.md` — Deployment guide

**Key decisions:**
- Images tagged with git commit SHA (not just latest)
- CI runs on push + PR to main and feature/** branches
- CD runs on push to main only
- Automatic rollback on deployment failure
- Manual rollback supports: specific service or all, previous revision or specific tag
- Gitleaks scans for accidentally committed secrets

### Member 3 — Monitoring + Security
**Files created:**
- `monitoring/prometheus.yml` — Scrape configs for backend + chatbot
- `monitoring/grafana/provisioning/datasources/datasource.yml`
- `k8s/network-policy.yaml` — Zero-trust pod networking
- `k8s/alerting-rules.yaml` — 6 alert rules
- `SECURITY.md`
- `MONITORING.md`
- `ALERTS.md`

**Code changes:**
- `chatbot/chatbot_service.py` — Added `/metrics` and `/health` endpoints
- `chatbot/chatbot_service.py` — Added 4 Prometheus metrics
- `backend/src/app.js` — Added `/metrics` endpoint using prom-client
- All 3 Dockerfiles — Added non-root USER directive

---

## Running the Project

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 18+
- MongoDB (handled by Docker)

### Environment Setup
Create `.env` in project root:
```env
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=secretpassword
MONGO_URI=mongodb://admin:secretpassword@mongodb:27017/yt_chatbot?authSource=admin
MONGO_PORT=27017
BACKEND_PORT=5000
JWT_SECRET=<min 32 chars - generate with python -c "import secrets; print(secrets.token_urlsafe(32))">
SESSION_SECRET=<min 32 chars>
CORS_ORIGINS=http://localhost:3000,http://frontend:3000
CHATBOT_PORT=8000
FASTAPI_URL=http://chatbot:8000
BACKEND_URL=http://backend:5000
CHATBOT_URL=http://chatbot:8000
FRONTEND_PORT=3000
GOOGLE_API_KEY=your-gemini-api-key
GOOGLE_SEARCH_KEY=your-google-search-key
GOOGLE_CSE_ID=your-cse-id
```

### Start Everything
```bash
docker-compose up --build -d
docker-compose ps   # verify all 6 healthy
```

### Access Points
| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3000 | Register new account |
| Backend API | http://localhost:5000 | — |
| Chatbot API docs | http://localhost:8000/docs | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin/admin |

---

## Monitoring Stack

### Prometheus Metrics

**Chatbot service (Python):**
| Metric | Type | Description |
|---|---|---|
| chatbot_queries_total | Counter | Total queries, label: mode (qa/summarize/translate) |
| chatbot_query_duration_seconds | Histogram | Query processing time |
| chatbot_errors_total | Counter | Total errors |
| chatbot_active_sessions | Gauge | Current active sessions |

**Backend service (Node.js):**
| Metric | Type | Description |
|---|---|---|
| backend_http_requests_total | Counter | Total HTTP requests |
| backend_process_resident_memory_bytes | Gauge | Memory usage |
| backend_process_cpu_seconds_total | Counter | CPU usage |

### Grafana Dashboard Panels
1. Query Rate by Mode — `rate(chatbot_queries_total[5m])` by mode label
2. Query Latency p95 — `histogram_quantile(0.95, rate(chatbot_query_duration_seconds_bucket[5m]))`
3. Error Rate — `rate(chatbot_errors_total[5m])`
4. Backend Request Rate — `rate(backend_http_requests_total[5m])`
5. Active Sessions — `chatbot_active_sessions`
6. Backend Memory — `backend_process_resident_memory_bytes`

### Alert Rules (6 total)
| Alert | Severity | Condition |
|---|---|---|
| PodNotReady | Critical | Pod unready > 1 min |
| PodCrashLooping | Critical | Container restart rate > 0 for 5 min |
| HighQueryLatency | Warning | p95 latency > 10s for 2 min |
| HighErrorRate | Warning | Error rate > 5% for 2 min |
| HighMemoryUsage | Warning | Memory > 80% of limit for 5 min |
| MongoDBDown | Critical | MongoDB replicas == 0 for 1 min |

---

## CI/CD Pipeline

### Workflows
ci.yml — triggers on: push to main/feature/**, PR to main
Job 1: security-scan (Gitleaks)
Job 2: lint-and-build-backend (Node 18, npm ci, lint, build)
Job 3: lint-and-build-chatbot (Python 3.10, pip, flake8)
Job 4: lint-frontend (Node 18, npm ci, Vite build)
cd.yml — triggers on: push to main only
Job 1: build-and-push
- Tag images with git commit SHA
- Push to Docker Hub (3 images)
Job 2: deploy
- Apply K8s manifests in correct order
- Update image tags on deployments
- Wait for rollout status
- Auto rollback on failure
rollback.yml — triggers on: manual workflow_dispatch
Inputs: service (backend/chatbot/frontend/all), image-tag (optional)

If no tag: kubectl rollout undo (previous revision)
If tag given: kubectl set image to specific tag


### GitHub Secrets Required
| Secret | Purpose |
|---|---|
| DOCKER_USERNAME | Docker Hub login |
| DOCKER_PASSWORD | Docker Hub password/PAT |
| KUBECONFIG_DATA | Base64 encoded kubeconfig |

---

## Security Measures

1. **Non-root containers** — All 3 Dockerfiles run as appuser (uid 1001)
2. **Secrets management** — K8s Secrets for all sensitive values, never in ConfigMap
3. **K8s Security Context** — runAsNonRoot, allowPrivilegeEscalation: false, drop ALL capabilities
4. **NetworkPolicy** — Zero-trust: frontend→backend only, backend→chatbot+mongodb, chatbot→mongodb+external
5. **Gitleaks** — CI pipeline scans for accidentally committed secrets
6. **Environment variables** — All from .env file (never committed), .env.example as template

---

## Known Issues & Limitations

1. **MongoDB K8s CrashLoop** — Liveness probe times out during startup. MongoDB works fine in Docker Compose. K8s probe needs `timeoutSeconds: 10` (current is 1s). Workaround: use Docker Compose for demo.
2. **FAISS not persistent in K8s** — Embeddings stored in memory, lost on pod restart. Fix: add PVC for rag_store/ directory. Works fine in Docker Compose.
3. **Chatbot replicas fixed at 1** — FAISS is file-based, not concurrent-safe. Cannot scale horizontally without migrating to managed vector DB (Pinecone/pgvector).
4. **No TLS between services** — All inter-service communication is HTTP. Production would need mTLS.
5. **K8s deploy step in CD** — Requires accessible cluster. Local Minikube not reachable from GitHub runners. Deploy step will fail without cloud cluster or self-hosted runner.
6. **Vite env vars** — REACT_APP_BACKEND_URL in K8s frontend deployment has no effect. Vite bakes env vars at build time, not runtime.

---

## Demo Script

### Docker Compose Demo (Primary)

Show docker-compose ps — all 6 services healthy
Open http://localhost:3000 — show frontend
Register account → paste YouTube URL → ask question
Show response from chatbot (QA mode)
Ask for summary → show summarize mode working
Open http://localhost:9090/targets — show Prometheus scraping
Open http://localhost:3001 — show Grafana dashboards
Show live metrics updating as you use chatbot
Show alert rules in Prometheus (http://localhost:9090/alerts)


### K8s Demo (Supplementary)

kubectl get pods -n rag-chatbot — show running pods
Show backend/frontend running with 2 replicas each
Show Prometheus + Grafana in K8s
Show NetworkPolicy: kubectl get networkpolicy -n rag-chatbot
Show rolling update: kubectl rollout history deployment/backend -n rag-chatbot
Explain MongoDB known issue honestly


### CI/CD Demo

Show .github/workflows/ files
Go to GitHub Actions tab
Show CI workflow runs (lint + security scan)
Show CD workflow (build + push images)
Show rollback.yml — trigger manually, pick a service
Show Docker Hub — images with SHA tags


---

## Frequently Asked Questions for Presentation

**Q: Why use both Docker Compose and Kubernetes?**
A: Docker Compose for local development and testing (simpler, faster). 
Kubernetes for production — gives us rolling updates, auto-scaling (HPA), 
health-based scheduling, and declarative config.

**Q: Why is MongoDB crashing in K8s?**
A: The liveness probe timeout is 1 second but MongoDB takes longer to 
respond during startup on resource-constrained local clusters. This is a 
known configuration issue, not an application bug. It works perfectly in 
Docker Compose. Fix is to increase timeoutSeconds to 10 in the StatefulSet.

**Q: Why can't you scale the chatbot horizontally?**
A: The chatbot uses FAISS (file-based vector store) for embeddings. 
Multiple pods would each have their own copy and can't share it. 
Production solution: migrate to Pinecone or pgvector (shared managed 
vector database).

**Q: How does the AI routing work?**
A: The Orchestrator node in LangGraph sends the user query to Gemini 
with a structured output parser. Gemini decides which mode to use 
(QA/Summarize/Translate) based on the query intent. If parsing fails, 
it defaults to QA mode.

**Q: What happens if Gemini API is down?**
A: The chatbot returns a 500 error. There's no fallback LLM currently. 
This would be a production improvement — add retry logic and a fallback model.

**Q: How does the RAG pipeline work?**
A: 
1. YouTube transcript fetched via youtube-transcript-api
2. Transcript split into chunks
3. Each chunk embedded using HuggingFace sentence-transformers
4. Embeddings stored in FAISS index
5. User query embedded and similarity search finds top-k relevant chunks
6. Relevant chunks + chat history sent to Gemini as context
7. Gemini generates response grounded in the transcript

**Q: Why use both MongoDB and FAISS?**
A: Different purposes. MongoDB stores full chat history for user viewing 
and session management. FAISS stores embeddings for semantic similarity 
search — finding relevant transcript chunks and similar past queries.

**Q: What does the NetworkPolicy do?**
A: Implements zero-trust networking in K8s. By default K8s allows all 
pod-to-pod communication. NetworkPolicy restricts this — frontend can 
only talk to backend, backend can only talk to chatbot and MongoDB, etc. 
This limits blast radius if any service is compromised.

**Q: How does the rollback work?**
A: Two ways. Automatic: if kubectl rollout status fails during CD, the 
pipeline runs kubectl rollout undo on all services. Manual: GitHub Actions 
workflow_dispatch lets you pick a service and optionally a specific image 
tag to roll back to.