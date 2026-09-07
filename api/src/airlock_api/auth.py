"""Role check for the staff (approver) surface.

The client sends its role in the X-Airlock-Role header so the execute path is
gated server-side, not only hidden in the UI. Replace the header with SSO/JWT
and map identities to roles; the enforcement point stays here.
"""
from fastapi import Header, HTTPException


def require_approver(x_airlock_role: str = Header(default="")) -> str:
    if x_airlock_role != "approver":
        raise HTTPException(status_code=403, detail="Approver role required for this action.")
    return x_airlock_role
