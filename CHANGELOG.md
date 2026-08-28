# Changelog - Multi-OS Support & Bug Fixes

## Unreleased

- Update the Ansible lint toolchain and GitHub Actions dependencies, with Python 3.14 for CI.
- Exclude checkout metadata and local Ansible caches from Docker test images so the harness also works from Git worktrees.
- Preserve service-user privilege switching in the Docker test harness to avoid recurring pnpm ownership changes.
- Remove the OpenClaw service user from the root-equivalent Docker group, including on existing installations. Thanks @Tonynanra for the report.
- Document expected results for post-install security verification and link the checks from setup documentation. Thanks @justinfiore for the report.

## [2.0.0] - 2025-01-09

### 🎉 Major Changes

#### Multi-OS Support
- **Added macOS support** alongside Debian/Ubuntu
- **Homebrew installation** for both Linux and macOS
- **OS-specific task files** for clean separation
- **Automatic OS detection** with proper fallback

#### Installation Modes
- **Release Mode** (default): Install via `pnpm install -g openclaw@latest`
- **Development Mode**: Clone repo, build from source, symlink binary
- Switch modes with `-e openclaw_install_mode=development`
- Development aliases: `openclaw-rebuild`, `openclaw-dev`, `openclaw-pull`

#### System Improvements
- **apt update & upgrade** runs automatically at start (Debian/Ubuntu)
- **Homebrew integrated** in PATH for all users
- **pnpm package manager** used for OpenClaw installation

### 🐛 Bug Fixes

#### Critical Fixes from User Feedback
1. **DBus Session Bus Issues** ✅
   - Fixed: `loginctl enable-linger` now configured automatically
   - Fixed: `XDG_RUNTIME_DIR` set in .bashrc
   - Fixed: `DBUS_SESSION_BUS_ADDRESS` configured properly
   - **No more manual** `eval $(dbus-launch --sh-syntax)` needed!

2. **User Switching Command** ✅
   - Fixed: Changed from `sudo -i -u openclaw` to `sudo su - openclaw`
   - Ensures proper login shell with .bashrc loading
   - Alternative documented: `sudo -u openclaw -i`

3. **OpenClaw Installation** ✅
   - Changed: `pnpm add -g` → `pnpm install -g openclaw@latest`
   - Added installation verification
   - Added version display

4. **Configuration Management** ✅
   - Removed automatic config.yml creation
   - Removed automatic systemd service installation
   - Let `openclaw onboard --install-daemon` handle setup
   - Only create directory structure

### 📦 New Files Created

#### OS-Specific Task Files
```
roles/openclaw/tasks/
├── system-tools-linux.yml      # apt-based tool installation
├── system-tools-macos.yml      # brew-based tool installation
├── docker-linux.yml            # Docker CE installation
├── docker-macos.yml            # Docker Desktop installation
├── firewall-linux.yml          # UFW configuration
├── firewall-macos.yml          # Application Firewall config
├── openclaw-release.yml        # Release mode installation
└── openclaw-development.yml    # Development mode installation
```

#### Documentation
- `UPGRADE_NOTES.md` - Detailed upgrade information
- `CHANGELOG.md` - This file
- `docs/development-mode.md` - Development mode guide

### 🔧 Modified Files

#### Core Playbook & Scripts
- **playbook.yml**
  - Added OS detection (is_macos, is_debian, is_linux, is_redhat)
  - Added apt update/upgrade at start
  - Added Homebrew installation
  - Enhanced welcome message with `openclaw onboard --install-daemon`
  - Removed automatic config.yml creation
  
- **install.sh**
  - Added macOS detection
  - Removed Debian-only restriction
  - Better error messages for unsupported OS

- **run-playbook.sh**
  - Fixed user switch command documentation
  - Added alternative command options
  - Enhanced post-install instructions

- **README.md**
  - Updated for multi-OS support
  - Added OS-specific requirements
  - Updated quick-start with `openclaw onboard --install-daemon`
  - Added Homebrew to feature list

#### Role Files
- **roles/openclaw/defaults/main.yml**
  - Added OS-specific variables (homebrew_prefix, package_manager)
  
- **roles/openclaw/tasks/main.yml**
  - No changes (orchestrator)

- **roles/openclaw/tasks/system-tools.yml**
  - Refactored to delegate to OS-specific files
  - Added fail-safe for unsupported OS

- **roles/openclaw/tasks/docker.yml**
  - Refactored to delegate to OS-specific files

- **roles/openclaw/tasks/firewall.yml**
  - Refactored to delegate to OS-specific files

- **roles/openclaw/tasks/user.yml**
  - Added loginctl enable-linger
  - Added XDG_RUNTIME_DIR configuration
  - Added DBUS_SESSION_BUS_ADDRESS setup
  - Fixed systemd user service support

- **roles/openclaw/tasks/openclaw.yml**
  - Changed to `pnpm install -g openclaw@latest`
  - Added installation verification
  - Removed config.yml template generation
  - Removed systemd service installation
  - Only creates directory structure

- **roles/openclaw/templates/openclaw-host.service.j2**
  - Added XDG_RUNTIME_DIR environment
  - Added DBUS_SESSION_BUS_ADDRESS
  - Added Homebrew to PATH
  - Enhanced security settings (ProtectSystem, ProtectHome)

### 🚀 Workflow Changes

#### Old Workflow
```bash
# Installation
curl -fsSL https://.../install.sh | bash
sudo -i -u openclaw              # ❌ Wrong command
nano ~/.openclaw/config.yml      # Manual config
openclaw login                   # Manual setup
# Missing DBus setup              # ❌ Errors
```

#### New Workflow - Release Mode (Default)
```bash
# Installation
curl -fsSL https://.../install.sh | bash
sudo su - openclaw               # ✅ Correct command
openclaw onboard --install-daemon # ✅ One command setup!
# DBus auto-configured             # ✅ Works
# Service auto-installed           # ✅ Works
```

#### New Workflow - Development Mode
```bash
# Installation with development mode
git clone https://github.com/openclaw/openclaw-ansible.git
cd openclaw-ansible
./run-playbook.sh -e openclaw_install_mode=development

# Switch to openclaw user
sudo su - openclaw

# Make changes
openclaw-dev              # cd ~/code/openclaw
vim src/some-file.ts      # Edit code
openclaw-rebuild          # pnpm build

# Test immediately
openclaw doctor           # Uses new build
```

### 🎯 User Experience Improvements

#### Welcome Message
- Shows environment status (XDG_RUNTIME_DIR, DBUS, Homebrew, OpenClaw version)
- Recommends `openclaw onboard --install-daemon` as primary command
- Provides manual setup steps as alternative
- Lists useful commands for troubleshooting

#### Environment Configuration
- Homebrew automatically added to PATH
- pnpm global bin directory configured
- DBus session bus properly initialized
- XDG_RUNTIME_DIR set for systemd user services

#### Directory Structure
Ansible creates only structure, no config files:
```
~/.openclaw/
├── sessions/       # Created (empty)
├── credentials/    # Created (secure: 0700)
├── data/          # Created (empty)
└── logs/          # Created (empty)
# openclaw.json    # NOT created - user's openclaw creates it
# config.yml       # NOT created - deprecated
```

### 🔒 Security Enhancements

#### Systemd Service Hardening
- `ProtectSystem=strict` - System directories read-only
- `ProtectHome=read-only` - Limited home access
- `ReadWritePaths=~/.openclaw` - Only config writable
- `NoNewPrivileges=true` - No privilege escalation

#### User Isolation
- Dedicated openclaw system user
- lingering enabled for systemd user services
- Proper DBus session isolation
- XDG_RUNTIME_DIR per-user

### 📊 Platform Support Matrix

| Feature | Debian/Ubuntu | macOS | Status |
|---------|--------------|-------|--------|
| Base Installation | ✅ | ✅ | Tested |
| Homebrew | ✅ | ✅ | Working |
| Docker | Docker CE | Docker Desktop | Working |
| Firewall | UFW | Application FW | Working |
| systemd | ✅ | ❌ | Linux only |
| DBus Setup | ✅ | N/A | Linux only |
| pnpm + OpenClaw | ✅ | ✅ | Working |

### ⚠️ Breaking Changes

1. **User Switch Command Changed**
   - Old: `sudo -i -u openclaw`
   - New: `sudo su - openclaw`
   - Impact: Update documentation, scripts

2. **No Auto-Configuration**
   - Old: config.yml auto-created
   - New: User runs `openclaw onboard`
   - Impact: Users must run onboard command

3. **No Auto-Service Install**
   - Old: systemd service auto-installed
   - New: `openclaw onboard --install-daemon`
   - Impact: Service not running after ansible

### 🔄 Migration Guide

#### For Fresh Installations
Just run the new installer - everything works out of the box!

#### For Existing Installations
```bash
# 1. Add environment variables
echo 'export XDG_RUNTIME_DIR=/run/user/$(id -u)' >> ~/.bashrc

# 2. Enable lingering
sudo loginctl enable-linger openclaw

# 3. Add Homebrew (Linux)
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc

# 4. Reload
source ~/.bashrc

# 5. Reinstall openclaw
pnpm install -g openclaw@latest
```

### 📚 Documentation Updates

- README.md: Multi-OS support documented
- UPGRADE_NOTES.md: Detailed technical changes
- CHANGES.md: User-facing changelog (this file)
- install.sh: Updated help text
- run-playbook.sh: Better instructions

### 🐛 Known Issues

#### macOS Limitations
- systemd not available (Linux feature)
- Some Linux-specific tools not installed
- Firewall configuration limited
- **Recommendation**: Use for development, not production

#### Future Enhancements
- [ ] launchd support for macOS service management
- [ ] Full pf firewall configuration for macOS
- [ ] macOS-specific user management
- [ ] Cross-platform testing suite

### 🙏 Credits

Based on user feedback and real-world usage patterns from the openclaw community.

Special thanks to early testers who identified the DBus and user switching issues!

---

**For detailed technical information**, see `UPGRADE_NOTES.md`

**For installation instructions**, see `README.md`
