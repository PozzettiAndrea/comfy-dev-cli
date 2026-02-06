#!/bin/bash
# =============================================================================
# 04-WSL-SETUP.SH
# Run this inside Ubuntu WSL2 after initial setup
# Usage: bash /mnt/c/Users/YOUR_USERNAME/github-runners/04-wsl-setup.sh
# =============================================================================

set -e

echo "=== WSL2 Ubuntu Setup ==="

# ============================================================================
# PASSWORDLESS SUDO
# Needed so the runner can install system deps without hanging on a prompt
# ============================================================================
if sudo -n true 2>/dev/null; then
    echo "Passwordless sudo already configured"
else
    echo "Configuring passwordless sudo..."
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/nopasswd > /dev/null
    sudo chmod 440 /etc/sudoers.d/nopasswd
    echo "Passwordless sudo configured"
fi

# ============================================================================
# SYSTEM UPDATE
# ============================================================================
echo "Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# ============================================================================
# ESSENTIAL TOOLS
# ============================================================================
echo "Installing essential tools..."
sudo apt-get install -y zstd zip

# ============================================================================
# DOCKER
# Container runtime for isolated job execution
# ============================================================================
if command -v docker &> /dev/null; then
    echo "Docker already installed"
else
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed"
fi

# ============================================================================
# NVIDIA CONTAINER TOOLKIT
# GPU passthrough for Docker containers
# ============================================================================
if command -v nvidia-ctk &> /dev/null; then
    echo "NVIDIA Container Toolkit already installed"
else
    echo "Installing NVIDIA Container Toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker || true
    echo "NVIDIA Container Toolkit installed"
fi

# ============================================================================
# GITHUB ACTIONS RUNNER
# Self-hosted runner for Linux jobs
# ============================================================================
RUNNER_DIR="$HOME/github-runners/linux"
mkdir -p "$RUNNER_DIR"

if [ -f "$RUNNER_DIR/run.sh" ]; then
    echo "Linux GitHub Runner already downloaded"
else
    echo "Downloading Linux GitHub Runner..."
    RUNNER_VERSION="2.321.0"
    cd "$RUNNER_DIR"
    curl -o actions-runner-linux.tar.gz -L "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
    tar xzf actions-runner-linux.tar.gz
    rm actions-runner-linux.tar.gz
    echo "Linux GitHub Runner downloaded"
fi

# ============================================================================
# VERIFY GPU ACCESS
# ============================================================================
echo ""
echo "Verifying GPU access..."
if nvidia-smi &> /dev/null; then
    echo "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "WARNING: nvidia-smi not working. GPU passthrough may not be configured."
    echo "Make sure you have NVIDIA drivers installed on Windows."
fi

# ============================================================================
# VERIFY DOCKER GPU ACCESS
# ============================================================================
echo ""
echo "Verifying Docker GPU access..."
if docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi &> /dev/null; then
    echo "Docker GPU passthrough working!"
else
    echo "WARNING: Docker GPU passthrough not working yet."
    echo "You may need to restart WSL: wsl --shutdown (from Windows)"
fi

echo ""
echo "=== WSL2 Ubuntu Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Run 'gh auth login' in Windows"
echo "  2. Double-click 'Register-Runner.bat' on Desktop"
