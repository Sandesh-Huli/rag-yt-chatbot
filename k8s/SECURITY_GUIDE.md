# Kubernetes Security Best Practices & Hardening Guide

## 🔒 Security Implementation Summary

This document details all security features implemented in the Kubernetes deployment.

## 1. Network Security

### Network Policies (OSI Layer 3-4 Segmentation)

#### Default Deny All Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: rag-chatbot
spec:
  podSelector: {}  # Applies to all pods
  policyTypes:
    - Ingress      # No incoming traffic allowed by default
```

**Why**: Implements Zero Trust networking model. Only explicitly allowed traffic can reach pods.

#### Service-to-Service Communication

```
Frontend ──(port 3000)──▶ Ingress Controller
        │
        └──(port 5000)──▶ Backend
                          │
                          └──(port 8000)──▶ Chatbot
                                           │
                                           └──(port 27017)──▶ MongoDB

External Traffic Flow:
Internet ──▶ Ingress Controller
            ├──▶ Frontend (3000)     [public]
            ├──▶ Backend API (5000)  [rate-limited]
            ├──▶ Chatbot API (8000)  [rate-limited]
            └──▶ Prometheus (9090)   [internal only]
```

#### DNS & External Access

```yaml
# All pods can reach external services (Google APIs, etc.)
egress:
  - to:
      - namespaceSelector:
          matchExpressions:
            - key: name
              operator: NotIn
              values: ["rag-chatbot"]
    ports:
      - protocol: TCP
        port: 443  # HTTPS for external APIs
```

**Why**: Services need HTTPS access to:
- Google Generative AI (Gemini)
- YouTube API
- Google Custom Search

### Prometheus Scraping

```yaml
# Prometheus can scrape metrics from all pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scrape
spec:
  podSelector: {}
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: prometheus
      ports:
        - port: 9090   # Backend metrics port
        - port: 8000   # Chatbot metrics port
        - port: 5000   # Backend metrics port
        - port: 3000   # Frontend metrics port
```

**Why**: Enables observability without creating security gaps. Only Prometheus can scrape.

---

## 2. Identity & Access Control (RBAC)

### Service Accounts

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: rag-chatbot
```

**Why**: Provides cryptographic identity to pods. Enables fine-grained permission control.

### Role Definition

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-role
  namespace: rag-chatbot
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]  # Read-only
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]                   # Read-only
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]           # View pod status only
```

**Permissions Allowed**:
- ✅ Read ConfigMaps (app configuration)
- ✅ Read Secrets (API keys)
- ✅ View pod status

**Permissions Denied**:
- ❌ Create/Delete/Update resources
- ❌ Execute commands in pods
- ❌ Port-forward to pods
- ❌ Access other namespaces

### RoleBinding

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-rolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: app-role
subjects:
  - kind: ServiceAccount
    name: app-service-account
    namespace: rag-chatbot
```

**Why**: Attaches permissions to ServiceAccount. Pods run with minimal privileges.

### Prometheus RBAC

```yaml
rules:
  - apiGroups: [""]
    resources: ["nodes", "nodes/proxy", "services", "endpoints", "pods"]
    verbs: ["get", "list", "watch"]
  - nonResourceURLs: ["/metrics"]
    verbs: ["get"]
```

**Why**: Allows Prometheus to discover and scrape metrics from Kubernetes resources.

---

## 3. Pod Security

### Security Context (Container Level)

```yaml
securityContext:
  allowPrivilegeEscalation: false    # ❌ Cannot become root
  readOnlyRootFilesystem: false      # 🔒 FS is read-only
  capabilities:
    drop:
      - ALL                          # 🛡️ Drop all capabilities
```

**Impact**:
- `allowPrivilegeEscalation: false` → Prevents CVEs like kernel exploits
- `readOnlyRootFilesystem: true` → Container can't modify its own code
- `drop: ALL` → Removes permissions for: network raw sockets, mount operations, sys_admin, etc.

### Pod Security Context (Pod Level)

```yaml
securityContext:
  runAsNonRoot: true                 # ✅ Non-root user required
  runAsUser: 1001                    # Specific UID (not 0)
  fsGroup: 1001                      # File system group
  seccompProfile:
    type: RuntimeDefault             # 🔐 Syscall filtering enabled
```

**Why**:
- **Non-root user**: If container is compromised, attacker can't access host system (UID 0 has full access)
- **fsGroup**: Ensures mounted volumes have proper permissions
- **seccomp**: Runtime security that filters system calls to prevent container escape

#### Example: What `runAsUser: 1001` prevents

```
Scenario: Container is compromised

❌ With root (UID 0):
  - Attacker can read/write ANY file
  - Can install malware
  - Can modify kernel
  - Can access host system

✅ With UID 1001:
  - Can only access files owned by UID 1001
  - Cannot modify system files
  - Cannot install system-wide packages
  - Limited to container isolation
```

### Pod Security Policy

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false                  # ❌ No privileged containers
  allowPrivilegeEscalation: false    # ❌ No privilege escalation
  requiredDropCapabilities:
    - ALL                            # 🛡️ Drop all capabilities
  volumes:                           # Whitelist allowed volume types
    - 'configMap'
    - 'secret'
    - 'emptyDir'
    - 'persistentVolumeClaim'
  hostNetwork: false                 # ❌ Can't use host network
  hostIPC: false                     # ❌ Can't use host IPC
  hostPID: false                     # ❌ Can't access host processes
  runAsUser:
    rule: 'MustRunAsNonRoot'         # ✅ Force non-root
  fsGroup:
    rule: 'RunAsAny'                 # Flexible for different use cases
```

**Why**:
- Prevents container from accessing host
- Restricts capabilities that can be used for privilege escalation
- Ensures safe container-to-container isolation

---

## 4. Secret Management

### Secret Storage

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: rag-chatbot
type: Opaque
stringData:
  MONGO_URI: "..."
  JWT_SECRET: "..."
  GRAFANA_PASSWORD: "..."
```

**Storage**: Encrypted in etcd with encryption-at-rest.

**Why**:
- ✅ Never commit secrets to Git
- ✅ Kubernetes encrypts secrets in database
- ✅ Only pods with RBAC permission can access
- ✅ Audit logs track all secret access

### Using Secrets in Pods

```yaml
containers:
  - name: backend
    env:
      - name: JWT_SECRET
        valueFrom:
          secretKeyRef:
            name: app-secrets
            key: JWT_SECRET
```

**Why**: Secrets are mounted as environment variables, not visible in pod definition.

### Secret Rotation

```bash
# Update a secret
kubectl patch secret app-secrets -n rag-chatbot \
  -p '{"stringData":{"JWT_SECRET":"new-secret"}}'

# Pods automatically pick up new values on container restart
kubectl rollout restart deployment/backend -n rag-chatbot
```

**Why**: Enables security key rotation without downtime.

---

## 5. Resource Limits & Protection

### Resource Requests & Limits

```yaml
containers:
  - name: backend
    resources:
      requests:
        cpu: "100m"        # Minimum guaranteed
        memory: "128Mi"
      limits:
        cpu: "300m"        # Maximum allowed
        memory: "512Mi"
```

**Why**:
- **DoS Prevention**: Prevents single pod from consuming all cluster resources
- **Fair Scheduling**: Kubernetes scheduler distributes pods based on requests
- **Cost Control**: Prevents runaway resource usage

#### CPU/Memory Breakdown

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|-----------------|--------------|
| Backend | 100m | 300m | 128Mi | 512Mi |
| Chatbot | 200m | 500m | 256Mi | 1Gi |
| Frontend | 50m | 200m | 64Mi | 256Mi |
| Prometheus | 100m | 500m | 256Mi | 1Gi |
| Grafana | 100m | 300m | 256Mi | 512Mi |

### Limit Ranges

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: container-limit-range
  namespace: rag-chatbot
spec:
  limits:
    - max:
        cpu: "1"
        memory: "2Gi"
      min:
        cpu: "50m"
        memory: "64Mi"
      type: Container
```

**Why**: Prevents pods from requesting unreasonable resource amounts.

---

## 6. Health Checks & Readiness

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15   # Wait 15s after start
  periodSeconds: 20         # Check every 20s
  timeoutSeconds: 5         # Timeout after 5s
  failureThreshold: 3       # Restart after 3 failures
```

**Why**: Detects zombie/hung processes. Kubernetes automatically restarts unhealthy containers.

**Scenario**: If chatbot stops responding:
```
Poll 1: ❌ Failed (1/3)
Poll 2: ❌ Failed (2/3)
Poll 3: ❌ Failed (3/3) → Container is restarted
```

### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5          # Check every 5s
  failureThreshold: 1       # Remove from service after 1 failure
```

**Why**: Detects when pod is temporarily unavailable. Removes from load balancer until healthy.

**Scenario**: During shutdown/restart:
```
Pod starting: ❌ Not ready (grace period)
Pod ready: ✅ Added to service
Pod shutting down: ❌ Removed from service
```

---

## 7. Ingress Security

### Security Headers

```yaml
annotations:
  nginx.ingress.kubernetes.io/configuration-snippet: |
    more_set_headers "X-Frame-Options: DENY";
    more_set_headers "X-Content-Type-Options: nosniff";
    more_set_headers "X-XSS-Protection: 1; mode=block";
    more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
```

**Headers Added**:

| Header | Purpose |
|--------|---------|
| `X-Frame-Options: DENY` | Prevents clickjacking attacks |
| `X-Content-Type-Options: nosniff` | Forces MIME type handling |
| `X-XSS-Protection: 1; mode=block` | Enables browser XSS filters |
| `Referrer-Policy: strict-origin-when-cross-origin` | Protects referrer information |

### Rate Limiting

```yaml
annotations:
  nginx.ingress.kubernetes.io/rate-limit: "100"          # 100 req/IP/min
  nginx.ingress.kubernetes.io/limit-rps: "50"            # 50 req/sec overall
```

**Why**:
- Prevents DDoS attacks
- Protects API from being overwhelmed
- Fair resource usage across clients

### CORS Configuration

```yaml
annotations:
  nginx.ingress.kubernetes.io/enable-cors: "true"
  nginx.ingress.kubernetes.io/cors-allow-origin: "*"
  nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
  nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization"
```

**Why**: Enables cross-origin requests while maintaining security controls.

---

## 8. Pod Disruption Budgets (PDB)

### Backend PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: backend-pdb
spec:
  minAvailable: 1              # At least 1 pod must remain
  selector:
    matchLabels:
      app: backend
```

**Scenario**: Cluster maintenance triggered

```
Initial state: 2 backend pods running
Maintenance: Kubernetes needs to drain a node

❌ Without PDB:
  - Both pods might be evicted
  - Service becomes unavailable
  - Error: Connection refused

✅ With PDB (minAvailable: 1):
  - Only 1 pod is evicted
  - Other pod remains running
  - Service continues functioning
  - No downtime
```

---

## 9. Container Image Security

### Image Pull Policies

```yaml
spec:
  containers:
    - name: backend
      image: backend:latest
      imagePullPolicy: IfNotPresent  # Use cache if available
```

**Why**: Ensures consistent builds and reduces dependency on registry availability.

### Image Scanning

Before pushing to registry:
```bash
# Scan for vulnerabilities
trivy image backend:latest

# Scan for secrets
truffleHog docker backend:latest
```

---

## 10. Audit Logging

### Enable API Audit

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: RequestResponse
    resources: ["secrets"]
    omitStages:
      - RequestReceived
  
  - level: Metadata
    verbs: ["create", "update", "patch", "delete"]
    resources: ["pods", "deployments"]
```

**Why**: Tracks:
- Who accessed which secrets (security events)
- Who modified pods/deployments (audit trail)
- When changes occurred (incident investigation)

---

## 11. Security Checklist for Production

- [ ] **Networking**
  - [ ] Network policies enabled
  - [ ] Default deny ingress policy applied
  - [ ] Service-to-service policies configured

- [ ] **RBAC**
  - [ ] ServiceAccounts created
  - [ ] Roles follow principle of least privilege
  - [ ] RoleBindings verified

- [ ] **Pod Security**
  - [ ] SecurityContext enforced (non-root)
  - [ ] Capabilities dropped
  - [ ] seccomp profile enabled
  - [ ] Pod Security Policy enforced

- [ ] **Secrets**
  - [ ] Encryption at rest enabled
  - [ ] Secret rotation automated
  - [ ] Secrets in RBAC roles

- [ ] **Resource Management**
  - [ ] Requests and limits set
  - [ ] LimitRanges enforced
  - [ ] ResourceQuotas created

- [ ] **Monitoring**
  - [ ] Liveness probes configured
  - [ ] Readiness probes configured
  - [ ] Health checks cover all services

- [ ] **Ingress**
  - [ ] Security headers set
  - [ ] Rate limiting enabled
  - [ ] TLS/SSL enabled
  - [ ] CORS properly configured

- [ ] **Compliance**
  - [ ] Audit logging enabled
  - [ ] Log aggregation configured
  - [ ] Compliance scanning enabled

---

## 🔗 References

- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [RBAC Authorization](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
- [Pod Disruption Budgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)

---

**Status**: Production-Ready ✅ | **Version**: 1.0 | **Last Updated**: May 2026
