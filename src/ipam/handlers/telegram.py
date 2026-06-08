"""
Telegram command handler for VPN onboarding.
Exposes a simple ``/vpn-setup <brownfield_cidr>`` command.
The handler calls ``services.allocator.allocate_for_tenant`` and returns
human‑readable feedback.
"""

import json
import re
from typing import Optional

from ..services.allocator import allocate_for_tenant, AllocationError

# Simple placeholder for sending a message back to Telegram – replace with your
# actual messaging wrapper (e.g. openclaw.sessions_send or a custom bot API).
def send_telegram_message(chat_id: str, text: str):
    # In a real deployment this would be a POST to the Telegram Bot API.
    # For this skeleton we just print – the OpenClaw runtime will capture the
    # stdout and forward it to the chat.
    print(f"[Telegram:{chat_id}] {text}")

COMMAND_REGEX = re.compile(r"^/vpn-setup\s+(?P<cidr>\S+)$")

def handle_message(chat_id: str, message_text: str, sender_name: str):
    """Entry point called by the OpenClaw Telegram integration.

    Args:
        chat_id: Telegram chat identifier (string, as received from inbound meta).
        message_text: Raw text sent by the user.
        sender_name: Human readable name of the sender.
    """
    match = COMMAND_REGEX.match(message_text.strip())
    if not match:
        send_telegram_message(chat_id, "Usage: /vpn-setup <brownfield_cidr> (e.g. /vpn-setup 192.168.50.0/24)")
        return

    cidr = match.group("cidr")
    tenant_name = sender_name  # we tie the tenant to the Telegram user name
    try:
        result = allocate_for_tenant(tenant_name, cidr)
        resp = (
            f"✅ VPN prepared for *{tenant_name}*\n"
            f"*Tunnel IP*: {result['tunnel_ip']} (from 100.64.0.0/10)\n"
        )
        if result.get("routing_cidr"):
            resp += f"*Routing subnet*: {result['routing_cidr']} (will be advertised via NetBird)\n"
        else:
            resp += "*Routing subnet*: none supplied – only tunnel IP allocated.\n"
        send_telegram_message(chat_id, resp)
    except AllocationError as e:
        send_telegram_message(chat_id, f"❌ Allocation error: {e}")
    except Exception as exc:
        # Unexpected error – log and inform the user
        send_telegram_message(chat_id, f"⚠️ Unexpected error: {exc}")
