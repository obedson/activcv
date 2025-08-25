#!/bin/bash

# AI CV Agent - Staging Deployment Script
set -e

echo "🚀 Starting AI CV Agent staging deployment..."

# Configuration
STAGING_ENV="staging"
API_URL="https://api-staging.aicvagent.com"
FRONTEND_URL="https://staging.aicvagent.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed. Aborting."; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { log_error "Docker Compose is required but not installed. Aborting."; exit 1; }
    command -v npm >/dev/null 2>&1 || { log_error "npm is required but not installed. Aborting."; exit 1; }
    
    # Check if environment files exist
    if [ ! -f "agent/.env.staging" ]; then
        log_error "agent/.env.staging file not found. Please create it from .env.example"
        exit 1
    fi
    
    if [ ! -f "web/.env.local" ]; then
        log_error "web/.env.local file not found. Please create it from .env.local.example"
        exit 1
    fi
    
    log_info "Prerequisites check passed ✓"
}

backup_current_deployment() {
    log_info "Creating backup of current deployment..."
    
    # Create backup directory with timestamp
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database (if needed)
    # pg_dump $DATABASE_URL > "$BACKUP_DIR/database_backup.sql"
    
    # Backup configuration files
    cp -r agent/.env.staging "$BACKUP_DIR/" 2>/dev/null || true
    cp -r web/.env.local "$BACKUP_DIR/" 2>/dev/null || true
    
    log_info "Backup created in $BACKUP_DIR ✓"
}

run_tests() {
    log_info "Running pre-deployment tests..."
    
    # Backend tests
    cd agent
    if [ -f "pytest.ini" ] || [ -d "tests" ]; then
        log_info "Running backend tests..."
        python -m pytest tests/ -v || { log_error "Backend tests failed"; exit 1; }
    else
        log_warn "No backend tests found, skipping..."
    fi
    cd ..
    
    # Frontend tests
    cd web
    if [ -f "package.json" ] && grep -q "test" package.json; then
        log_info "Running frontend tests..."
        npm test -- --watchAll=false || { log_error "Frontend tests failed"; exit 1; }
    else
        log_warn "No frontend tests found, skipping..."
    fi
    cd ..
    
    log_info "Tests completed ✓"
}

deploy_backend() {
    log_info "Deploying backend services..."
    
    # Build and start services
    docker-compose -f docker-compose.staging.yml down
    docker-compose -f docker-compose.staging.yml build --no-cache
    docker-compose -f docker-compose.staging.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 30
    
    # Health check
    for i in {1..10}; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_info "Backend health check passed ✓"
            break
        else
            log_warn "Backend not ready, attempt $i/10..."
            sleep 10
        fi
        
        if [ $i -eq 10 ]; then
            log_error "Backend health check failed after 10 attempts"
            exit 1
        fi
    done
}

deploy_frontend() {
    log_info "Deploying frontend..."
    
    cd web
    
    # Install dependencies
    npm ci
    
    # Build application
    npm run build
    
    # Deploy to Vercel (or your chosen platform)
    if command -v vercel >/dev/null 2>&1; then
        log_info "Deploying to Vercel..."
        vercel --prod --yes --env staging
    else
        log_warn "Vercel CLI not found. Please deploy manually or configure your deployment platform."
    fi
    
    cd ..
    
    log_info "Frontend deployment completed ✓"
}

run_smoke_tests() {
    log_info "Running smoke tests..."
    
    # Test API endpoints
    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$API_HEALTH" = "200" ]; then
        log_info "API health check: PASS ✓"
    else
        log_error "API health check: FAIL (HTTP $API_HEALTH)"
        exit 1
    fi
    
    # Test database connection
    API_DB=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)
    if [ "$API_DB" = "200" ]; then
        log_info "Database connection: PASS ✓"
    else
        log_error "Database connection: FAIL (HTTP $API_DB)"
        exit 1
    fi
    
    # Test frontend (if deployed)
    if [ -n "$FRONTEND_URL" ]; then
        FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
        if [ "$FRONTEND_STATUS" = "200" ]; then
            log_info "Frontend health check: PASS ✓"
        else
            log_warn "Frontend health check: FAIL (HTTP $FRONTEND_STATUS)"
        fi
    fi
    
    log_info "Smoke tests completed ✓"
}

setup_monitoring() {
    log_info "Setting up monitoring and alerting..."
    
    # Configure log aggregation
    if [ -f "fluentd/staging.conf" ]; then
        log_info "Fluentd configuration found, starting log aggregation..."
        # Fluentd is already started with docker-compose
    fi
    
    # Setup health check monitoring
    cat > monitoring/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for monitoring
API_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ "$RESPONSE" != "200" ]; then
    echo "ALERT: API health check failed with status $RESPONSE"
    # Add your alerting mechanism here (email, Slack, etc.)
fi
EOF
    
    chmod +x monitoring/health-check.sh
    
    # Add to crontab for regular monitoring
    (crontab -l 2>/dev/null; echo "*/5 * * * * /path/to/monitoring/health-check.sh") | crontab -
    
    log_info "Monitoring setup completed ✓"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    
    # Remove old Docker images
    docker image prune -f
    
    # Clean up build artifacts
    rm -rf agent/__pycache__
    rm -rf web/.next/cache
    
    log_info "Cleanup completed ✓"
}

rollback() {
    log_error "Deployment failed. Starting rollback..."
    
    # Stop current services
    docker-compose -f docker-compose.staging.yml down
    
    # Restore from backup if available
    LATEST_BACKUP=$(ls -t backups/ | head -n1)
    if [ -n "$LATEST_BACKUP" ]; then
        log_info "Restoring from backup: $LATEST_BACKUP"
        cp "backups/$LATEST_BACKUP/.env.staging" agent/ 2>/dev/null || true
        cp "backups/$LATEST_BACKUP/.env.local" web/ 2>/dev/null || true
    fi
    
    log_error "Rollback completed. Please check the logs and fix issues before retrying."
    exit 1
}

# Main deployment flow
main() {
    log_info "AI CV Agent Staging Deployment Started"
    log_info "Timestamp: $(date)"
    
    # Set trap for cleanup on failure
    trap rollback ERR
    
    check_prerequisites
    backup_current_deployment
    run_tests
    deploy_backend
    deploy_frontend
    run_smoke_tests
    setup_monitoring
    cleanup
    
    log_info "🎉 Staging deployment completed successfully!"
    log_info "API URL: $API_URL"
    log_info "Frontend URL: $FRONTEND_URL"
    log_info "Monitoring: Check logs in ./logs/ directory"
    
    echo ""
    echo "Next steps:"
    echo "1. Run User Acceptance Testing (UAT)"
    echo "2. Monitor application performance"
    echo "3. Collect user feedback"
    echo "4. Plan production deployment"
}

# Run main function
main "$@"