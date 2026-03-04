from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from typing import Dict, Optional, Any
from collections.abc import Mapping

import streamlit as st


@dataclass(frozen=True)
class AuthConfig:
    # username -> plain password
    users: Dict[str, str]


def _to_str_dict(x: Any) -> Dict[str, str]:
    """Convert any Mapping into {str: str}. Otherwise return {}."""
    if x is None or not isinstance(x, Mapping):
        return {}
    out: Dict[str, str] = {}
    for k, v in x.items():
        if k is None or v is None:
            continue
        kk = str(k).strip()
        vv = str(v).strip()
        if not kk or not vv:
            continue
        out[kk] = vv
    return out


def _load_users_from_secrets() -> Dict[str, str]:
    """
    Supported secrets formats:

    A) Inline table:
       [auth]
       users = { Carlos="admin123", Doc="doc123" }

    B) Nested table:
       [auth.users]
       Carlos = "admin123"
       Doc = "doc123"

    C) Single JSON secret (recommended):
       AUTH_USERS_JSON = {"Carlos":"admin123","Doc":"doc123"}
    """

    # C) JSON secret (single key) – easiest to manage later
    raw_json = st.secrets.get("AUTH_USERS_JSON")
    if isinstance(raw_json, str) and raw_json.strip():
        try:
            parsed = json.loads(raw_json)
            users = _to_str_dict(parsed)
            if users:
                return users
        except Exception:
            pass

    # auth can be Mapping-like in Streamlit
    auth_cfg = st.secrets.get("auth", {})
    if not isinstance(auth_cfg, Mapping):
        auth_cfg = {}

    # A) users inline table or B) nested table materializes as auth_cfg["users"]
    users = _to_str_dict(auth_cfg.get("users"))
    if users:
        return users

    # Extra fallback: sometimes a different nesting can happen; try st.secrets.get("auth.users")
    # (Streamlit typically doesn't do dot-keys, but this costs nothing)
    maybe = st.secrets.get("auth.users")
    users2 = _to_str_dict(maybe)
    if users2:
        return users2

    return {}


def _verify_password(entered: str, stored: str) -> bool:
    """Plain password constant-time compare."""
    try:
        return hmac.compare_digest(entered, stored)
    except Exception:
        return False


def _get_auth_config() -> AuthConfig:
    return AuthConfig(users=_load_users_from_secrets())


def require_login() -> str:
    """Returns username if authenticated; otherwise renders login UI and stops."""
    st.session_state.setdefault("auth_user", None)

    if st.session_state.get("auth_user"):
        return str(st.session_state["auth_user"])

    cfg = _get_auth_config()

    st.title("Underwriting (SAT + Buró)")
    st.caption("Acceso restringido")

    # Safe debug: shows only usernames detected (no passwords)
    if st.secrets.get("DEBUG_AUTH", False):
        st.info(
            f"DEBUG_AUTH: found_users={bool(cfg.users)}; "
            f"usernames={sorted(list(cfg.users.keys()))}"
        )

    if not cfg.users:
        # Show deterministic debug info about what secrets contain (no sensitive values)
        auth_cfg = st.secrets.get("auth", {})
        auth_keys = list(auth_cfg.keys()) if isinstance(auth_cfg, Mapping) else []
        users_obj = auth_cfg.get("users") if isinstance(auth_cfg, Mapping) else None
        st.error(
            "No hay usuarios configurados en secrets.\n\n"
            "Configura usuarios en Secrets (Streamlit Cloud).\n\n"
            f"DEBUG: auth_keys={auth_keys}, users_type={type(users_obj).__name__}, "
            f"has_AUTH_USERS_JSON={bool(st.secrets.get('AUTH_USERS_JSON'))}"
        )
        st.stop()

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        username = (username or "").strip()
        stored_password = cfg.users.get(username)

        ok = bool(stored_password) and _verify_password(password or "", stored_password)

        if ok:
            st.session_state["auth_user"] = username
            st.rerun()
        else:
            # Reduce leakage about whether user exists
            _ = hmac.compare_digest("x" * 60, (stored_password or "")[:60].ljust(60, "x"))
            st.error("Usuario o contraseña incorrectos")

    st.stop()


def logout_button() -> None:
    if st.button("Salir"):
        st.session_state["auth_user"] = None
        st.rerun()
