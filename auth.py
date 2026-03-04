from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Dict, Optional, Any
from collections.abc import Mapping

import streamlit as st


@dataclass(frozen=True)
class AuthConfig:
    # username -> plain password
    users: Dict[str, str]


def _to_str_dict(x: Any) -> Dict[str, str]:
    """
    Streamlit secrets often return mapping-like objects (not plain dict).
    Convert any Mapping into a clean {str: str}. Otherwise return {}.
    """
    if x is None or not isinstance(x, Mapping):
        return {}

    out: Dict[str, str] = {}
    for k, v in x.items():
        if k is None or v is None:
            continue
        out[str(k)].strip()
        out[str(k)] = str(v)
    return out


def _get_auth_config() -> AuthConfig:
    # `st.secrets` is Mapping-like; so is `st.secrets.get("auth")`
    auth_cfg = st.secrets.get("auth", {})
    if not isinstance(auth_cfg, Mapping):
        auth_cfg = {}

    # Supports:
    # [auth]
    # users = { Carlos="admin123", Doc="doc123" }
    #
    # or:
    # [auth.users]
    # Carlos = "admin123"
    # Doc = "doc123"
    users = _to_str_dict(auth_cfg.get("users"))

    # Normalize keys/values (strip whitespace, force strings)
    norm: Dict[str, str] = {}
    for k, v in users.items():
        kk = str(k).strip()
        vv = str(v).strip()
        if not kk or not vv:
            continue
        norm[kk] = vv

    return AuthConfig(users=norm)


def _verify_password(password: str, stored_password: str) -> bool:
    # constant-time comparison for plain passwords
    try:
        return hmac.compare_digest(password, stored_password)
    except Exception:
        return False


def require_login() -> Optional[str]:
    """Returns the username if authenticated; otherwise renders login UI and stops."""
    st.session_state.setdefault("auth_user", None)

    if st.session_state.get("auth_user"):
        return str(st.session_state["auth_user"])

    cfg = _get_auth_config()

    st.title("Underwriting (SAT + Buró)")
    st.caption("Acceso restringido")

    if not cfg.users:
        # Debug (safe): show what keys exist under auth and the type Streamlit is providing.
        auth_cfg = st.secrets.get("auth", {})
        auth_keys = list(auth_cfg.keys()) if isinstance(auth_cfg, Mapping) else []
        users_obj = auth_cfg.get("users") if isinstance(auth_cfg, Mapping) else None
        st.error(
            "No hay usuarios configurados en secrets.\n\n"
            "Agrega usuarios en `.streamlit/secrets.toml`.\n\n"
            f"DEBUG: auth_keys={auth_keys}, users_type={type(users_obj).__name__}"
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
            # reduce leakage about whether user exists
            _ = hmac.compare_digest("x" * 60, (stored_password or "")[:60].ljust(60, "x"))
            st.error("Usuario o contraseña incorrectos")

    st.stop()


def logout_button() -> None:
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("Salir"):
            st.session_state["auth_user"] = None
            st.rerun()
