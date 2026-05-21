# EUREKA Deployment Guide

## Local Development (Docker)

```bash
# Clone and start
git clone https://github.com/Minato95-ayu/EUREKA.git
cd EUREKA
docker-compose up -d

# Pull LLM model
docker-compose exec ollama ollama pull llama3

# Access
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000/docs
# Ollama:    http://localhost:11434
```

## Production Deployment

### AWS (EKS)

```bash
# 1. Create EKS cluster
eksctl create cluster --name eureka --region us-east-1 --nodes 3

# 2. Create namespace and secrets
kubectl create namespace eureka
kubectl create secret generic eureka-secrets \
  --from-literal=database-url=$DATABASE_URL \
  -n eureka

# 3. Deploy with Helm
helm install eureka ./helm/eureka \
  --namespace eureka \
  --values helm/eureka/values.yaml

# 4. Apply ingress
kubectl apply -f kubernetes/ingress.yaml

# 5. Verify
kubectl rollout status deployment/eureka-backend -n eureka
```

### GCP (GKE)

```bash
# 1. Create GKE cluster
gcloud container clusters create eureka \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2

# 2. Get credentials
gcloud container clusters get-credentials eureka --zone us-central1-a

# 3. Deploy
helm install eureka ./helm/eureka \
  --namespace eureka \
  --create-namespace

# 4. Setup Cloud SQL
gcloud sql instances create eureka-db \
  --database-version POSTGRES_15 \
  --tier db-f1-micro \
  --region us-central1
```

## Kubernetes Resources

| Resource | File | Description |
|----------|------|-------------|
| Namespace | `kubernetes/namespace.yaml` | `eureka` namespace |
| Backend | `kubernetes/backend-deployment.yaml` | 3 replicas, probes |
| Frontend | `kubernetes/frontend-deployment.yaml` | 2 replicas |
| Services | `kubernetes/*-service.yaml` | ClusterIP services |
| HPA | `kubernetes/hpa.yaml` | Auto-scale 3→10 pods |
| Ingress | `kubernetes/ingress.yaml` | TLS + cert-manager |

## Monitoring

```bash
# Start ELK stack
docker-compose -f docker-compose-elk.yml up -d

# Prometheus is configured in monitoring/prometheus.yml
# Alert rules in monitoring/alert_rules.yml
```

## SSL/TLS Setup

1. Place certificates in `ssl/` directory:
   - `ssl/cert.pem` — SSL certificate
   - `ssl/key.pem` — Private key
2. Nginx is pre-configured for TLS 1.2/1.3

## Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Detailed (DB + Redis + Ollama)
curl http://localhost:8000/health/detailed

# Kubernetes readiness
curl http://localhost:8000/health/ready
```

## Backup & Recovery

```bash
# Database backup
docker-compose exec postgres pg_dump -U eureka eureka_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U eureka eureka_db < backup.sql
```
