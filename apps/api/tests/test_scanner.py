import socket
import socketserver
import struct
import threading
import unittest

from smart_engineer_api.config import ConfigurationError, Settings
from smart_engineer_api.scanner import ClamdScanner, ScannerUnavailable


def _read_exact(connection: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        part = connection.recv(size - len(data))
        if not part:
            raise ConnectionError
        data += part
    return data


class FakeClamd(socketserver.ThreadingTCPServer):
    """Speaks just enough of clamd's INSTREAM protocol for tests."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, reply: bytes | None) -> None:
        self.reply = reply
        self.received: list[bytes] = []
        super().__init__(("127.0.0.1", 0), self._handler())

    def _handler(self):
        outer = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                command = b""
                while not command.endswith(b"\0"):
                    command += self.request.recv(1)
                if command != b"zINSTREAM\0":
                    return
                body = b""
                while True:
                    (size,) = struct.unpack(">I", _read_exact(self.request, 4))
                    if size == 0:
                        break
                    body += _read_exact(self.request, size)
                outer.received.append(body)
                if outer.reply is not None:
                    self.request.sendall(outer.reply)

        return Handler

    @property
    def port(self) -> int:
        return self.server_address[1]


class ClamdScannerTests(unittest.TestCase):
    def serve(self, reply: bytes | None) -> FakeClamd:
        server = FakeClamd(reply)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def scanner(self, server: FakeClamd) -> ClamdScanner:
        return ClamdScanner(host="127.0.0.1", port=server.port, timeout=5)

    def test_clean_verdict_and_the_whole_file_is_streamed_in_chunks(self) -> None:
        server = self.serve(b"stream: OK\0")
        content = bytes(range(256)) * 1000  # larger than one chunk
        self.assertEqual(self.scanner(server).scan(content).verdict, "clean")
        self.assertEqual(server.received, [content])

    def test_found_is_quarantined_with_a_safe_signature_name(self) -> None:
        server = self.serve(b"stream: Win.Test.EICAR_HDB-1 FOUND\0")
        result = self.scanner(server).scan(b"data")
        self.assertEqual((result.verdict, result.detail), ("quarantined", "clamav:Win.Test.EICAR_HDB-1"))
        odd = self.serve(b"stream: bad name<script> FOUND\0")
        self.assertEqual(self.scanner(odd).scan(b"x").detail, "clamav:bad_name_script_")

    def test_errors_and_silence_give_no_verdict(self) -> None:
        for reply in (b"INSTREAM size limit exceeded. ERROR\0", b"stream: weird\0", None):
            server = self.serve(reply)
            with self.assertRaises(ScannerUnavailable):
                self.scanner(server).scan(b"data")

    def test_unreachable_daemon_gives_no_verdict(self) -> None:
        free = socket.socket()
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
        free.close()
        with self.assertRaises(ScannerUnavailable):
            ClamdScanner(host="127.0.0.1", port=port, timeout=1).scan(b"data")

    def test_settings_read_the_scanner_from_the_environment(self) -> None:
        self.assertFalse(Settings.from_env({}).clamav_configured)
        settings = Settings.from_env({
            "SMART_ENGINEER_CLAMAV_HOST": "10.0.0.5",
            "SMART_ENGINEER_CLAMAV_PORT": "3311",
            "SMART_ENGINEER_CLAMAV_TIMEOUT": "60",
        })
        self.assertEqual(
            (settings.clamav_configured, settings.clamav_host, settings.clamav_port,
             settings.clamav_timeout),
            (True, "10.0.0.5", 3311, 60.0))
        for bad in ({"SMART_ENGINEER_CLAMAV_PORT": "x"}, {"SMART_ENGINEER_CLAMAV_PORT": "0"},
                    {"SMART_ENGINEER_CLAMAV_TIMEOUT": "0"}):
            with self.assertRaises(ConfigurationError):
                Settings.from_env(bad)


if __name__ == "__main__":
    unittest.main()
