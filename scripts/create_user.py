"""Create a bcrypt hash for a new Streamlit user.

Usage:
  python scripts/create_user.py <username> <password>

Output:
  A TOML snippet you can paste into .streamlit/secrets.toml under [auth].
"""

from __future__ import annotations

import sys

import bcrypt


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_user.py <username> <password>")
        return 2

    username = sys.argv[1].strip()
    password = sys.argv[2]

    if not username:
        print("Username cannot be empty")
        return 2

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    print("\nPaste this into .streamlit/secrets.toml under [auth] -> users:\n")
    print(f'  "{username}" = "{hashed}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
