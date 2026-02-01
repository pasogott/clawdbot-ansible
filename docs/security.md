---
title: Security Architecture
description: Firewall configuration, Docker isolation, and security hardening details
---

# Security Architecture

## Overview

This playbook implements a multi-layer defense strategy to secure Clawdbot installations.

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

Container processes run as unprivileged `clawdbot` user.

### Layer 6: Systemd Hardening

The clawdbot service runs with security restrictions:

- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=read-only` - Limited home directory access
- `ReadWritePaths` - Only ~/.clawdbot is writable

### Layer 7: Scoped Sudo Access

The clawdbot user has limited sudo permissions (not full root):

```bash
# Allowed commands only:
- systemctl start/stop/restart/status clawdbot
- systemctl daemon-reload
- tailscale commands
- journalctl for clawdbot logs
```

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

```bash
# Check firewall
sudo ufw status verbose

# Check fail2ban
sudo fail2ban-client status

# Check Tailscale status
sudo tailscale status

# Check Docker isolation
sudo iptables -L DOCKER-USER -n -v

# Port scan from external machine (only SSH + Tailscale should be open)
nmap -p- YOUR_SERVER_IP

# Test container isolation
sudo docker run -d -p 80:80 --name test-nginx nginx
curl http://YOUR_SERVER_IP:80  # Should fail/timeout
curl http://localhost:80        # Should work
sudo docker rm -f test-nginx

# Check unattended-upgrades
sudo systemctl status unattended-upgrades
```

## Tailscale Access

Clawdbot's web interface (port 3000) is bound to localhost. Access it via:

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
- [ ] `nmap -p- YOUR_IP` from external shows only port 22
- [ ] `docker run -p 80:80 nginx` + `curl YOUR_IP:80` times out
- [ ] Tailscale access works for web UI

## Reporting Security Issues

If you discover a security vulnerability, please report it privately:
- Clawdbot: https://github.com/clawdbot/clawdbot/security
- This installer: https://github.com/openclaw/clawdbot-ansible/security
