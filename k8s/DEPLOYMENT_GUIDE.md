# Kubernetes Deployment Guide - Production Ready with Monitoring & Security

## 📋 Overview

This guide covers deploying the YouTube Chatbot application on Kubernetes with:
- ✅ **Security**: RBAC, Network Policies, Pod Security Policies, Non-root containers
- ✅ **Monitoring**: Prometheus + Grafana for observability
- ✅ **Scalability**: Horizontal Pod Autoscaling (HPA)
- ✅ **Reliability**: Pod Disruption Budgets, Health Checks
- ✅ **Best Practices**: Resource limits, liveness/readiness probes, security contexts

## 🚀 Prerequisites

1. **Kubernetes Cluster** (v1.24+)
   ```bash
   # Check cluster version
   kubectl version --short
   ```

2. **kubectl CLI** installed and configured
   ```bash
   # Verify connection
   kubectl cluster-info
   ```

3. **NGINX Ingress Controller** (for routing)
   ```bash
   # Install with Helm
   helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
   helm install nginx-ingress ingress-nginx/ingress-nginx \
     --namespace ingress-nginx --create-namespace
   ```

4. **Container Images** pushed to registry
   - `backend:latest` (Node.js/Express)
   - `chatbot:latest` (Python/FastAPI)
   - `frontend:latest` (React/Vite)

## 📁 Deployment Structure

```
k8s/
├── namespace.yaml              # Namespace with pod security labels
├── secrets.yaml                # Sensitive data (update before apply!)
├── configmap.yaml              # Application configuration
├── ingress.yaml                # Routing with security headers
├── security/
│   ├── rbac.yaml               # Service accounts, roles, bindings
│   ├── network-policies.yaml   # Network segmentation
│   └── pod-security.yaml       # Pod security policies
├── monitoring/
│   ├── prometheus.yaml         # Prometheus server + scrape config
│   └── grafana.yaml            # Grafana dashboards
├── observability/
│   └── hpa.yaml                # Auto-scaling policies
├── backend/
│   ├── deployment.yaml         # Backend service
│   └── service.yaml
├── chatbot/
│   ├── deployment.yaml         # Chatbot service
│   └── service.yaml
├── frontend/
│   ├── deployment.yaml         # Frontend service
│   └── service.yaml
└── mongodb/
    ├── deployment.yaml         # MongoDB database
    └── service.yaml
```

## 🔧 Step 1: Update Secrets (CRITICAL!)

⚠️ **DO NOT commit with default secrets to Git!**

```bash
# Edit secrets with strong values
kubectl create secret generic app-secrets \
  --from-literal=MONGO_INITDB_ROOT_USERNAME=admin \
  --from-literal=MONGO_INITDB_ROOT_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=JWT_SECRET=$(openssl rand -base64 32) \
  --from-literal=SESSION_SECRET=$(openssl rand -base64 32) \
  --from-literal=GRAFANA_PASSWORD=$(openssl rand -base64 16) \
  --from-literal=GRAFANA_SECRET=$(openssl rand -base64 32) \
  --from-literal=GOOGLE_API_KEY="your-actual-key" \
  --from-literal=GOOGLE_SEARCH_KEY="your-actual-key" \
  --from-literal=GOOGLE_CSE_ID="your-actual-id" \
  --from-literal=MONGO_URI="mongodb://admin:PASSWORD@mongodb:27017/rag_chatbot?authSource=admin" \
  -n rag-chatbot --dry-run=client -o yaml > secrets.yaml
```

## 📦 Step 2: Apply Manifests (Recommended Order)

```bash
# 1. Create namespace with security labels
kubectl apply -f k8s/namespace.yaml

# 2. Create secrets and config
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# 3. Deploy security policies
kubectl apply -f k8s/security/rbac.yaml
kubectl apply -f k8s/security/pod-security.yaml
kubectl apply -f k8s/security/network-policies.yaml

# 4. Deploy applications in order (dependencies first)
kubectl apply -f k8s/mongodb/deployment.yaml
kubectl apply -f k8s/mongodb/service.yaml

kubectl apply -f k8s/chatbot/deployment.yaml
kubectl apply -f k8s/chatbot/service.yaml

kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/backend/service.yaml

kubectl apply -f k8s/frontend/deployment.yaml
kubectl apply -f k8s/frontend/service.yaml

# 5. Deploy monitoring and observability
kubectl apply -f k8s/monitoring/prometheus.yaml
kubectl apply -f k8s/monitoring/grafana.yaml
kubectl apply -f k8s/observability/hpa.yaml

# 6. Create ingress (routing layer)
kubectl apply -f k8s/ingress.yaml
```

Or deploy everything at once (after services are ready):
```bash
kubectl apply -f k8s/ -R
```

## 🔍 Verification

```bash
# Check namespace creation
kubectl get namespace rag-chatbot

# Verify all pods are running
kubectl get pods -n rag-chatbot -w

# Check pod readiness
kubectl get pods -n rag-chatbot -o wide
kubectl get pods -n rag-chatbot -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}'

# Check services
kubectl get svc -n rag-chatbot

# Check ingress
kubectl get ingress -n rag-chatbot

# View logs
kubectl logs -n rag-chatbot deployment/backend --tail=50 -f
kubectl logs -n rag-chatbot deployment/chatbot --tail=50 -f
kubectl logs -n rag-chatbot deployment/mongodb --tail=50 -f

# Debug pod issues
kubectl describe pod -n rag-chatbot <pod-name>
kubectl logs -n rag-chatbot <pod-name> -c <container-name>
```

## 📊 Accessing Services

### Frontend
```bash
# Port forward to access locally
kubectl port-forward -n rag-chatbot svc/frontend 3000:3000
# Visit: http://localhost:3000
```

### Prometheus Metrics
```bash
kubectl port-forward -n rag-chatbot svc/prometheus 9090:9090
# Visit: http://localhost:9090
```

### Grafana Dashboards
```bash
kubectl port-forward -n rag-chatbot svc/grafana 3000:3000
# Visit: http://localhost:3000
# Default login: admin / <GRAFANA_PASSWORD>
```

### Backend API
```bash
kubectl port-forward -n rag-chatbot svc/backend 5000:5000
# Access: http://localhost:5000/api
```

### Chatbot Service
```bash
kubectl port-forward -n rag-chatbot svc/chatbot 8000:8000
# Access: http://localhost:8000/health
```

## 🔐 Security Features Explained

### 1. **RBAC (Role-Based Access Control)**
- ServiceAccount: `app-service-account` with minimal permissions
- Roles defined for: app services, prometheus monitoring
- Prevents unauthorized API access

### 2. **Network Policies**
- Default-deny ingress (whitelist approach)
- Allow traffic only between necessary services
- External HTTPS access allowed (for APIs)
- DNS enabled for all pods

### 3. **Pod Security**
- Non-root users (UID 1001)
- Read-only root filesystem (where applicable)
- Dropped ALL Linux capabilities
- Seccomp profile: RuntimeDefault

### 4. **Container Security**
- Verified container images
- Resource limits enforced (prevent resource exhaustion)
- Health checks (liveness & readiness)
- No privileged containers

## 📈 Scaling & Auto-scaling

### Manual Scaling
```bash
# Scale backend to 4 replicas
kubectl scale deployment backend --replicas=4 -n rag-chatbot

# Scale chatbot to 2 replicas
kubectl scale deployment chatbot --replicas=2 -n rag-chatbot
```

### Auto-scaling (HPA)
- **Backend**: scales 2-5 replicas based on 70% CPU / 80% memory
- **Chatbot**: scales 1-3 replicas based on 75% CPU / 85% memory
- **Monitor HPA status**:
  ```bash
  kubectl get hpa -n rag-chatbot -w
  ```

### Pod Disruption Budgets (PDB)
- Ensures 1 pod of each service stays available during maintenance
- Kubernetes won't evict pods below PDB threshold

## 🚨 Monitoring Alerts Setup

In Prometheus (`k8s/monitoring/prometheus.yaml`), add alerting rules:

```yaml
rule_files:
  - '/etc/prometheus/rules/alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

Create `prometheus-rules.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: rag-chatbot
data:
  alerts.yml: |
    groups:
      - name: rag-chatbot
        rules:
          - alert: PodCrashLooping
            expr: rate(kube_pod_container_status_restarts_total[15m]) > 0.1
            for: 5m
            
          - alert: HighMemoryUsage
            expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
            for: 2m
```

## 🔄 Rolling Updates & Deployments

```bash
# Update image
kubectl set image deployment/backend backend=backend:v1.1 -n rag-chatbot

# Monitor rollout
kubectl rollout status deployment/backend -n rag-chatbot

# Rollback if needed
kubectl rollout undo deployment/backend -n rag-chatbot
```

## 📋 Pre-deployment Checklist

- [ ] Secrets updated with real values
- [ ] Container images built and pushed to registry
- [ ] Kubernetes cluster is running (v1.24+)
- [ ] kubectl configured and working
- [ ] NGINX Ingress Controller installed
- [ ] Persistent volumes available (for MongoDB)
- [ ] Resource quotas reviewed
- [ ] Network policies align with your use case

## ⚠️ Known Limitations

1. **Prometheus Storage**: Uses `emptyDir` (data lost on restart)
   - For production, use `PersistentVolume`

2. **Grafana Storage**: Uses `emptyDir` (dashboards lost on restart)
   - For production, mount persistent storage

3. **MongoDB**: Single replica (no HA)
   - For production, use StatefulSet with replication

4. **RBAC/PSP**: May need adjustment for your cluster
   - Check with your cluster admin

## 🛠️ Troubleshooting

### Pods stuck in `Pending`
```bash
kubectl describe pod -n rag-chatbot <pod-name>
# Check: PersistentVolume availability, node affinity, resource requests
```

### Pods in `CrashLoopBackOff`
```bash
kubectl logs -n rag-chatbot <pod-name>
# Check application logs for errors
```

### Network connectivity issues
```bash
# Test connectivity between pods
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- bash
# Inside pod: curl http://mongodb:27017
```

### Metrics not appearing in Prometheus
```bash
# Check Prometheus targets
kubectl port-forward -n rag-chatbot svc/prometheus 9090:9090
# Visit http://localhost:9090/targets
```

## 📚 Additional Resources

- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [RBAC Authorization](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

---

**Last Updated**: May 2026 | **Version**: 1.0 | **Status**: Production Ready ✅
