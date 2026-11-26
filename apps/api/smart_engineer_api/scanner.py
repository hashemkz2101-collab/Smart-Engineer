"""Malware scanning of uploaded files through a ClamAV daemon (SEC-002, DEC-023).

The daemon (``clamd``) runs on the owner's own server; this module only speaks its
``INSTREAM`` protocol over TCP or a Unix socket, so file bytes never leave the owner's
infrastructure. The scan is fail closed: if the daemon cannot be reached or answers
with anything but a clear verdict, :class:`ScannerUnavailable` is raised and the file
stays ``pending`` (never downloadable) until a later rescan succeeds.
"""

import logging
import re
import socket
import struct
from typing import Protocol

from .file_policy import ScanResult

logger = logging.getLogger("smart_engineer_api.scanner")

_CHUNK = 64 * 1024
_SIGNATURE = re.compile(r"[^A-Za-z0-9._\-+/]")


class ScannerUnavailable(Exception):
    """The scanner could not give a verdict (down, timed out, or refused the stream)."""


class ContentScanner(Protocol):
    def scan(self, content: bytes) -> ScanResult: ...


class ClamdScanner:
    def __init__(
        self,
        *,
        host: str | None = None,
        port: int = 3310,
        socket_path: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not (host or socket_path):
            raise ValueError("ClamdScanner needs a host or a socket path")
        self._host = host
        self._port = port
        self._socket_path = socket_path
        self._timeout = timeout

    def _connect(self) -> socket.socket:
        if self._socket_path:
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            connection.settimeout(self._timeout)
            connection.connect(self._socket_path)
            return connection
        return socket.create_connection((self._host, self._port), timeout=self._timeout)

    def scan(self, content: bytes) -> ScanResult:
        try:
            with self._connect() as connection:
                connection.sendall(b"zINSTREAM\0")
                for start in range(0, len(content), _CHUNK):
                    chunk = content[start : start + _CHUNK]
                    connection.sendall(struct.pack(">I", len(chunk)) + chunk)
                connection.sendall(struct.pack(">I", 0))
                reply = b""
                while not reply.endswith(b"\0"):
                    part = connection.recv(4096)
                    if not part:
                        break
                    reply += part
                    if len(reply) > 4096:
                        break
        except (OSError, TimeoutError) as error:
            # Type only: the message could carry the server address.
            logger.warning("clamd unreachable (%s)", type(error).__name__)
            raise ScannerUnavailable from None
        return _parse(reply)


def _parse(reply: bytes) -> ScanResult:
    text = reply.rstrip(b"\0\r\n").decode("utf-8", "replace").strip()
    if text.endswith(" OK"):
        return ScanResult("clean")
    if text.endswith(" FOUND"):
        name = text.removeprefix("stream:").removesuffix(" FOUND").strip()
        name = _SIGNATURE.sub("_", name)[:120] or "unknown"
        return ScanResult("quarantined", f"clamav:{name}")
    # "ERROR", size limit exceeded, empty or truncated answers: no verdict.
    logger.warning("clamd gave no verdict")
    raise ScannerUnavailable
