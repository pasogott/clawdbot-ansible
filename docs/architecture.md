---
title: Architecture
description: Technical implementation details
---

# Architecture

## Component Overview

The Gateway runs natively on the host as the dedicated `openclaw` user. Docker is installed for sandbox use, not to host the Gateway.

```text
Host
├── UFW + fail2ban (host firewall and SSH protection)
├── Docker + DOCKER-USER (container network isolation)
└── openclaw user
    ├── Node.js + OpenClaw (npm release or source checkout)
    ├── ~/.openclaw/openclaw.json (created by onboarding)
    └── systemd user service (installed by onboarding)
```

The role creates the account, installs dependencies and OpenClaw, and prepares its directory structure. It does not generate application configuration, install a Gateway service, or start the Gateway. The operator completes setup with `openclaw onboard --install-daemon` as the OpenClaw user.

## File Structure

Default paths after installation and onboarding:

```text
/home/openclaw/
├── .local/bin/openclaw
├── .local/share/pnpm/
├── .openclaw/
│   ├── openclaw.json                 # Onboarding-owned JSON5 configuration
│   ├── sessions/
│   └── credentials/
└── .config/systemd/user/
    └── openclaw-gateway.service      # Onboarding-owned user unit

/etc/docker/daemon.json               # Role-managed Docker configuration
/etc/ufw/after.rules                  # Role-managed DOCKER-USER rules
```

The role does not create `/opt/openclaw/docker-compose.yml` or `/etc/systemd/system/openclaw.service`. Development mode additionally creates a source checkout under `~/code/openclaw` by default.

## Service and Configuration Ownership

Onboarding owns the native Gateway's configuration and service lifecycle. Use `openclaw gateway status`, `openclaw gateway restart`, and `openclaw logs` as the OpenClaw user; see the [upstream Gateway runbook](https://docs.openclaw.ai/gateway).

The installer does not apply systemd sandboxing directives or application allowlists and rate limits. Inspect the installed service and application configuration rather than inferring runtime controls from the presence of Docker. See [security verification](security.md#verification).

## Ansible Task Order

```text
roles/openclaw/tasks/main.yml
├── system-tools.yml (base packages and host tools)
├── tailscale-linux.yml (optional VPN installation)
├── user.yml (account and user-service prerequisites)
├── docker-linux.yml (Docker; includes docker-security.yml)
├── firewall-linux.yml (UFW and Docker daemon configuration)
├── nodejs.yml (Node.js and pnpm)
└── openclaw.yml (directories and release/development installation)
```

Docker must be installed before firewall configuration: `/etc/docker` must exist for `daemon.json`, and the Docker service must exist before configuration changes can restart it.

## Security Boundaries

UFW protects host services. Docker-published traffic can bypass UFW, so the separate DOCKER-USER chain filters incoming container traffic. Neither mechanism configures the native Gateway's bind address.

The default native Gateway uses loopback; onboarding owns that setting. Verify it after setup, and use an SSH tunnel or explicitly configured Tailscale Serve for remote access. The role excludes the service account from the root-equivalent Docker group; operators administer Docker explicitly through `sudo`.
