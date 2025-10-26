#!/bin/bash
#
# Setup Script for Sequential Thinking MCP Server
#
# This script helps configure the Sequential Thinking MCP server for Claude Code.
#

set -e

echo "========================================"
echo "Sequential Thinking MCP Server Setup"
echo "========================================"
echo

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect Claude Code settings file location
if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
    SETTINGS_FILE="$HOME/.config/claude-code/settings.json"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    SETTINGS_FILE="$APPDATA/claude-code/settings.json"
else
    echo -e "${RED}❌ Unsupported OS: $OSTYPE${NC}"
    exit 1
fi

echo "Claude Code settings file: $SETTINGS_FILE"
echo

# Check if settings file exists
if [ ! -f "$SETTINGS_FILE" ]; then
    echo -e "${YELLOW}⚠️  Settings file not found. Creating directory...${NC}"
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    echo "{}" > "$SETTINGS_FILE"
    echo -e "${GREEN}✅ Created settings file${NC}"
fi

# Backup settings file
BACKUP_FILE="${SETTINGS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$SETTINGS_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✅ Backed up settings to: $BACKUP_FILE${NC}"
echo

# Check if npx is available
if ! command -v npx &> /dev/null; then
    echo -e "${RED}❌ npx not found. Please install Node.js first.${NC}"
    echo "   Download from: https://nodejs.org/"
    exit 1
fi

echo -e "${GREEN}✅ npx found: $(which npx)${NC}"
echo

# Create MCP server configuration
MCP_CONFIG='{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking"
      ]
    }
  }
}'

# Check if file already has mcpServers
if grep -q "mcpServers" "$SETTINGS_FILE"; then
    echo -e "${YELLOW}⚠️  mcpServers already exists in settings.json${NC}"
    echo "Please manually add the following to your mcpServers section:"
    echo
    echo '    "sequential-thinking": {'
    echo '      "command": "npx",'
    echo '      "args": ['
    echo '        "-y",'
    echo '        "@modelcontextprotocol/server-sequential-thinking"'
    echo '      ]'
    echo '    }'
    echo
else
    # Add mcpServers configuration
    python3 -c "
import json
import sys

try:
    with open('$SETTINGS_FILE', 'r') as f:
        settings = json.load(f)
except:
    settings = {}

if 'mcpServers' not in settings:
    settings['mcpServers'] = {}

settings['mcpServers']['sequential-thinking'] = {
    'command': 'npx',
    'args': ['-y', '@modelcontextprotocol/server-sequential-thinking']
}

with open('$SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)

print('✅ Added Sequential Thinking MCP server to settings.json')
" 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Successfully configured Sequential Thinking MCP server${NC}"
    else
        echo -e "${RED}❌ Failed to update settings.json${NC}"
        exit 1
    fi
fi

echo
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo
echo "1. Restart Claude Code to load the MCP server"
echo "2. The Sequential Thinking server will be available as 'mcp__sequential-thinking__*' tools"
echo "3. You can test it by asking Claude Code to use sequential thinking"
echo
echo -e "${GREEN}✅ Setup complete!${NC}"
echo
echo "Backup saved at: $BACKUP_FILE"
