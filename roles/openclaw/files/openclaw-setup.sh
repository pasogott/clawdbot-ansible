#!/bin/bash

# Accept variables with fallbacks
openclaw_user="${1:-openclaw}"
openclaw_home="${2:-/home/openclaw}"

# Enable 256 colors
export TERM=xterm-256color
export COLORTERM=truecolor

echo ""
echo -e "${GREEN}🔒 Security Status:${NC}"
echo "  - UFW Firewall: ENABLED"
echo "  - Open Ports: SSH (22) + Tailscale (41641/udp)"
echo "  - Docker isolation: ACTIVE"
echo ""
echo -e "📚 Documentation: ${GREEN}https://docs.openclaw.ai${NC}"
echo ""

# Switch to openclaw user for setup
echo -e "${YELLOW}Switching to ${openclaw_user} user for setup...${NC}"
echo ""
echo "DEBUG: About to create init script..."

# Create init script that will be sourced on login
cat > "${openclaw_home}/.openclaw-init" << 'INIT_EOF'
# Display welcome message
echo "============================================"
echo "📋 OpenClaw Setup - Next Steps"
echo "============================================"
echo ""
echo "You are now: $(whoami)@$(hostname)"
echo "Home: $HOME"
echo ""
echo "🔧 Setup Commands:"
echo ""
echo "1. Configure OpenClaw:"
echo "   nano ~/.openclaw/config.yml"
echo ""
echo "2. Login to provider (WhatsApp/Telegram/Signal):"
echo "   openclaw login"
echo ""
echo "3. Test gateway:"
echo "   openclaw gateway"
echo ""
echo "4. Exit and manage as service:"
echo "   exit"
echo "   sudo systemctl status openclaw"
echo "   sudo journalctl -u openclaw -f"
echo ""
echo "5. Connect Tailscale (as root):"
echo "   exit"
echo "   sudo tailscale up"
echo ""
echo "============================================"
echo ""
echo "Type 'exit' to return to previous user"
echo ""

# Remove this init file after first login
rm -f ~/.openclaw-init
INIT_EOF

chown "${openclaw_user}:${openclaw_user}" "${openclaw_home}/.openclaw-init"

# Add one-time sourcing to .bashrc if not already there
grep -q '.openclaw-init' "${openclaw_home}/.bashrc" 2>/dev/null || {
    echo '' >> "${openclaw_home}/.bashrc"
    echo '# One-time setup message' >> "${openclaw_home}/.bashrc"
    echo '[ -f ~/.openclaw-init ] && source ~/.openclaw-init' >> "${openclaw_home}/.bashrc"
}

# Switch to openclaw user with explicit interactive shell
# Using setsid to create new session + force pseudo-terminal allocation
exec sudo -i -u "${openclaw_user}" /bin/bash --login
