#!/usr/bin/env python3
"""
Dependency checker script for AI CV Agent backend
Verifies all required Python packages are installed and compatible
"""

import sys
import subprocess
import importlib
import pkg_resources
from typing import List, Tuple, Dict
import json

# Required packages with minimum versions
REQUIRED_PACKAGES = {
    'fastapi': '0.104.0',
    'uvicorn': '0.24.0',
    'pydantic': '2.5.0',
    'supabase': '2.3.0',
    'crewai': '0.28.0',
    'python-dotenv': '1.0.0',
    'pypdf': '3.17.0',
    'jinja2': '3.1.0',
    'weasyprint': '60.0.0',
    'requests': '2.31.0',
    'aiofiles': '23.2.0',
    'python-jose': '3.3.0',
    'passlib': '1.7.0',
    'beautifulsoup4': '4.12.0',
    'schedule': '1.2.0'
}

# Optional packages for development
OPTIONAL_PACKAGES = {
    'pytest': '7.4.0',
    'pytest-asyncio': '0.21.0',
    'black': '23.11.0',
    'flake8': '6.1.0',
    'mypy': '1.7.0'
}

def check_python_version() -> bool:
    """Check if Python version meets requirements"""
    required_version = (3, 11)
    current_version = sys.version_info[:2]
    
    print(f"Python version: {sys.version}")
    
    if current_version >= required_version:
        print("✅ Python version requirement met")
        return True
    else:
        print(f"❌ Python {required_version[0]}.{required_version[1]}+ required, found {current_version[0]}.{current_version[1]}")
        return False

def check_package_installed(package_name: str, min_version: str = None) -> Tuple[bool, str]:
    """Check if a package is installed and meets version requirements"""
    try:
        # Try to import the package
        importlib.import_module(package_name.replace('-', '_'))
        
        # Check version if specified
        if min_version:
            try:
                installed_version = pkg_resources.get_distribution(package_name).version
                if pkg_resources.parse_version(installed_version) >= pkg_resources.parse_version(min_version):
                    return True, installed_version
                else:
                    return False, f"Version {installed_version} < {min_version}"
            except pkg_resources.DistributionNotFound:
                return False, "Package not found in pip"
        
        return True, "Installed"
        
    except ImportError:
        return False, "Not installed"

def check_system_dependencies() -> Dict[str, bool]:
    """Check system-level dependencies"""
    system_deps = {}
    
    # Check for system libraries needed by WeasyPrint
    try:
        import weasyprint
        # Try to create a simple HTML document
        html_doc = weasyprint.HTML(string='<html><body>Test</body></html>')
        html_doc.render()
        system_deps['weasyprint_system_libs'] = True
    except Exception as e:
        system_deps['weasyprint_system_libs'] = False
        print(f"⚠️  WeasyPrint system dependencies issue: {e}")
    
    # Check for Redis (optional)
    try:
        import redis
        system_deps['redis_available'] = True
    except ImportError:
        system_deps['redis_available'] = False
    
    return system_deps

def install_missing_package(package_name: str, version: str = None) -> bool:
    """Attempt to install a missing package"""
    try:
        package_spec = f"{package_name}>={version}" if version else package_name
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_spec])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Main dependency checking function"""
    print("🔍 Checking AI CV Agent Backend Dependencies\n")
    
    # Check Python version
    python_ok = check_python_version()
    print()
    
    # Check required packages
    print("📦 Checking Required Packages:")
    required_ok = True
    missing_packages = []
    
    for package, min_version in REQUIRED_PACKAGES.items():
        is_installed, version_info = check_package_installed(package, min_version)
        
        if is_installed:
            print(f"✅ {package}: {version_info}")
        else:
            print(f"❌ {package}: {version_info}")
            required_ok = False
            missing_packages.append((package, min_version))
    
    print()
    
    # Check optional packages
    print("🛠️  Checking Optional Development Packages:")
    for package, min_version in OPTIONAL_PACKAGES.items():
        is_installed, version_info = check_package_installed(package, min_version)
        
        if is_installed:
            print(f"✅ {package}: {version_info}")
        else:
            print(f"⚠️  {package}: {version_info} (optional)")
    
    print()
    
    # Check system dependencies
    print("🖥️  Checking System Dependencies:")
    system_deps = check_system_dependencies()
    
    for dep, status in system_deps.items():
        if status:
            print(f"✅ {dep}: Available")
        else:
            print(f"❌ {dep}: Not available")
    
    print()
    
    # Offer to install missing packages
    if missing_packages:
        print("🔧 Missing Required Packages Found!")
        response = input("Would you like to install missing packages? (y/n): ")
        
        if response.lower() == 'y':
            print("\n📥 Installing missing packages...")
            
            for package, version in missing_packages:
                print(f"Installing {package}>={version}...")
                if install_missing_package(package, version):
                    print(f"✅ Successfully installed {package}")
                else:
                    print(f"❌ Failed to install {package}")
            
            print("\n🔄 Re-checking dependencies...")
            # Re-run the check
            main()
            return
    
    # Final summary
    print("📋 Dependency Check Summary:")
    print(f"Python Version: {'✅' if python_ok else '❌'}")
    print(f"Required Packages: {'✅' if required_ok else '❌'}")
    print(f"System Dependencies: {'✅' if all(system_deps.values()) else '⚠️'}")
    
    if python_ok and required_ok:
        print("\n🎉 All required dependencies are satisfied!")
        print("You can now run the AI CV Agent backend.")
        
        # Create a dependency report
        report = {
            'python_version': sys.version,
            'required_packages': {},
            'optional_packages': {},
            'system_dependencies': system_deps,
            'status': 'ready'
        }
        
        for package, min_version in REQUIRED_PACKAGES.items():
            is_installed, version_info = check_package_installed(package, min_version)
            report['required_packages'][package] = {
                'installed': is_installed,
                'version': version_info,
                'required': min_version
            }
        
        with open('dependency_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("📄 Dependency report saved to: dependency_report.json")
        
    else:
        print("\n❌ Some dependencies are missing or incompatible.")
        print("Please install missing dependencies before running the application.")
        sys.exit(1)

if __name__ == "__main__":
    main()