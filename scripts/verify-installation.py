#!/usr/bin/env python3
"""
Complete installation verification script for AI CV Agent
Tests all components and generates a comprehensive report
"""

import sys
import os
import subprocess
import json
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Any

def run_command(command: str) -> Tuple[bool, str]:
    """Run a shell command and return success status and output"""
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def check_python_environment() -> Dict[str, Any]:
    """Check Python environment and virtual environment"""
    results = {
        'python_version': sys.version,
        'python_executable': sys.executable,
        'virtual_env': False,
        'pip_version': None,
        'site_packages': None
    }
    
    # Check if in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        results['virtual_env'] = True
    
    # Get pip version
    success, output = run_command('pip --version')
    if success:
        results['pip_version'] = output
    
    # Get site packages location
    try:
        import site
        results['site_packages'] = site.getsitepackages()
    except:
        pass
    
    return results

def check_required_imports() -> Dict[str, bool]:
    """Test importing all required packages"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'supabase',
        'crewai',
        'dotenv',
        'pypdf',
        'jinja2',
        'weasyprint',
        'requests',
        'aiofiles',
        'jose',
        'passlib',
        'bs4',
        'schedule'
    ]
    
    results = {}
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            results[package] = True
        except ImportError:
            results[package] = False
    
    return results

def test_core_functionality() -> Dict[str, Any]:
    """Test core application functionality"""
    results = {
        'fastapi_app': False,
        'database_models': False,
        'pdf_generation': False,
        'template_rendering': False,
        'ai_services': False
    }
    
    try:
        # Test FastAPI app creation
        from fastapi import FastAPI
        app = FastAPI()
        results['fastapi_app'] = True
    except Exception as e:
        results['fastapi_app'] = str(e)
    
    try:
        # Test database models
        from app.models.cover_letter import CoverLetter
        from app.models.jobs import Job
        results['database_models'] = True
    except Exception as e:
        results['database_models'] = str(e)
    
    try:
        # Test PDF generation
        from weasyprint import HTML
        html_doc = HTML(string='<html><body>Test</body></html>')
        pdf_bytes = html_doc.write_pdf()
        results['pdf_generation'] = len(pdf_bytes) > 0
    except Exception as e:
        results['pdf_generation'] = str(e)
    
    try:
        # Test template rendering
        from jinja2 import Template
        template = Template('Hello {{ name }}!')
        rendered = template.render(name='World')
        results['template_rendering'] = rendered == 'Hello World!'
    except Exception as e:
        results['template_rendering'] = str(e)
    
    return results

def check_frontend_setup() -> Dict[str, Any]:
    """Check frontend setup and dependencies"""
    results = {
        'node_version': None,
        'npm_version': None,
        'package_json': False,
        'node_modules': False,
        'next_build': False
    }
    
    # Check Node.js
    success, output = run_command('node --version')
    if success:
        results['node_version'] = output
    
    # Check npm
    success, output = run_command('npm --version')
    if success:
        results['npm_version'] = output
    
    # Check package.json
    package_json_path = Path('web/package.json')
    if package_json_path.exists():
        results['package_json'] = True
        
        # Check node_modules
        node_modules_path = Path('web/node_modules')
        if node_modules_path.exists():
            results['node_modules'] = True
    
    # Test Next.js build (in web directory)
    if results['package_json'] and results['node_modules']:
        original_dir = os.getcwd()
        try:
            os.chdir('web')
            success, output = run_command('npm run build')
            results['next_build'] = success
        except:
            results['next_build'] = False
        finally:
            os.chdir(original_dir)
    
    return results

def check_environment_files() -> Dict[str, Any]:
    """Check environment configuration files"""
    results = {
        'backend_env': False,
        'frontend_env': False,
        'backend_env_vars': [],
        'frontend_env_vars': []
    }
    
    # Check backend .env
    backend_env_path = Path('agent/.env')
    if backend_env_path.exists():
        results['backend_env'] = True
        try:
            with open(backend_env_path, 'r') as f:
                content = f.read()
                # Extract variable names (lines that don't start with # and contain =)
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        var_name = line.split('=')[0]
                        results['backend_env_vars'].append(var_name)
        except:
            pass
    
    # Check frontend .env.local
    frontend_env_path = Path('web/.env.local')
    if frontend_env_path.exists():
        results['frontend_env'] = True
        try:
            with open(frontend_env_path, 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        var_name = line.split('=')[0]
                        results['frontend_env_vars'].append(var_name)
        except:
            pass
    
    return results

def check_database_migrations() -> Dict[str, Any]:
    """Check database migration files"""
    results = {
        'migration_files': [],
        'migration_count': 0
    }
    
    migrations_dir = Path('infra/supabase/migrations')
    if migrations_dir.exists():
        migration_files = list(migrations_dir.glob('*.sql'))
        results['migration_files'] = [f.name for f in migration_files]
        results['migration_count'] = len(migration_files)
    
    return results

def check_docker_setup() -> Dict[str, Any]:
    """Check Docker configuration"""
    results = {
        'docker_available': False,
        'docker_compose_available': False,
        'dockerfile_backend': False,
        'docker_compose_files': []
    }
    
    # Check Docker
    success, output = run_command('docker --version')
    if success:
        results['docker_available'] = True
    
    # Check Docker Compose
    success, output = run_command('docker-compose --version')
    if success:
        results['docker_compose_available'] = True
    
    # Check Dockerfile
    dockerfile_path = Path('agent/Dockerfile.prod')
    if dockerfile_path.exists():
        results['dockerfile_backend'] = True
    
    # Check docker-compose files
    compose_files = [
        'docker-compose.yml',
        'docker-compose.staging.yml',
        'docker-compose.prod.yml'
    ]
    
    for compose_file in compose_files:
        if Path(compose_file).exists():
            results['docker_compose_files'].append(compose_file)
    
    return results

def generate_verification_report(all_results: Dict[str, Any]) -> str:
    """Generate a comprehensive verification report"""
    
    # Calculate overall status
    critical_checks = [
        all_results['python_env']['virtual_env'],
        all(all_results['imports'].values()),
        all_results['core_functionality']['fastapi_app'],
        all_results['frontend']['package_json'],
        all_results['environment']['backend_env']
    ]
    
    overall_status = "✅ READY" if all(critical_checks) else "⚠️ ISSUES FOUND"
    
    report = f"""
# 🔍 AI CV Agent - Installation Verification Report

**Generated:** {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}
**Overall Status:** {overall_status}

## 🐍 Python Environment
- **Version:** {all_results['python_env']['python_version'].split()[0]}
- **Virtual Environment:** {'✅' if all_results['python_env']['virtual_env'] else '❌'}
- **Pip Version:** {all_results['python_env']['pip_version'] or 'Not found'}

## 📦 Package Imports
"""
    
    for package, status in all_results['imports'].items():
        status_icon = '✅' if status else '❌'
        report += f"- **{package}:** {status_icon}\n"
    
    report += f"""
## ⚙️ Core Functionality Tests
- **FastAPI App:** {'✅' if all_results['core_functionality']['fastapi_app'] else '❌'}
- **Database Models:** {'✅' if all_results['core_functionality']['database_models'] else '❌'}
- **PDF Generation:** {'✅' if all_results['core_functionality']['pdf_generation'] else '❌'}
- **Template Rendering:** {'✅' if all_results['core_functionality']['template_rendering'] else '❌'}

## 🌐 Frontend Setup
- **Node.js Version:** {all_results['frontend']['node_version'] or 'Not found'}
- **npm Version:** {all_results['frontend']['npm_version'] or 'Not found'}
- **package.json:** {'✅' if all_results['frontend']['package_json'] else '❌'}
- **node_modules:** {'✅' if all_results['frontend']['node_modules'] else '❌'}
- **Next.js Build:** {'✅' if all_results['frontend']['next_build'] else '❌'}

## 🔧 Environment Configuration
- **Backend .env:** {'✅' if all_results['environment']['backend_env'] else '❌'}
- **Frontend .env.local:** {'✅' if all_results['environment']['frontend_env'] else '❌'}
- **Backend Variables:** {len(all_results['environment']['backend_env_vars'])} found
- **Frontend Variables:** {len(all_results['environment']['frontend_env_vars'])} found

## 🗄️ Database Setup
- **Migration Files:** {all_results['database']['migration_count']} found
- **Files:** {', '.join(all_results['database']['migration_files'])}

## 🐳 Docker Setup
- **Docker Available:** {'✅' if all_results['docker']['docker_available'] else '❌'}
- **Docker Compose Available:** {'✅' if all_results['docker']['docker_compose_available'] else '❌'}
- **Backend Dockerfile:** {'✅' if all_results['docker']['dockerfile_backend'] else '❌'}
- **Compose Files:** {', '.join(all_results['docker']['docker_compose_files']) if all_results['docker']['docker_compose_files'] else 'None'}

## 🚀 Next Steps

"""
    
    if overall_status == "✅ READY":
        report += """
### You're ready to go! 🎉

1. **Start the backend:**
   ```bash
   cd agent
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   python main.py
   ```

2. **Start the frontend:**
   ```bash
   cd web
   npm run dev
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

"""
    else:
        report += """
### Issues to resolve:

"""
        if not all_results['python_env']['virtual_env']:
            report += "- ❌ **Virtual environment not active** - Run `source venv/bin/activate`\n"
        
        failed_imports = [pkg for pkg, status in all_results['imports'].items() if not status]
        if failed_imports:
            report += f"- ❌ **Missing packages:** {', '.join(failed_imports)} - Run `pip install -r requirements.txt`\n"
        
        if not all_results['frontend']['node_modules']:
            report += "- ❌ **Frontend dependencies missing** - Run `cd web && npm install`\n"
        
        if not all_results['environment']['backend_env']:
            report += "- ❌ **Backend environment file missing** - Copy `.env.example` to `.env` and configure\n"
    
    report += """
## 📞 Support

If you encounter issues:
1. Check the troubleshooting section in README.md
2. Verify all environment variables are set correctly
3. Ensure all services (Supabase, etc.) are configured
4. Run this verification script again after making changes

---
*Generated by AI CV Agent Installation Verifier*
"""
    
    return report

def main():
    """Main verification function"""
    print("🔍 AI CV Agent - Installation Verification")
    print("=" * 50)
    
    # Run all checks
    print("Running comprehensive installation checks...")
    
    all_results = {
        'python_env': check_python_environment(),
        'imports': check_required_imports(),
        'core_functionality': test_core_functionality(),
        'frontend': check_frontend_setup(),
        'environment': check_environment_files(),
        'database': check_database_migrations(),
        'docker': check_docker_setup()
    }
    
    # Generate and save report
    report = generate_verification_report(all_results)
    
    # Save to file
    with open('VERIFICATION_REPORT.md', 'w') as f:
        f.write(report)
    
    # Save JSON data for programmatic access
    with open('verification_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n✅ Verification complete!")
    print("📄 Report saved to: VERIFICATION_REPORT.md")
    print("📊 Raw data saved to: verification_results.json")
    
    # Print summary
    critical_issues = []
    if not all_results['python_env']['virtual_env']:
        critical_issues.append("Virtual environment not active")
    
    failed_imports = [pkg for pkg, status in all_results['imports'].items() if not status]
    if failed_imports:
        critical_issues.append(f"Missing packages: {', '.join(failed_imports)}")
    
    if critical_issues:
        print(f"\n⚠️  Critical issues found: {len(critical_issues)}")
        for issue in critical_issues:
            print(f"   - {issue}")
        sys.exit(1)
    else:
        print("\n🎉 All critical checks passed! You're ready to run the application.")

if __name__ == "__main__":
    main()