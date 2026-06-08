"""
Central audit helper – thin wrapper around the DB audit_log table.
All modules should import and call ``audit(event, details)``.
"""

from .db.models import audit_log

def audit(event: str, details: dict, actor: str = "ai_coordinator"):
    """Write a structured audit entry.
    
    Args:
        event: Short string describing the action (e.g. ``tunnel_ip_allocated``).
        details: Arbitrary JSON‑serialisable mapping with context.
        actor: Who performed the action – default is the AI coordinator.
    """
    audit_log(actor=actor, action=event, details=details)
