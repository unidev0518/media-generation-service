#!/bin/bash

# Media Generation Service - Quick Setup Script
# This script sets up the entire system for immediate testing

echo "🚀 Setting up Media Generation Service..."
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created"
else
    echo "📄 .env file already exists"
fi

echo
echo "🔧 Configuration Options:"
echo "   1. MOCK MODE (recommended for testing)"
echo "      - No external API required"
echo "      - Generates placeholder images"
echo "      - Perfect for development"
echo
echo "   2. REAL MODE (for production)"
echo "      - Requires Replicate API token"
echo "      - Actual AI-generated images"
echo "      - Get token at: https://replicate.com/account/api-tokens"
echo

read -p "Do you have a Replicate API token? (y/N): " has_token

if [[ $has_token =~ ^[Yy]$ ]]; then
    echo
    read -p "Enter your Replicate API token: " replicate_token
    
    # Update .env file with the token
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/REPLICATE_API_TOKEN=.*/REPLICATE_API_TOKEN=$replicate_token/" .env
    else
        # Linux
        sed -i "s/REPLICATE_API_TOKEN=.*/REPLICATE_API_TOKEN=$replicate_token/" .env
    fi
    
    echo "✅ Token added to .env file"
    echo "🎨 System will use REAL AI generation"
else
    echo "🔧 Using MOCK MODE - no token required"
    echo "   System will generate placeholder images for testing"
fi

echo
echo "🐳 Starting services with Docker Compose..."
echo "   This may take a few minutes on first run..."

# Start all services
docker-compose up -d

# Wait for services to be healthy
echo
echo "⏳ Waiting for services to start..."
sleep 15

# Check service health
echo
echo "🔍 Checking service health..."

# Check API
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API service is running (http://localhost:8000)"
else
    echo "❌ API service is not responding"
fi

# Check Flower
if curl -s http://localhost:5555 > /dev/null; then
    echo "✅ Celery monitoring is running (http://localhost:5555)"
else
    echo "❌ Celery monitoring is not responding"
fi

# Check MinIO
if curl -s http://localhost:9001 > /dev/null; then
    echo "✅ MinIO storage console is running (http://localhost:9001)"
else
    echo "❌ MinIO storage console is not responding"
fi

echo
echo "🎉 Setup complete!"
echo
echo "📚 Available endpoints:"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • API Health Check:  http://localhost:8000/health"
echo "   • Task Monitoring:    http://localhost:5555"
echo "   • Storage Console:    http://localhost:9001 (admin/minioadmin)"
echo
echo "🧪 Test the API:"
echo '   curl -X POST "http://localhost:8000/api/v1/generate" \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"prompt": "A beautiful sunset", "parameters": {"width": 512, "height": 512}}'"'"
echo
echo "📋 Useful commands:"
echo "   • View logs:     docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart:       docker-compose restart"
echo
echo "🔗 Documentation: Check README.md for detailed usage instructions" 