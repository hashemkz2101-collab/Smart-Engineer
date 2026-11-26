"""Operator commands. Run inside the API environment, for example::

    uv run --group dev python -m smart_engineer_api.manage grant-admin person@example.com

``grant-admin`` is the only way to create the first system administrator; later ones are
granted through the audited admin API.
"""

import argparse
import sys

from . import admin_service, dev_seed, file_service
from .config import ConfigurationError, Settings
from .db.session import create_db_engine, create_session_factory
from .file_storage import FileStorage
from .scanner import ClamdScanner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smart_engineer_api.manage")
    commands = parser.add_subparsers(dest="command", required=True)
    grant = commands.add_parser("grant-admin", help="mark an existing user as system administrator")
    grant.add_argument("email")
    commands.add_parser(
        "rescan-files", help="scan files left pending because the scanner was unavailable"
    )
    commands.add_parser(
        "seed-demo", help="create demo accounts and sample projects in a LOCAL throwaway database"
    )
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if not settings.database_url:
        print("SMART_ENGINEER_DATABASE_URL is not set.", file=sys.stderr)
        return 2
    if args.command == "rescan-files":
        return _rescan(settings)
    if args.command == "seed-demo":
        return _seed_demo(settings)
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


def _rescan(settings: Settings) -> int:
    if not settings.clamav_configured:
        print("SMART_ENGINEER_CLAMAV_HOST (or _SOCKET) is not set.", file=sys.stderr)
        return 2
    scanner = ClamdScanner(
        host=settings.clamav_host,
        port=settings.clamav_port,
        socket_path=settings.clamav_socket,
        timeout=settings.clamav_timeout,
    )
    engine = create_db_engine(settings.database_url or "")
    try:
        with create_session_factory(engine)() as session:
            counts = file_service.rescan_pending(
                session, FileStorage(settings.file_storage_dir), scanner
            )
    finally:
        engine.dispose()
    print(
        f"clean: {counts['clean']}, quarantined: {counts['quarantined']}, "
        f"still pending: {counts['still_pending']}"
    )
    return 0 if counts["still_pending"] == 0 else 1


def _seed_demo(settings: Settings) -> int:
    try:
        dev_seed.ensure_local_demo_database(settings)
    except ConfigurationError as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2
    engine = create_db_engine(settings.database_url or "")
    try:
        with create_session_factory(engine)() as session:
            emails = dev_seed.seed(session)
    finally:
        engine.dispose()
    print("Demo accounts (password for all: " + dev_seed.DEMO_PASSWORD + "):")
    for email in emails:
        print(f"  {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
