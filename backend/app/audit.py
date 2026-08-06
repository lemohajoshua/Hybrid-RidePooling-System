# app/audit.py
"""
Lightweight audit logging (security requirement 3.6.3.v: "System activities
are logged to enable monitoring and forensic analysis. Logs include
timestamps, user identification, and actions performed.").

Deliberately fire-and-forget: a logging failure should never break the
actual action it's recording, so every call is wrapped in a try/except.
"""

from .database import supabase


def log_action(user_id: str, user_role: str, action: str, details: dict = None):
    try:
        supabase.table('audit_log').insert({
            'user_id': user_id,
            'user_role': user_role,
            'action': action,
            'details': details or {}
        }).execute()
    except Exception as e:
        print(f"Audit log failed (non-fatal): {e}")
