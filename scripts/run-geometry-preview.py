"""Run a local, disposable Phase 2 preview; never opens a real project database."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    import uvicorn
    from alembic import command
    from alembic.config import Config

    from smart_engineer_api.config import Settings
    from smart_engineer_api.main import create_app

    with tempfile.TemporaryDirectory(
        prefix="smart-engineer-geometry-", ignore_cleanup_errors=True,
    ) as tmp:
        url = f"sqlite:///{Path(tmp, 'preview.db').as_posix()}"
        config = Config(str(ROOT / "apps/api/alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "apps/api/migrations"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        app = create_app(Settings(
            environment="development", database_url=url,
            allowed_origins=("http://127.0.0.1:3000", "http://localhost:3000"),
            file_storage_dir=str(Path(tmp, "files")),
        ))
        print(
            "Disposable preview ready; do not use it for data intended to persist.", flush=True,
        )
        try:
            uvicorn.run(app, host="127.0.0.1", port=args.port)
        finally:
            app.state.session_factory.kw["bind"].dispose()


if __name__ == "__main__":
    main()
