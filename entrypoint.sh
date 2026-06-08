#!/bin/bash
set -e

# Validate required environment variables
if [ -z "$NETBIRD_API_TOKEN" ]; then
    echo "Error: NETBIRD_API_TOKEN is not set"
    exit 1
fi
if [ -z "$DB_URL" ]; then
    echo "Error: DB_URL is not set"
    exit 1
fi

# Start NetBird daemon
echo "Starting NetBird daemon..."
netbird service install
netbird service start

# Wait briefly for daemon to be ready (simple sleep; could be improved)
sleep 2

# Start the Flask AI Coordinator API
echo "Starting AI Coordinator API..."
python app.py