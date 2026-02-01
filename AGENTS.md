# Agent Guidelines

## Project Overview

Ansible playbook for automated, hardened OpenClaw installation on Debian/Ubuntu systems.

## Key Principles

1. **Security First**: Firewall must be configured before Docker installation
2. **One Command Install**: `curl | bash` should work out of the box
3. **Localhost Only**: All container ports bind to 127.0.0.1
4. **Defense in Depth**: UFW + DOCKER-USER + localhost binding + non-root container

## Critical Components

### Task Order
Docker must be installed **before** firewall configuration.

Task order in `roles/openclaw/tasks/main.yml`:
```yaml
- tailscale.yml  # VPN setup
- user.yml       # Create system user
- docker.yml     # Install Docker (creates /etc/docker)
- firewall.yml   # Configure UFW + daemon.json (needs /etc/docker to exist)
- nodejs.yml     # Node.js + pnpm
- openclaw.yml   # Container setup
```

Reason: `firewall.yml` writes `/etc/docker/daemon.json` and restarts Docker service.

### DOCKER-USER Chain
Located in `/etc/ufw/after.rules`. Uses dynamic interface detection (not hardcoded `eth0`).

**Never** use `iptables: false` in Docker daemon config - this would break container networking.

### Port Binding
Always use `127.0.0.1:HOST_PORT:CONTAINER_PORT` in docker-compose.yml, never `HOST_PORT:CONTAINER_PORT`.

## Code Style

### Ansible
- Use loops instead of repeated tasks
- No `become_user` (playbook already runs as root)
- Use `community.docker.docker_compose_v2` (not deprecated `docker_compose`)
- Always specify collections in `requirements.yml`

### Docker
- Multi-stage builds if needed
- USER directive for non-root
- Proper healthchecks (test the app, not just Node)
- Use `docker compose` (V2) not `docker-compose` (V1)
- No `version:` in compose files

### Templates
- Use variables for all paths/ports
- Add comments explaining security decisions
- Keep jinja2 logic simple

## Testing Checklist

Before committing changes:

```bash
# 1. Syntax check
ansible-playbook playbook.yml --syntax-check

# 2. Dry run
ansible-playbook playbook.yml --check

# 3. Full install (on test VM)
curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash

# 4. Verify security
sudo ufw status verbose
sudo iptables -L DOCKER-USER -n
sudo ss -tlnp  # Only SSH + localhost should listen

# 5. External port scan
nmap -p- TEST_SERVER_IP  # Only port 22 should be open

# 6. Test isolation
sudo docker run -p 80:80 nginx
curl http://TEST_SERVER_IP:80  # Should fail
curl http://localhost:80        # Should work
```

## Common Mistakes to Avoid

1. ❌ Installing Docker before configuring firewall
2. ❌ Using `0.0.0.0` port binding
3. ❌ Hardcoding network interface names (use dynamic detection)
4. ❌ Setting `iptables: false` in Docker daemon
5. ❌ Running container as root
6. ❌ Using deprecated `docker-compose` (V1)
7. ❌ Forgetting to add collections to requirements.yml

## Documentation

### User-Facing
- **README.md**: Installation, quick start, basic management
- **docs/**: Technical details, architecture, troubleshooting

### Developer-Facing
- **AGENTS.md**: This file - guidelines for AI agents/contributors
- Code comments: Explain *why*, not *what*

Keep docs concise. No progress logs, no refactoring summaries.

## File Locations

### Host System
```
/opt/openclaw/              # Installation files
/home/openclaw/.openclaw/   # Config and data
/etc/systemd/system/openclaw.service
/etc/docker/daemon.json
/etc/ufw/after.rules
```

### Repository
```
roles/openclaw/
├── tasks/       # Ansible tasks (order matters!)
├── templates/   # Jinja2 configs
├── defaults/    # Variables
└── handlers/    # Service restart handlers

docs/            # Technical documentation (frontmatter format)
requirements.yml # Ansible Galaxy collections
```

## Security Notes

### Why UFW + DOCKER-USER?
Docker bypasses UFW by default. DOCKER-USER chain is evaluated first, allowing us to block before Docker sees the traffic.

### Why Fail2ban?
SSH is exposed to the internet. Fail2ban automatically bans IPs after 5 failed attempts for 1 hour.

### Why Unattended-Upgrades?
Security patches should be applied promptly. Automatic security-only updates reduce vulnerability windows.

### Why Scoped Sudo?
The openclaw user only needs to manage its own service and Tailscale. Full root access would be dangerous if the app is compromised.

### Why Localhost Binding?
Defense in depth. If DOCKER-USER fails, localhost binding prevents external access.

### Why Non-Root Container?
Least privilege. Limits damage if container is compromised.

### Why Systemd?
Clean lifecycle, auto-start, logging integration.

### Known Limitations
- **macOS**: Incomplete support (no launchd, basic firewall). Test thoroughly.
- **IPv6**: Disabled in Docker. Review if your network uses IPv6.
- **curl | bash**: Inherent risks. For production, clone and audit first.

## Making Changes

### Adding a New Task
1. Add to appropriate file in `roles/openclaw/tasks/`
2. Update main.yml if new task file
3. Test with `--check` first
4. Verify idempotency (can run multiple times safely)

### Changing Firewall Rules
1. Test on disposable VM first
2. Always keep SSH accessible
3. Update `docs/security.md` with changes
4. Verify with external port scan

### Updating Docker Config
1. Changes to `daemon.json.j2` trigger Docker restart (via handler)
2. Test container networking after restart
3. Verify DOCKER-USER chain still works

## Version Management

- Use semantic versioning for releases
- Tag releases in git
- Update CHANGELOG.md with user-facing changes
- No version numbers in code (use git tags)

## Support Channels

- OpenClaw issues: https://github.com/openclaw/openclaw
- This installer: https://github.com/openclaw/openclaw-ansible
