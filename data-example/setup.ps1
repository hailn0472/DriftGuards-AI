# Setup script for Pulumi E-commerce Infrastructure

Write-Host "🚀 Setting up Pulumi E-commerce Infrastructure..." -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.7+" -ForegroundColor Red
    exit 1
}

# Check if Pulumi is installed
try {
    $pulumiVersion = pulumi version 2>&1
    Write-Host "✅ Pulumi found: $pulumiVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Pulumi not found. Installing Pulumi..." -ForegroundColor Yellow
    Write-Host "Please install Pulumi from: https://www.pulumi.com/docs/install/" -ForegroundColor Yellow
    Write-Host "Or run: choco install pulumi (if you have Chocolatey)" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "1. Configure AWS credentials:" -ForegroundColor White
Write-Host "   aws configure" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Login to Pulumi:" -ForegroundColor White
Write-Host "   pulumi login" -ForegroundColor Gray
Write-Host "   (or 'pulumi login --local' for local backend)" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Set required secrets:" -ForegroundColor White
Write-Host "   pulumi config set --secret instana:agentKey YOUR_KEY" -ForegroundColor Gray
Write-Host "   pulumi config set --secret db:password YOUR_PASSWORD" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Preview the deployment:" -ForegroundColor White
Write-Host "   pulumi preview" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Deploy the infrastructure:" -ForegroundColor White
Write-Host "   pulumi up" -ForegroundColor Gray
Write-Host ""
