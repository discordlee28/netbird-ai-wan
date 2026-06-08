# IPAM + NetBird VPN Allocation Project

A complete reference implementation for allocating NetBird VPN tunnel IPs and managing customer routing subnets.

## Project Structure
```
/ipam_netbird_vpn
├── db/
│   ├── models.py      # Database abstraction layer
│   └── ipam_schema.sql # Schema definition & initial data
│
├── services/
│   └── allocator.py   # Core allocation logic
│
├── handlers/
│   └── telegram.py    # Telegram command handler
│
├── audit.py           # Centralized audit logging
└── README.md          # This file
```

## Dependencies
- Python 3.8+
- psycopg2-binary (PostgreSQL driver)
- ipaddress (standard library)
- Optional: OpenClaw integration (for automation)

## Deployment Steps
1. **Database Setup**:
   - Run `psql -f ipam_schema.sql` to create tables
   - Initialize pools with:
     ```sql
     -- NetBird default P2P pool
     INSERT INTO cidr_pool (cidr, type, pool_purpose)
     VALUES ('100.64.0.0/10', 'provider', 'netbird_p2p');
     -- User-defined routing pool (optional)
     INSERT INTO cidr_pool (cidr, type, pool_purpose)
     VALUES ('10.0.0.0/16', 'provider', 'user_routing');
     ```

2. **Start Services**:
   - Run allocator.py and Telegram handler as needed
   - Requires PostgreSQL service running

3. **Telegram Integration**:
   - Replace `send_telegram_message` with your bot API handler
   - Set up `/vpn-setup` command via OpenClaw Telegram module

## Usage
```bash
# Allocate for a tenant with brownfield subnet
python -m services.allocator.allocate_for_tenant "Acme-Branch" "192.168.50.0/24"
```

## Testing
1. Trigger `/vpn-setup 192.168.50.0/24` in Telegram
2. Verify allocation in audit_log:
   ```sql
   SELECT * FROM audit_log ORDER BY ts DESC LIMIT 5;
   ```
3. Check NetBird via API:
   ```bash
   curl -X GET https://netbird.example.com/api/v1/peers/<tenant_id>/routing
   ```

## Audit Logging
All actions are recorded in audit_log. Example review:
```python
# From python
from .audit import audit

# In allocator.py
audit("tunnel_ip_allocated", {"tenant_id": "..."}, "ai_coordinator")
```