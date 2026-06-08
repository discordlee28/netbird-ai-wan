-- IPAM schema for NetBird VPN coordination
-- Run once to create tables and seed initial data

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE tenant (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cidr_pool (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cidr CIDR NOT NULL,
    type TEXT CHECK (type IN ('provider','corporate','reserved')) NOT NULL,
    pool_purpose TEXT CHECK (pool_purpose IN ('netbird_p2p','user_routing')) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE subnet (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenant(id),
    cidr      CIDR NOT NULL,
    source    TEXT CHECK (source IN ('corporate','brownfield','allocated')) NOT NULL,
    purpose   TEXT CHECK (purpose IN ('corporate','brownfield','routing')) NOT NULL,
    status    TEXT CHECK (status IN ('active','released')) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE allocation (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID REFERENCES tenant(id),
    parent_pool_id UUID REFERENCES cidr_pool(id),
    cidr          CIDR NOT NULL,
    expires_at    TIMESTAMPTZ,
    created_by    TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit_log (
    ts      TIMESTAMPTZ DEFAULT now(),
    actor   TEXT,
    action  TEXT,
    details JSONB
);

-- Indexes for performance
CREATE INDEX ix_subnet_tenant ON subnet(tenant_id);
CREATE INDEX ix_subnet_cidr ON subnet(cidr);
CREATE INDEX ix_allocation_parent ON allocation(parent_pool_id);
CREATE INDEX ix_audit_ts ON audit_log(ts);

-- Seed initial pools
-- NetBird built-in P2P range
INSERT INTO cidr_pool (cidr, type, pool_purpose)
VALUES ('100.64.0.0/10', 'provider', 'netbird_p2p')
ON CONFLICT DO NOTHING;

-- Example corporate pool (adjust as needed)
INSERT INTO cidr_pool (cidr, type, pool_purpose)
VALUES ('192.168.0.0/16', 'corporate', 'user_routing')
ON CONFLICT DO NOTHING;

-- Example provider allocation pool for user-defined routing subnets
-- (if you have a separate pool for customer‑defined subnets)
INSERT INTO cidr_pool (cidr, type, pool_purpose)
VALUES ('10.0.0.0/16', 'provider', 'user_routing')
ON CONFLICT DO NOTHING;

-- Seed a corporate subnet (example hub)
INSERT INTO subnet (tenant_id, cidr, source, purpose, status)
SELECT id, '192.168.1.0/24', 'corporate', 'corporate', 'active'
FROM tenant WHERE name = 'Corporate Hub'
ON CONFLICT DO NOTHING;