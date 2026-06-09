# NetBird AI-WAN

An intelligent IP Address Management (IPAM) and automated onboarding system for NetBird VPN networks. This project provides an AI Coordinator service that manages subnet allocations and generates NetBird setup keys for spoke devices, enabling zero-touch VPN provisioning.

## Overview

The system consists of two main components:

1. **AI Coordinator** - Central service that:
   - Manages IP address pools and subnet allocations
   - Integrates with NetBird API to generate setup keys
   - Provides REST API for tenant/site onboarding
   - Tracks allocations in a PostgreSQL database

2. **Spoke Equipment** - Lightweight container that runs on remote devices:
   - Joins the NetBird mesh using a setup key from the Coordinator
   - Maintains persistent VPN tunnel
   - Requires minimal configuration

## Architecture

```
[Remote Sites] <--(NetBird Tunnel)--> [NetBird Mesh] <--(API)--> [AI Coordinator]
      ^                                     ^
      |                                     |
  Setup Key                           Database & IPAM Logic
```

## Directory Structure

```
Netbird_AI-WAN/
├─ Dockerfile.coordinator        # AI Coordinator service image
├─ Dockerfile.spoke             # Spoke equipment image
├─ requirements.txt             # Python dependencies
├─ entrypoint.sh                # Coordinator startup script
├─ spoke-entrypoint.sh          # Spoke startup script
├─ deployment/
│   └─ docker-compose.yml       # Local testing compose file
└─ src/
    └─ ipam/                    # IPAM and coordination logic
        ├─ README.md
        ├─ audit.py
        ├─ ipam_schema.sql
        ├─ db/
        │   └─ models.py
        ├─ handlers/
        │   └─ telegram.py
        └─ services/
            └─ allocator.py
```

## Prerequisites

- Docker Engine
- NetBird account (for API token)
- PostgreSQL database (for Coordinator)

## Local Development & Testing

The provided `docker-compose.yml` in the `deployment/` directory allows you to test the full stack locally:

```bash
# Build and start services
docker compose -f deployment/docker-compose.yml up -d

# Check logs
docker compose -f deployment/docker-compose.yml logs -f

# Stop and clean up
docker compose -f deployment/docker-compose.yml down
```

Note: This brings up both Coordinator and Spoke on the same host for testing. In production, these run on separate nodes.

## Production Deployment

### AI Coordinator (Hub Server)

```bash
docker run -d \
  --name netbird-coordinator \
  --restart unless-stopped \
  -p 5000:5000 \
  -e NETBIRD_API_TOKEN=your_netbird_api_token \
  -e DB_URL=postgresql://user:password@host:5432/netbird_ipam \
  --cap-add=NET_ADMIN \
  --device /dev/net/tun \
  your-registry/ai-coordinator:latest
```

### Spoke Equipment (Remote Devices)

```bash
docker run -d \
  --name netbird-spoke \
  --restart unless-stopped \
  -e NETBIRD_SETUP_KEY=generated_by_coordinator \
  --cap-add=NET_ADMIN \
  --device /dev/net/tun \
  your-registry/netbird-spoke:latest
```

## API Endpoints (Coordinator)

The Coordinator exposes a Flask API on port 5000:

- `POST /allocate` - Request a new subnet allocation and setup key
- `GET /health` - Health check endpoint
- `GET /allocations` - List all current allocations

## NetBird API Route Management

### Create a Route

To add a network route via the NetBird API (e.g., for site LAN access), use:

```bash
# Create route with specific peer and distribution group
curl -X POST https://api.netbird.io/api/routes \
  -H "Authorization: Bearer <NETBIRD_API_TOKEN>" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Hub LAN 1",
    "network_id": "Hub_LAN1",
    "network": "10.0.1.0/24",
    "peer": "d8jo71rl0ubs738a9u30",
    "groups": ["d8jdjtjl0ubs738sp4i0"],
    "enabled": true,
    "metric": 1
  }'
```

### Update a Route

```bash
curl -X PUT https://api.netbird.io/api/routes/<ROUTE_ID> \
  -H "Authorization: Bearer <NETBIRD_API_TOKEN>" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "network_id": "Updated_Network",
    "network": "10.0.1.0/24",
    "peer": "<PEER_ID>",
    "groups": ["<GROUP_ID>"],
    "enabled": true,
    "metric": 1
  }'
```

### List Routes

```bash
curl -sS https://api.netbird.io/api/routes \
  -H "Authorization: Bearer <NETBIRD_API_TOKEN>" \
  -H "Accept: application/json"
```

### Get Route by ID

```bash
curl -sS https://api.netbird.io/api/routes/<ROUTE_ID> \
  -H "Authorization: Bearer <NETBIRD_API_TOKEN>" \
  -H "Accept: application/json"
```

### Route Parameter Reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Friendly name for the route |
| `network_id` | string | Yes | Unique identifier for the route |
| `network` | string | Yes | CIDR notation of the network (e.g., `10.0.1.0/24`) |
| `peer` | string | Yes (if no peer_groups) | Peer ID that announces this route |
| `peer_groups` | array | Yes (if no peer) | List of peer group IDs for route announcement |
| `groups` | array | Yes | Distribution group IDs (who can access this route) |
| `enabled` | boolean | Yes | Whether the route is active |
| `metric` | integer | Yes | Route priority metric (1-9999, lower = higher priority) |
| `masquerade` | boolean | No | Enable NAT masquerading (default: false) |

### Get Peer/Group IDs

```bash
# List all peers with their IDs
curl -sS https://api.netbird.io/api/peers \
  -H "Authorization: Bearer <NETBIRD_API_TOKEN>" \
  -H "Accept: application/json"

# List all groups with their IDs
curl -sS https://api.netbird.io/api/groups \
  -H "Authorization: Bearer <NETBIRD_API_TOKEN>" \
  -H "Accept: application/json"
```

### Example: Route Announcement for Site LAN

To announce a site's LAN (`10.0.1.0/24`) via the hub-node Docker container:

```bash
curl -X POST https://api.netbird.io/api/routes \
  -H "Authorization: Bearer <NETBIRD_API_TOKEN>" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Site LAN 10.0.1.0/24",
    "network_id": "site-lan-1",
    "network": "10.0.1.0/24",
    "peer": "<HUB_NODE_PEER_ID>",
    "groups": ["<ALL_GROUP_ID>"],
    "enabled": true,
    "metric": 1
  }'
```

Replace `<NETBIRD_API_TOKEN>`, `<HUB_NODE_PEER_ID>`, and `<ALL_GROUP_ID>` with actual values.

## Environment Variables

### Coordinator
- `NETBIRD_API_TOKEN` - Token for NetBird API authentication
- `DB_URL` - PostgreSQL connection string

### Spoke
- `NETBIRD_SETUP_KEY` - Key generated by Coordinator for this device

## Security Notes

For production use, consider:
- Using non-root users in Docker images
- Adding health checks
- Using Docker secrets for sensitive values
- Implementing proper TLS for API endpoints
- Using read-only filesystems where possible

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

*Built with ❤️ for automated, secure VPN provisioning*