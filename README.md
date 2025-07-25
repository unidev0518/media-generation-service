# Media Generation Service

A production-ready asynchronous media generation microservice built with FastAPI, Celery, and the Replicate API. This service provides a robust, scalable solution for generating media content using AI models with proper error handling, retry mechanisms, and monitoring.

## 🏗️ Architecture Overview

This microservice follows clean architecture principles with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI API   │    │  Celery Worker  │    │  Storage Layer  │
│                 │    │                 │    │                 │
│ • REST Endpoints│    │ • Media Gen     │    │ • MinIO/S3      │
│ • Validation    │    │ • Retry Logic   │    │ • Local FS      │
│ • Error Handling│    │ • Progress      │    │ • File Mgmt     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────┐    ┌┴─────────────────┐    ┌─────────────────┐
         │   PostgreSQL    │    │      Redis       │    │  Replicate API  │
         │                 │    │                  │    │                 │
         │ • Job Metadata  │    │ • Task Queue     │    │ • AI Models     │
         │ • Status Track  │    │ • Result Cache   │    │ • Media Gen     │
         │ • Persistence   │    │ • Session Store  │    │ • External API  │
         └─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Components

- **API Layer**: FastAPI with async endpoints, Pydantic validation, and comprehensive error handling
- **Service Layer**: Business logic with clean separation of concerns
- **Task Queue**: Celery workers for async processing with retry logic
- **Storage**: MinIO (S3-compatible) or local filesystem for media files
- **Database**: PostgreSQL with SQLModel for job metadata and status tracking
- **External API**: Replicate integration with exponential backoff retry logic

## 🚀 Features

### Core Functionality
- ✅ **Async Media Generation**: Submit jobs and get results asynchronously
- ✅ **Multiple Storage Options**: MinIO S3-compatible or local filesystem
- ✅ **Retry Logic**: Exponential backoff with configurable retry attempts
- ✅ **Progress Tracking**: Real-time job progress and status updates
- ✅ **Error Handling**: Comprehensive error handling with detailed logging

### API Endpoints
- `POST /api/v1/generate` - Create media generation job
- `GET /api/v1/status/{job_id}` - Get job status and progress
- `GET /api/v1/jobs/{job_id}` - Get detailed job information
- `GET /api/v1/jobs` - List jobs with pagination and filtering
- `POST /api/v1/jobs/{job_id}/cancel` - Cancel running job
- `POST /api/v1/jobs/{job_id}/retry` - Retry failed job
- `GET /api/v1/stats` - System statistics and health

### Production Features
- 🐳 **Docker Support**: Complete containerization with docker-compose
- 📊 **Monitoring**: Celery Flower for task monitoring
- 🔒 **Security**: Non-root containers, input validation, error sanitization
- 📈 **Scalability**: Horizontal scaling support for workers
- 🔄 **Health Checks**: Built-in health monitoring for all services
- 📝 **Documentation**: Auto-generated OpenAPI/Swagger documentation

## 🛠️ Tech Stack

- **Framework**: FastAPI (async Python web framework)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL with SQLModel (async SQLAlchemy)
- **Storage**: MinIO (S3-compatible) or Local Filesystem
- **External API**: Replicate AI models
- **Containerization**: Docker + Docker Compose
- **Migrations**: Alembic
- **Monitoring**: Celery Flower
- **Validation**: Pydantic

## 📋 Prerequisites

- Docker and Docker Compose
- **Optional**: Replicate API token (sign up at [replicate.com](https://replicate.com))
  - **Without token**: System runs in **MOCK MODE** for testing
  - **With token**: Real AI-powered image generation
- Python 3.11+ (for local development)
- Poetry (for dependency management)

## 🚀 Quick Start

### Option A: Automated Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd media-generation-service

# Run the automated setup script
./setup.sh
```

The setup script will:
- ✅ Check Docker installation
- ✅ Create configuration files
- ✅ Ask about Replicate API token (optional)
- ✅ Start all services
- ✅ Verify system health

### Option B: Manual Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd media-generation-service

# Copy environment configuration
cp env.example .env

# Optional: Add your Replicate API token for real AI generation
# Leave empty for MOCK MODE (testing without real API calls)
# REPLICATE_API_TOKEN=r8_your_real_token_here
```

### 2. Docker Deployment

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f celery_worker
```

### 3. Initialize Database

```bash
# Run database migrations
docker-compose exec api poetry run alembic upgrade head
```

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Access documentation
open http://localhost:8000/docs

# Monitor Celery tasks
open http://localhost:5555  # Flower UI

# MinIO console
open http://localhost:9001  # MinIO UI (admin/minioadmin)
```

## 📊 Service Endpoints

| Service | Port | Description |
|---------|------|-------------|
| FastAPI API | 8000 | Main application API |
| Celery Flower | 5555 | Task monitoring dashboard |
| MinIO Console | 9001 | Storage management UI |
| PostgreSQL | 5432 | Database (internal) |
| Redis | 6379 | Cache/Queue (internal) |
| MinIO API | 9000 | Object storage API |

## 🔧 Local Development

### Setup Environment

```bash
# Install Poetry
pip install poetry

# Install dependencies
poetry install

# Setup pre-commit hooks
poetry run pre-commit install

# Start infrastructure services
docker-compose up -d postgres redis minio

# Copy and configure environment
cp env.example .env
# Edit .env with local configuration
```

### Run Services

```bash
# Terminal 1: Run API server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Run Celery worker
poetry run celery -A app.tasks.celery_app worker --loglevel=info --queues=generation

# Terminal 3: Run Celery beat (optional, for scheduled tasks)
poetry run celery -A app.tasks.celery_app beat --loglevel=info

# Terminal 4: Run Flower monitoring (optional)
poetry run celery -A app.tasks.celery_app flower --port=5555
```

### Database Operations

```bash
# Create migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1
```

## 📚 API Usage Examples

### Create Generation Job

```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over the ocean",
    "parameters": {
      "width": 512,
      "height": 512,
      "num_inference_steps": 50,
      "guidance_scale": 7.5
    }
  }'
```

### Check Job Status

```bash
curl "http://localhost:8000/api/v1/status/{job_id}"
```

### List Jobs

```bash
curl "http://localhost:8000/api/v1/jobs?limit=10&status=completed"
```

## 🔧 Development Mode Options

### Option 1: Mock Mode (No Replicate Token)

Run the system **without a Replicate API token** for testing:

```bash
# In your .env file, leave empty:
REPLICATE_API_TOKEN=

# The system will:
# ✅ Accept all generation requests
# ✅ Simulate processing time
# ✅ Generate mock image files
# ✅ Test all endpoints and workflows
# 🔧 Print "MOCK MODE" messages in logs
```

**Mock Mode Features:**
- Generates simple pink placeholder images
- Simulates 2-second processing time
- Tests entire workflow without external API costs
- Perfect for development and CI/CD testing

### Option 2: Real AI Generation (With Replicate Token)

Get a real token for actual AI-powered generation:

1. **Sign up**: Visit [replicate.com](https://replicate.com)
2. **Get token**: Go to [Account → API Tokens](https://replicate.com/account/api-tokens)
3. **Add to .env**:
   ```bash
   REPLICATE_API_TOKEN=r8_your_actual_token_here
   ```

**Real Mode Features:**
- Actual AI-generated images using Stable Diffusion
- Professional quality results
- Uses your Replicate credits
- Full production capabilities

## 🔧 Configuration

### Environment Variables

Key configuration options (see `env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `REPLICATE_API_TOKEN` | Replicate API token (optional) | Empty (Mock Mode) |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://...` |
| `STORAGE_TYPE` | Storage backend (minio/local) | `minio` |
| `MAX_RETRY_ATTEMPTS` | Max job retry attempts | `3` |
| `JOB_TIMEOUT` | Job timeout in seconds | `300` |

### Scaling Configuration

To scale Celery workers:

```bash
# Scale to 3 worker instances
docker-compose up -d --scale celery_worker=3

# Or specify in docker-compose.yml
deploy:
  replicas: 3
```

## 📈 Monitoring & Observability

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Service statistics
curl http://localhost:8000/api/v1/stats
```

### Celery Monitoring

Access Flower dashboard at `http://localhost:5555` to monitor:
- Active tasks
- Worker status
- Task history
- Performance metrics

### Logs

```bash
# API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f celery_worker

# All service logs
docker-compose logs -f
```

## 🧪 Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app

# Run specific test file
poetry run pytest tests/test_api.py

# Run integration tests
poetry run pytest tests/integration/
```

## 🔒 Security Considerations

- **Non-root containers**: All services run as non-root users
- **Input validation**: Comprehensive Pydantic validation
- **Error sanitization**: Sensitive information filtered from responses
- **Environment isolation**: Secrets managed via environment variables
- **Network security**: Internal services isolated in Docker network

## 🚀 Production Deployment

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml media-generation
```

### Kubernetes

```bash
# Generate Kubernetes manifests
kompose convert -f docker-compose.yml

# Apply to cluster
kubectl apply -f .
```

### Environment-Specific Configurations

Create environment-specific compose files:

```bash
# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

## 🐛 Troubleshooting

### Common Issues

1. **Celery workers not processing tasks**
   ```bash
   # Check Redis connection
   docker-compose exec redis redis-cli ping
   
   # Restart workers
   docker-compose restart celery_worker
   ```

2. **Database connection errors**
   ```bash
   # Check PostgreSQL status
   docker-compose exec postgres pg_isready
   
   # View database logs
   docker-compose logs postgres
   ```

3. **MinIO connection issues**
   ```bash
   # Check MinIO health
   curl http://localhost:9000/minio/health/live
   
   # Verify bucket exists
   docker-compose exec minio mc ls local/
   ```

### Performance Tuning

1. **Database optimization**
   - Enable connection pooling
   - Add database indexes for frequent queries
   - Adjust PostgreSQL configuration

2. **Celery optimization**
   - Tune worker concurrency
   - Optimize task routing
   - Configure result backend settings

3. **Storage optimization**
   - Use CDN for file serving
   - Implement file compression
   - Configure MinIO caching

## 📄 License

[Add your license information here]

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review logs for error details

---

Built with ❤️ for FleekLabs Assessment 