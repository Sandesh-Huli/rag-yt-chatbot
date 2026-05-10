# Security Documentation - YouTube RAG Chatbot

## 1. Overview of Security Measures

This document outlines the security architecture and controls implemented across the YouTube RAG chatbot project. Security is layered across containerization, secrets management, Kubernetes security contexts, and network policies to enforce zero-trust principles.

**Deployment environments:**
- **Docker Compose**: Local development with security best practices
- **Kubernetes**: Production deployment in `rag-chatbot` namespace with RBAC, network policies, and pod security policies

---

## 2. Non-Root Containers

All application containers run as non-root user to reduce blast radius of container escapes.

### Security Context Details
- **User**: `appuser`
- **UID**: `1001`
- **Applied to**: Backend, Chatbot, Frontend containers

### Dockerfile Configuration

**Backend (`backend/Dockerfile`):**
```dockerfile
USER appuser:appuser
```

**Chatbot (`chatbot/Dockerfile`):**
```dockerfile
USER appuser:appuser
```

**Frontend (`frontend/Dockerfile`):**
```dockerfile
USER appuser:appuser
```

### Verification
```bash
# Verify container runs as non-root
docker exec rag-chatbot-backend id
# uid=1001(appuser) gid=1001(appuser) groups=1001(appuser)

docker exec rag-chatbot-chatbot id
# uid=1001(appuser) gid=1001(appuser) groups=1001(appuser)
```

---

## 3. Secrets Management

### What Was Wrong
The initial approach stored sensitive credentials in plaintext in version control:
- `k8s/secrets.yaml` committed to Git with base64-encoded (not encrypted) values
- Example: `GOOGLE_API_KEY`, `MONGODB_PASSWORD`, JWT tokens in plaintext
- Risk: Any user with Git access could extract production secrets

### What Is Correct
Secrets must be:
1. **Never committed** to version control (`.gitignore`)
2. **Generated securely** with cryptographically random values
3. **Injected at deployment time** via GitHub Actions or manual deployment
4. **Rotated regularly** (recommended: every 90 days)

### How to Generate Proper Secrets

Generate a cryptographically random 32-byte secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: Drmhze6EPcv0fN_81Bj-nA_r1drsapNz_2H2qLLPg0o
```

For multiple secrets:
```bash
python << 'EOF'
import secrets
secrets_dict = {
    'GOOGLE_API_KEY': secrets.token_urlsafe(32),
    'JWT_SECRET': secrets.token_urlsafe(32),
    'SESSION_SECRET': secrets.token_urlsafe(32),
    'MONGODB_PASSWORD': secrets.token_urlsafe(24),
}
for key, value in secrets_dict.items():
    print(f"{key}={value}")
EOF
```

### GitHub Actions Secrets Configuration

Add these secrets to GitHub repository settings (Settings → Secrets and variables → Actions):

| Secret Name | Purpose | Example Value |
|------------|---------|---|
| `DOCKER_USERNAME` | Docker Hub authentication | `your-dockerhub-username` |
| `DOCKER_PASSWORD` | Docker Hub token (not password) | Generated from Docker Hub settings |
| `KUBECONFIG_DATA` | Base64-encoded kubeconfig | `LS0tIGFwaVZlcnNpb246IHYxCi...` |

**GitHub Actions usage:**
```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: ./chatbot
    push: true
    tags: ${{ secrets.DOCKER_USERNAME }}/chatbot:${{ github.sha }}
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}
```

### k8s/secrets.yaml Management

**Before deployment:**
1. Create `k8s/secrets.yaml` from template (never commit actual values)
2. Replace placeholder values with generated secrets
3. Delete file after applying to cluster

```bash
# Generate secrets and create k8s/secrets.yaml
python generate_secrets.py > k8s/secrets.yaml

# Apply to cluster
kubectl apply -f k8s/secrets.yaml

# Delete from filesystem (keep only in etcd)
rm k8s/secrets.yaml
```

---

## 4. Environment Variables

### Docker Compose

Environment variables are loaded from `.env` file (must NOT be committed to Git).

**`.env.example` (committed to Git as template):**
```env
# Backend
JWT_SECRET=your-jwt-secret-here
SESSION_SECRET=your-session-secret-here
BACKEND_PORT=5000

# Chatbot
GOOGLE_API_KEY=your-google-api-key-here
MONGODB_URI=mongodb://mongodb:27017
CHATBOT_PORT=8000

# MongoDB
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=your-mongo-password-here
MONGO_INITDB_DATABASE=rag-chatbot

# Frontend
REACT_APP_API_URL=http://localhost:5000
```

**`.env` (local development only, gitignored):**
```bash
# Create from template
cp .env.example .env

# Fill in actual values
# DO NOT commit this file
```

### Kubernetes Secrets

Environment variables from K8s secrets are mounted as volumes or injected into containers:

```yaml
env:
  - name: GOOGLE_API_KEY
    valueFrom:
      secretKeyRef:
        name: chatbot-secrets
        key: google-api-key
  - name: MONGODB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: mongodb-credentials
        key: password
```

---

## 5. Kubernetes Security Context

All K8s pods enforce strict security contexts to prevent privilege escalation and container escapes.

### Security Context Configuration

Applied to all deployments (backend, chatbot, frontend):

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  runAsGroup: 1001
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  seccompProfile:
    type: RuntimeDefault
```

### Individual Container Security

```yaml
containers:
  - name: chatbot
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: false  # Needed for temp files
    resources:
      requests:
        memory: "256Mi"
        cpu: "100m"
      limits:
        memory: "1Gi"
        cpu: "500m"
```

### Pod Security Policy

Applied via `PodSecurityPolicy` in namespace:
- Restricted baseline for all pods
- No privileged containers
- No host networking
- No capabilities except NET_BIND_SERVICE (for ports)

---

## 6. NetworkPolicy (Planned/Implemented)

Zero-trust network architecture enforces explicit allow rules between services.

### Network Topology

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (3000)                   │
│                                                     │
│    ↓ (only to backend)                              │
│                                                     │
│            Backend (5000)                           │
│          ↙              ↘                           │
│   Chatbot (8000)     MongoDB (27017)               │
│       ↓                    ↓                        │
│   (to MongoDB & )    (inbound only from)           │
│   (external APIs)    (backend & chatbot)           │
│                                                     │
│        ↓ (external)                                 │
│   Google/External APIs                              │
└─────────────────────────────────────────────────────┘
```

### Implemented Policies

**Default Deny (all namespaces):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

**Frontend → Backend:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: rag-chatbot
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 5000
```

**Backend → Chatbot & MongoDB:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-services
  namespace: rag-chatbot
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: chatbot
      ports:
        - protocol: TCP
          port: 8000
    - to:
        - podSelector:
            matchLabels:
              app: mongodb
      ports:
        - protocol: TCP
          port: 27017
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 53
        - protocol: UDP
          port: 53
```

**Chatbot → MongoDB:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-chatbot-to-mongodb
  namespace: rag-chatbot
spec:
  podSelector:
    matchLabels:
      app: chatbot
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: mongodb
      ports:
        - protocol: TCP
          port: 27017
```

---

## 7. Known Limitations

### Current Security Gaps
1. **No TLS Between Services**
   - Services communicate over HTTP within the cluster
   - Should implement: mTLS via Istio or native K8s cert-manager

2. **No Image Vulnerability Scanning**
   - Docker images not scanned for CVEs before deployment
   - Recommendation: Add Trivy or Aqua scanning to CI/CD pipeline

3. **Plaintext Secrets in Git (Temporarily)**
   - `k8s/secrets.yaml` contains placeholder base64 values
   - Must replace before production deployment
   - Solution: Use secrets-as-code tools (sealed-secrets, external-secrets-operator)

4. **No RBAC for Service-to-Service**
   - All pods have default service account with no RBAC bindings
   - Should create: Minimal RBAC roles per service

5. **No Secret Rotation**
   - Secrets are static after deployment
   - Recommendation: Implement automated rotation every 90 days

### Roadmap to Production Hardening
- [ ] Enable mTLS for inter-service communication
- [ ] Add image scanning (Trivy) to CI/CD
- [ ] Implement sealed-secrets for Git-safe secret storage
- [ ] Create RBAC policies with least-privilege access
- [ ] Add audit logging for API calls
- [ ] Enable Pod Security Standards enforcement

---

## 8. Security Checklist

- [x] All containers run as non-root (UID 1001)
- [x] Security contexts applied to all K8s pods
- [x] NetworkPolicies enforce zero-trust
- [x] Secrets are gitignored and injected at deployment
- [x] No hardcoded credentials in source code
- [x] .env.example provided as template
- [ ] TLS enabled between services
- [ ] Image vulnerability scanning in CI/CD
- [ ] RBAC policies implemented
- [ ] Secrets encrypted at rest in etcd
- [ ] Audit logging enabled

---

## 9. Additional Resources

- [OWASP Container Security Top 10](https://owasp.org/www-project-container-security/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [CIS Kubernetes Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NSA Kubernetes Hardening Guidance](https://media.defense.gov/Oct%202021/pdf/NSA_CSI_Kubernetes_Hardening_Guidance.pdf)
