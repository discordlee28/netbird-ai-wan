#!/bin/bash
set -e

# Check if a setup key was provided via environment variable
if [ -z "$NETBIRD_SETUP_KEY" ]; then
    echo "Error: NETBIRD_SETUP_KEY environment variable is not set."
    exit 1
fi

# Start NetBird daemon
netbird service install
netbird service start

# Join the network using the key provided by the AI Coordinator
echo "Joining NetBird network..."
netbird up --setup-key "$NETBIRD_SETUP_KEY"

# Keep the container alive to maintain the VPN tunnel
tail -f /dev/null
