# Release v2.0.0 - Multi-OS Support & Critical Fixes

## 🎉 Major Release

This release adds **multi-OS support** (macOS + Linux), **development mode**, and fixes **all critical issues** reported by users.

### ✨ New Features

#### Multi-OS Support
- ✅ **macOS support** alongside Debian/Ubuntu
- ✅ **Homebrew** automatically installed on both platforms
- ✅ OS-specific tasks for clean separation
- ✅ Automatic OS detection with proper fallback

#### Installation Modes
- ✅ **Release Mode** (default): `pnpm install -g openclaw@latest`
- ✅ **Development Mode**: Clone repo, build from source, symlink binary
- ✅ Switch with `-e openclaw_install_mode=development`
- ✅ Development aliases: `openclaw-rebuild`, `openclaw-dev`, `openclaw-pull`

### 🐛 Critical Bug Fixes

All issues from user feedback resolved:

1. ✅ **DBus Session Bus Errors**
   - Auto-configured `loginctl enable-linger`
   - Dynamic `XDG_RUNTIME_DIR=/run/user/$(id -u)`
   - Proper `DBUS_SESSION_BUS_ADDRESS` setup
   - No more manual `eval $(dbus-launch --sh-syntax)` needed!

2. ✅ **User Switch Command**
   - Fixed from `sudo -i -u openclaw` to `sudo su - openclaw`
   - Ensures proper login shell with environment

3. ✅ **Homebrew Integration**
   - Installed for both Linux and macOS
   - Added to PATH in both `.bashrc` and `.zshrc`
   - `brew shellenv` properly configured

4. ✅ **PNPM Configuration**
   - `PNPM_HOME` properly set in shell configs
   - PATH includes pnpm directories
   - Correct permissions on `~/.local/share/pnpm`

5. ✅ **User-ID Dynamic**
   - No longer hardcoded to 1000
   - Dynamically determined with `id -u`

### 🔧 Improvements

- ✅ **Better onboarding**: Recommends `openclaw onboard --install-daemon`
- ✅ **No auto-config**: Config files created by openclaw itself
- ✅ **Enhanced security**: systemd service hardening
- ✅ **Linting**: yamllint & ansible-lint production profile passed

### 📦 Installation

#### Quick Start (Release Mode)
```bash
curl -fsSL https://raw.githubusercontent.com/openclaw/openclaw-ansible/main/install.sh | bash
```

#### Development Mode
```bash
git clone https://github.com/openclaw/openclaw-ansible.git
cd openclaw-ansible
./run-playbook.sh -e openclaw_install_mode=development
```

### 📚 Documentation

- [README.md](README.md) - Getting started
- [CHANGELOG.md](CHANGELOG.md) - Full changelog
- [UPGRADE_NOTES.md](UPGRADE_NOTES.md) - Technical details
- [docs/development-mode.md](docs/development-mode.md) - Development guide

### ⚠️ Breaking Changes

1. **User switch command changed**: Use `sudo su - openclaw` instead of `sudo -i -u openclaw`
2. **No auto-configuration**: Config files no longer auto-generated, use `openclaw onboard`
3. **No auto-service**: systemd service not auto-installed, use `--install-daemon` flag

### 🔄 Migration

For existing installations:
```bash
# Add environment variables
echo 'export XDG_RUNTIME_DIR=/run/user/$(id -u)' >> ~/.bashrc
echo 'export PNPM_HOME="$HOME/.local/share/pnpm"' >> ~/.bashrc

# Enable lingering
sudo loginctl enable-linger openclaw

# Add Homebrew (Linux)
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc

# Reload
source ~/.bashrc

# Reinstall openclaw
pnpm install -g openclaw@latest
```

### 📊 Testing

- ✅ yamllint: **PASSED**
- ✅ ansible-lint: **PASSED** (production profile)
- ✅ Tested on Debian 11/12
- ✅ Tested on Ubuntu 20.04/22.04
- ⚠️  macOS framework ready (needs real hardware testing)

### 🙏 Thanks

Special thanks to early adopters who provided feedback on the DBus and user switching issues!

---

**Full Changelog**: https://github.com/openclaw/openclaw-ansible/blob/main/CHANGELOG.md
