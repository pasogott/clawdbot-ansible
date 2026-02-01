#!/bin/bash
set -e

# OpenClaw Ansible Installer
# This script installs Ansible if needed and runs the OpenClaw playbook

# Enable 256 colors
export TERM=xterm-256color

# Force color support
if [ -z "$COLORTERM" ]; then
    export COLORTERM=truecolor
fi

REPO_URL="https://raw.githubusercontent.com/openclaw/openclaw-ansible/main"
PLAYBOOK_URL="${REPO_URL}/playbook.yml"
TEMP_DIR=$(mktemp -d)

# Colors (with 256-color support)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   OpenClaw Ansible Installer          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Detect operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    echo -e "${GREEN}Detected: macOS${NC}"
elif command -v apt-get &> /dev/null; then
    OS_TYPE="linux"
    echo -e "${GREEN}Detected: Debian/Ubuntu Linux${NC}"
else
    echo -e "${RED}Error: Unsupported operating system.${NC}"
    echo -e "${RED}This installer supports: Debian/Ubuntu and macOS${NC}"
    exit 1
fi

# Check if running as root or with sudo access
if [ "$EUID" -eq 0 ]; then
    echo -e "${GREEN}Running as root.${NC}"
    SUDO=""
    ANSIBLE_EXTRA_VARS="-e ansible_become=false"
else
    if ! command -v sudo &> /dev/null; then
        echo -e "${RED}Error: sudo is not installed. Please install sudo or run as root.${NC}"
        exit 1
    fi
    SUDO="sudo"
    ANSIBLE_EXTRA_VARS="--ask-become-pass"
fi

echo -e "${GREEN}[1/4] Checking prerequisites...${NC}"

# Check if Ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${YELLOW}Ansible not found. Installing...${NC}"
    $SUDO apt-get update -qq
    $SUDO apt-get install -y ansible
    echo -e "${GREEN}✓ Ansible installed${NC}"
else
    echo -e "${GREEN}✓ Ansible already installed${NC}"
fi

echo -e "${GREEN}[2/5] Downloading playbook...${NC}"

# Download the playbook and role files
cd "$TEMP_DIR"

# For simplicity, we'll clone the entire repo
echo "Cloning repository..."
git clone https://github.com/openclaw/openclaw-ansible.git
cd openclaw-ansible

echo -e "${GREEN}✓ Playbook downloaded${NC}"

echo -e "${GREEN}[3/5] Installing Ansible collections...${NC}"
ansible-galaxy collection install -r requirements.yml

echo -e "${GREEN}[4/5] Running Ansible playbook...${NC}"
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}You will be prompted for your sudo password.${NC}"
fi
echo ""

# Run the playbook
./run-playbook.sh $ANSIBLE_EXTRA_VARS

# Cleanup
cd /
rm -rf "$TEMP_DIR"

# run-playbook.sh will display instructions to switch to openclaw user
