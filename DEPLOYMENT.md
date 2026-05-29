# Kubernetes Deployment Guide

This document covers first-time setup, deployment verification, image flow, and rollout history management for the RAG chatbot system.

---

## First-Time Setup

Before deploying for the first time, follow these steps:

### Step 1: Prepare Your Kubernetes Cluster

Ensure you have a running Kubernetes cluster and `kubectl` is configured:

```bash
kubectl cluster-info
kubectl get nodes
```

### Step 2: Configure Kubeconfig Secret

Convert your kubeconfig to base64 and add to GitHub Secrets:

```bash
# Get base64-encoded kubeconfig (no line breaks)
cat ~/.kube/config | base64 -w 0
```

1. Copy the output (entire string, no newlines)
2. Go to GitHub Repository → **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `KUBECONFIG_DATA`
5. Value: Paste the base64 string
6. Click **Add secret**

### Step 3: Add Docker Hub Credentials

1. Go to GitHub Repository → **Settings** → **Secrets and variables** → **Actions**
2. Create two new secrets:
   - **DOCKER_USERNAME**: Your Docker Hub username
   - **DOCKER_PASSWORD**: Your Docker Hub password or Personal Access Token

### Step 4: Manually Apply Kubernetes Secrets

⚠️ **CRITICAL:** Secrets must be applied manually before first deployment (NOT via GitHub Actions).

```bash
# First, edit k8s/secrets.yaml with your actual secret values
# Then apply to your cluster
kubectl apply -f k8s/secrets.yaml
```

**Why manual?** Secrets should never be committed to Git or run through CI/CD pipelines.

### Step 5: Apply Namespace and Initial Manifests

Apply the namespace and initial configuration:

```bash
# Apply namespace (required for all other resources)
kubectl apply -f k8s/namespace.yaml

# Apply configmap
kubectl apply -f k8s/configmap.yaml

# Verify namespace was created
kubectl get namespace rag-chatbot
```

### Step 6: Trigger First Deployment

Push to the `main` branch to trigger the CD workflow:

```bash
git push origin main
```

Monitor the deployment:

1. Go to GitHub → **Actions** tab
2. Click **CD - Build, Push & Deploy**
3. Watch the workflow run
4. If successful, check Kubernetes:
   ```bash
   kubectl get pods -n rag-chatbot
   kubectl get deployments -n rag-chatbot
   ```

---

## Verifying Deployments

### Check Deployment Status

```bash
# List all deployments in the namespace
kubectl get deployments -n rag-chatbot

# Get detailed status of a specific deployment
kubectl describe deployment backend -n rag-chatbot

# Watch rollout in real-time
kubectl rollout status deployment/backend -n rag-chatbot -w
```

### Check Pod Status

```bash
# List all pods
kubectl get pods -n rag-chatbot

# Get detailed pod information
kubectl describe pod <pod-name> -n rag-chatbot

# View pod logs
kubectl logs pod/<pod-name> -n rag-chatbot -f
```

### Verify Services

```bash
# List all services
kubectl get services -n rag-chatbot

# Get service endpoints
kubectl get endpoints -n rag-chatbot

# Check LoadBalancer/Ingress status
kubectl get ingress -n rag-chatbot
kubectl describe ingress <ingress-name> -n rag-chatbot
```

### Verify ConfigMap and Secrets

```bash
# Check if configmap exists
kubectl get configmap -n rag-chatbot

# View configmap contents
kubectl describe configmap <configmap-name> -n rag-chatbot

# Verify secrets exist (do NOT display values)
kubectl get secrets -n rag-chatbot
```

---

## Image Flow: Git Commit → Docker Hub → Kubernetes

Understanding how images flow through the system:

### 1. Code Push to Git

```
Developer pushes commit to main branch
    ↓
git commit hash: abc1234567 (full SHA)
Short SHA: abc1234 (7 chars)
```

### 2. Docker Image Build & Push

**In GitHub Actions (cd.yml):**

```
1. Generate tag from commit SHA
   IMAGE_TAG = "abc1234"

2. Build and push backend image
   docker build ./backend
   Tags applied:
     - docker.io/username/rag-backend:abc1234 ← Latest commit version
     - docker.io/username/rag-backend:latest   ← Always points to latest

3. Same for chatbot and frontend

4. All images pushed to Docker Hub
```

**View on Docker Hub:**

```
Docker Hub → username → rag-backend
├── Tags
│   ├── abc1234 (5 minutes ago)
│   ├── def5678 (2 hours ago)
│   ├── ghi9012 (1 day ago)
│   └── latest (5 minutes ago) ← Points to abc1234
```

### 3. Kubernetes Deployment Update

**In GitHub Actions (cd.yml deploy job):**

```
1. Extract image tag from build-and-push job output
   IMAGE_TAG = "abc1234"

2. Update each deployment with new image
   kubectl set image deployment/backend \
     backend=docker.io/username/rag-backend:abc1234 \
     -n rag-chatbot

3. Kubernetes detects image change
   Pulls new image from Docker Hub
   Terminates old pods
   Starts new pods with updated image

4. Wait for rollout to complete (120s timeout)
```

### 4. Verify Image in Kubernetes

```bash
# Check current image running on backend deployment
kubectl get deployment backend -n rag-chatbot \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
# Output: docker.io/username/rag-backend:abc1234

# Check all containers in a pod
kubectl get pod <pod-name> -n rag-chatbot \
  -o jsonpath='{.spec.containers[*].image}'

# View image history via events
kubectl describe deployment backend -n rag-chatbot | grep Image
```

---

## Deployment Workflow

### Successful Deployment Flow

```
1. Developer pushes to main
   ↓
2. GitHub Actions CI (ci.yml) triggers
   - Lint and build backend ✓
   - Lint and test chatbot ✓
   - Lint and build frontend ✓
   ↓
3. GitHub Actions CD (cd.yml) triggers
   - Build images (backend, chatbot, frontend)
   - Push to Docker Hub with commit SHA tag
   - Log in to Kubernetes cluster
   - Apply namespace and configmap
   - Update deployment image references
   - Wait for rollout (120s timeout per service)
   ↓
4. Kubernetes detects changes
   - Pulls new images from Docker Hub
   - Starts new pod replicas
   - Terminates old pods gracefully
   ↓
5. Service online with new version
   ✓ Deployment complete
```

### Failure & Automatic Rollback Flow

```
1. Deploy job encounters failure
   - Image pull fails
   - Pod startup fails
   - Health check fails
   - Rollout timeout (>120s)
   ↓
2. GitHub Actions detects failure
   ↓
3. Automatic rollback triggered
   kubectl rollout undo deployment/backend -n rag-chatbot
   kubectl rollout undo deployment/chatbot -n rag-chatbot
   kubectl rollout undo deployment/frontend -n rag-chatbot
   ↓
4. Kubernetes reverts to previous ReplicaSet
   - Old pods restart
   - New pods terminate
   ↓
5. Previous version running again
   ⚠️ Investigate root cause before retrying
```

---

## Checking Rollout History

### View Revision History

```bash
# Show all revisions for a deployment
kubectl rollout history deployment/backend -n rag-chatbot

# Output example:
# REVISION  CHANGE-CAUSE
# 1         <none>
# 2         <none>
# 3         <none>
# 4         <none>
```

### Get Details About Specific Revision

```bash
# Show details of a specific revision
kubectl rollout history deployment/backend -n rag-chatbot --revision=2

# Output example:
# Pod Template:
#   Labels:
#     app: backend
#   Containers:
#    backend:
#     Image: docker.io/username/rag-backend:def5678
```

### Map Revisions to Commits

Since `CHANGE-CAUSE` may be empty, map revisions to commits manually:

```bash
# Get current image of a revision
kubectl rollout history deployment/backend -n rag-chatbot --revision=3 | grep Image

# Example: Image: docker.io/username/rag-backend:abc1234
# → Revision 3 was deployed with commit abc1234

# Cross-reference with git
git log --oneline | grep abc1234
# Output: abc1234 - Fixed authentication bug
```

### Add Change Cause to Annotations

To make revision tracking easier, update deployments with change cause:

```bash
# Manually trigger rollout with change cause
kubectl patch deployment backend -n rag-chatbot \
  -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"kubernetes.io/change-cause\":\"$(git log -1 --pretty=%B)\"}}}}}"

# Now rollout history shows reason:
kubectl rollout history deployment/backend -n rag-chatbot
# REVISION  CHANGE-CAUSE
# 4         Fixed authentication bug
```

---

## Manual Rollback Scenarios

### Scenario 1: Rollback to Previous Version (Unknown Revision)

**Situation:** Deployment is broken, need to go back to previous working version

```bash
# Using GitHub Actions
1. Go to Actions tab
2. Click "Rollback - Manual Service Rollback"
3. Click "Run workflow"
4. Service: select "backend" (or affected service)
5. Image tag: leave empty
6. Click "Run workflow"

# OR manually
kubectl rollout undo deployment/backend -n rag-chatbot
```

### Scenario 2: Rollback to Specific Known Version

**Situation:** Need to revert to a specific commit/image tag

```bash
# Using GitHub Actions
1. Go to Actions tab
2. Click "Rollback - Manual Service Rollback"
3. Click "Run workflow"
4. Service: select "backend"
5. Image tag: enter "abc1234" (commit SHA)
6. Click "Run workflow"

# OR manually
kubectl set image deployment/backend \
  backend=docker.io/username/rag-backend:abc1234 \
  -n rag-chatbot
```

### Scenario 3: Rollback All Services at Once

**Situation:** Full deployment failure, need to revert everything

```bash
# Using GitHub Actions
1. Go to Actions tab
2. Click "Rollback - Manual Service Rollback"
3. Click "Run workflow"
4. Service: select "all"
5. Image tag: leave empty
6. Click "Run workflow"

# OR manually
kubectl rollout undo deployment/backend -n rag-chatbot
kubectl rollout undo deployment/chatbot -n rag-chatbot
kubectl rollout undo deployment/frontend -n rag-chatbot
```

---

## Deployment Readiness Checks

Before deploying, verify:

### Infrastructure Ready

- [ ] Kubernetes cluster running and accessible
- [ ] Nodes have sufficient resources (CPU, memory, disk)
- [ ] PersistentVolumes available for stateful services (MongoDB)

### Secrets & Config Ready

- [ ] `k8s/secrets.yaml` applied manually
- [ ] `DOCKER_USERNAME` secret in GitHub
- [ ] `DOCKER_PASSWORD` secret in GitHub
- [ ] `KUBECONFIG_DATA` secret in GitHub (base64-encoded)

### Container Images Ready

- [ ] Dockerfiles present and valid in each service directory
- [ ] All dependencies listed in requirements files
- [ ] No hardcoded credentials in Dockerfiles

### Kubernetes Manifests Ready

- [ ] Namespace manifest (`k8s/namespace.yaml`)
- [ ] ConfigMap manifest (`k8s/configmap.yaml`)
- [ ] Service manifests for each component
- [ ] Deployment manifests with correct resource requests/limits
- [ ] Ingress or LoadBalancer for external access

---

## Monitoring Deployments

### Real-Time Status

```bash
# Watch deployment updates live
kubectl rollout status deployment/backend -n rag-chatbot -w

# Alternative: Watch pods
kubectl get pods -n rag-chatbot -w

# Alternative: Watch events
kubectl get events -n rag-chatbot -w
```

### Pod Troubleshooting

```bash
# Pods stuck in ImagePullBackOff
kubectl describe pod <pod-name> -n rag-chatbot
# Look for "Failed to pull image" — verify image exists and credentials correct

# Pods stuck in Pending
# Check node capacity
kubectl describe nodes

# Check resource quotas
kubectl get resourcequota -n rag-chatbot

# Pods stuck in CrashLoopBackOff
kubectl logs pod/<pod-name> -n rag-chatbot --previous
```

### Deployment History

```bash
# See past deployments
kubectl get replicasets -n rag-chatbot -o wide

# View current deployment revision
kubectl get deployment backend -n rag-chatbot -o yaml | grep observedGeneration

# List all events for a deployment
kubectl describe deployment backend -n rag-chatbot | grep -A 20 "Events:"
```

---

## Troubleshooting Deployment Issues

### Issue: Pods are in ImagePullBackOff

**Cause:** Docker image cannot be pulled from Docker Hub

**Fix:**

```bash
# Verify image exists
docker pull docker.io/username/rag-backend:abc1234

# Check image pull secrets in deployment
kubectl get deployment backend -n rag-chatbot -o yaml | grep -A 5 imagePullSecrets

# If missing, add docker-registry secret
kubectl create secret docker-registry regcred \
  --docker-server=docker.io \
  --docker-username=<username> \
  --docker-password=<password> \
  -n rag-chatbot
```

### Issue: Pods Stuck in Pending

**Cause:** Insufficient cluster resources or missing persistent volumes

**Fix:**

```bash
# Check node capacity
kubectl top nodes
kubectl describe nodes | grep -A 5 "Allocated resources"

# Check for pending PVCs
kubectl get pvc -n rag-chatbot

# If PV missing, create one
kubectl apply -f k8s/chatbot/pvc.yaml
```

### Issue: Pod CrashLoopBackOff

**Cause:** Application crashed at startup

**Fix:**

```bash
# View pod logs (current attempt)
kubectl logs pod/<pod-name> -n rag-chatbot

# View previous pod logs (from crash)
kubectl logs pod/<pod-name> -n rag-chatbot --previous

# Check pod events
kubectl describe pod <pod-name> -n rag-chatbot | grep -A 10 "Events:"
```

### Issue: Deployment Didn't Update with New Image

**Cause:** Image tag not changed, or image pull cached

**Fix:**

```bash
# Force pod restart
kubectl rollout restart deployment/backend -n rag-chatbot

# Or manually delete pods (will be recreated)
kubectl delete pod -l app=backend -n rag-chatbot

# Verify new image pulled
kubectl get pods -n rag-chatbot -o jsonpath='{.items[0].spec.containers[0].image}'
```

---

## Best Practices

1. **Always tag images with commit SHA**
   - Ensures traceability from code to production
   - Enables precise rollbacks

2. **Monitor rollout status**
   - Check GitHub Actions logs after every deployment
   - Use `kubectl rollout status` to verify completion

3. **Maintain rollout history**
   - Kubernetes keeps last 10 revisions by default
   - Older revisions are garbage-collected

4. **Test rollbacks regularly**
   - Practice manual rollbacks in staging
   - Ensure team understands procedure

5. **Keep secrets secure**
   - Never commit kubeconfig or credentials
   - Use short-lived tokens when possible
   - Rotate credentials quarterly

6. **Monitor resource usage**
   - Check pod CPU and memory regularly
   - Adjust resource requests/limits based on actual usage
   - Prevent node overcommitment

7. **Use health checks**
   - Configure liveness probes (detect crashed containers)
   - Configure readiness probes (detect failed startup)
   - Kubernetes will restart/replace unhealthy pods
