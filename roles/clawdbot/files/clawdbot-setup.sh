#!/bin/bash
set -e

# Enable 256 colors
export TERM=xterm-256color
export COLORTERM=truecolor

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Clawdbot ASCII Art Lobster
cat << 'LOBSTER'
[0;36m
   +====================================================+
   |                                                    |
   |         [0;33mWelcome to Clawdbot! [0;31m🦞[0;36m                    |
   |                                                    |
   |[0;31m                   ,.---._                         [0;36m|
   |[0;31m               ,,,,     /       `,                 [0;36m|
   |[0;31m                \\\\\\   /    '\_  ;                [0;36m|
   |[0;31m                 |||| /\/``-.__\;'                 [0;36m|
   |[0;31m                 ::::/\/_                          [0;36m|
   |[0;31m {{`-.__.-'(`(^^(^^^(^ 9 `.========='              [0;36m|
   |[0;31m{{{{{{ { ( ( (  (   (-----:=                      [0;36m|
   |[0;31m {{.-'~~'-.(,(,,(,,,(__6_.'=========.              [0;36m|
   |[0;31m                 ::::\/\                           [0;36m|
   |[0;31m                 |||| \/\  ,-'/,                   [0;36m|
   |[0;31m                ////   \ `` _/ ;                   [0;36m|
   |[0;31m               ''''     \  `  .'                   [0;36m|
   |[0;31m                         `---'                     [0;36m|
   |                                                    |
   |           [0;32m✅  Installation Successful![0;36m             |
   |                                                    |
   +====================================================+[0m
LOBSTER

echo ""
echo -e "${GREEN}🔒 Security Status:${NC}"
echo "  - UFW Firewall: ENABLED"
echo "  - Open Ports: SSH (22) + Tailscale (41641/udp)"
echo "  - Docker isolation: ACTIVE"
echo ""
echo -e "📚 Documentation: ${GREEN}https://docs.clawd.bot${NC}"
echo ""

# Switch to clawdbot user for setup
echo -e "${YELLOW}Switching to clawdbot user for setup...${NC}"
echo ""
echo "DEBUG: About to create init script..."

# Create init script that will be sourced on login
cat > /home/clawdbot/.clawdbot-init << 'INIT_EOF'
# Display welcome message
echo "============================================"
echo "📋 Clawdbot Setup - Next Steps"
echo "============================================"
echo ""
echo "You are now: $(whoami)@$(hostname)"
echo "Home: $HOME"
echo ""
echo "🔧 Setup Commands:"
echo ""
echo "1. Configure Clawdbot:"
echo "   nano ~/.clawdbot/config.yml"
echo ""
echo "2. Login to provider (WhatsApp/Telegram/Signal):"
echo "   clawdbot login"
echo ""
echo "3. Test gateway:"
echo "   clawdbot gateway"
echo ""
echo "4. Exit and manage as service:"
echo "   exit"
echo "   sudo systemctl status clawdbot"
echo "   sudo journalctl -u clawdbot -f"
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
rm -f ~/.clawdbot-init
INIT_EOF

chown clawdbot:clawdbot /home/clawdbot/.clawdbot-init

# Add one-time sourcing to .bashrc if not already there
grep -q '.clawdbot-init' /home/clawdbot/.bashrc 2>/dev/null || {
    echo '' >> /home/clawdbot/.bashrc
    echo '# One-time setup message' >> /home/clawdbot/.bashrc
    echo '[ -f ~/.clawdbot-init ] && source ~/.clawdbot-init' >> /home/clawdbot/.bashrc
}

# Switch to clawdbot user with explicit interactive shell
# Using setsid to create new session + force pseudo-terminal allocation
exec sudo -i -u clawdbot /bin/bash --login
