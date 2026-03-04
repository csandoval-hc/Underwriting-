from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Dict, Optional

import bcrypt
import streamlit as st


@dataclass(frozen=True)
class AuthConfig:
    # username -> bcrypt hash string
    users: Dict[str, str]


def _get_auth_config() -> AuthConfig:
    cfg = st.secrets.get("auth", {})
    users = cfg.get("users", {})
    if users is None:
        users = {}
    if not isinstance(users, dict):
        # misconfigured secrets
        users = {}

    # normalize keys/values to str
    norm: Dict[str, str] = {}
    for k, v in users.items():
        if k is None or v is None:
            continue
        norm[str(k)] = str(v)

    return AuthConfig(users=norm)


def _verify_password(password: str, bcrypt_hash: str) -> bool:
    try:
        pw = password.encode("utf-8")
        hh = bcrypt_hash.encode("utf-8")
        return bcrypt.checkpw(pw, hh)
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
        st.error(
            "No hay usuarios configurados en secrets.\n\n"
            "Agrega usuarios en `.streamlit/secrets.toml` (ver README)."
        )
        st.stop()

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        username = (username or "").strip()
        bcrypt_hash = cfg.users.get(username)
        ok = bool(bcrypt_hash) and _verify_password(password or "", bcrypt_hash)

        if ok:
            st.session_state["auth_user"] = username
            st.rerun()
        else:
            # use constant-time comparison for the "user exists" branch to reduce leakage
            _ = hmac.compare_digest("x" * 60, (bcrypt_hash or "")[:60].ljust(60, "x"))
            st.error("Usuario o contraseña incorrectos")

    st.stop()


def logout_button() -> None:
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("Salir"):
            st.session_state["auth_user"] = None
            st.rerun()
