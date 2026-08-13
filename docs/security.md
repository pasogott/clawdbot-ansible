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

### Layer 4: Localhost-Only Binding

All container ports bind to 127.0.0.1:

```yaml
ports:
  - "127.0.0.1:3000:3000"
```

### Layer 5: Non-Root Container

Container processes run as unprivileged `openclaw` user.

### Layer 6: Systemd Hardening

The openclaw service runs with security restrictions:

- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=read-only` - Limited home directory access
- `ReadWritePaths` - Only ~/.openclaw is writable

### Layer 7: Scoped Sudo Access

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

### Layer 8: Automatic Security Updates

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

OpenClaw's web interface (port 3000) is bound to localhost. Access it via:

1. **SSH tunnel**:
   ```bash
   ssh -L 3000:localhost:3000 user@server
   # Then browse to http://localhost:3000
   ```

2. **Tailscale** (recommended):
   ```bash
   # On server: already done by playbook
   sudo tailscale up
   
   # From your machine:
   # Browse to http://TAILSCALE_IP:3000
   ```

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
