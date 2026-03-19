from __future__ import annotations

import argparse

from app.auth.password import hash_password
from app.db import execute_write


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update a backend user.",
        epilog="Usage: python -m scripts.create_user --username admin --password <pw> --role editor",
    )
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", choices=["viewer", "editor"], required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password_hash = hash_password(args.password)

    rowcount = execute_write(
        """
        INSERT INTO users (username, password_hash, role, is_active)
        VALUES (:username, :password_hash, :role, 1)
        ON DUPLICATE KEY UPDATE
          password_hash = VALUES(password_hash),
          role = VALUES(role),
          is_active = 1,
          locked_until = NULL,
          failed_login_count = 0
        """,
        {
            "username": args.username,
            "password_hash": password_hash,
            "role": args.role,
        },
    )

    if rowcount >= 0:
        print(f"OK: user '{args.username}' is ready with role '{args.role}'")
        return 0

    print(f"ERROR: failed to create or update user '{args.username}'")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
