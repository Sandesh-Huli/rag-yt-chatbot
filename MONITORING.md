# Monitoring Documentation - YouTube RAG Chatbot

## 1. Overview

The YouTube RAG chatbot implements comprehensive monitoring using **Prometheus** for metrics collection and **Grafana** for visualization and dashboarding.

### Deployment Status
- **Docker Compose**: ✅ Fully working - Prometheus and Grafana running, all services exporting metrics
- **Kubernetes**: ✅ Prometheus and Grafana running, chatbot pending (blocked by MongoDB crash loop)

### Components
- **Prometheus**: Time-series metrics database (port 9090)
- **Grafana**: Visualization and alerting platform (port 3001)
- **Exporters**: 
  - Backend (Node.js): prom-client library
  - Chatbot (Python): prometheus-client library
  - MongoDB: External mongodb-exporter sidecar (planned)

---

## 2. Architecture

### Monitoring Data Flow

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Backend    │         │   Chatbot    │         │  MongoDB     │
│  (Node.js)   │         │  (FastAPI)   │         │   (Service)  │
│  :5000/      │         │  :8000/      │         │   (tracked)  │
│  metrics     │         │  metrics     │         │              │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       └────────────────┬───────┴────────────────┬───────┘
                        │                        │
                  (scrape @ 15s)            (scrape @ 15s)
                        │                        │
                 ┌──────▼──────────────┐        │
                 │   Prometheus       │◄───────┘
                 │  (Time-series DB)  │
                 │   :9090            │
                 └──────┬──────────────┘
                        │
                   (query via API)
                        │
                 ┌──────▼──────────────┐
                 │     Grafana        │
                 │  (Dashboards)      │
                 │   :3001            │
                 │  (admin/admin)     │
                 └────────────────────┘
```

---

## 3. How to Access

### Prometheus
- **URL**: http://localhost:9090
- **Targets Page**: http://localhost:9090/targets
- **Query Console**: http://localhost:9090/graph

### Grafana
- **URL**: http://localhost:3001
- **Username**: `admin`
- **Password**: `admin`
- **Datasource**: Prometheus (auto-configured)

### Verify All Targets Are Scraping

Visit http://localhost:9090/targets and verify all 3 targets show **UP** status:

| Target | Endpoint | Status | Scrape Interval |
|--------|----------|--------|-----------------|
| Backend | http://backend:5000/metrics | UP | 15s |
| Chatbot | http://chatbot:8000/metrics | UP | 15s |
| Prometheus | http://prometheus:9090/metrics | UP | 15s |

---

## 4. Metrics Exposed by Chatbot Service (Python)

### Custom Metrics

**1. `chatbot_queries_total` (Counter)**
- **Type**: Counter (monotonically increasing)
- **Labels**: `mode` (qa, summarize, translate)
- **Purpose**: Total number of queries processed by mode
- **Example**:
  ```
  chatbot_queries_total{mode="qa"} 45
  chatbot_queries_total{mode="summarize"} 12
  chatbot_queries_total{mode="translate"} 8
  ```

**2. `chatbot_query_duration_seconds` (Histogram)**
- **Type**: Histogram (with buckets)
- **Labels**: `mode`
- **Purpose**: Query processing time distribution (p50, p95, p99)
- **Buckets**: 0.1, 0.5, 1, 2, 5, 10 seconds
- **Example**:
  ```
  chatbot_query_duration_seconds_bucket{le="0.5",mode="qa"} 10
  chatbot_query_duration_seconds_bucket{le="1",mode="qa"} 32
  chatbot_query_duration_seconds_bucket{le="10",mode="qa"} 45
  chatbot_query_duration_seconds_sum{mode="qa"} 87.3
  chatbot_query_duration_seconds_count{mode="qa"} 45
  ```

**3. `chatbot_errors_total` (Counter)**
- **Type**: Counter
- **Labels**: `error_type` (api_error, validation_error, timeout, unknown)
- **Purpose**: Total errors by type
- **Example**:
  ```
  chatbot_errors_total{error_type="api_error"} 2
  chatbot_errors_total{error_type="timeout"} 1
  ```

**4. `chatbot_active_sessions` (Gauge)**
- **Type**: Gauge (can go up/down)
- **Purpose**: Current active user sessions
- **Example**:
  ```
  chatbot_active_sessions 7
  ```

### Process Metrics (Auto-exported)

```
# Memory
process_resident_memory_bytes 125000000
process_virtual_memory_bytes 500000000

# CPU
process_cpu_seconds_total 45.3

# File descriptors
process_open_fds 32

# Python garbage collection
python_gc_collections_total{generation="0"} 123
python_gc_collected_objects_total 5000
```

---

## 5. Metrics Exposed by Backend Service (Node.js)

### Custom Metrics

**1. `backend_http_requests_total` (Counter)**
- **Type**: Counter
- **Labels**: `method` (GET, POST, PUT, DELETE), `route`, `status_code`
- **Purpose**: Total HTTP requests by method and endpoint
- **Example**:
  ```
  backend_http_requests_total{method="POST",route="/api/chat",status_code="200"} 45
  backend_http_requests_total{method="GET",route="/api/users",status_code="200"} 128
  ```

**2. `backend_http_request_duration_ms` (Histogram)**
- **Type**: Histogram
- **Labels**: `method`, `route`
- **Purpose**: Request latency distribution
- **Example**:
  ```
  backend_http_request_duration_ms_bucket{le="100",route="/api/chat"} 30
  backend_http_request_duration_ms_bucket{le="1000",route="/api/chat"} 44
  ```

### Process Metrics (Auto-exported)

```
# Memory (resident set size in bytes)
process_resident_memory_bytes 87000000

# CPU
process_cpu_seconds_total 23.5

# Event loop
nodejs_eventloop_lag_seconds 0.001

# GC
nodejs_gc_duration_seconds_bucket{le="0.01",kind="MarkSweepCompact"} 5
```

---

## 6. Grafana Dashboard Panels

### Dashboard Overview

A production monitoring dashboard has been configured with 6 key panels for observability.

#### **Panel 1: Query Rate by Mode**

**Purpose**: Track query volume over time by mode (qa/summarize/translate)

**PromQL Query**:
```promql
rate(chatbot_queries_total[5m])
```

**Configuration**:
- **Type**: Time series (Line graph)
- **Legend**: `{{mode}}` (shows qa, summarize, translate as separate lines)
- **Y-axis**: Queries/sec
- **Time range**: Last 1 hour

**What to look for**:
- Normal patterns: steady-state usage during business hours
- Spikes: traffic surges (feature releases, viral content)
- Drops: service degradation or user issues

---

#### **Panel 2: Query Latency p95**

**Purpose**: Monitor query response time at 95th percentile (p95)

**PromQL Query**:
```promql
histogram_quantile(0.95, rate(chatbot_query_duration_seconds_bucket[5m]))
```

**Configuration**:
- **Type**: Gauge (or Time series)
- **Thresholds**: 
  - 🟢 Green: 0-5 seconds (acceptable)
  - 🟡 Yellow: 5-10 seconds (degraded)
  - 🔴 Red: >10 seconds (critical)
- **Unit**: Seconds

**What to look for**:
- Baseline latency: Should be consistent
- Degradation: May indicate Gemini API slowdown or overload
- Spikes: Check if correlated with traffic spikes

---

#### **Panel 3: Error Rate**

**Purpose**: Monitor percentage of queries that fail

**PromQL Query**:
```promql
rate(chatbot_errors_total[5m]) / rate(chatbot_queries_total[5m]) * 100
```

**Configuration**:
- **Type**: Time series (Line graph)
- **Y-axis**: % (0-100%)
- **Alert threshold**: >5% for 2 minutes

**What to look for**:
- Baseline error rate: Usually 0-1% (network glitches)
- Spike >5%: Critical issue - check logs
- Trending up: Application degradation over time

---

#### **Panel 4: Backend Request Rate**

**Purpose**: Track backend API request volume (all endpoints combined)

**PromQL Query**:
```promql
rate(backend_http_requests_total[5m])
```

**Configuration**:
- **Type**: Time series (Area graph)
- **Legend**: Shows by status code (200, 400, 500)
- **Y-axis**: Requests/sec

**What to look for**:
- Normal load: Steady baseline
- 4xx errors: Client issues (bad input)
- 5xx errors: Server problems (must investigate)

---

#### **Panel 5: Active Sessions**

**Purpose**: Monitor concurrent active user sessions

**PromQL Query**:
```promql
chatbot_active_sessions
```

**Configuration**:
- **Type**: Stat (single number display)
- **Color**:
  - 🟢 Green: 0-50 users
  - 🟡 Yellow: 50-100 users
  - 🔴 Red: >100 users

**What to look for**:
- Normal range: 10-30 concurrent users during peak
- Spike: Potential viral moment or bot activity
- Zero: Service down or metrics collection stopped

---

#### **Panel 6: Backend Memory Usage**

**Purpose**: Monitor memory consumption of backend process

**PromQL Query**:
```promql
process_resident_memory_bytes{job="backend"} / 1024 / 1024
```

**Configuration**:
- **Type**: Gauge
- **Unit**: MB
- **Thresholds**:
  - 🟢 Green: 0-200 MB
  - 🟡 Yellow: 200-300 MB
  - 🔴 Red: >300 MB
- **Max**: 512 MB (container limit)

**What to look for**:
- Baseline: Usually 50-100 MB
- Gradual increase: Memory leak (restart needed)
- Sudden spike: Load spike or bug

---

## 7. Prometheus Configuration

### Configuration File Location
```
monitoring/prometheus.yml
```

### Scrape Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:5000']
    metrics_path: '/metrics'

  - job_name: 'chatbot'
    static_configs:
      - targets: ['chatbot:8000']
    metrics_path: '/metrics'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `scrape_interval` | 15s | Collect metrics every 15 seconds |
| `evaluation_interval` | 15s | Evaluate alert rules every 15s |
| `retention_period` | 15d | Keep metrics for 15 days |
| `memory_limit` | 512M | Max memory for Prometheus process |

---

## 8. How to Verify Metrics Are Working

### Step 1: Check Prometheus Targets
```bash
# Visit http://localhost:9090/targets
# Expected: All 3 targets show status=UP
```

### Step 2: Query Raw Metrics in Prometheus
```bash
# Go to http://localhost:9090/graph
# Enter query: chatbot_queries_total
# Click "Execute"
# Expected: See counter values for each mode
```

### Step 3: Send a Chat Message and Verify Metrics Update
```bash
# Send a chat request to backend
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Summarize the video","mode":"summarize"}'

# Check metrics incremented
curl http://localhost:8000/metrics | grep chatbot_queries_total

# Expected output:
# chatbot_queries_total{mode="summarize"} 1
# (value increases on each request)
```

### Step 4: Verify Grafana Datasource Connection
```bash
# Go to http://localhost:3001/datasources
# Click "Prometheus"
# Click "Test" button
# Expected: Success message "Data source is working"
```

### Step 5: View Dashboard
```bash
# Go to http://localhost:3001
# Navigate to RAG Chatbot Dashboard
# Expected: All 6 panels show data (not "No data" errors)
```

---

## 9. Common Prometheus Queries

### Query Examples for Troubleshooting

**1. Query rate over 5 minutes:**
```promql
rate(chatbot_queries_total[5m])
```

**2. Top 5 errors by type:**
```promql
topk(5, chatbot_errors_total)
```

**3. 99th percentile latency:**
```promql
histogram_quantile(0.99, rate(chatbot_query_duration_seconds_bucket[5m]))
```

**4. Memory usage in MB:**
```promql
process_resident_memory_bytes / 1024 / 1024
```

**5. Error rate as percentage:**
```promql
(rate(chatbot_errors_total[5m]) / rate(chatbot_queries_total[5m])) * 100
```

**6. HTTP status code distribution:**
```promql
sum by (status_code) (rate(backend_http_requests_total[5m]))
```

---

## 10. Known Limitations

### Current Issues

1. **MongoDB Metrics Not Exposed**
   - MongoDB service is not exporting Prometheus metrics
   - Solution: Deploy mongodb-exporter sidecar container
   - Estimated metrics needed: connection count, operation latency, replication lag

2. **K8s Chatbot Pod Pending**
   - Blocked by MongoDB crash loop (liveness probe timeout)
   - Metrics not available until MongoDB stabilizes

3. **No Histogram Percentiles in Node.js Backend**
   - Backend exports histogram for response time but limited buckets
   - Consider: Adding explicit p50/p95/p99 gauges

4. **Alerting Rules Stored Separately**
   - Alert rules in `k8s/alerting-rules.yaml` (not yet configured)
   - Prometheus ConfigMap must mount this file

### Future Enhancements

- [ ] Add mongodb-exporter for database metrics
- [ ] Export custom business metrics (e.g., video processing time)
- [ ] Add Prometheus remote storage (for long-term retention beyond 15 days)
- [ ] Configure Grafana alerting channels (email, Slack)
- [ ] Create SLO/SLI dashboards (availability, latency, error rate targets)
- [ ] Add distributed tracing (Jaeger/Tempo) for trace correlation

---

## 11. Dashboard Management

### Accessing Dashboards in Grafana

```
http://localhost:3001
→ Dashboards (left sidebar)
→ RAG Chatbot Monitoring
```

### Creating Custom Panels

**Steps:**
1. Go to Dashboard → Edit
2. Click "+ Add panel"
3. Enter PromQL query
4. Customize visualization (time series, gauge, stat, etc.)
5. Set thresholds and alerts
6. Save panel

### Exporting Dashboard

```bash
# Dashboard JSON can be exported from Grafana UI
# Settings (dashboard) → Export → Save JSON
# Import to another Grafana instance:
# Create → Import → Paste JSON
```

---

## 12. Troubleshooting

### Prometheus Shows "No Data"
1. Check if scrape targets are UP: http://localhost:9090/targets
2. Verify service metrics endpoints:
   ```bash
   curl http://localhost:8000/metrics  # Chatbot
   curl http://localhost:5000/metrics  # Backend
   ```
3. Check Prometheus logs: `docker logs rag-chatbot-prometheus`

### Grafana Dashboard Shows Blank Panels
1. Verify Prometheus datasource is connected (Settings → Datasources → Test)
2. Check if queries return data (go to Prometheus and run query manually)
3. Check graph time range (default: Last 6 hours)

### High Memory Usage in Prometheus
1. Check retention period: `monitoring/prometheus.yml` → `retention`
2. Reduce if >15 days
3. Restart Prometheus: `docker restart rag-chatbot-prometheus`

---

## 13. Metrics Collection Endpoints

| Service | Endpoint | Port | Path |
|---------|----------|------|------|
| Backend | http://localhost:5000/metrics | 5000 | `/metrics` |
| Chatbot | http://localhost:8000/metrics | 8000 | `/metrics` |
| Prometheus | http://localhost:9090/metrics | 9090 | `/metrics` |

Verify all endpoints return Prometheus format (TYPE, HELP comments followed by metric lines).
