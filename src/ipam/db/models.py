"""
Simple DB abstraction layer for the IPAM + NetBird VPN service.
Uses psycopg (or asyncpg) in production; swap for your favourite driver.
"""

import psycopg2
from typing import List, Tuple, Optional
from dataclasses import dataclass

# --- Enums ---
class PoolPurpose(str):
    NETBIRD_P2P = "netbird_p2p"
    USER_ROUTING = "user_routing"

class SubnetPurpose(str):
    CORPORATE = "corporate"
    BROWNFIELD = "brownfield"
    ROUTING = "routing"

class SubnetSource(str):
    CORPORATE = "corporate"
    BROWNFIELD = "brownfield"
    ALLOCATED = "allocated"

class SubnetStatus(str):
    ACTIVE = "active"
    RELEASED = "released"

# --- Data classes ---
@dataclass
class CidrPool:
    id: str
    cidr: str
    type: str
    pool_purpose: str

@dataclass
class Subnet:
    id: str
    tenant_id: Optional[str]
    cidr: str
    source: str
    purpose: str
    status: str

@dataclass
class Allocation:
    id: str
    tenant_id: str
    parent_pool_id: str
    cidr: str
    expires_at: Optional[str]
    created_by: str

# --- Thin DB wrapper (replace DSN with your own) ---
DSN = "host=localhost dbname=ipam user=postgres password=secret"

def _conn():
    return psycopg2.connect(DSN)

# --- Core queries ----------------------------------------------------------

def get_pool_by_purpose(purpose: str) -> CidrPool:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, cidr, type, pool_purpose FROM cidr_pool WHERE pool_purpose = %s",
            (purpose,)
        )
        row = cur.fetchone()
        return CidrPool(*row) if row else None

def create_tenant(name: str) -> str:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tenant (name) VALUES (%s) RETURNING id",
            (name,)
        )
        return cur.fetchone()[0]

def add_subnet(tenant_id: str, cidr: str, source: str, purpose: str, status: str = "active") -> str:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO subnet (tenant_id, cidr, source, purpose, status)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (tenant_id, cidr, source, purpose, status)
        )
        return cur.fetchone()[0]

def list_subnets_by_purpose(purpose: str) -> List[Subnet]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, tenant_id, cidr, source, purpose, status FROM subnet WHERE purpose = %s AND status = 'active'",
            (purpose,)
        )
        return [Subnet(*row) for row in cur.fetchall()]

def allocate_from_pool(tenant_id: str, pool_id: str, cidr: str, creator: str = "ai_coordinator") -> str:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO allocation (tenant_id, parent_pool_id, cidr, created_by)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (tenant_id, pool_id, cidr, creator)
        )
        return cur.fetchone()[0]

def is_cidr_allocated(cidr: str, pool_id: str) -> bool:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM allocation WHERE cidr = %s AND parent_pool_id = %s",
            (cidr, pool_id)
        )
        return cur.fetchone() is not None

def audit_log(actor: str, action: str, details: dict):
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO audit_log (actor, action, details) VALUES (%s, %s, %s)",
            (actor, action, details)
        )