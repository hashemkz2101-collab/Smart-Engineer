import os
import tempfile
import unittest
import uuid
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from smart_engineer_api import auth_service as auth
from smart_engineer_api import file_policy, file_service, org_service, project_service
from smart_engineer_api.config import Settings
from smart_engineer_api.db import Membership
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.file_storage import FileStorage
from smart_engineer_api.main import create_app
from smart_engineer_api.permissions import AccessDenied
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config

POSTGRES_URL = os.environ.get("SMART_ENGINEER_TEST_DATABASE_URL")
POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 16
PDF_WITH_SCRIPT = b"%PDF-1.4\n<< /JavaScript (app.alert(1)) >>\n"


def _zip(parts: dict[str, str]) -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class PolicyTests(unittest.TestCase):
    def test_type_is_decided_from_content(self) -> None:
        self.assertEqual(
            [file_policy.detect_type(b) for b in (PDF, PNG, JPEG, WEBP)],
            ["pdf", "png", "jpeg", "webp"],
        )
        for blob in (b"", b"MZ\x90\x00", b"<html></html>", b"#!/bin/sh\n", b"PK\x03\x04", b"GIF89a"):
            self.assertIsNone(file_policy.detect_type(blob))

    def test_new_engineering_and_office_formats_are_detected(self) -> None:
        cases = {
            "dxf": b"0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1027\n0\nENDSEC\n0\nEOF\n",
            "dwg": b"AC1032\x00\x00\x00\x00\x00\x0f" + b"\x00" * 32,
            "ifc": b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n",
            "csv": "نام,مقدار\nبتن,۱۲\n".encode(),
            "docx": _zip({"[Content_Types].xml": "<Types/>", "word/document.xml": "<w/>"}),
            "xlsx": _zip({"[Content_Types].xml": "<Types/>", "xl/workbook.xml": "<w/>"}),
            "doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + "WordDocument".encode("utf-16-le") + b"\x00" * 16,
            "xls": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + "Workbook".encode("utf-16-le") + b"\x00" * 16,
        }
        for expected, blob in cases.items():
            self.assertEqual(file_policy.detect_type(blob), expected, expected)

    def test_macro_files_and_unsafe_archives_are_refused(self) -> None:
        macro = _zip({"[Content_Types].xml": "<Types/>", "word/document.xml": "<w/>",
                      "word/vbaProject.bin": "x"})
        self.assertEqual(file_policy.classify(macro).reason, "macro_not_allowed")
        macro_ct = _zip({"[Content_Types].xml": "application/vnd.ms-word.document.macroEnabled.main+xml",
                         "word/document.xml": "<w/>"})
        self.assertEqual(file_policy.classify(macro_ct).reason, "macro_not_allowed")
        ole_macro = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + "WordDocument".encode("utf-16-le") + "Macros".encode("utf-16-le")
        self.assertEqual(file_policy.classify(ole_macro).reason, "macro_not_allowed")
        traversal = _zip({"[Content_Types].xml": "<Types/>", "../evil.xml": "x", "word/document.xml": "<w/>"})
        self.assertEqual(file_policy.classify(traversal).reason, "unsafe_archive")

    def test_office_files_with_embedded_or_external_content_are_quarantined(self) -> None:
        embedded = _zip({"[Content_Types].xml": "<Types/>", "word/document.xml": "<w/>",
                         "word/embeddings/oleObject1.bin": "x"})
        self.assertEqual(file_policy.builtin_scan(embedded, "docx").verdict, "quarantined")
        linked = _zip({"[Content_Types].xml": "<Types/>", "word/document.xml": "<w/>",
                       "word/_rels/document.xml.rels":
                       '<Relationship Type="x/attachedTemplate" Target="http://e/x" TargetMode="External"/>'})
        self.assertEqual(file_policy.builtin_scan(linked, "docx").verdict, "quarantined")
        clean = _zip({"[Content_Types].xml": "<Types/>", "word/document.xml": "<w/>"})
        self.assertEqual(file_policy.builtin_scan(clean, "docx").verdict, "clean")

    def test_names_are_reduced_to_a_safe_display_name(self) -> None:
        self.assertEqual(file_policy.clean_filename("../../etc/pass\x00wd.pdf"), "passwd.pdf")
        self.assertEqual(file_policy.clean_filename("C:\\dir\\plan.PDF"), "plan.PDF")
        self.assertEqual(file_policy.clean_filename("نقشه برداری.pdf"), "نقشه برداری.pdf")
        self.assertIsNone(file_policy.clean_filename("..."))
        self.assertIsNone(file_policy.clean_filename("a" * 201 + ".pdf"))

    def test_extension_must_agree_with_content(self) -> None:
        self.assertTrue(file_policy.extension_matches("a.JPG", "jpeg"))
        self.assertTrue(file_policy.extension_matches("a.jpeg", "jpeg"))
        self.assertFalse(file_policy.extension_matches("a.pdf", "png"))
        self.assertFalse(file_policy.extension_matches("a", "pdf"))

    def test_builtin_scan_flags_the_eicar_fixture_and_active_pdf_content(self) -> None:
        eicar = PDF + file_policy.EICAR_SIGNATURE
        self.assertEqual(file_policy.builtin_scan(eicar, "pdf").detail, "eicar_test_signature")
        self.assertEqual(file_policy.builtin_scan(PDF_WITH_SCRIPT, "pdf").verdict, "quarantined")
        self.assertEqual(file_policy.builtin_scan(PDF, "pdf").verdict, "clean")
        self.assertEqual(file_policy.builtin_scan(PNG, "png").verdict, "clean")

    def test_storage_keeps_keys_inside_its_root(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            storage = FileStorage(root)
            key = storage.new_key()
            storage.save(key, b"data")
            self.assertEqual(storage.read(key), b"data")
            with self.assertRaises(FileExistsError):
                storage.save(key, b"again")
            storage.delete(key)
            storage.delete(key)
            for bad in ("../x", "a/b", "", "Z" * 32, key + "0"):
                with self.assertRaises(ValueError):
                    storage.read(bad)


class FileChecks:
    url: str

    def setUp(self) -> None:  # noqa: N802
        command.upgrade(alembic_config(self.url), "head")
        self.engine = create_db_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.session = create_session_factory(self.engine)()
        self.addCleanup(self.session.close)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.storage = FileStorage(self._tmp.name)

    def user(self, name: str):
        return auth.register(
            self.session, POLICY, email=f"{name}@example.com", display_name=name, password=PASSWORD
        )

    def org_of(self, user):
        return self.session.scalar(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        )

    def project(self, owner):
        return project_service.create_project(
            self.session, owner, self.org_of(owner), name="House", project_type="residential_house"
        )

    def upload(self, actor, project, name="plan.pdf", content=PDF, kind="survey", **extra):
        return file_service.upload_file(
            self.session, self.storage, actor, project.id, filename=name, kind=kind,
            document_date=extra.get("document_date"), ownership=extra.get("ownership"),
            content=content, builtin_scan_is_authoritative=extra.get("authoritative", True))

    def test_upload_persists_metadata_and_bytes_stay_private(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        saved = self.upload(owner, project, "نقشه.pdf", PDF, "survey",
                            document_date="2026-05-01", ownership="کارفرما")
        self.assertEqual(
            (saved["original_name"], saved["kind"], saved["document_date"], saved["ownership"],
             saved["detected_type"], saved["size_bytes"], saved["scan_status"],
             saved["uploaded_by_name"], saved["downloadable"]),
            ("نقشه.pdf", "survey", "2026-05-01", "کارفرما", "pdf", len(PDF), "clean",
             owner.display_name, True))
        self.assertEqual(len(saved["sha256"]), 64)
        listed = file_service.list_files(self.session, owner, project.id)
        self.assertEqual([f["id"] for f in listed], [saved["id"]])
        row, content = file_service.download_file(
            self.session, self.storage, owner, project.id, uuid.UUID(saved["id"]))
        self.assertEqual((content, row.detected_type), (PDF, "pdf"))
        on_disk = [p for p in Path(self._tmp.name).rglob("*") if p.is_file()]
        self.assertEqual(len(on_disk), 1)
        self.assertNotIn("plan", on_disk[0].name)
        self.assertEqual(on_disk[0].read_bytes(), PDF)

    def test_disallowed_files_are_rejected_and_nothing_is_stored(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        cases = [
            (dict(name="a.pdf", content=b""), "empty_file"),
            (dict(name="a.exe", content=b"MZ\x90"), "unsupported_type"),
            (dict(name="a.png", content=PDF), "extension_mismatch"),
            (dict(name="a.pdf", content=PDF, kind="nope"), "invalid_kind"),
            (dict(name="...", content=PDF), "invalid_file_name"),
            (dict(name="a.pdf", content=PDF, document_date="2026-13-40"), "invalid_date"),
            (dict(name="a.pdf", content=PDF + b"0" * file_policy.MAX_UPLOAD_BYTES), "file_too_large"),
        ]
        for kwargs, code in cases:
            with self.assertRaises(file_service.FileError) as raised:
                self.upload(owner, project, **kwargs)
            self.assertEqual(raised.exception.code, code, kwargs.get("name"))
        self.assertEqual(file_service.list_files(self.session, owner, project.id), [])
        self.assertEqual([p for p in Path(self._tmp.name).rglob("*") if p.is_file()], [])

    def test_count_limit(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        self.addCleanup(setattr, file_service, "MAX_FILES_PER_PROJECT", file_service.MAX_FILES_PER_PROJECT)
        file_service.MAX_FILES_PER_PROJECT = 2
        first = self.upload(owner, project, "a.pdf")
        self.upload(owner, project, "b.pdf")
        with self.assertRaises(file_service.FileError) as raised:
            self.upload(owner, project, "c.pdf")
        self.assertEqual(raised.exception.code, "too_many_files")
        file_service.delete_file(self.session, self.storage, owner, project.id, uuid.UUID(first["id"]))
        self.upload(owner, project, "c.pdf")
        self.assertEqual(file_policy.MAX_FILES_PER_PROJECT, 100)

    def test_malware_fixture_is_quarantined_and_never_downloadable(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        saved = self.upload(owner, project, "bad.pdf", PDF + file_policy.EICAR_SIGNATURE)
        self.assertEqual((saved["scan_status"], saved["scan_detail"], saved["downloadable"]),
                         ("quarantined", "eicar_test_signature", False))
        with self.assertRaises(file_service.FileError) as raised:
            file_service.download_file(self.session, self.storage, owner, project.id,
                                       uuid.UUID(saved["id"]))
        self.assertEqual(raised.exception.code, "not_available")
        script = self.upload(owner, project, "js.pdf", PDF_WITH_SCRIPT)
        self.assertEqual(script["scan_status"], "quarantined")

    def test_without_an_authoritative_scanner_files_stay_pending_and_private(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        saved = self.upload(owner, project, "a.png", PNG, authoritative=False)
        self.assertEqual((saved["scan_status"], saved["downloadable"]), ("pending", False))
        with self.assertRaises(file_service.FileError) as raised:
            file_service.download_file(self.session, self.storage, owner, project.id,
                                       uuid.UUID(saved["id"]))
        self.assertEqual(raised.exception.code, "not_available")
        quarantined = self.upload(owner, project, "e.pdf", PDF + file_policy.EICAR_SIGNATURE,
                                  authoritative=False)
        self.assertEqual(quarantined["scan_status"], "quarantined")

    def test_roles_upload_read_and_delete_rules(self) -> None:
        owner, mep, qs, stranger = (self.user(n) for n in ("owner", "mep", "qs", "stranger"))
        project, other = self.project(owner), self.project(owner)
        for person, role in ((mep, "mep_engineer"), (qs, "quantity_surveyor")):
            _, token = org_service.create_invitation(
                self.session, owner, self.org_of(owner), email=person.email, org_role="member")
            org_service.accept_invitation(self.session, person, token)
            project_service.add_member(self.session, owner, project.id, email=person.email, role=role)
        saved = self.upload(mep, project, "m.pdf")
        fid = uuid.UUID(saved["id"])
        self.assertEqual(len(file_service.list_files(self.session, qs, project.id)), 1)
        self.assertEqual(file_service.download_file(self.session, self.storage, qs, project.id, fid)[1], PDF)
        with self.assertRaises(AccessDenied) as denied:
            self.upload(qs, project, "q.pdf")
        self.assertFalse(denied.exception.hidden)
        with self.assertRaises(AccessDenied):
            file_service.delete_file(self.session, self.storage, mep, project.id, fid)
        for action in (
            lambda: file_service.list_files(self.session, stranger, project.id),
            lambda: file_service.download_file(self.session, self.storage, stranger, project.id, fid),
            lambda: self.upload(stranger, project),
        ):
            with self.assertRaises(AccessDenied) as hidden:
                action()
            self.assertTrue(hidden.exception.hidden)
        # A file id from one project is not reachable through another project.
        with self.assertRaises(file_service.FileError) as wrong:
            file_service.download_file(self.session, self.storage, owner, other.id, fid)
        self.assertEqual(wrong.exception.code, "not_found")

    def test_delete_removes_bytes_keeps_audit_trail_and_archive_is_read_only(self) -> None:
        owner = self.user("owner")
        project = self.project(owner)
        saved = self.upload(owner, project, "a.pdf")
        fid = uuid.UUID(saved["id"])
        file_service.delete_file(self.session, self.storage, owner, project.id, fid)
        self.assertEqual(file_service.list_files(self.session, owner, project.id), [])
        self.assertEqual([p for p in Path(self._tmp.name).rglob("*") if p.is_file()], [])
        with self.assertRaises(file_service.FileError) as gone:
            file_service.download_file(self.session, self.storage, owner, project.id, fid)
        self.assertEqual(gone.exception.code, "not_found")
        actions = [e.action for e in project_service.list_activity(self.session, owner, project.id)]
        self.assertEqual(actions[-2:], ["project.file_uploaded", "project.file_deleted"])
        kept = self.upload(owner, project, "b.pdf")
        project_service.archive_project(self.session, owner, project.id)
        with self.assertRaises(AccessDenied):
            self.upload(owner, project, "c.pdf")
        with self.assertRaises(AccessDenied):
            file_service.delete_file(self.session, self.storage, owner, project.id,
                                     uuid.UUID(kept["id"]))
        self.assertEqual(len(file_service.list_files(self.session, owner, project.id)), 1)

    def test_http_upload_download_delete(self) -> None:
        engine = create_db_engine(self.url)
        self.addCleanup(engine.dispose)
        app = create_app(Settings(environment="test"),
                         session_factory=create_session_factory(engine), auth_policy=POLICY,
                         file_storage=self.storage)
        client = TestClient(app)
        self.addCleanup(client.close)
        client.post(f"{V1}/auth/register", json={
            "email": "http@example.com", "display_name": "Http", "password": PASSWORD})
        csrf = client.post(f"{V1}/auth/login", json={
            "email": "http@example.com", "password": PASSWORD}).json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        org = client.get(f"{V1}/orgs").json()["organizations"][0]["id"]
        pid = client.post(f"{V1}/projects", headers=headers, json={
            "organization_id": org, "name": "P", "project_type": "other"}).json()["project"]["id"]
        url = f"{V1}/projects/{pid}/files"
        params = {"filename": "survey.pdf", "kind": "survey"}

        self.assertEqual(client.get(url).json(), {"files": []})
        self.assertEqual(client.post(url, params=params, content=PDF).status_code, 403)
        bad = client.post(url, params={"filename": "x.exe", "kind": "survey"}, headers=headers,
                          content=b"MZ")
        self.assertEqual((bad.status_code, bad.json()["error"]["code"]), (415, "unsupported_type"))
        macro = client.post(
            url, params={"filename": "m.docx", "kind": "survey"}, headers=headers,
            content=_zip({"[Content_Types].xml": "<Types/>", "word/document.xml": "<w/>",
                          "word/vbaProject.bin": "x"}),
        )
        self.assertEqual((macro.status_code, macro.json()["error"]["code"]), (415, "macro_not_allowed"))
        big = client.post(url, params=params, headers=headers,
                          content=PDF + b"0" * file_policy.MAX_UPLOAD_BYTES)
        self.assertEqual((big.status_code, big.json()["error"]["code"]), (413, "file_too_large"))
        ok = client.post(url, params=params, headers=headers, content=PDF)
        self.assertEqual((ok.status_code, ok.json()["scan_status"]), (201, "clean"))
        fid = ok.json()["id"]
        quarantined = client.post(url, params={"filename": "e.pdf", "kind": "other"}, headers=headers,
                                  content=PDF + file_policy.EICAR_SIGNATURE)
        self.assertEqual(quarantined.json()["scan_status"], "quarantined")
        self.assertEqual(client.get(f"{url}/{quarantined.json()['id']}/download").status_code, 409)

        download = client.get(f"{url}/{fid}/download")
        self.assertEqual((download.status_code, download.content), (200, PDF))
        self.assertEqual(download.headers["content-type"], "application/pdf")
        self.assertIn("attachment", download.headers["content-disposition"])
        self.assertEqual(download.headers["x-content-type-options"], "nosniff")
        self.assertEqual(len(client.get(url).json()["files"]), 2)
        self.assertEqual(client.delete(f"{url}/{fid}").status_code, 403)
        self.assertEqual(client.delete(f"{url}/{fid}", headers=headers).status_code, 204)
        self.assertEqual(client.get(f"{url}/{fid}/download").status_code, 404)
        anonymous = TestClient(app)
        self.addCleanup(anonymous.close)
        self.assertEqual(anonymous.get(f"{url}/{fid}/download").status_code, 401)


class SqliteFileTests(FileChecks, unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        super().setUp()


@unittest.skipUnless(POSTGRES_URL, "SMART_ENGINEER_TEST_DATABASE_URL is not set")
class PostgresFileTests(FileChecks, unittest.TestCase):
    def setUp(self) -> None:
        self.url = POSTGRES_URL
        command.downgrade(alembic_config(self.url), "base")
        self.addCleanup(lambda: command.downgrade(alembic_config(self.url), "base"))
        super().setUp()


if __name__ == "__main__":
    unittest.main()
