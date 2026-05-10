# Alerting Documentation - YouTube RAG Chatbot

## 1. Overview of Alerting Strategy

The YouTube RAG chatbot implements comprehensive alerting to detect and notify operators of issues affecting service availability, performance, and reliability. Alerts are organized into three categories:

- **Pod Health**: Container and pod-level availability issues
- **Chatbot Performance**: Application-level query latency and error rates
- **Infrastructure**: System resource constraints and external dependencies

Alert rules are configured in **Prometheus** and evaluated every 15 seconds. Firing alerts are visualized in Grafana and can trigger notifications (email, Slack, PagerDuty).

---

## 2. Alert Rules File Location

```
k8s/alerting-rules.yaml
```

This file contains a Kubernetes ConfigMap with Prometheus alert rules. The ConfigMap is mounted into the Prometheus pod and automatically loaded on startup.

```bash
# View alert rules
kubectl get configmap prometheus-alert-rules -n rag-chatbot -o yaml

# Update alert rules
kubectl apply -f k8s/alerting-rules.yaml

# Verify rules loaded
kubectl exec prometheus-0 -n rag-chatbot -- curl http://localhost:9090/api/v1/rules | jq '.data.groups'
```

---

## 3. Alert Rules Reference

### Alert 1: PodNotReady

| Attribute | Value |
|-----------|-------|
| **Name** | `PodNotReady` |
| **Condition** | Pod ready status = 0 for 1 minute |
| **Severity** | 🔴 Critical |
| **What it means** | A pod has been unable to become ready for over 1 minute (likely crash, misconfiguration, or resource constraint) |

**When triggered:**
- Pod fails liveness probe
- Container fails to start
- Image pull fails
- Resource limits exceeded
- Dependencies unavailable (e.g., MongoDB not ready)

**How to investigate:**
```bash
# Get pod status
kubectl get pods -n rag-chatbot

# Describe pod for events
kubectl describe pod <pod-name> -n rag-chatbot

# Check logs
kubectl logs <pod-name> -n rag-chatbot

# Check previous logs if pod is restarting
kubectl logs <pod-name> --previous -n rag-chatbot
```

**How to resolve:**
1. Read pod description events (usually explain the issue)
2. Check application logs for startup errors
3. Verify environment variables and secrets are set
4. Check resource requests/limits vs available cluster resources
5. For MongoDB pod: Check PVC status and storage
6. For other pods: Check dependency pods (MongoDB) are ready first

---

### Alert 2: PodCrashLooping

| Attribute | Value |
|-----------|-------|
| **Name** | `PodCrashLooping` |
| **Condition** | Container restart rate > 0 continuously for 5 minutes |
| **Severity** | 🔴 Critical |
| **What it means** | A container repeatedly crashes and restarts (application bug, misconfiguration, or external dependency issue) |

**When triggered:**
- Application throws unhandled exception
- Container exits with non-zero code
- Liveness probe fails repeatedly
- Environment variable missing (app can't start)
- API key invalid or expired

**How to investigate:**
```bash
# Check restart count and events
kubectl describe pod <pod-name> -n rag-chatbot

# Get logs from previous crash
kubectl logs <pod-name> --previous -n rag-chatbot

# Watch logs in real-time while pod crashes
kubectl logs <pod-name> -n rag-chatbot -f

# Get the exit code
kubectl get pod <pod-name> -n rag-chatbot -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'
```

**How to resolve:**
1. **Exit code 1**: Application error - check logs, fix bug
2. **Exit code 127**: Command not found - check Dockerfile CMD/ENTRYPOINT
3. **Exit code 134**: SIGABRT - memory issue or assertion failure
4. **Exit code 137**: SIGKILL - OOMKilled (increase memory limit)
5. **Environment issues**: 
   ```bash
   kubectl describe secret chatbot-secrets -n rag-chatbot  # Check secrets exist
   kubectl get cm -n rag-chatbot  # Check config maps
   ```

---

### Alert 3: HighQueryLatency

| Attribute | Value |
|-----------|-------|
| **Name** | `HighQueryLatency` |
| **Condition** | P95 query latency > 10 seconds for 2 minutes |
| **Severity** | 🟡 Warning |
| **What it means** | 95% of queries are taking >10 seconds (users experiencing slow responses, likely external API delay) |

**When triggered:**
- Google Gemini API is slow or rate-limited
- Embedding model (sentence-transformers) is slow
- Database query is slow (MongoDB overload)
- Network latency between services

**How to investigate:**
```bash
# Check latency in Grafana
http://localhost:3001 → Dashboard → Query Latency p95

# Check which queries are slow
kubectl logs -n rag-chatbot -l app=chatbot --tail=100 | grep "duration"

# Check Gemini API status
# See https://status.cloud.google.com/

# Check if MongoDB is responding
kubectl exec chatbot-0 -n rag-chatbot -- curl -v mongodb:27017

# Check network latency between pods
kubectl exec backend-0 -n rag-chatbot -- ping -c 3 chatbot-0
```

**How to resolve:**
1. **Check Gemini API quota**:
   ```bash
   kubectl logs -n rag-chatbot -l app=chatbot | grep "quota\|rate_limit\|429"
   ```
2. **Reduce prompt/context size** to speed up embeddings
3. **Enable query caching** to avoid re-processing identical queries
4. **Increase chatbot pod memory/CPU** if CPU-bound
5. **Check MongoDB performance**:
   ```bash
   kubectl exec mongodb-0 -n rag-chatbot -- mongosh admin --eval "db.currentOp()"
   ```
6. **Wait for API to recover** (usually 5-30 minutes)

---

### Alert 4: HighErrorRate

| Attribute | Value |
|-----------|-------|
| **Name** | `HighErrorRate` |
| **Condition** | Errors/total queries > 5% for 2 minutes |
| **Severity** | 🟡 Warning |
| **What it means** | More than 5% of queries are failing (API key issue, invalid input, or service degradation) |

**When triggered:**
- Google API key invalid or expired
- API quota exceeded
- Malformed user input causing validation errors
- MongoDB connection lost
- External API unreachable

**How to investigate:**
```bash
# Check error rate in Grafana
http://localhost:3001 → Dashboard → Error Rate

# Get recent errors from chatbot logs
kubectl logs -n rag-chatbot -l app=chatbot --tail=200 | grep -i error

# Check error breakdown by type
kubectl logs -n rag-chatbot -l app=chatbot | grep -oP 'error_type=\K[^}]+' | sort | uniq -c

# Verify API key is set
kubectl get secret chatbot-secrets -n rag-chatbot -o jsonpath='{.data.GOOGLE_API_KEY}' | base64 -d

# Test API key validity
kubectl exec chatbot-0 -n rag-chatbot -- python3 -c "
import google.generativeai as genai
genai.configure(api_key='$GOOGLE_API_KEY')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('test')
print('API key valid')
"
```

**How to resolve:**
1. **Check Google API key**:
   - Verify key is set in K8s secret
   - Verify key hasn't been rotated/revoked
   - Check quota on Google Cloud console
   - If quota exceeded, wait 24 hours or increase quota

2. **Check logs for specific error**:
   ```bash
   kubectl logs -n rag-chatbot -l app=chatbot | grep -i "401\|403\|429"
   # 401 = Invalid key
   # 403 = Quota exceeded  
   # 429 = Rate limit hit
   ```

3. **Restart chatbot to clear any cached state**:
   ```bash
   kubectl rollout restart deployment chatbot -n rag-chatbot
   ```

---

### Alert 5: HighMemoryUsage

| Attribute | Value |
|-----------|-------|
| **Name** | `HighMemoryUsage` |
| **Condition** | Container memory > 80% of limit for 5 minutes |
| **Severity** | 🟡 Warning |
| **What it means** | A container is approaching its memory limit (risk of OOMKill if it reaches 100%) |

**When triggered:**
- Application has memory leak
- Large dataset loaded into memory
- Too many active sessions
- Inappropriate resource request/limit configuration

**How to investigate:**
```bash
# Check current memory usage
kubectl top pods -n rag-chatbot

# Get memory limits for all pods
kubectl get pods -n rag-chatbot -o custom-columns=NAME:.metadata.name,MEM_REQ:.spec.containers[0].resources.requests.memory,MEM_LIM:.spec.containers[0].resources.limits.memory

# Check memory trend in Grafana
http://localhost:3001 → Dashboard → Backend Memory

# Monitor memory usage over time
watch -n 5 'kubectl top pods -n rag-chatbot'

# For chatbot pod, check if it's a memory leak
kubectl logs -n rag-chatbot -l app=chatbot --tail=50 | grep -i "memory\|gc"
```

**How to resolve:**
1. **Short term**: Restart pod to clear memory
   ```bash
   kubectl rollout restart deployment chatbot -n rag-chatbot
   ```

2. **If leak suspected**:
   - Review recent code changes for memory leaks
   - Check for circular references, event listener cleanup
   - Monitor memory trend after restart

3. **Increase resource limit** (only if truly needed):
   ```yaml
   # Edit deployment
   kubectl edit deployment chatbot -n rag-chatbot
   
   # Change limits.memory from 1Gi to 2Gi
   # Save and exit (triggers pod restart)
   ```

4. **Optimize application**:
   - Reduce cache size
   - Stream responses instead of buffering
   - Add session cleanup background job
   - Profile with memory debugger

---

### Alert 6: MongoDBDown

| Attribute | Value |
|-----------|-------|
| **Name** | `MongoDBDown` |
| **Condition** | MongoDB statefulset ready replicas = 0 for 1 minute |
| **Severity** | 🔴 Critical |
| **What it means** | MongoDB has no running instances (database completely unavailable, all services will fail) |

**When triggered:**
- MongoDB container crashes on startup
- Liveness/readiness probe fails
- PersistentVolumeClaim (PVC) is not bound or full
- Insufficient resources to run MongoDB
- Configuration error in StatefulSet

**How to investigate:**
```bash
# Check StatefulSet status
kubectl get statefulset mongodb -n rag-chatbot
kubectl describe statefulset mongodb -n rag-chatbot

# Check pod status
kubectl get pods -n rag-chatbot -l app=mongodb
kubectl describe pod mongodb-0 -n rag-chatbot

# Check logs (often contains real error)
kubectl logs mongodb-0 -n rag-chatbot

# Get previous logs if pod crashed
kubectl logs mongodb-0 --previous -n rag-chatbot

# Check events for more details
kubectl get events -n rag-chatbot --sort-by='.lastTimestamp'

# Check PVC status
kubectl get pvc -n rag-chatbot
kubectl describe pvc mongodb-data -n rag-chatbot

# Check disk space on PVC
kubectl exec mongodb-0 -n rag-chatbot -- df -h /data
```

**How to resolve:**

**Issue 1: Readiness Probe Timeout** (Common)
```bash
# Symptoms: logs show probe failures, pod not ready
# Solution: Increase probe timeout in StatefulSet
kubectl edit statefulset mongodb -n rag-chatbot

# Change readinessProbe.initialDelaySeconds from 5 to 30
# Change readinessProbe.timeoutSeconds from 2 to 10

# Save and MongoDB will restart with new probes
```

**Issue 2: PVC Not Bound**
```bash
# Check if PVC is pending
kubectl describe pvc mongodb-data -n rag-chatbot

# If pending:
# 1. Check StorageClass exists
kubectl get storageclass

# 2. If no storage available, create manually:
kubectl apply -f k8s/mongodb/pvc.yaml
```

**Issue 3: Out of Storage**
```bash
# Check disk usage
kubectl exec mongodb-0 -n rag-chatbot -- du -sh /data

# If full, need to delete old data or expand PVC
# Option A: Delete and restart (loses data)
kubectl delete pvc mongodb-data -n rag-chatbot
kubectl rollout restart statefulset mongodb -n rag-chatbot

# Option B: Expand PVC
kubectl patch pvc mongodb-data -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}' -n rag-chatbot
```

**Issue 4: MongoDB Container Crashes**
```bash
# Check logs for specific error
kubectl logs mongodb-0 --previous -n rag-chatbot | tail -50

# Common errors:
# - "replication configured but no replSetName" → fix k8s/mongodb/statefulset.yaml
# - "cannot write, not replicated" → replica set not initialized
# - "keyfile does not have correct permissions" → chmod 400 needed

# If corrupted, full restart:
kubectl delete pod mongodb-0 -n rag-chatbot --grace-period=0 --force
kubectl rollout restart statefulset mongodb -n rag-chatbot
```

**Nuclear Option** (if all else fails):
```bash
# Delete MongoDB completely and restart from scratch
kubectl delete statefulset mongodb -n rag-chatbot
kubectl delete svc mongodb -n rag-chatbot
kubectl delete pvc mongodb-data -n rag-chatbot

# Wait 30 seconds
sleep 30

# Redeploy MongoDB
kubectl apply -f k8s/mongodb/
```

---

## 4. How to Add New Alerts

### Creating a New Alert

**Step 1: Define alert condition**
```yaml
- alert: MyNewAlert
  expr: my_metric > 100  # Prometheus query
  for: 5m  # Duration before firing
  labels:
    severity: warning  # critical/warning/info
  annotations:
    summary: "Short description of alert"
    description: "Detailed explanation of what happened and what to check"
```

**Step 2: Add to alerting-rules.yaml**
- Edit `k8s/alerting-rules.yaml`
- Add to appropriate group (pod-health, chatbot-performance, infrastructure)

**Step 3: Reload alert rules**
```bash
kubectl apply -f k8s/alerting-rules.yaml
```

**Step 4: Verify alert loaded**
```bash
# Check Prometheus UI for new alert
http://localhost:9090/alerts

# Or query API
kubectl exec prometheus-0 -n rag-chatbot -- curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="chatbot-performance")'
```

**Step 5: Create corresponding runbook entry** in ALERTS.md (this file)

### Alert Writing Best Practices

1. **Use meaningful metric names** - e.g., `chatbot_errors_total`, not `errors`
2. **Include labels for context** - e.g., `{mode="qa"}` to distinguish error types
3. **Set appropriate `for` duration** - avoid flapping
   - Critical: 1-2 minutes (fast detection)
   - Warning: 5-10 minutes (allow temporary spikes)
4. **Write clear annotations**
   - Summary: 1-line description
   - Description: Multi-line with remediation steps
5. **Test before deploying**
   - Use Prometheus UI to test PromQL query
   - Verify alert triggers when condition met

---

## 5. Current Firing Alerts (Known Issues)

### Alert: MongoDBDown ⚠️ Firing

**Status**: Actively firing

**Reason**: MongoDB StatefulSet readiness probe is timing out

**Details**:
- MongoDB pod becomes ready after ~20 seconds (liveness probe timeout is 2 seconds)
- Probe fails → pod marked NotReady
- Probe continues to fail → never reaches Ready state

**Temporary Solution**:
```bash
# Increase probe timeout
kubectl edit statefulset mongodb -n rag-chatbot

# Under readinessProbe section, change:
# timeoutSeconds: 2  → 10
# initialDelaySeconds: 5 → 30

# Save and exit (MongoDB will restart)
```

**Permanent Fix**:
- Update `k8s/mongodb/statefulset.yaml` with increased probe values
- Commit to Git
- Redeploy

### Alert: PodCrashLooping ⚠️ Firing (for chatbot)

**Status**: Actively firing

**Reason**: Chatbot pod cannot start because MongoDB is not ready

**Details**:
- Chatbot tries to connect to MongoDB on startup
- MongoDB is down (probe issue)
- Chatbot exits with connection error
- K8s restarts chatbot
- Cycle repeats (crash loop)

**Resolution**: Fix MongoDB alert first → chatbot will automatically start

---

## 6. Alert Configuration in Grafana

### Enable Alert Notifications

**Step 1: Add Notification Channel**
```
Grafana UI → Configuration (gear icon) → Notification channels
```

**Step 2: Create Channel**
- Type: Email / Slack / PagerDuty / Webhook
- Name: "devops-oncall"
- Send to: ops-team@example.com (or Slack #alerts)

**Step 3: Set as Default**
- Check "Send on all alerts"

### Connect Prometheus Alerts to Grafana

**Step 1: Go to Alerting Settings**
```
Grafana UI → Configuration → Alerting
```

**Step 2: Add Alert Evaluation**
- Prometheus datasource should auto-detect alerts from ConfigMap

**Step 3: Set Alert Rules File**
```
Grafana UI → Dashboards → RAG Chatbot
→ Alert Rules → Link Prometheus alerts to dashboard panels
```

---

## 7. Alert Metrics by Severity

### Critical Alerts (Immediate Action Required)
| Alert | Impact | MTTR |
|-------|--------|------|
| PodNotReady | Service unavailable | <5 min |
| PodCrashLooping | Service unavailable | <5 min |
| MongoDBDown | Total data loss | <5 min |

### Warning Alerts (Investigate Soon)
| Alert | Impact | MTTR |
|-------|--------|------|
| HighQueryLatency | Poor user experience | <15 min |
| HighErrorRate | Degraded functionality | <15 min |
| HighMemoryUsage | Risk of future crash | <30 min |

---

## 8. Testing Alerts

### Trigger Alert Manually (for testing)

**Test HighQueryLatency:**
```bash
# Simulate slow API response
kubectl port-forward -n rag-chatbot svc/chatbot 8000:8000 &

# Make slow request
time curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Long prompt..."}'

# Check if alert fires after 2 minutes
http://localhost:9090/alerts
```

**Test PodNotReady:**
```bash
# Delete MongoDB pod to trigger alert
kubectl delete pod mongodb-0 -n rag-chatbot

# Observe:
# - MongoDB pod stays NotReady for 1+ minutes
# - PodNotReady alert fires
# - Pod eventually recovers

# Verify alert clears
http://localhost:9090/alerts
```

---

## 9. Resources

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/overview/)
- [Prometheus Query Language (PromQL)](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Kubernetes Monitoring Best Practices](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-metrics-pipeline/)
- [Alert Writing Best Practices](https://runbooks.dev/)
