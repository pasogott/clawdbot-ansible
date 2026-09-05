#!/bin/bash
set -e

# OpenClaw Ansible Installer
# This script installs Ansible if needed and runs the OpenClaw playbook via Ansible Galaxy

# Enable 256 colors
export TERM=xterm-256color

# Force color support
if [ -z "$COLORTERM" ]; then
    export COLORTERM=truecolor
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Collection requires ansible-core >=2.14 (meta/runtime.yml). Distro apt
# ansible on Ubuntu 22.04 / Debian 11 is older; fail closed instead of
# adding a PPA from curl|bash.
MIN_ANSIBLE_CORE="2.14.0"

ansible_core_version_from_banner() {
    local banner="$1"
    if [[ "$banner" =~ \[core[[:space:]]+([0-9]+)\.([0-9]+)(\.([0-9]+))? ]]; then
        printf '%s.%s.%s' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[4]:-0}"
        return 0
    fi
    if [[ "$banner" =~ ansible-playbook[[:space:]]+([0-9]+)\.([0-9]+)(\.([0-9]+))? ]]; then
        printf '%s.%s.%s' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[4]:-0}"
        return 0
    fi
    return 1
}

version_ge() {
    local -a have need
    local i h n
    IFS=. read -r -a have <<<"$1"
    IFS=. read -r -a need <<<"$2"
    for i in 0 1 2; do
        h="${have[i]:-0}"
        n="${need[i]:-0}"
        if ((10#$h > 10#$n)); then
            return 0
        fi
        if ((10#$h < 10#$n)); then
            return 1
        fi
    done
    return 0
}

require_ansible_core() {
    local banner version first_line
    if ! banner="$(ansible-playbook --version 2>&1)"; then
        echo -e "${RED}Error: ansible-playbook --version failed.${NC}"
        echo -e "${RED}  Install ansible-core ${MIN_ANSIBLE_CORE} or newer, then re-run.${NC}"
        exit 1
    fi
    first_line="${banner%%$'\n'*}"
    if ! version="$(ansible_core_version_from_banner "$banner")"; then
        version=""
    fi
    if [ -z "$version" ] || ! version_ge "$version" "$MIN_ANSIBLE_CORE"; then
        echo -e "${RED}Error: ansible-playbook is older than ansible-core ${MIN_ANSIBLE_CORE}.${NC}"
        echo -e "${RED}  Found: ${first_line}${NC}"
        echo -e "${RED}  This collection requires ansible-core ${MIN_ANSIBLE_CORE}+ (meta/runtime.yml).${NC}"
        echo -e "${RED}  Debian 11 and Ubuntu 20.04/22.04 apt ansible is too old.${NC}"
        echo -e "${YELLOW}  Install a current controller, then re-run:${NC}"
        echo -e "${YELLOW}    pip3 install --user 'ansible-core>=2.14'${NC}"
        echo -e "${YELLOW}    # or add the Ansible PPA and install ansible-core${NC}"
        echo -e "${YELLOW}    # or use Debian 12+ / Ubuntu 24.04+, where apt meets 2.14${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ ansible-playbook ${version} meets ansible-core ${MIN_ANSIBLE_CORE}+${NC}"
}

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   OpenClaw Ansible Installer           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Detect operating system
if command -v apt-get &> /dev/null; then
    echo -e "${GREEN}✓ Detected: Debian/Ubuntu Linux${NC}"
else
    echo -e "${RED}✗ Error: Unsupported operating system${NC}"
    echo -e "${RED}  This installer supports: Debian/Ubuntu Linux only${NC}"
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

echo -e "${GREEN}[1/3] Checking prerequisites...${NC}"

# Check if Ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${YELLOW}Ansible not found. Installing Ansible and git...${NC}"
    $SUDO apt-get update -qq
    $SUDO apt-get install -y ansible git
    echo -e "${GREEN}✓ Ansible and git installed${NC}"
else
    echo -e "${GREEN}✓ Ansible already installed${NC}"
    if ! command -v git &> /dev/null; then
        echo -e "${YELLOW}git not found. Installing...${NC}"
        $SUDO apt-get update -qq
        $SUDO apt-get install -y git
        echo -e "${GREEN}✓ git installed${NC}"
    else
        echo -e "${GREEN}✓ git already installed${NC}"
    fi
fi

require_ansible_core

echo -e "${GREEN}[2/3] Installing OpenClaw collection...${NC}"

# Create temporary requirements file
REQUIREMENTS_FILE=$(mktemp)
cat > "$REQUIREMENTS_FILE" << EOF
---
collections:
  - name: https://github.com/openclaw/openclaw-ansible.git
    type: git
    version: main
EOF

# Install collection
ansible-galaxy collection install -r "$REQUIREMENTS_FILE" --force

echo -e "${GREEN}✓ Collection installed${NC}"

echo -e "${GREEN}[3/3] Running Ansible playbook...${NC}"
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}You will be prompted for your sudo password.${NC}"
fi
echo ""

# Run the playbook
ansible-playbook openclaw.installer.install $ANSIBLE_EXTRA_VARS "$@"

# Cleanup
rm -f "$REQUIREMENTS_FILE"
