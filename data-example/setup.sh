#!/usr/bin/env bash
# Setup script for Pulumi E-commerce Infrastructure (for WSL/Linux/macOS)

set -e

echo "🚀 Setting up Pulumi E-commerce Infrastructure..."

# Check if Python is installed
if command -v python3 &> /dev/null; then
    echo "✅ Python found: $(python3 --version)"
else
    echo "❌ Python not found. Please install Python 3.7+"
    exit 1
fi

# Check if Pulumi is installed
if command -v pulumi &> /dev/null; then
    echo "✅ Pulumi found: $(pulumi version)"
else
    echo "❌ Pulumi not found. Installing Pulumi..."
    echo "Please install Pulumi from: https://www.pulumi.com/docs/install/"
    echo "Or run: curl -fsSL https://get.pulumi.com | sh"
    exit 1
fi

# Check and install python3-venv if needed (for Ubuntu/Debian)
if [ -f /etc/debian_version ]; then
    if ! dpkg -l | grep -q python3-venv; then
        echo "📦 Installing python3-venv..."
        sudo apt update
        sudo apt install -y python3-venv python3-pip
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Configure AWS credentials:"
echo "   aws configure"
echo ""
echo "2. Login to Pulumi:"
echo "   pulumi login"
echo "   (or 'pulumi login --local' for local backend)"
echo ""
echo "3. Set required secrets:"
echo "   pulumi config set --secret instana:agentKey YOUR_KEY"
echo "   pulumi config set --secret db:password YOUR_PASSWORD"
echo ""
echo "4. Preview the deployment:"
echo "   pulumi preview"
echo ""
echo "5. Deploy the infrastructure:"
echo "   pulumi up"
echo ""
