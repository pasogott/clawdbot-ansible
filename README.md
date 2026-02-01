# Clawdbot Ansible Installer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Lint](https://github.com/pasogott/clawdbot-ansible/actions/workflows/lint.yml/badge.svg)](https://github.com/pasogott/clawdbot-ansible/actions/workflows/lint.yml)
[![Ansible](https://img.shields.io/badge/Ansible-2.14+-blue.svg)](https://www.ansible.com/)
[![Multi-OS](https://img.shields.io/badge/OS-Debian%20%7C%20Ubuntu%20%7C%20macOS-orange.svg)](https://www.debian.org/)

Automated, hardened installation of [Clawdbot](https://github.com/clawdbot/clawdbot) with Docker, Homebrew, and Tailscale VPN support for Linux and macOS.

## Features

- 🔒 **Firewall-first**: UFW (Linux) + Application Firewall (macOS) + Docker isolation
- 🛡️ **Fail2ban**: SSH brute-force protection out of the box
- 🔄 **Auto-updates**: Automatic security patches via unattended-upgrades
- 🔐 **Tailscale VPN**: Secure remote access without exposing services
- 🍺 **Homebrew**: Package manager for both Linux and macOS
- 🐳 **Docker**: Docker CE (Linux) / Docker Desktop (macOS)
- 🌐 **Multi-OS Support**: Debian, Ubuntu, and macOS
- 🚀 **One-command install**: Complete setup in minutes
- 🔧 **Auto-configuration**: DBus, systemd, environment setup
- 📦 **pnpm installation**: Uses `pnpm install -g clawdbot@latest`

## Quick Start

### Release Mode (Recommended)

Install the latest stable version from npm:

```bash
curl -fsSL https://raw.githubusercontent.com/pasogott/clawdbot-ansible/main/install.sh | bash
```

### Development Mode

Install from source for development or testing:

```bash
# Clone the installer
git clone https://github.com/pasogott/clawdbot-ansible.git
cd clawdbot-ansible

# Install in development mode
ansible-playbook playbook.yml --ask-become-pass -e clawdbot_install_mode=development
```

## What Gets Installed

- Tailscale (mesh VPN)
- UFW firewall (SSH + Tailscale ports only)
- Docker CE + Compose V2 (for sandboxes)
- Node.js 22.x + pnpm
- Clawdbot on host (not containerized)
- Systemd service (auto-start)

## Post-Install

After installation completes, switch to the clawdbot user:

```bash
sudo su - clawdbot
```

Then run the quick-start onboarding wizard:

```bash
clawdbot onboard --install-daemon
```

This will:
- Guide you through the setup wizard
- Configure your messaging provider (WhatsApp/Telegram/Signal)
- Install and start the daemon service

### Alternative Manual Setup

```bash
# Configure manually
clawdbot configure

# Login to provider
clawdbot providers login

# Test gateway
clawdbot gateway

# Install as daemon
clawdbot daemon install
clawdbot daemon start

# Check status
clawdbot status
clawdbot logs
```

## Installation Modes

### Release Mode (Default)
- Installs via `pnpm install -g clawdbot@latest`
- Gets latest stable version from npm registry
- Automatic updates via `pnpm install -g clawdbot@latest`
- **Recommended for production**

### Development Mode
- Clones from `https://github.com/clawdbot/clawdbot.git`
- Builds from source with `pnpm build`
- Symlinks binary to `~/.local/bin/clawdbot`
- Adds helpful aliases:
  - `clawdbot-rebuild` - Rebuild after code changes
  - `clawdbot-dev` - Navigate to repo directory
  - `clawdbot-pull` - Pull, install deps, and rebuild
- **Recommended for development and testing**

Enable with: `-e clawdbot_install_mode=development`

## Security

- **Public ports**: SSH (22), Tailscale (41641/udp) only
- **Fail2ban**: SSH brute-force protection (5 attempts → 1 hour ban)
- **Automatic updates**: Security patches via unattended-upgrades
- **Docker isolation**: Containers can't expose ports externally (DOCKER-USER chain)
- **Non-root**: Clawdbot runs as unprivileged user
- **Scoped sudo**: Limited to service management (not full root)
- **Systemd hardening**: NoNewPrivileges, PrivateTmp, ProtectSystem

Verify: `nmap -p- YOUR_SERVER_IP` should show only port 22 open.

### Security Note

For high-security environments, audit before running:

```bash
git clone https://github.com/openclaw/clawdbot-ansible.git
cd clawdbot-ansible
# Review playbook.yml and roles/
ansible-playbook playbook.yml --check --diff  # Dry run
ansible-playbook playbook.yml --ask-become-pass
```

## Documentation

- [Configuration Guide](docs/configuration.md) - All configuration options
- [Development Mode](docs/development-mode.md) - Build from source
- [Security Architecture](docs/security.md) - Security details
- [Technical Details](docs/architecture.md) - Architecture overview
- [Troubleshooting](docs/troubleshooting.md) - Common issues
- [Agent Guidelines](AGENTS.md) - AI agent instructions

## Requirements

### Linux (Debian/Ubuntu)
- Debian 11+ or Ubuntu 20.04+
- Root/sudo access
- Internet connection

### macOS
- macOS 11 (Big Sur) or later
- Homebrew will be installed automatically
- Admin/sudo access
- Internet connection

## What Gets Installed

### Common (All OS)
- Homebrew package manager
- Node.js 22.x + pnpm
- Clawdbot via `pnpm install -g clawdbot@latest`
- Essential development tools
- Git, zsh, oh-my-zsh

### Linux-Specific
- Docker CE + Compose V2
- UFW firewall (configured)
- Tailscale VPN
- systemd service

### macOS-Specific
- Docker Desktop (via Homebrew Cask)
- Application Firewall
- Tailscale app

## Manual Installation

### Release Mode (Default)

```bash
# Install dependencies
sudo apt update && sudo apt install -y ansible git

# Clone repository
git clone https://github.com/pasogott/clawdbot-ansible.git
cd clawdbot-ansible

# Install Ansible collections
ansible-galaxy collection install -r requirements.yml

# Run installation
./run-playbook.sh
```

### Development Mode

Build from source for development:

```bash
# Same as above, but with development mode flag
./run-playbook.sh -e clawdbot_install_mode=development

# Or directly:
ansible-playbook playbook.yml --ask-become-pass -e clawdbot_install_mode=development
```

This will:
- Clone clawdbot repo to `~/code/clawdbot`
- Run `pnpm install` and `pnpm build`
- Symlink binary to `~/.local/bin/clawdbot`
- Add development aliases to `.bashrc`

## Configuration Options

All configuration variables can be found in [`roles/clawdbot/defaults/main.yml`](roles/clawdbot/defaults/main.yml).

You can override them in three ways:

### 1. Via Command Line

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e clawdbot_install_mode=development \
  -e "clawdbot_ssh_keys=['ssh-ed25519 AAAAC3... user@host']"
```

### 2. Via Variables File

```bash
# Create vars.yml
cat > vars.yml << EOF
clawdbot_install_mode: development
clawdbot_ssh_keys:
  - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGxxxxxxxx user@host"
  - "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... user@host"
clawdbot_repo_url: "https://github.com/YOUR_USERNAME/clawdbot.git"
clawdbot_repo_branch: "feature-branch"
tailscale_authkey: "tskey-auth-xxxxxxxxxxxxx"
EOF

# Use it
ansible-playbook playbook.yml --ask-become-pass -e @vars.yml
```

### 3. Edit Defaults Directly

Edit `roles/clawdbot/defaults/main.yml` before running the playbook.

### Available Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `clawdbot_user` | `clawdbot` | System user name |
| `clawdbot_home` | `/home/clawdbot` | User home directory |
| `clawdbot_install_mode` | `release` | `release` or `development` |
| `clawdbot_ssh_keys` | `[]` | List of SSH public keys |
| `clawdbot_repo_url` | `https://github.com/clawdbot/clawdbot.git` | Git repository (dev mode) |
| `clawdbot_repo_branch` | `main` | Git branch (dev mode) |
| `tailscale_authkey` | `""` | Tailscale auth key for auto-connect |
| `nodejs_version` | `22.x` | Node.js version to install |

See [`roles/clawdbot/defaults/main.yml`](roles/clawdbot/defaults/main.yml) for the complete list.

### Common Configuration Examples

#### SSH Keys for Remote Access

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e "clawdbot_ssh_keys=['ssh-ed25519 AAAAC3... user@host']"
```

#### Development Mode with Custom Repository

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e clawdbot_install_mode=development \
  -e clawdbot_repo_url=https://github.com/YOUR_USERNAME/clawdbot.git \
  -e clawdbot_repo_branch=feature-branch
```

#### Tailscale Auto-Connect

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e tailscale_authkey=tskey-auth-xxxxxxxxxxxxx
```

## License

MIT - see [LICENSE](LICENSE)

## Support

- Clawdbot: https://github.com/clawdbot/clawdbot
- This installer: https://github.com/pasogott/clawdbot-ansible/issues
