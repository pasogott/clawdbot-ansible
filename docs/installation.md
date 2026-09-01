---
title: Installation Guide
description: Detailed installation and configuration instructions
---

# Installation Guide

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/openclaw/openclaw-ansible/main/install.sh | bash
```

## Manual Installation

### Prerequisites

```bash
sudo apt update
sudo apt install -y ansible git
```

### Clone and Run

```bash
git clone https://github.com/openclaw/openclaw-ansible.git
cd openclaw-ansible

# Install Ansible collections
ansible-galaxy collection install -r requirements.yml

# Run playbook
ansible-playbook playbook.yml --ask-become-pass
```

## Post-Installation

### 1. Connect the Selected Mesh VPN

For Tailscale:

```bash
# Interactive login
sudo tailscale up

# Or with auth key for automation
sudo tailscale up --authkey tskey-auth-xxxxx

# Check status
sudo tailscale status
```

Get auth keys from: https://login.tailscale.com/admin/settings/keys

For NetBird:

```bash
# NetBird Cloud
sudo netbird up

# Self-hosted NetBird
sudo netbird up --management-url=https://netbird.example.com

sudo netbird status
```

When `netbird_setup_key` is supplied, the role performs this registration
automatically. NetBird clients do not require an inbound firewall port.

### 2. Configure OpenClaw and Install the Gateway Service

Switch to the dedicated account and run onboarding:

```bash
sudo su - openclaw
openclaw onboard --install-daemon
```

Onboarding creates `~/.openclaw/openclaw.json` (JSON5), guides provider setup, and installs the native Gateway as a systemd user service. The Ansible role prepares directories and dependencies but does not create the application configuration or service. There is no installer-managed `config.yml` or OpenClaw container.

## Service Management

Run these as the OpenClaw user:

```bash
openclaw gateway status
openclaw gateway stop
openclaw gateway start
openclaw gateway restart
openclaw logs
```

For systemd inspection, the default user unit is `openclaw-gateway.service`:

```bash
systemctl --user status openclaw-gateway.service
journalctl --user -u openclaw-gateway.service -n 50
```

The installer does not add systemd sandboxing directives to this unit. See [service security](security.md#native-gateway-service) and the [upstream Gateway runbook](https://docs.openclaw.ai/gateway) for configuration and service details.

### Firewall Management

```bash
# View UFW status
sudo ufw status verbose

# Add custom rule
sudo ufw allow 8080/tcp comment 'Custom service'
sudo ufw reload

# View Docker isolation
sudo iptables -L DOCKER-USER -n -v
```

## Accessing OpenClaw

The native Gateway defaults to loopback port `18789`. Use the actual port reported by `openclaw gateway status` if you changed it during configuration.

### Via SSH Tunnel

```bash
ssh -N -L 18789:127.0.0.1:18789 user@server
# Then browse to: http://localhost:18789
```

The server can be reached through its Tailscale address. Connecting Tailscale alone does not make a loopback listener reachable at the server's Tailscale IP. For direct browser access, configure [Tailscale Serve](https://docs.openclaw.ai/gateway/tailscale) separately.

## Verification

Run the complete [post-install security verification](security.md#verification). It includes every command, the expected healthy result, and notes about output that varies by host.

At minimum, confirm:

- UFW is active with incoming and routed traffic denied by default.
- The `sshd` fail2ban jail is enabled.
- OpenClaw listens on `127.0.0.1`, not `0.0.0.0`.
- The `DOCKER-USER` chain drops externally routed container traffic.
- An external TCP scan exposes only the configured SSH port.
- A published test container works locally but cannot be reached externally.
- Tailscale is connected when enabled, and unattended upgrades are active.

## Uninstall

First back up any configuration and data you need. As the OpenClaw user, remove the onboarding-managed service:

```bash
openclaw gateway stop
openclaw gateway uninstall
```

Then, as an administrator, remove the account or packages only if they are no longer needed. Removing the account's home deletes its OpenClaw data; Docker, Node.js, Tailscale, and firewall rules may be shared with other services.

## Advanced Configuration

Use `openclaw configure` as the OpenClaw user for application settings. Gateway ports, credentials, and channel policy belong to `~/.openclaw/openclaw.json`, not a Compose file. See the [upstream configuration guide](https://docs.openclaw.ai/gateway/configuration) for supported settings and restart requirements.

The legacy installer variable `openclaw_port` does not configure the native Gateway. Use onboarding or OpenClaw configuration to change the port.

## Automation

### Unattended Install

```bash
# Set Tailscale auth key in playbook vars
ansible-playbook playbook.yml \
  --ask-become-pass \
  -e "tailscale_authkey=tskey-auth-xxxxx"
```

### CI/CD Integration

```yaml
# Example GitHub Actions
- name: Deploy OpenClaw
  run: |
    ansible-playbook playbook.yml \
      -e "tailscale_authkey=${{ secrets.TAILSCALE_KEY }}" \
      --become
```
