# Quick Start Script - Run Pulumi E-commerce Infrastructure
# This script automates the entire setup and deployment process

param(
    [switch]$SkipSetup,
    [switch]$Preview,
    [switch]$Deploy,
    [string]$InstanaKey = "",
    [string]$DbPassword = ""
)

$ErrorActionPreference = "Stop"

Write-Host @"
╔═══════════════════════════════════════════════════════════╗
║   Pulumi E-commerce Infrastructure Quick Start           ║
║   Complete AWS stack with Instana monitoring             ║
╔═══════════════════════════════════════════════════════════╗
"@ -ForegroundColor Cyan

# Step 1: Setup (unless skipped)
if (-not $SkipSetup) {
    Write-Host "`n📦 Step 1: Running setup..." -ForegroundColor Yellow
    .\setup.ps1
} else {
    Write-Host "`n⏭️  Skipping setup..." -ForegroundColor Gray
    & ".\venv\Scripts\Activate.ps1"
}

# Step 2: Check AWS credentials
Write-Host "`n🔐 Step 2: Checking AWS credentials..." -ForegroundColor Yellow
try {
    $awsIdentity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
    Write-Host "✅ AWS credentials configured" -ForegroundColor Green
    Write-Host "   Account: $($awsIdentity.Account)" -ForegroundColor Gray
    Write-Host "   User: $($awsIdentity.Arn)" -ForegroundColor Gray
} catch {
    Write-Host "❌ AWS credentials not configured!" -ForegroundColor Red
    Write-Host "Please run: aws configure" -ForegroundColor Yellow
    exit 1
}

# Step 3: Login to Pulumi
Write-Host "`n🔑 Step 3: Checking Pulumi login..." -ForegroundColor Yellow
try {
    $pulumiWhoami = pulumi whoami 2>&1
    Write-Host "✅ Logged in to Pulumi as: $pulumiWhoami" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Not logged in to Pulumi" -ForegroundColor Yellow
    Write-Host "Logging in to local backend..." -ForegroundColor Yellow
    pulumi login --local
}

# Step 4: Initialize stack
Write-Host "`n📚 Step 4: Initializing Pulumi stack..." -ForegroundColor Yellow
$stackExists = $false
try {
    pulumi stack select dev 2>&1 | Out-Null
    $stackExists = $true
    Write-Host "✅ Using existing 'dev' stack" -ForegroundColor Green
} catch {
    Write-Host "Creating new 'dev' stack..." -ForegroundColor Yellow
    pulumi stack init dev
    Write-Host "✅ Stack 'dev' created" -ForegroundColor Green
}

# Step 5: Configure secrets
Write-Host "`n🔒 Step 5: Configuring secrets..." -ForegroundColor Yellow

# Check if Instana key is set
$instanaKeySet = $false
try {
    $currentKey = pulumi config get instana:agentKey 2>&1
    if ($currentKey) {
        $instanaKeySet = $true
        Write-Host "✅ Instana agent key already set" -ForegroundColor Green
    }
} catch {}

if (-not $instanaKeySet) {
    if ($InstanaKey) {
        Write-Host "Setting Instana agent key from parameter..." -ForegroundColor Yellow
        pulumi config set --secret instana:agentKey $InstanaKey
        Write-Host "✅ Instana agent key set" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Instana agent key not set" -ForegroundColor Yellow
        $key = Read-Host "Enter your Instana agent key (or press Enter to skip)"
        if ($key) {
            pulumi config set --secret instana:agentKey $key
            Write-Host "✅ Instana agent key set" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Skipping Instana configuration (required for monitoring)" -ForegroundColor Yellow
        }
    }
}

# Check if DB password is set
$dbPasswordSet = $false
try {
    $currentPassword = pulumi config get db:password 2>&1
    if ($currentPassword) {
        $dbPasswordSet = $true
        Write-Host "✅ Database password already set" -ForegroundColor Green
    }
} catch {}

if (-not $dbPasswordSet) {
    if ($DbPassword) {
        Write-Host "Setting database password from parameter..." -ForegroundColor Yellow
        pulumi config set --secret db:password $DbPassword
        Write-Host "✅ Database password set" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Database password not set" -ForegroundColor Yellow
        $password = Read-Host "Enter Aurora database password (or press Enter to use default)"
        if ($password) {
            pulumi config set --secret db:password $password
            Write-Host "✅ Database password set" -ForegroundColor Green
        } else {
            Write-Host "Using default password (ChangeMe123!)" -ForegroundColor Yellow
        }
    }
}

# Step 6: Preview or Deploy
Write-Host "`n🚀 Step 6: Ready to deploy!" -ForegroundColor Yellow

if ($Preview) {
    Write-Host "`nRunning preview..." -ForegroundColor Cyan
    pulumi preview
} elseif ($Deploy) {
    Write-Host "`nDeploying infrastructure..." -ForegroundColor Cyan
    Write-Host "⚠️  This will create real AWS resources and incur costs!" -ForegroundColor Yellow
    $confirm = Read-Host "Continue? (yes/no)"
    if ($confirm -eq "yes") {
        pulumi up --yes
        Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
        Write-Host "`nOutputs:" -ForegroundColor Cyan
        pulumi stack output
    } else {
        Write-Host "Deployment cancelled" -ForegroundColor Yellow
    }
} else {
    Write-Host @"

Next steps:
  1. Preview changes:
     pulumi preview

  2. Deploy infrastructure:
     pulumi up

  3. Or use quick commands:
     .\run.ps1 -Preview
     .\run.ps1 -Deploy

  4. Destroy when done:
     pulumi destroy

"@ -ForegroundColor Cyan
}

Write-Host "`n✅ Quick start complete!" -ForegroundColor Green
