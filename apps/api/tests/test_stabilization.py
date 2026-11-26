"""Regression tests added for Phase 1 stabilization, separate from legacy suites."""

import tempfile
import unittest
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from smart_engineer_api import auth_service as auth
from smart_engineer_api import (
    environment_service,
    file_service,
    intake_service,
    requirements_service,
    site_service,
    zoning_service,
)
from smart_engineer_api.db import (
    ActivityEvent,
    Base,
    EnvironmentRecord,
    IntakeStep,
    Membership,
    RequirementSection,
    SiteSection,
    ZoningRecord,
)
from smart_engineer_api.db.session import create_session_factory
from smart_engineer_api.file_storage import FileStorage
from smart_engineer_api.project_service import create_project
from smart_engineer_api.security import ScryptParams
from smart_engineer_api.versioned_documents import write_document
from tests.geometry_helpers import memory_engine

POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=16))
PDF = b"%PDF-1.4\n%%EOF\n"


class StabilizationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.directory.cleanup)
        engine = memory_engine()
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.sessions = create_session_factory(engine)
        self.session = self.sessions()
        self.addCleanup(self.session.close)
        self.owner = auth.register(self.session, POLICY, email="regression@example.com",
                                   display_name="Regression", password="correct horse battery")
        org = self.session.scalar(select(Membership.organization_id).where(Membership.user_id == self.owner.id))
        self.project = create_project(self.session, self.owner, org, name="Regression", project_type="other")
        self.storage = FileStorage(str(Path(self.directory.name, "files")))

    def count_events(self):
        return self.session.scalar(select(func.count()).select_from(ActivityEvent))

    def test_stale_identity_maps_cannot_overwrite_any_of_the_five_documents(self):
        cases = [
            (IntakeStep, "step_key", "location", intake_service.save_step, intake_service.IntakeError,
             {"city": "first"}, {"city": "editor A"}, {"city": "editor B"}),
            (SiteSection, "section_key", "terrain", site_service.save_section, site_service.SiteError,
             {"slope_percent": 1}, {"slope_percent": 2}, {"slope_percent": 3}),
            (RequirementSection, "section_key", "preferences", requirements_service.save_section,
             requirements_service.RequirementsError, {}, {"budget_amount": 12, "budget_currency": "toman"}, {}),
            (ZoningRecord, "field_key", "coverage", zoning_service.save_record, zoning_service.ZoningError,
             {"max_coverage_percent": 10}, {"max_coverage_percent": 20}, {"max_coverage_percent": 30}),
            (EnvironmentRecord, "field_key", "rainfall", environment_service.save_record,
             environment_service.EnvironmentError_, {"annual_mm": 1}, {"annual_mm": 2}, {"annual_mm": 3}),
        ]
        for model, key_name, key_value, save, error_type, initial, edit_a, edit_b in cases:
            with self.subTest(document=model.__name__):
                save(self.session, self.owner, self.project.id, key_value, initial, 0)
                with self.sessions() as second:
                    cached = second.scalar(select(model).where(model.project_id == self.project.id,
                                                                getattr(model, key_name) == key_value))
                    self.assertEqual(cached.version, 1)
                    first = save(self.session, self.owner, self.project.id, key_value, edit_a, 1)
                    self.assertEqual(first["version"], 2)
                    count = self.count_events()
                    with self.assertRaises(error_type) as rejected:
                        save(second, self.owner, self.project.id, key_value, edit_b, 1)
                    self.assertEqual(rejected.exception.code, "version_conflict")
                    self.assertEqual(self.count_events(), count)
                    actual = self.session.scalar(select(model).where(model.project_id == self.project.id,
                        getattr(model, key_name) == key_value).execution_options(populate_existing=True))
                    self.assertEqual((actual.version, actual.data), (2, edit_a))
                    retry = save(second, self.owner, self.project.id, key_value, edit_b, 2)
                    self.assertEqual(retry["version"], 3)

    def test_two_initial_creations_report_conflict_and_do_not_add_an_audit(self):
        intake_service.save_step(self.session, self.owner, self.project.id, "location", {"city": "first"}, 0)
        count = self.count_events()
        with self.sessions() as second, self.assertRaises(intake_service.IntakeError) as raised:
            intake_service.save_step(second, self.owner, self.project.id, "location", {"city": "second"}, 0)
        self.assertEqual(raised.exception.code, "version_conflict")
        self.assertEqual(self.count_events(), count)

    def test_unrelated_integrity_errors_are_not_disguised_as_version_conflicts(self):
        with self.assertRaises(IntegrityError):
            write_document(self.session, IntakeStep, {"project_id": self.project.id, "step_key": "identity"},
                           data={}, actor_id=uuid.uuid4(), expected_version=0, complete=False,
                           conflict=lambda: intake_service.IntakeError("version_conflict"))

    def upload(self, version_of=None, suffix=b""):
        return file_service.upload_file(self.session, self.storage, self.owner, self.project.id,
            filename="plan.pdf", kind="survey", document_date=None, ownership=None,
            content=PDF + suffix, builtin_scan_is_authoritative=True, new_version_of=version_of)

    def test_comparing_old_versions_uses_the_real_latest_version_and_stale_basis(self):
        first = self.upload()
        second = self.upload(uuid.UUID(first["id"]), b"v2")
        file_service.set_basis(self.session, self.owner, self.project.id, uuid.UUID(second["id"]), is_basis=True)
        third = self.upload(uuid.UUID(second["id"]), b"v3")
        result = file_service.compare_versions(self.session, self.owner, self.project.id,
                                               uuid.UUID(first["id"]), uuid.UUID(second["id"]))
        self.assertFalse(result["to"]["is_latest"])
        self.assertTrue(result["to"]["basis_outdated"])
        file_service.delete_file(self.session, self.storage, self.owner, self.project.id, uuid.UUID(third["id"]))
        after = file_service.compare_versions(self.session, self.owner, self.project.id,
                                              uuid.UUID(first["id"]), uuid.UUID(second["id"]))
        self.assertTrue(after["to"]["is_latest"])
        self.assertFalse(after["to"]["basis_outdated"])
