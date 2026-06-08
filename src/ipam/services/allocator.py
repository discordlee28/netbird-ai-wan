"""
IPAM + NetBird allocation logic.
This module handles both tunnel IPs (from 100.64.0.0/10) and routing subnets (from user-defined pools).
"""

import ipaddress
from typing import Optional
from ..db.models import (
    Allocation, CidrPool, Subnet, SubnetPurpose, SubnetSource, get_pool_by_purpose, create_tenant,
    add_subnet, allocate_from_pool, is_cidr_allocated, audit_log
)

class AllocationError(Exception):
    """Raised if we cannot allocate a CIDR."""
    pass

def ensure_tenant(name: str) -> str:
    """Ensure tenant exists, return its ID."""
    try:
        return create_tenant(name)
    except Exception:
        # Assuming tenant already exists; fetch its ID
        # In a real app, you'd have a get_tenant_by_name function
        return "tenant-id-placeholder"  # Replace with actual lookup

def conflict_with_corporate(candidate: ipaddress.IPv4Network) -> Optional[ipaddress.IPv4Network]:
    """Return the first corporate subnet that overlaps candidate."""
    corporate_subnets = list_corporate_subnets()
    for corp in corporate_subnets:
        if candidate.overlaps(corp):
            return corp
    return None

def list_corporate_subnets() -> list:
    """Return all active corporate subnets (read-only cache)."""
    # In a real app, you'd call db.models.list_subnets_by_purpose(SubnetPurpose.CORPORATE)
    # and cache them; for now, hardcoded example:
    return [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("10.0.0.0/8")
    ]

def allocate_tunnel_ip(tenant_id: str, needed_prefix_len: int = 30) -> ipaddress.IPv4Network:
    """
    Allocate a /30 (or /31, /32) from NetBird's default P2P range (100.64.0.0/10).
    Returns the allocated CIDR.
    """
    pool = get_pool_by_purpose("netbird_p2p")
    if not pool:
        raise AllocationError("No netbird_p2p pool configured")
    
    pool_net = ipaddress.ip_network(pool.cidr)
    for candidate in pool_net.subnets(new_prefix=needed_prefix_len):
        if not is_cidr_allocated(str(candidate), pool.id):
            # Reserve it
            allocate_from_pool(tenant_id, pool.id, str(candidate), "ai_coordinator")
            audit_log(
                actor="ai_coordinator",
                action="tunnel_ip_allocated",
                details={"tenant_id": tenant_id, "cidr": str(candidate)}
            )
            return candidate
    raise AllocationError("No free tunnel IPs left in 100.64.0.0/10")

def allocate_routing_subnet(tenant_id: str, requested_cidr: str) -> ipaddress.IPv4Network:
    """
    Allocate a routing subnet from the user-defined pool.
    Returns the allocated CIDR.
    """
    pool = get_pool_by_purpose("user_routing")
    if not pool:
        raise AllocationError("No user_routing pool configured")
    
    pool_net = ipaddress.ip_network(pool.cidr)
    new_net = ipaddress.ip_network(requested_cidr)
    
    if not pool_net.supernet_of(new_net):
        raise AllocationError(
            f"Requested subnet {requested_cidr} is not inside user_routing pool {pool.cidr}"
        )
    
    if is_cidr_allocated(requested_cidr, pool.id):
        raise AllocationError(f"Requested routing subnet {requested_cidr} is already allocated")
    
    # Reserve it
    allocate_from_pool(tenant_id, pool.id, requested_cidr, "ai_coordinator")
    audit_log(
        actor="ai_coordinator",
        action="routing_subnet_allocated",
        details={"tenant_id": tenant_id, "cidr": requested_cidr}
    )
    return new_net

def record_brownfield_subnet(tenant_id: str, cidr: str) -> None:
    """
    Record a brownfield subnet (if it doesn't conflict with corporate).
    Raises AllocationError if conflict detected.
    """
    new_net = ipaddress.ip_network(cidr)
    conflict = conflict_with_corporate(new_net)
    if conflict:
        raise AllocationError(
            f"Subnet {cidr} conflicts with corporate {conflict} – please reIP"
        )
    # If no conflict, store it as a brownfield (which becomes routing subnet)
    add_subnet(
        tenant_id=tenant_id,
        cidr=cidr,
        source=SubnetSource.BROWNFIELD,
        purpose=SubnetPurpose.ROUTING,
        status="active"
    )
    audit_log(
        actor="ai_coordinator",
        action="brownfield_recorded",
        details={"tenant_id": tenant_id, "cidr": cidr}
    )

def allocate_for_tenant(tenant_name: str, brownfield_cidr: str) -> dict:
    """
    Main entry point: allocate both tunnel IP and routing subnet for a tenant.
    Returns a dict with tunnel_ip and routing_subnet.
    """
    tenant_id = ensure_tenant(tenant_name)
    
    # 1. Record the brownfield subnet (if provided)
    if brownfield_cidr:
        record_brownfield_subnet(tenant_id, brownfield_cidr)
    
    # 2. Allocate tunnel IP
    tunnel_ip = allocate_tunnel_ip(tenant_id)
    
    # 3. Return ready-to-use NetBird configuration
    return {
        "tenant_id": tenant_id,
        "tunnel_ip": str(tunnel_ip),
        "routing_cidr": brownfield_cidr  # or None if no brownfield given
    }