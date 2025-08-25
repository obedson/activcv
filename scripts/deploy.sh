#!/bin/bash

# AI CV Agent Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environments: development, staging, production

set -e

ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying AI CV Agent to $ENVIRONMENT environment..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found. Copy .env.example and configure it."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Build application
build_application() {
    log_info "Building application..."
    
    cd "$PROJECT_ROOT"
    
    # Build backend
    log_info "Building backend Docker image..."
    docker build -t ai-cv-agent-api:latest -f agent/Dockerfile.prod agent/
    
    # Build worker
    log_info "Building worker Docker image..."
    docker build -t ai-cv-agent-worker:latest -f agent/Dockerfile.worker agent/
    
    # Build frontend (if deploying locally)
    if [ "$ENVIRONMENT" = "development" ]; then
        log_info "Building frontend..."
        cd web
        npm install
        npm run build
        cd ..
    fi
    
    log_success "Application build completed"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Check if Supabase CLI is available
    if command -v supabase &> /dev/null; then
        cd "$PROJECT_ROOT/infra/supabase"
        supabase db push
        log_success "Database migrations completed"
    else
        log_warning "Supabase CLI not found. Please run migrations manually."
    fi
}

# Deploy based on environment
deploy_environment() {
    log_info "Deploying to $ENVIRONMENT environment..."
    
    cd "$PROJECT_ROOT"
    
    case $ENVIRONMENT in
        development)
            deploy_development
            ;;
        staging)
            deploy_staging
            ;;
        production)
            deploy_production
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

# Development deployment
deploy_development() {
    log_info "Starting development environment..."
    
    # Stop existing containers
    docker-compose down
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_success "API is healthy"
    else
        log_error "API health check failed"
        exit 1
    fi
    
    log_success "Development environment deployed successfully"
    log_info "Frontend: http://localhost:3000"
    log_info "API: http://localhost:8000"
    log_info "API Docs: http://localhost:8000/docs"
}

# Staging deployment
deploy_staging() {
    log_info "Deploying to staging environment..."
    
    # Use production compose file
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services
    sleep 60
    
    # Health check
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_success "Staging deployment successful"
    else
        log_error "Staging deployment failed"
        exit 1
    fi
}

# Production deployment
deploy_production() {
    log_info "Deploying to production environment..."
    
    # Backup current deployment
    log_info "Creating backup..."
    docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres ai_cv_agent > "backup_$(date +%Y%m%d_%H%M%S).sql" || true
    
    # Deploy with zero downtime
    log_info "Performing rolling deployment..."
    
    # Update images
    docker-compose -f docker-compose.prod.yml pull
    
    # Restart services one by one
    docker-compose -f docker-compose.prod.yml up -d --no-deps api
    sleep 30
    
    docker-compose -f docker-compose.prod.yml up -d --no-deps worker
    sleep 15
    
    docker-compose -f docker-compose.prod.yml up -d --no-deps nginx
    
    # Health check
    if curl -f http://localhost/api/v1/health > /dev/null 2>&1; then
        log_success "Production deployment successful"
    else
        log_error "Production deployment failed"
        exit 1
    fi
}

# Post-deployment tasks
post_deployment() {
    log_info "Running post-deployment tasks..."
    
    # Clear caches
    log_info "Clearing application caches..."
    docker-compose exec redis redis-cli FLUSHALL || true
    
    # Warm up services
    log_info "Warming up services..."
    curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1 || true
    
    # Send deployment notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 AI CV Agent deployed to $ENVIRONMENT successfully!\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    log_success "Post-deployment tasks completed"
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."
    
    # Stop current containers
    docker-compose -f docker-compose.prod.yml down
    
    # Start previous version (assuming tagged images)
    docker-compose -f docker-compose.prod.yml up -d
    
    log_success "Rollback completed"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backups (keep last 5)
    find . -name "backup_*.sql" -type f -printf '%T@ %p\n' | sort -n | head -n -5 | cut -d' ' -f2- | xargs -r rm
    
    log_success "Cleanup completed"
}

# Main execution
main() {
    log_info "Starting deployment process for $ENVIRONMENT environment"
    
    check_prerequisites
    build_application
    run_migrations
    deploy_environment
    post_deployment
    cleanup
    
    log_success "🎉 Deployment completed successfully!"
    
    # Show useful information
    echo ""
    echo "📊 Monitoring URLs:"
    echo "   Grafana: http://localhost:3001"
    echo "   Prometheus: http://localhost:9090"
    echo "   API Metrics: http://localhost:8000/api/v1/metrics"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View logs: docker-compose logs -f"
    echo "   Restart API: docker-compose restart api"
    echo "   Scale workers: docker-compose up -d --scale worker=3"
    echo "   Rollback: $0 rollback"
}

# Handle script arguments
case "${1:-}" in
    rollback)
        rollback
        ;;
    cleanup)
        cleanup
        ;;
    *)
        main
        ;;
esac