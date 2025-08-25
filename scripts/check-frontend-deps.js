#!/usr/bin/env node
/**
 * Frontend dependency checker for AI CV Agent
 * Verifies all required Node.js packages are installed and compatible
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Required Node.js version
const REQUIRED_NODE_VERSION = '18.0.0';

// Required packages from package.json
const REQUIRED_PACKAGES = {
  'next': '^14.0.0',
  'react': '^18.0.0',
  'react-dom': '^18.0.0',
  '@supabase/supabase-js': '^2.38.0',
  'tailwindcss': '^3.0.0',
  'typescript': '^5.0.0'
};

// Development packages
const DEV_PACKAGES = {
  '@types/node': '^20.0.0',
  '@types/react': '^18.0.0',
  '@types/react-dom': '^18.0.0',
  'eslint': '^8.0.0',
  'eslint-config-next': '^14.0.0'
};

function compareVersions(version1, version2) {
  const v1parts = version1.split('.').map(Number);
  const v2parts = version2.split('.').map(Number);
  
  for (let i = 0; i < Math.max(v1parts.length, v2parts.length); i++) {
    const v1part = v1parts[i] || 0;
    const v2part = v2parts[i] || 0;
    
    if (v1part > v2part) return 1;
    if (v1part < v2part) return -1;
  }
  return 0;
}

function checkNodeVersion() {
  const currentVersion = process.version.substring(1); // Remove 'v' prefix
  console.log(`Node.js version: ${process.version}`);
  
  if (compareVersions(currentVersion, REQUIRED_NODE_VERSION) >= 0) {
    console.log('✅ Node.js version requirement met');
    return true;
  } else {
    console.log(`❌ Node.js ${REQUIRED_NODE_VERSION}+ required, found ${currentVersion}`);
    return false;
  }
}

function checkNpmVersion() {
  try {
    const npmVersion = execSync('npm --version', { encoding: 'utf8' }).trim();
    console.log(`npm version: ${npmVersion}`);
    
    if (compareVersions(npmVersion, '9.0.0') >= 0) {
      console.log('✅ npm version requirement met');
      return true;
    } else {
      console.log(`⚠️  npm 9.0.0+ recommended, found ${npmVersion}`);
      return true; // Not critical
    }
  } catch (error) {
    console.log('❌ npm not found');
    return false;
  }
}

function loadPackageJson() {
  try {
    const packageJsonPath = path.join(process.cwd(), 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    return packageJson;
  } catch (error) {
    console.log('❌ package.json not found or invalid');
    return null;
  }
}

function checkPackageInstalled(packageName, requiredVersion, installedPackages) {
  const installed = installedPackages[packageName];
  
  if (!installed) {
    return { installed: false, message: 'Not installed' };
  }
  
  // Remove version prefixes (^, ~, etc.)
  const cleanRequired = requiredVersion.replace(/^[\^~>=<]/, '');
  const cleanInstalled = installed.replace(/^[\^~>=<]/, '');
  
  if (compareVersions(cleanInstalled, cleanRequired) >= 0) {
    return { installed: true, message: installed };
  } else {
    return { installed: false, message: `Version ${installed} < ${requiredVersion}` };
  }
}

function getInstalledPackages() {
  try {
    const nodeModulesPath = path.join(process.cwd(), 'node_modules');
    if (!fs.existsSync(nodeModulesPath)) {
      return {};
    }
    
    const packageLockPath = path.join(process.cwd(), 'package-lock.json');
    if (fs.existsSync(packageLockPath)) {
      const packageLock = JSON.parse(fs.readFileSync(packageLockPath, 'utf8'));
      const packages = {};
      
      if (packageLock.packages) {
        for (const [packagePath, packageInfo] of Object.entries(packageLock.packages)) {
          if (packagePath.startsWith('node_modules/')) {
            const packageName = packagePath.replace('node_modules/', '');
            packages[packageName] = packageInfo.version;
          }
        }
      }
      
      return packages;
    }
    
    // Fallback: check package.json dependencies
    const packageJson = loadPackageJson();
    if (packageJson) {
      return { ...packageJson.dependencies, ...packageJson.devDependencies };
    }
    
    return {};
  } catch (error) {
    console.log('⚠️  Could not determine installed packages');
    return {};
  }
}

function checkDependencies() {
  console.log('📦 Checking Frontend Dependencies');
  
  const packageJson = loadPackageJson();
  if (!packageJson) {
    return false;
  }
  
  const installedPackages = getInstalledPackages();
  
  console.log('\n📋 Required Packages:');
  let allRequired = true;
  const missingPackages = [];
  
  for (const [packageName, requiredVersion] of Object.entries(REQUIRED_PACKAGES)) {
    const result = checkPackageInstalled(packageName, requiredVersion, installedPackages);
    
    if (result.installed) {
      console.log(`✅ ${packageName}: ${result.message}`);
    } else {
      console.log(`❌ ${packageName}: ${result.message}`);
      allRequired = false;
      missingPackages.push(packageName);
    }
  }
  
  console.log('\n🛠️  Development Packages:');
  for (const [packageName, requiredVersion] of Object.entries(DEV_PACKAGES)) {
    const result = checkPackageInstalled(packageName, requiredVersion, installedPackages);
    
    if (result.installed) {
      console.log(`✅ ${packageName}: ${result.message}`);
    } else {
      console.log(`⚠️  ${packageName}: ${result.message} (optional)`);
    }
  }
  
  return { allRequired, missingPackages };
}

function checkBuildTools() {
  console.log('\n🔧 Checking Build Tools:');
  
  const tools = [
    { name: 'TypeScript', command: 'npx tsc --version' },
    { name: 'ESLint', command: 'npx eslint --version' },
    { name: 'Tailwind CSS', command: 'npx tailwindcss --help' }
  ];
  
  const results = {};
  
  for (const tool of tools) {
    try {
      const version = execSync(tool.command, { encoding: 'utf8', stdio: 'pipe' });
      console.log(`✅ ${tool.name}: Available`);
      results[tool.name] = true;
    } catch (error) {
      console.log(`❌ ${tool.name}: Not available`);
      results[tool.name] = false;
    }
  }
  
  return results;
}

function installMissingPackages(missingPackages) {
  console.log('\n📥 Installing missing packages...');
  
  try {
    const installCommand = `npm install ${missingPackages.join(' ')}`;
    console.log(`Running: ${installCommand}`);
    
    execSync(installCommand, { stdio: 'inherit' });
    console.log('✅ Successfully installed missing packages');
    return true;
  } catch (error) {
    console.log('❌ Failed to install packages');
    console.log(error.message);
    return false;
  }
}

function generateDependencyReport(nodeOk, npmOk, depsResult, buildTools) {
  const report = {
    timestamp: new Date().toISOString(),
    node_version: process.version,
    npm_version: execSync('npm --version', { encoding: 'utf8' }).trim(),
    status: nodeOk && npmOk && depsResult.allRequired ? 'ready' : 'issues',
    required_packages: {},
    build_tools: buildTools,
    recommendations: []
  };
  
  const installedPackages = getInstalledPackages();
  
  for (const [packageName, requiredVersion] of Object.entries(REQUIRED_PACKAGES)) {
    const result = checkPackageInstalled(packageName, requiredVersion, installedPackages);
    report.required_packages[packageName] = {
      required: requiredVersion,
      installed: result.installed,
      version: result.message
    };
  }
  
  // Add recommendations
  if (!nodeOk) {
    report.recommendations.push('Update Node.js to version 18.0.0 or higher');
  }
  
  if (!depsResult.allRequired) {
    report.recommendations.push('Install missing required packages');
  }
  
  if (!buildTools.TypeScript) {
    report.recommendations.push('Install TypeScript for better development experience');
  }
  
  fs.writeFileSync('frontend-dependency-report.json', JSON.stringify(report, null, 2));
  console.log('📄 Frontend dependency report saved to: frontend-dependency-report.json');
}

function main() {
  console.log('🔍 AI CV Agent Frontend Dependency Check\n');
  
  // Check Node.js and npm versions
  const nodeOk = checkNodeVersion();
  const npmOk = checkNpmVersion();
  
  console.log();
  
  // Check package dependencies
  const depsResult = checkDependencies();
  
  // Check build tools
  const buildTools = checkBuildTools();
  
  // Offer to install missing packages
  if (!depsResult.allRequired && depsResult.missingPackages.length > 0) {
    console.log('\n🔧 Missing Required Packages Found!');
    
    // In a real interactive environment, you might want to prompt the user
    // For now, we'll just report what's missing
    console.log('Missing packages:', depsResult.missingPackages.join(', '));
    console.log('Run: npm install');
  }
  
  // Generate report
  generateDependencyReport(nodeOk, npmOk, depsResult, buildTools);
  
  // Final summary
  console.log('\n📋 Frontend Dependency Check Summary:');
  console.log(`Node.js Version: ${nodeOk ? '✅' : '❌'}`);
  console.log(`npm Version: ${npmOk ? '✅' : '❌'}`);
  console.log(`Required Packages: ${depsResult.allRequired ? '✅' : '❌'}`);
  console.log(`Build Tools: ${Object.values(buildTools).every(Boolean) ? '✅' : '⚠️'}`);
  
  if (nodeOk && npmOk && depsResult.allRequired) {
    console.log('\n🎉 All required frontend dependencies are satisfied!');
    console.log('You can now run the AI CV Agent frontend.');
    process.exit(0);
  } else {
    console.log('\n❌ Some dependencies are missing or incompatible.');
    console.log('Please install missing dependencies before running the application.');
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  checkNodeVersion,
  checkNpmVersion,
  checkDependencies,
  checkBuildTools
};