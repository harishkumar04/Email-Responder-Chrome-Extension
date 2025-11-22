# Alerting Setup

## What I Added:

### 🚨 Alert Rules (`monitoring/alert_rules.yml`):
- **ServiceDown**: API is unreachable for 1+ minutes
- **HighResponseTime**: 95th percentile > 5 seconds
- **HighErrorRate**: 5xx errors > 0.1/second
- **LowCacheHitRate**: Cache hit rate < 50%
- **AIServiceFailure**: 5+ AI failures in 5 minutes

### 📊 Enhanced Metrics:
- `cache_hits_total` - Cache performance tracking
- `cache_misses_total` - Cache miss tracking  
- `ai_generation_failures_total` - AI failure tracking
- `http_requests_total` - Now includes status codes

### 🔔 Alertmanager (`monitoring/alertmanager.yml`):
- Webhook notifications to your API
- Email notifications (configure SMTP)
- Alert grouping and deduplication

### 🎯 Alert Webhook (`/webhook/alerts`):
- Receives alerts from Alertmanager
- Logs all alerts
- Ready for Slack/Discord integration

## Quick Start:

```bash
# Start with alerting
docker-compose up -d

# Check services
curl http://localhost:8000/health    # API
curl http://localhost:9090           # Prometheus  
curl http://localhost:9093           # Alertmanager
curl http://localhost:3000           # Grafana
```

## View Alerts:
- **Prometheus**: http://localhost:9090/alerts
- **Alertmanager**: http://localhost:9093
- **Your API logs**: Check for "ALERT" messages

## Test Alerts:
```bash
# Stop API to trigger ServiceDown alert
docker-compose stop fastapi

# Check alert in 1 minute at:
# http://localhost:9093
```

## Add Slack Notifications:
Update `monitoring/alertmanager.yml`:
```yaml
receivers:
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: 'Email Responder Alert'
        text: '{{ .CommonAnnotations.summary }}'
```

You now have production-grade alerting! 🎉
