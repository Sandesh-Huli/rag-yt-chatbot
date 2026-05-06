# CI/CD Pipeline Documentation

This document explains the GitHub Actions workflows that automate building, testing, pushing, and deploying the RAG chatbot system.

## Overview

The CI/CD pipeline consists of three workflows:

1. **ci.yml** — Continuous Integration (runs on every push and PR)
2. **cd.yml** — Continuous Deployment (runs on push to main only)
3. **rollback.yml** — Manual Rollback (triggered manually)

---

## Workflow Files

### 1. CI Workflow (`ci.yml`)

**Trigger:** `push` and `pull_request` to `main` branch

**Purpose:** Validate code quality and build integrity before merging.

**Jobs:**

#### Job 1: lint-and-build-backend

- **Environment:** Ubuntu Latest
- **Steps:**
  - Checkout code
  - Setup Node.js 18
  - Cache `node_modules` (key: `backend-${{ hashFiles('backend/package-lock.json') }}`)
  - Install dependencies with `npm ci`
  - Run `npm run lint` (skipped if script doesn't exist)
  - Run `npm run build` (skipped if script doesn't exist)

#### Job 2: lint-and-build-chatbot

- **Environment:** Ubuntu Latest
- **Steps:**
  - Checkout code
  - Setup Python 3.10
  - Cache pip packages (key: `chatbot-${{ hashFiles('chatbot/requirements.txt') }}`)
  - Install dependencies with `pip install -r requirements.txt`
  - Install `flake8`
  - Run `flake8 chatbot/ --max-line-length=120 --ignore=E501`
  - Run `pytest` on the `tests/` directory (skipped if no tests found)

#### Job 3: lint-frontend

- **Environment:** Ubuntu Latest
- **Steps:**
  - Checkout code
  - Setup Node.js 18
  - Cache `node_modules` (key: `frontend-${{ hashFiles('frontend/package-lock.json') }}`)
  - Install dependencies with `npm ci`
  - Run `npm run lint` (skipped if script doesn't exist)
  - Run Vite build with `npm run build` (validates app compilation)

---

### 2. CD Workflow (`cd.yml`)

**Trigger:** `push` to `main` branch only (PRs do NOT trigger this)

**Purpose:** Build Docker images, push to Docker Hub, and deploy to Kubernetes.

**Environment Variables:**

```yaml
REGISTRY: docker.io
BACKEND_IMAGE: ${{ secrets.DOCKER_USERNAME }}/rag-backend
CHATBOT_IMAGE: ${{ secrets.DOCKER_USERNAME }}/rag-chatbot
FRONTEND_IMAGE: ${{ secrets.DOCKER_USERNAME }}/rag-frontend
```

#### Job 1: build-and-push

- **Environment:** Ubuntu Latest
- **Outputs:** `image-tag` (short commit SHA)
- **Steps:**
  1. Checkout code
  2. Generate image tag from commit SHA (e.g., `abc1234`)
  3. Log in to Docker Hub using secrets
  4. Set up Docker Buildx for multi-platform builds
  5. Build and push **backend** image
     - Tags: `${{ env.BACKEND_IMAGE }}:abc1234` and `${{ env.BACKEND_IMAGE }}:latest`
     - Uses GitHub Actions cache
  6. Build and push **chatbot** image
     - Tags: `${{ env.CHATBOT_IMAGE }}:abc1234` and `${{ env.CHATBOT_IMAGE }}:latest`
  7. Build and push **frontend** image
     - Tags: `${{ env.FRONTEND_IMAGE }}:abc1234` and `${{ env.FRONTEND_IMAGE }}:latest`

#### Job 2: deploy

- **Environment:** Ubuntu Latest
- **Depends on:** `build-and-push`
- **Steps:**
  1. Checkout code
  2. Set up `kubectl`
  3. Configure kubeconfig from secret (base64 decoded)
  4. Apply Kubernetes namespace and configmap
  5. ⚠️ **Skip** applying `k8s/secrets.yaml` (manual setup required)
  6. Update image tags in deployments:
     - Backend: `kubectl set image deployment/backend ...`
     - Chatbot: `kubectl set image deployment/chatbot ...`
     - Frontend: `kubectl set image deployment/frontend ...`
  7. Apply remaining K8s manifests (backend, chatbot, frontend, mongodb)
  8. Monitor rollout status with timeouts (120s for each service)
  9. **Automatic Rollback:** If any step fails, automatically roll back all deployments to previous revision

---

### 3. Rollback Workflow (`rollback.yml`)

**Trigger:** Manual dispatch (`workflow_dispatch`)

**Purpose:** Manually roll back a service to a previous version or specific image tag.

**Inputs:**

- **service** (required, choice):
  - `backend` — Roll back backend only
  - `chatbot` — Roll back chatbot only
  - `frontend` — Roll back frontend only
  - `all` — Roll back all services

- **image-tag** (optional, string):
  - Leave empty to roll back to previous K8s revision
  - Provide a tag (e.g., `abc1234`) to roll back to specific image

**Steps:**

1. Checkout code
2. Set up `kubectl`
3. Configure kubeconfig
4. **Branch A:** If `image-tag` is empty:
   - Execute `kubectl rollout undo deployment/{service} -n rag-chatbot`
5. **Branch B:** If `image-tag` is provided:
   - Execute `kubectl set image` with the specified tag
6. Verify rollout status (60s timeout)
7. Display current image running on each service
8. Confirm rollback completion

---

## GitHub Secrets Setup

Before running workflows, configure these secrets in your GitHub repository:

### 1. DOCKER_USERNAME

- **Value:** Your Docker Hub username
- **Used by:** `cd.yml` (login) and `rollback.yml` (image reference)

### 2. DOCKER_PASSWORD

- **Value:** Your Docker Hub password or Personal Access Token (PAT)
- **Used by:** `cd.yml` (login)

### 3. KUBECONFIG_DATA

- **Value:** Base64-encoded kubeconfig file from your Kubernetes cluster
- **How to generate:**
  ```bash
  cat ~/.kube/config | base64 -w 0
  ```
- **Used by:** `cd.yml` and `rollback.yml` (cluster authentication)

### 4. Manual Secrets Setup (NOT in GitHub)

- **File:** `k8s/secrets.yaml`
- **Action:** Must be applied manually BEFORE first deployment
  ```bash
  kubectl apply -f k8s/secrets.yaml
  ```
- **Reason:** Never commit sensitive data to Git

**To add secrets to GitHub:**

1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Enter name and value
4. Click **Add secret**

---

## Triggering Workflows

### CI Workflow (ci.yml)

**Automatic triggers:**

- Push to `main` branch
- Pull request to `main` branch

**View logs:**

1. Go to **Actions** tab in GitHub
2. Click **CI - Build & Test**
3. Select the workflow run
4. View job logs

---

### CD Workflow (cd.yml)

**Automatic trigger:**

- Push to `main` branch only

**Will NOT run on:**

- Pull requests
- Pushes to other branches

**View logs:**

1. Go to **Actions** tab
2. Click **CD - Build, Push & Deploy**
3. Select the workflow run
4. View build and deployment logs

---

### Rollback Workflow (rollback.yml)

**Manual trigger:**

1. Go to **Actions** tab
2. Click **Rollback - Manual Service Rollback** (left sidebar)
3. Click **Run workflow**
4. Select options:
   - **Service:** Choose `backend`, `chatbot`, `frontend`, or `all`
   - **Image tag:** Leave empty (for previous revision) OR enter a tag (e.g., `abc1234`)
5. Click **Run workflow**

**View logs:**

- Check the workflow run under the **Rollback** workflow

---

## Reading Workflow Logs

### How to Access Logs

1. Go to **Actions** tab in GitHub
2. Click the workflow name (e.g., "CI - Build & Test")
3. Select the specific run (by date/commit)
4. Click a job to expand details
5. Click a step to view its output

### Common Log Patterns

#### Successful CI Job

```
✅ Run npm ci in backend/
...
✅ Run npm run build
Build completed successfully
```

#### Failed Docker Build

```
❌ Build and push backend image
Error: docker build failed
...
Error message with details
```

#### Deployment Failure + Automatic Rollback

```
❌ Wait for backend rollout
Deployment rollout failed
✅ Automatic rollback on failure
Rollback completed
```

---

## Troubleshooting

### Workflow Doesn't Trigger

**Problem:** CD or CI workflow didn't run after push/PR

**Solutions:**

- Verify you pushed to/opened PR against `main` branch (not `develop`, etc.)
- Check workflow file syntax in `.github/workflows/`
- Go to **Actions** → **All workflows** to see if workflow exists
- Check branch protection rules haven't restricted deployments

### Docker Login Fails

**Problem:** `Error: Docker authentication failed`

**Solutions:**

- Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are set
- Check that Docker Hub credentials are correct
- If using Personal Access Token (PAT), ensure it has appropriate scopes
- Re-create the secret if unsure

### Kubeconfig Authentication Error

**Problem:** `Error: kubeconfig authentication failed` or `Unable to connect to cluster`

**Solutions:**

- Verify `KUBECONFIG_DATA` is correctly base64-encoded
- Regenerate with: `cat ~/.kube/config | base64 -w 0` (no extra newlines)
- Ensure cluster is accessible from GitHub runners (works with cloud-hosted clusters, may not work with local Minikube)
- For local testing, use a self-hosted runner in your network
- Check cluster certificates haven't expired

### Deployment Stuck in Pending

**Problem:** `kubectl rollout status` timeout (120s)

**Solutions:**

- Check pod events: `kubectl describe pod <pod-name> -n rag-chatbot`
- Check image exists in Docker Hub: `docker pull username/rag-backend:tag`
- Check node resources: `kubectl top nodes`
- Verify ConfigMap and Secrets exist: `kubectl get configmap -n rag-chatbot`
- Check resource requests/limits in deployment manifests

### Rollback Doesn't Show Current Image

**Problem:** After rollback, image still shows old version

**Solutions:**

- Wait for rollout to complete: `kubectl rollout status deployment/{service} -n rag-chatbot`
- Check pod termination: `kubectl get pods -n rag-chatbot`
- Manually verify deployment: `kubectl get deployment -o jsonpath='{.spec.template.spec.containers[0].image}'`

---

## Known Limitations

### Kubeconfig & Local Clusters

The `KUBECONFIG_DATA` secret must point to an **accessible Kubernetes cluster**:

- ✅ **Works with:** Cloud-hosted clusters (EKS, AKS, GKE, DigitalOcean, etc.)
- ❌ **Doesn't work with:** Local Minikube, Kind on your machine (not accessible from GitHub runners)

**Workaround for local development:**

- Deploy to a cloud-hosted cluster for CI/CD testing
- For local testing, run `kubectl apply` commands manually
- Set up a self-hosted runner in your network for local cluster access

### GitHub Actions Rate Limits

- Docker Hub anonymous pulls: ~100 pulls per 6 hours
- Solution: Log in to Docker Hub (already done in workflow) for higher limits (1000 pulls/IP per 24 hours)

### Cache Expiry

- GitHub Actions caches expire after 7 days of non-access
- Solution: Workflows rebuild cache on first run after expiry (no issue)

---

## Best Practices

1. **Always use tagged images in production**
   - Use commit SHA or semantic versioning (v1.0.0)
   - Avoid relying solely on `latest` tag

2. **Monitor deployment logs**
   - Check GitHub Actions logs immediately after push
   - Use `kubectl logs` for runtime debugging

3. **Test rollback procedures**
   - Practice manual rollbacks in non-production
   - Understand your rollout history

4. **Keep secrets secure**
   - Use GitHub Organization secrets for shared credentials
   - Rotate Docker Hub tokens regularly
   - Never commit kubeconfig or secrets to Git

5. **Review automatic rollbacks**
   - Check logs to understand why deployment failed
   - Address root cause before redeploying
