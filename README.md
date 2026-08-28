# OpenClaw Ansible Installer

![OpenClaw Ansible banner](docs/assets/readme-banner.jpg)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Lint](https://github.com/openclaw/openclaw-ansible/actions/workflows/lint.yml/badge.svg)](https://github.com/openclaw/openclaw-ansible/actions/workflows/lint.yml)
[![Ansible](https://img.shields.io/badge/Ansible-2.14+-blue.svg)](https://www.ansible.com/)
[![Multi-OS](https://img.shields.io/badge/OS-Debian%20%7C%20Ubuntu-orange.svg)](https://www.debian.org/)

Automated, hardened installation of [OpenClaw](https://github.com/openclaw/openclaw) with Docker and Tailscale VPN support for Debian/Ubuntu Linux.

## ⚠️ macOS Support: Deprecated & Disabled

**Effective 2026-02-06, support for bare-metal macOS installations has been removed from this playbook.**

### Why?
The underlying project currently requires system-level permissions and configurations that introduce significant security risks when executed on a primary host OS. To protect user data and system integrity, we have disabled bare-metal execution.

### What does this mean?
* The playbook will now explicitly fail if run on a `Darwin` (macOS) system.
* We strongly discourage manual workarounds to bypass this check.
* **Future Support:** We are evaluating a virtualization-first strategy (using Vagrant or Docker) to provide a sandboxed environment for this project in the future.

## Features

- 🔒 **Firewall-first**: UFW firewall + Docker isolation
- 🛡️ **Fail2ban**: SSH brute-force protection out of the box
- 🔄 **Auto-updates**: Automatic security patches via unattended-upgrades
- 🔐 **Tailscale VPN**: Secure remote access without exposing services
- 🐳 **Docker**: Docker CE with security hardening
- 🚀 **One-command install**: Complete setup in minutes
- 🔧 **Auto-configuration**: DBus, systemd, environment setup
- 📦 **pnpm installation**: Uses `pnpm install -g openclaw@latest`

## Quick Start (Standalone / Self-Hosted)

### Release Mode (Recommended)

Install the latest stable version from npm:

```bash
curl -fsSL https://raw.githubusercontent.com/openclaw/openclaw-ansible/main/install.sh | bash
```

### Development Mode

Install from source for development or testing:

```bash
# Clone the installer
git clone https://github.com/openclaw/openclaw-ansible.git
cd openclaw-ansible

# Install in development mode
./run-playbook.sh -e openclaw_install_mode=development
```

## What Gets Installed

- Tailscale (mesh VPN)
- UFW firewall (SSH + Tailscale ports only)
- Docker CE + Compose V2 (for sandboxes)
- Node.js 22.x + pnpm
- OpenClaw on host (not containerized)
- Systemd user-service prerequisites (onboarding installs the Gateway service)

## Post-Install

After installation completes, switch to the openclaw user:

```bash
sudo su - openclaw
```

Then run the quick-start onboarding wizard:

```bash
openclaw onboard --install-daemon
```

This will:
- Guide you through the setup wizard
- Configure your messaging provider (WhatsApp/Telegram/Signal)
- Install and start the daemon service

After onboarding, run the [post-install security verification](docs/security.md#verification). The checks confirm that the firewall and SSH protection are active, Docker-published ports remain externally blocked, and OpenClaw only listens on localhost.

### Alternative Manual Setup

```bash
# Configure manually
openclaw configure

# Login to provider
openclaw providers login

# Test gateway
openclaw gateway

# Install as daemon
openclaw daemon install
openclaw daemon start

# Check status
openclaw status
openclaw logs
```

## Manual Installation

### Release Mode (Default)

```bash
# Install dependencies
sudo apt update && sudo apt install -y ansible git

# Clone repository
git clone https://github.com/openclaw/openclaw-ansible.git
cd openclaw-ansible

# Install Ansible collections
ansible-galaxy collection install -r requirements.yml

# Run installation
./run-playbook.sh
```

### Development Mode

Build from source for development:

```bash
# Same as above, but with development mode flag
./run-playbook.sh -e openclaw_install_mode=development

# Or directly:
ansible-playbook playbook.yml --ask-become-pass -e openclaw_install_mode=development
```

This will:
- Clone openclaw repo to `~/code/openclaw`
- Run `pnpm install` and `pnpm build`
- Symlink binary to `~/.local/bin/openclaw`
- Add development aliases to `.bashrc`

## Installation as Ansible Collection

`openclaw.installer` is an Ansible collection and can be installed with the `ansible-galaxy` command:

```bash
ansible-galaxy collection install git+https://github.com/openclaw/openclaw-ansible.git
```

Alternatively, add it to the [`requirements.yml` file of your Ansible project](https://docs.ansible.com/ansible/latest/collections_guide/collections_installing.html#install-multiple-collections-with-a-requirements-file) as follows:

```yaml
collections:
  - name: https://github.com/openclaw/openclaw-ansible.git
    type: git
    version: main
```

As a version, you can use a branch, a version tag (e.g., `v2.0.0`), or a specific commit hash.

### Usage

First copy the sample inventory to `inventory.yml`.

```bash
cp inventory-sample.yml inventory.yml
```

Second edit the inventory file to match your cluster setup. For example:

```yaml
openclaw_servers:
  children:
    server:
      hosts:
        192.16.35.11:
        192.16.35.12:
```

If needed, you can also edit `vars` section to match your environment.

Start provisioning of the server using one of the following commands. The command to be used depends on whether you installed `openclaw.installer` with `ansible-galaxy` or if you run the playbook from within the cloned git repository:

*Installed with ansible-galaxy*

```bash
ansible-playbook openclaw.installer.deploy -i inventory.yml
```

*In your existing playbook*

```yaml
- name: Deploy OpenClaw
  hosts: my_servers
  become: true
  roles:
    - openclaw.installer.openclaw
```

*Running the playbook from inside the repository*

```bash
ansible-playbook playbooks/deploy.yml -i inventory.yml
```

Alternatively, to run the playbook from your existing project setup, run the playbook from within your own playbook:

*Installed with ansible-galaxy*

```yaml
- name: Deploy OpenClaw
  ansible.builtin.import_playbook: openclaw.installer.deploy
```

*Running the playbook from inside the repository*

```yaml
- name: Deploy OpenClaw
  ansible.builtin.import_playbook: playbooks/deploy.yml
```

## Installation Modes

### Release Mode (Default)
- Installs via `pnpm install -g openclaw@latest`
- Gets latest stable version from npm registry
- Automatic updates via `pnpm install -g openclaw@latest`
- **Recommended for production**

### Development Mode
- Clones from `https://github.com/openclaw/openclaw.git`
- Builds from source with `pnpm build`
- Symlinks binary to `~/.local/bin/openclaw`
- Adds helpful aliases:
  - `openclaw-rebuild` - Rebuild after code changes
  - `openclaw-dev` - Navigate to repo directory
  - `openclaw-pull` - Pull, install deps, and rebuild
- **Recommended for development and testing**

Enable with: `-e openclaw_install_mode=development`

## Security

- **Public ports**: SSH (22), Tailscale (41641/udp) only
- **Fail2ban**: SSH brute-force protection (5 attempts → 1 hour ban)
- **Automatic updates**: Security patches via unattended-upgrades
- **Docker isolation**: Containers can't expose ports externally (DOCKER-USER chain)
- **Non-root**: OpenClaw runs as unprivileged user
- **No Docker socket access**: The OpenClaw user is excluded from the root-equivalent `docker` group
- **Scoped sudo**: Limited to service management (not full root)
- **Service ownership**: Onboarding installs the native Gateway's systemd user service; this role does not apply systemd sandboxing directives

Run the [post-install security verification](docs/security.md#verification) for commands and expected results. In the default configuration, an external TCP scan should show only SSH on port 22; Tailscale uses UDP and is not included in that TCP scan.

### Security Note

For high-security environments, audit before running:

```bash
git clone https://github.com/openclaw/openclaw-ansible.git
cd openclaw-ansible
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

- Debian 11+ or Ubuntu 20.04+
- Root/sudo access
- Internet connection

## Configuration Options

All configuration variables can be found in [`roles/openclaw/defaults/main.yml`](roles/openclaw/defaults/main.yml).

You can override them in three ways:

### 1. Via Command Line

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e openclaw_install_mode=development \
  -e "openclaw_ssh_keys=['ssh-ed25519 AAAAC3... user@host']"
```

### 2. Via Variables File

```bash
# Create vars.yml
cat > vars.yml << EOF
openclaw_install_mode: development
openclaw_ssh_keys:
  - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGxxxxxxxx user@host"
  - "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... user@host"
openclaw_repo_url: "https://github.com/YOUR_USERNAME/openclaw.git"
openclaw_repo_branch: "feature-branch"
tailscale_authkey: "tskey-auth-xxxxxxxxxxxxx"
EOF

# Use it
ansible-playbook playbook.yml --ask-become-pass -e @vars.yml
```

### 3. Edit Defaults Directly

Edit `roles/openclaw/defaults/main.yml` before running the playbook.

### Available Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `openclaw_user` | `openclaw` | System user name |
| `openclaw_home` | `/home/openclaw` | User home directory |
| `openclaw_install_mode` | `release` | `release` or `development` |
| `openclaw_ssh_keys` | `[]` | List of SSH public keys |
| `openclaw_repo_url` | `https://github.com/openclaw/openclaw.git` | Git repository (dev mode) |
| `openclaw_repo_branch` | `main` | Git branch (dev mode) |
| `tailscale_authkey` | `""` | Tailscale auth key for auto-connect |
| `nodejs_version` | `22.x` | Node.js version to install |

See [`roles/openclaw/defaults/main.yml`](roles/openclaw/defaults/main.yml) for the complete list.

### Common Configuration Examples

#### SSH Keys for Remote Access

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e "openclaw_ssh_keys=['ssh-ed25519 AAAAC3... user@host']"
```

#### Development Mode with Custom Repository

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e openclaw_install_mode=development \
  -e openclaw_repo_url=https://github.com/YOUR_USERNAME/openclaw.git \
  -e openclaw_repo_branch=feature-branch
```

#### Tailscale Auto-Connect

```bash
ansible-playbook playbook.yml --ask-become-pass \
  -e tailscale_authkey=tskey-auth-xxxxxxxxxxxxx
```

## License

MIT - see [LICENSE](LICENSE)

## Support

- OpenClaw: https://github.com/openclaw/openclaw
- This installer: https://github.com/openclaw/openclaw-ansible/issues
