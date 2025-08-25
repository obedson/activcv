#!/bin/bash

# AI CV Agent - Complete Dependency Installation Script
# This script installs all dependencies for both backend and frontend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running on supported OS
check_os() {
    log_step "Checking operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        log_info "Detected Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_info "Detected macOS"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        log_info "Detected Windows (using WSL/Git Bash)"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

# Check system requirements
check_system_requirements() {
    log_step "Checking system requirements..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_info "Python found: $PYTHON_VERSION"
        
        # Check if version is 3.11+
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
            log_info "Python version requirement met ✓"
        else
            log_error "Python 3.11+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        log_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_info "Node.js found: $NODE_VERSION"
        
        # Check if version is 18+
        if node -e "process.exit(process.version.match(/^v(\d+)/)[1] >= 18 ? 0 : 1)"; then
            log_info "Node.js version requirement met ✓"
        else
            log_error "Node.js 18+ required, found $NODE_VERSION"
            exit 1
        fi
    else
        log_error "Node.js not found. Please install Node.js 18+"
        exit 1
    fi
    
    # Check npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        log_info "npm found: $NPM_VERSION"
    else
        log_error "npm not found. Please install npm"
        exit 1
    fi
    
    # Check git
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version)
        log_info "Git found: $GIT_VERSION"
    else
        log_error "Git not found. Please install Git"
        exit 1
    fi
}

# Install system dependencies
install_system_dependencies() {
    log_step "Installing system dependencies..."
    
    case $OS in
        "linux")
            log_info "Installing Linux system dependencies..."
            
            # Update package list
            sudo apt-get update
            
            # Install Python development packages
            sudo apt-get install -y \
                python3-dev \
                python3-pip \
                python3-venv \
                python3-cffi \
                python3-brotli \
                build-essential \
                libffi-dev \
                libssl-dev
            
            # Install WeasyPrint system dependencies
            sudo apt-get install -y \
                libpango-1.0-0 \
                libharfbuzz0b \
                libpangoft2-1.0-0 \
                libfontconfig1 \
                libcairo2 \
                libgdk-pixbuf2.0-0 \
                shared-mime-info
            
            # Install additional tools
            sudo apt-get install -y \
                curl \
                wget \
                unzip \
                software-properties-common
            ;;
            
        "macos")
            log_info "Installing macOS system dependencies..."
            
            # Check if Homebrew is installed
            if ! command -v brew &> /dev/null; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            # Install system dependencies
            brew install cairo pango gdk-pixbuf libffi pkg-config
            ;;
            
        "windows")
            log_warn "Windows detected. Please ensure you have:"
            log_warn "- Visual Studio Build Tools or Visual Studio Community"
            log_warn "- Windows SDK"
            log_warn "- Git for Windows"
            log_warn "Consider using Docker for easier setup on Windows"
            ;;
    esac
}

# Setup Python virtual environment
setup_python_environment() {
    log_step "Setting up Python virtual environment..."
    
    cd agent
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    log_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    log_info "Upgrading pip..."
    python -m pip install --upgrade pip
    
    cd ..
}

# Install Python dependencies
install_python_dependencies() {
    log_step "Installing Python dependencies..."
    
    cd agent
    source venv/bin/activate
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        log_info "Installing from requirements.txt..."
        pip install -r requirements.txt
    else
        log_warn "requirements.txt not found, installing individual packages..."
        
        # Install core packages
        pip install \
            fastapi==0.104.1 \
            uvicorn[standard]==0.24.0 \
            python-multipart==0.0.6 \
            pydantic==2.5.0 \
            pydantic-settings==2.1.0 \
            supabase==2.3.0 \
            crewai==0.28.8 \
            python-dotenv==1.0.0 \
            pypdf==3.17.4 \
            jinja2==3.1.2 \
            weasyprint==60.2 \
            requests==2.31.0 \
            aiofiles==23.2.1 \
            python-jose[cryptography]==3.3.0 \
            passlib[bcrypt]==1.7.4 \
            beautifulsoup4==4.12.2 \
            schedule==1.2.0
        
        # Install development packages
        pip install \
            pytest==7.4.3 \
            pytest-asyncio==0.21.1 \
            black==23.11.0 \
            flake8==6.1.0 \
            mypy==1.7.1
    fi
    
    # Verify installation
    log_info "Verifying Python installation..."
    python scripts/check-dependencies.py
    
    cd ..
}

# Install Node.js dependencies
install_nodejs_dependencies() {
    log_step "Installing Node.js dependencies..."
    
    cd web
    
    # Clean install
    if [ -f "package-lock.json" ]; then
        log_info "Found package-lock.json, running clean install..."
        npm ci
    else
        log_info "Running npm install..."
        npm install
    fi
    
    # Verify installation
    log_info "Verifying Node.js installation..."
    node ../scripts/check-frontend-deps.js
    
    cd ..
}

# Install optional tools
install_optional_tools() {
    log_step "Installing optional development tools..."
    
    # Docker (if not already installed)
    if ! command -v docker &> /dev/null; then
        log_info "Docker not found. Consider installing Docker for containerized deployment."
        log_info "Visit: https://docs.docker.com/get-docker/"
    else
        log_info "Docker found: $(docker --version)"
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_info "Docker Compose not found. Consider installing for multi-container deployment."
    else
        log_info "Docker Compose found: $(docker-compose --version)"
    fi
    
    # Supabase CLI (optional)
    if ! command -v supabase &> /dev/null; then
        log_info "Installing Supabase CLI..."
        npm install -g supabase
    else
        log_info "Supabase CLI found: $(supabase --version)"
    fi
}

# Setup development environment
setup_development_environment() {
    log_step "Setting up development environment..."
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p temp_storage
    mkdir -p backups
    mkdir -p monitoring
    
    # Copy environment files if they don't exist
    if [ ! -f "agent/.env" ] && [ -f "agent/.env.example" ]; then
        log_info "Creating agent/.env from example..."
        cp agent/.env.example agent/.env
        log_warn "Please update agent/.env with your configuration"
    fi
    
    if [ ! -f "web/.env.local" ] && [ -f "web/.env.local.example" ]; then
        log_info "Creating web/.env.local from example..."
        cp web/.env.local.example web/.env.local
        log_warn "Please update web/.env.local with your configuration"
    fi
    
    # Setup pre-commit hooks (if available)
    if [ -f "agent/.pre-commit-config.yaml" ]; then
        cd agent
        source venv/bin/activate
        pre-commit install
        cd ..
    fi
}

# Run verification tests
run_verification_tests() {
    log_step "Running verification tests..."
    
    # Test backend
    log_info "Testing backend setup..."
    cd agent
    source venv/bin/activate
    
    # Try to import main modules
    python -c "
import fastapi
import uvicorn
import supabase
import crewai
print('✅ All main backend modules imported successfully')
"
    
    cd ..
    
    # Test frontend
    log_info "Testing frontend setup..."
    cd web
    
    # Check if build works
    npm run build > /dev/null 2>&1 && log_info "✅ Frontend build test passed" || log_warn "⚠️  Frontend build test failed"
    
    cd ..
}

# Generate installation report
generate_installation_report() {
    log_step "Generating installation report..."
    
    cat > INSTALLATION_REPORT.md << EOF
# AI CV Agent - Installation Report

**Installation Date:** $(date)
**Operating System:** $OS
**User:** $(whoami)

## System Information
- **Python Version:** $(python3 --version)
- **Node.js Version:** $(node --version)
- **npm Version:** $(npm --version)
- **Git Version:** $(git --version)

## Backend Dependencies
$(cd agent && source venv/bin/activate && pip list)

## Frontend Dependencies
$(cd web && npm list --depth=0)

## Installation Status
- ✅ System requirements checked
- ✅ System dependencies installed
- ✅ Python environment setup
- ✅ Python dependencies installed
- ✅ Node.js dependencies installed
- ✅ Development environment configured

## Next Steps
1. Configure environment variables in:
   - \`agent/.env\`
   - \`web/.env.local\`

2. Start the development servers:
   \`\`\`bash
   # Backend
   cd agent
   source venv/bin/activate
   python main.py
   
   # Frontend (in another terminal)
   cd web
   npm run dev
   \`\`\`

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Troubleshooting
If you encounter issues:
1. Check the logs in the \`logs/\` directory
2. Verify environment variables are set correctly
3. Ensure all services (Supabase, etc.) are configured
4. Run dependency checks:
   - Backend: \`python scripts/check-dependencies.py\`
   - Frontend: \`node scripts/check-frontend-deps.js\`

EOF

    log_info "Installation report saved to: INSTALLATION_REPORT.md"
}

# Main installation function
main() {
    echo "🚀 AI CV Agent - Complete Dependency Installation"
    echo "=================================================="
    echo ""
    
    check_os
    check_system_requirements
    install_system_dependencies
    setup_python_environment
    install_python_dependencies
    install_nodejs_dependencies
    install_optional_tools
    setup_development_environment
    run_verification_tests
    generate_installation_report
    
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Configure your environment variables"
    echo "2. Set up your Supabase project"
    echo "3. Run the development servers"
    echo ""
    echo "For detailed instructions, see: INSTALLATION_REPORT.md"
}

# Run main function
main "$@"