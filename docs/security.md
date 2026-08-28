---
title: Security Architecture
description: Firewall configuration, Docker isolation, and security hardening details
---

# Security Architecture

## Overview

This playbook implements a multi-layer defense strategy to secure OpenClaw installations.

## Security Layers

### Layer 1: UFW Firewall

```bash
# Default policies
Incoming: DENY
Outgoing: ALLOW
Routed: DENY

# Allowed
SSH (22/tcp): ALLOW
Tailscale (41641/udp): ALLOW
```

### Layer 2: Fail2ban (SSH Protection)

Automatic protection against SSH brute-force attacks:

```bash
# Configuration
Max retries: 5 attempts
Ban time: 1 hour (3600 seconds)
Find time: 10 minutes (600 seconds)

# Check status
sudo fail2ban-client status sshd

# Unban an IP
sudo fail2ban-client set sshd unbanip IP_ADDRESS
```

### Layer 3: DOCKER-USER Chain

Custom iptables chain that prevents Docker from bypassing UFW:

```
*filter
:DOCKER-USER - [0:0]
-A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A DOCKER-USER -i lo -j ACCEPT
-A DOCKER-USER -i <default_interface> -j DROP
COMMIT
```

**Result**: Even `docker run -p 80:80 nginx` won't expose port 80 externally.

### Native Gateway and Container Binding

OpenClaw runs natively as the dedicated `openclaw` user. Onboarding owns its configuration, including the Gateway listener. OpenClaw's [default bind is loopback](https://docs.openclaw.ai/gateway/security#network-exposure-bind-ports-firewall); this role does not set `gateway.bind`. Verify the listener after onboarding or changing configuration.

For any containers you administer separately, explicitly bind published ports to localhost:

```yaml
ports:
  - "127.0.0.1:3000:3000"
```

The role installs Docker and its firewall isolation for sandbox use; it does not deploy an OpenClaw container or Compose file.

### Native Gateway Service

`openclaw onboard --install-daemon` installs the Gateway's systemd **user** service. The role prepares the account and user-service environment but does not install or harden that unit.

Do not assume `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, `ProtectHome`, or scoped `ReadWritePaths` are enabled by this installer. Inspect the installed unit as the OpenClaw user:

```bash
systemctl --user show openclaw-gateway.service \
  -p NoNewPrivileges -p PrivateTmp -p ProtectSystem -p ProtectHome -p ReadWritePaths
```

Application authentication, channel allowlists, and rate limits belong to OpenClaw's JSON5 configuration at `~/.openclaw/openclaw.json`, managed through onboarding/configuration. This role does not supply an application security policy. Follow the [upstream security guide](https://docs.openclaw.ai/gateway/security) and run `openclaw security audit` after configuring it.

### Scoped Sudo Access

The openclaw user has limited sudo permissions (not full root):

```bash
# Allowed commands only:
- systemctl start/stop/restart/status openclaw
- systemctl daemon-reload
- tailscale commands
- journalctl for openclaw logs
```

The user is deliberately excluded from the `docker` group. Membership would
grant root-equivalent control through the rootful Docker daemon and bypass the
scoped sudo boundary. Reapplying the playbook also removes this legacy grant
from existing installations without changing other supplementary groups.

### Automatic Security Updates

Unattended-upgrades is configured for automatic security patches:

```bash
# Check status
sudo unattended-upgrade --dry-run

# View logs
sudo cat /var/log/unattended-upgrades/unattended-upgrades.log
```

**Note**: Automatic reboots are disabled. Monitor for pending reboots:
```bash
cat /var/run/reboot-required 2>/dev/null || echo "No reboot required"
```

## Verification

Run these checks after installation and onboarding. Interface names, IP addresses, packet counters, and process IDs vary by host; compare the stated healthy result rather than expecting byte-for-byte output.

### Firewall

```bash
sudo ufw status verbose
```

Expected: `Status: active`, with incoming and routed traffic denied by default. The default rules allow `22/tcp` for SSH and, when Tailscale is enabled, `41641/udp`; IPv6-enabled hosts may show matching `(v6)` entries.

### SSH Protection

```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

Expected: the first command lists `sshd` under `Jail list`; the second reports the jail as active and shows its failure and ban counters. Zero failures or bans is healthy.

### Local Listeners

```bash
sudo ss -tlnp
```

Expected: SSH listens on the configured public address or `0.0.0.0`; OpenClaw and its supporting services listen on `127.0.0.1`. No OpenClaw or Docker service should listen on `0.0.0.0`.

### Docker Isolation

```bash
sudo iptables -L DOCKER-USER -n -v
```

Expected: the chain includes accepts for established traffic and loopback traffic, followed by a drop rule for traffic arriving on the server's default external interface. Packet counters may be zero before traffic reaches the chain.

Verify that the OpenClaw service account cannot access the Docker socket:

```bash
id -nG openclaw
```

Expected: the output does not include `docker`. Operators should use `sudo
docker ...` for explicit container administration.

From another machine, scan the server:

```bash
nmap -p- YOUR_SERVER_IP
```

Expected: only the configured SSH TCP port is open in the default configuration. Tailscale uses UDP port `41641`, so it does not appear in this TCP scan.

Then publish a temporary container port:

```bash
sudo docker run -d -p 80:80 --name test-nginx nginx
curl --connect-timeout 5 http://YOUR_SERVER_IP:80
curl --fail http://localhost:80
sudo docker rm -f test-nginx
```

Expected: the external request fails or times out, while the localhost request returns the nginx welcome page. Remove the test container even if either request produces an unexpected result.

### Tailscale

```bash
sudo tailscale status
```

When Tailscale is enabled, expected: the server has a `100.x.x.x` Tailscale address and appears in the peer table. `Logged out` or `Stopped` means `sudo tailscale up` still needs to be completed. Skip this check when `tailscale_enabled` is false.

### Automatic Security Updates

```bash
sudo systemctl status unattended-upgrades
```

Expected: the unit is loaded and active. Use `sudo unattended-upgrade --dry-run --debug` if the service is inactive or reports errors.

## Tailscale Access

For a default Gateway on loopback port `18789`, use an SSH tunnel:

```bash
ssh -N -L 18789:127.0.0.1:18789 user@server
# Then browse to http://localhost:18789
```

The server address can be its Tailscale address. A loopback listener is not directly reachable at `TAILSCALE_IP:18789`; direct browser access through Tailscale requires separately configured [Tailscale Serve](https://docs.openclaw.ai/gateway/tailscale). Use your configured Gateway port if different.

## Network Flow

```
Internet → UFW (SSH only) → fail2ban → DOCKER-USER Chain → DROP
Container → NAT → Internet (outbound allowed)
```

## Known Limitations

### macOS Support
- macOS firewall configuration is basic (Application Firewall only)
- No fail2ban equivalent on macOS
- Consider using Little Snitch or similar for enhanced macOS security

### IPv6
- Docker IPv6 is disabled by default (`ip6tables: false` in daemon.json)
- If your network uses IPv6, review and test firewall rules accordingly

### Installation Script
- The `curl | bash` installation pattern has inherent risks
- For high-security environments, clone the repository and audit before running
- Consider using `--check` mode first: `ansible-playbook playbook.yml --check`

## Security Checklist

After installation, verify:

- [ ] `sudo ufw status` shows only SSH and Tailscale allowed
- [ ] `sudo fail2ban-client status sshd` shows jail active
- [ ] `sudo iptables -L DOCKER-USER -n` shows DROP rule
- [ ] `id -nG openclaw` does not include the `docker` group
- [ ] `nmap -p- YOUR_IP` from external shows only port 22
- [ ] `docker run -p 80:80 nginx` + `curl YOUR_IP:80` times out
- [ ] Tailscale access works for web UI

## Reporting Security Issues

If you discover a security vulnerability, please report it privately:
- OpenClaw: https://github.com/openclaw/openclaw/security
- This installer: https://github.com/openclaw/openclaw-ansible/security
