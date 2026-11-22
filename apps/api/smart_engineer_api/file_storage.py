"""Private on-disk storage for uploaded files (SEC-002).

Files are stored under random hex keys inside one private directory. The directory is
never mounted as static content; bytes leave only through the authorized download
endpoint. Keys are validated so a key can never escape the root.
"""

import os
import re
import secrets
from pathlib import Path

_KEY = re.compile(r"[0-9a-f]{32}")


class FileStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def new_key(self) -> str:
        return secrets.token_hex(16)

    def _path(self, key: str) -> Path:
        if not _KEY.fullmatch(key):
            raise ValueError("invalid storage key")
        return self.root / key[:2] / key

    def save(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
