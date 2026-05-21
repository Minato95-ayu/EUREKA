#!/bin/bash
# EUREKA Deploy Script
# Usage: ./scripts/deploy.sh [local|staging|production]

set -e

ENVIRONMENT=${1:-local}

echo "🚀 EUREKA Deployment - $ENVIRONMENT"
echo "===================================="

case $ENVIRONMENT in
  local)
    echo "📦 Deploying locally with Docker Compose..."
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo ""
    echo "⏳ Waiting for services..."
    sleep 15
    echo "🏥 Health check..."
    curl -sf http://localhost:8000/health && echo " ✅ Backend healthy" || echo " ❌ Backend not ready"
    echo ""
    echo "✅ Local deployment complete!"
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend:   http://localhost:8000/docs"
    ;;

  staging|production)
    echo "☸️  Deploying to Kubernetes ($ENVIRONMENT)..."
    
    # Build and push images
    echo "🔨 Building images..."
    docker build -t eureka/backend:latest ./eureka-backend
    docker build -t eureka/frontend:latest ./eureka-frontend
    
    # Deploy with Helm
    echo "📦 Deploying with Helm..."
    helm upgrade --install eureka ./helm/eureka \
      --namespace eureka \
      --create-namespace \
      --values helm/eureka/values.yaml
    
    # Verify
    echo "⏳ Verifying deployment..."
    kubectl rollout status deployment/eureka-backend -n eureka
    kubectl rollout status deployment/eureka-frontend -n eureka
    
    echo ""
    echo "✅ $ENVIRONMENT deployment complete!"
    ;;

  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    echo "Usage: ./scripts/deploy.sh [local|staging|production]"
    exit 1
    ;;
esac
