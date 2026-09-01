# Docker CI Test Harness

This directory contains a Docker-based CI test harness for the Ansible playbook. It validates convergence, correctness, and idempotency by running the playbook inside an Ubuntu 24.04 container.

The Lint workflow runs this harness in its Installer Integration job on pushes and pull requests, alongside lint, syntax, and Docker-group security checks.

## Quick Start

```bash
# Run all tests
bash tests/run-tests.sh

# Or specify a distro (currently only ubuntu2404 available)
bash tests/run-tests.sh ubuntu2404
```

## Test Structure

The test harness runs three sequential tests:

1. **Convergence**: Runs the playbook with `ci_test=true` to verify it completes without errors
2. **Verification**: Runs `verify.yml` to assert the system is in the expected state
3. **Idempotency**: Runs the playbook a second time and verifies `changed=0`

## Files

- `Dockerfile.ubuntu2404` - Ubuntu 24.04 container with Ansible pre-installed
- `entrypoint.sh` - Test execution script (convergence → verification → idempotency)
- `verify.yml` - Post-convergence assertions (user exists, packages installed, directories created, etc.)
- `run-tests.sh` - Local test runner script

## CI Test Mode

The `ci_test` variable skips tasks that require:
- Docker-in-Docker (Docker CE installation)
- Kernel access (UFW/iptables firewall)
- systemd services (loginctl, daemon installation)

Everything else runs normally: package installation, user creation, Node.js/pnpm setup, OpenClaw installation from npm, directory structure, config file rendering, etc. The harness requires internet access.

## Hosted VPN Tests

The GitHub Actions workflow also runs two destructive integration playbooks on
fresh `ubuntu-24.04` hosted runners. Do not run these on a persistent host:

- `vpn-provider-transition.yml` installs both real VPN clients, exercises both
  provider-switch directions, verifies service and UFW convergence, preserves
  unconfigured existing providers, renders self-hosted manual guidance, rejects
  ready and stopped-client management endpoint drift (including self-hosted to
  Cloud), exercises fresh-install and credential paths in check mode, and
  repeats reconciliation for idempotency.
- `tailscale-operator-boundary.yml` uses a real Tailscale daemon and the
  production sudoers template to prove grant, revocation, preservation of a
  different operator, stopped-daemon reconciliation, explicit migration from
  legacy wildcard sudo access, rejection of a sudo-based authority restore,
  and revocation before a replacement provider fails validation.

Neither test enrolls the runner in a private network or requires credentials.

## What Gets Tested

| Component | Tested? | Notes |
|-----------|---------|-------|
| System packages (35+) | ✅ Yes | Full apt install |
| User creation + config | ✅ Yes | User, .bashrc, sudoers, SSH dir |
| Node.js + pnpm | ✅ Yes | Full install + version check |
| Directory structure | ✅ Yes | All .openclaw/* dirs with perms |
| Git global config | ✅ Yes | Aliases, default branch |
| Vim config | ✅ Yes | Template rendering |
| Docker CE install | ❌ No | Needs Docker-in-Docker |
| UFW / iptables | ⚠️ Partial | Hosted VPN tests verify the Tailscale rule; Docker-chain tests still need kernel access |
| fail2ban / systemd | ❌ No | Needs running systemd |
| Tailscale | ✅ Hosted | Real package, daemon, provider transitions, fresh/auth-key check mode, and operator boundary |
| NetBird | ✅ Hosted | Real package, daemon, provider transitions, check mode, endpoint-drift refusal, keyring repair, and rejection of a valid unapproved signing key |
| OpenClaw app install | ✅ Yes | Latest npm release and version check |
| Idempotency | ✅ Yes | Second run must have 0 changes |

## Exit Codes

- `0` - All tests passed
- `1` - Test failure (convergence failed, verification failed, or idempotency check failed)

## Development

### Lint and Syntax Checks

The pinned lint tools in `requirements-lint.txt` require Python 3.12 or newer; CI uses Python 3.14. These development tools do not change the installer's minimum Ansible version.

```bash
python -m pip install -r requirements-lint.txt
ansible-galaxy collection install -r requirements.yml
yamllint .
ansible-lint playbook.yml tests/*.yml
ansible-playbook playbook.yml --syntax-check
ansible-playbook tests/docker-group-security.yml --syntax-check
ansible-playbook tests/vpn-provider-transition.yml --syntax-check
ansible-playbook tests/tailscale-operator-boundary.yml --syntax-check
```

### Additional Distributions

To add tests for additional distributions:
1. Create `Dockerfile.<distro>` (e.g., `Dockerfile.debian12`)
2. Run: `bash tests/run-tests.sh <distro>`

The test harness automatically builds the image and runs the test suite.
