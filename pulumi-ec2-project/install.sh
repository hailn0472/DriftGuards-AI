#!/usr/bin/env bash
set -e

echo "🚀 Installing Pulumi 'ec2' plugins..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLUGINS_DIR="$SCRIPT_DIR/pulumi-plugins"
PLUGIN_EC2="$PLUGINS_DIR/pulumi-ec2"
PLUGIN_EC2_DOWN="$PLUGINS_DIR/pulumi-ec2-down"

# Check if plugin files exist
if [ ! -f "$PLUGIN_EC2" ]; then
    echo "❌ Error: pulumi-ec2 script not found in $PLUGINS_DIR"
    exit 1
fi

if [ ! -f "$PLUGIN_EC2_DOWN" ]; then
    echo "❌ Error: pulumi-ec2-down script not found in $PLUGINS_DIR"
    exit 1
fi

# Make the plugins executable
chmod +x "$PLUGIN_EC2"
chmod +x "$PLUGINS_DIR/pulumi-ec2.py"
chmod +x "$PLUGIN_EC2_DOWN"
chmod +x "$PLUGINS_DIR/pulumi-ec2-down.py"
echo "✅ Made plugins executable"

# Detect installation method
echo ""
echo "Choose installation method:"
echo "1) Install to ~/.local/bin (no sudo required)"
read -p "Enter choice [1]: " choice

case $choice in
    1)
        echo "Installing to /usr/local/bin..."
        sudo cp "$PLUGIN_EC2" /usr/local/bin/pulumi-ec2
        sudo cp "$PLUGINS_DIR/pulumi-ec2.py" /usr/local/bin/pulumi-ec2.py
        sudo cp "$PLUGIN_EC2_DOWN" /usr/local/bin/pulumi-ec2-down
        sudo cp "$PLUGINS_DIR/pulumi-ec2-down.py" /usr/local/bin/pulumi-ec2-down.py
        echo "✅ Plugins installed to /usr/local/bin/"
        echo "You can now run:"
        echo "  - pulumi-ec2         (deploy and SSH)"
        echo "  - pulumi-ec2-down    (destroy infrastructure)"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Usage:"
echo "  pulumi-ec2               # Deploy and SSH (with confirmation)"
echo "  pulumi-ec2 --yes         # Deploy and SSH (auto-approve)"
echo "  pulumi-ec2-down          # Destroy infrastructure (with confirmation)"
echo "  pulumi-ec2-down --yes    # Destroy infrastructure (auto-approve)"
