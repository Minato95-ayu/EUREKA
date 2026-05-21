#!/bin/bash
# EUREKA Setup Script
# Usage: ./scripts/setup.sh

set -e

echo "🔬 EUREKA Setup Script"
echo "======================"

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

if command -v docker &> /dev/null; then
    echo "  ✅ Docker found: $(docker --version)"
else
    echo "  ❌ Docker not found. Please install Docker."
    exit 1
fi

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo "  ✅ Docker Compose found"
else
    echo "  ❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Create SSL directory (self-signed for development)
echo ""
echo "🔐 Setting up SSL certificates (self-signed for dev)..."
mkdir -p ssl
if [ ! -f ssl/cert.pem ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/key.pem \
        -out ssl/cert.pem \
        -subj "/CN=localhost" 2>/dev/null || echo "  ⚠️  OpenSSL not found, skipping SSL setup"
    echo "  ✅ Self-signed certificates created"
else
    echo "  ✅ SSL certificates already exist"
fi

# Create logs directory
mkdir -p eureka-backend/logs

# Start services
echo ""
echo "🚀 Starting EUREKA services..."
docker-compose up -d

# Wait for services
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Pull Ollama model
echo ""
echo "🤖 Pulling Llama 3 model (this may take a while)..."
docker-compose exec -T ollama ollama pull llama3 || echo "  ⚠️  Could not pull model. Run manually: docker-compose exec ollama ollama pull llama3"

# Health check
echo ""
echo "🏥 Running health check..."
curl -s http://localhost:8000/health || echo "  ⚠️  Backend not responding yet. Give it a moment."

echo ""
echo "✅ EUREKA Setup Complete!"
echo ""
echo "🌐 Access Points:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000/docs"
echo "   Ollama:    http://localhost:11434"
echo ""
echo "📖 Documentation: docs/"
echo "🧪 Run tests: cd eureka-backend && pytest tests/ -v"
