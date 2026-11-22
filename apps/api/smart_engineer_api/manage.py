"""Operator commands. Run inside the API environment, for example::

    uv run --group dev python -m smart_engineer_api.manage grant-admin person@example.com

``grant-admin`` is the only way to create the first system administrator; later ones are
granted through the audited admin API.
"""

import argparse
import sys

from . import admin_service
from .config import Settings
from .db.session import create_db_engine, create_session_factory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smart_engineer_api.manage")
    commands = parser.add_subparsers(dest="command", required=True)
    grant = commands.add_parser("grant-admin", help="mark an existing user as system administrator")
    grant.add_argument("email")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if not settings.database_url:
        print("SMART_ENGINEER_DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_db_engine(settings.database_url)
    try:
        with create_session_factory(engine)() as session:
            try:
                user = admin_service.grant_first_admin(session, args.email)
            except admin_service.AdminError as error:
                print(f"Could not grant: {error.code}", file=sys.stderr)
                return 1
    finally:
        engine.dispose()
    print(f"{user['email']} is a system administrator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
