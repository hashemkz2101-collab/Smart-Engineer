import tempfile
import unittest
from pathlib import Path
from unittest import mock

from alembic import command
from fastapi.testclient import TestClient

from smart_engineer_api import auth_service as auth
from smart_engineer_api.config import Settings
from smart_engineer_api.db.session import create_db_engine, create_session_factory
from smart_engineer_api.mail import SmtpMailer
from smart_engineer_api.main import create_app
from smart_engineer_api.security import ScryptParams
from tests.helpers import alembic_config
from tests.test_email_auth import MAIL_ENV, FakeSmtp

POLICY = auth.AuthPolicy(scrypt=ScryptParams(n=2**4, r=8, p=1))
PASSWORD = "correct horse battery"
V1 = "/api/v1"


class InvitationEmailTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        url = f"sqlite:///{Path(directory.name, 'test.db').as_posix()}"
        command.upgrade(alembic_config(url), "head")
        self.engine = create_db_engine(url)
        self.addCleanup(self.engine.dispose)
        self.mailer = auth.OutboxMailer()

    def client(self, settings: Settings | None = None) -> tuple[TestClient, dict]:
        app = create_app(
            settings or Settings(environment="test"),
            session_factory=create_session_factory(self.engine),
            auth_policy=POLICY,
            mailer=self.mailer,
        )
        client = TestClient(app)
        self.addCleanup(client.close)
        client.post(f"{V1}/auth/register", json={
            "email": "owner@example.com", "display_name": "علی مالک", "password": PASSWORD})
        csrf = client.post(f"{V1}/auth/login", json={
            "email": "owner@example.com", "password": PASSWORD}).json()["csrf_token"]
        return client, {"X-CSRF-Token": csrf}

    def create_project(self, client, headers) -> tuple[str, str]:
        org = client.get(f"{V1}/orgs").json()["organizations"][0]["id"]
        project = client.post(f"{V1}/projects", headers=headers, json={
            "organization_id": org, "name": "ویلای شمال", "project_type": "other"})
        return org, project.json()["project"]["id"]

    def test_organization_and_project_invitations_are_emailed_once_each(self) -> None:
        client, headers = self.client()
        org, project = self.create_project(client, headers)
        org_response = client.post(f"{V1}/orgs/{org}/invitations", headers=headers, json={
            "email": "org-guest@example.com", "org_role": "member"})
        project_response = client.post(f"{V1}/projects/{project}/invitations", headers=headers, json={
            "email": "project-guest@example.com", "role": "architect"})
        self.assertEqual((org_response.status_code, project_response.status_code), (201, 201))
        self.assertEqual(len(self.mailer.invitations), 2)
        (org_email, org_token, org_notice), (project_email, project_token, project_notice) = (
            self.mailer.invitations
        )
        self.assertEqual((org_email, org_token), ("org-guest@example.com", org_response.json()["token"]))
        self.assertEqual((org_notice.kind, org_notice.inviter_name, org_notice.role),
                         ("organization", "علی مالک", "member"))
        self.assertEqual(
            (project_email, project_notice.kind, project_notice.target_name, project_notice.role),
            ("project-guest@example.com", "project", "ویلای شمال", "architect"),
        )
        self.assertEqual(project_token, project_response.json()["token"])
        self.assertFalse(org_response.json()["email_sent"])

    def test_refused_invitations_send_nothing(self) -> None:
        client, headers = self.client()
        org, project = self.create_project(client, headers)
        client.post(f"{V1}/projects/{project}/invitations", headers=headers, json={
            "email": "x@example.com", "role": "emperor"})
        client.post(f"{V1}/projects/{project}/invitations", json={
            "email": "x@example.com", "role": "architect"})
        client.post(f"{V1}/orgs/{org}/invitations", headers=headers, json={
            "email": "not-an-email", "org_role": "member"})
        self.assertEqual(self.mailer.invitations, [])

    def test_email_sent_flag_follows_the_mail_configuration(self) -> None:
        settings = Settings.from_env({"SMART_ENGINEER_ENV": "test", **MAIL_ENV})
        client, headers = self.client(settings)
        _, project = self.create_project(client, headers)
        response = client.post(f"{V1}/projects/{project}/invitations", headers=headers, json={
            "email": "g@example.com", "role": "architect"})
        self.assertTrue(response.json()["email_sent"])

    def test_the_smtp_message_names_the_inviter_target_and_role_and_links_to_accept(self) -> None:
        settings = Settings.from_env({**MAIL_ENV})
        mailer = SmtpMailer(settings, background=False)
        with mock.patch("smart_engineer_api.mail.smtplib.SMTP", FakeSmtp):
            FakeSmtp.instances = []
            mailer.send_invitation(
                "guest@example.com", "t k",
                auth.InvitationNotice("project", "علی مالک", "ویلای شمال", "quantity_surveyor"),
            )
            mailer.send_invitation(
                "guest@example.com", "tok",
                auth.InvitationNotice("organization", "علی مالک", "دفتر نمونه", "member"),
            )
        project_mail, org_mail = (i.sent[0] for i in FakeSmtp.instances)
        body = project_mail.get_content()
        for expected in ("علی مالک", "پروژهٔ «ویلای شمال»", "متره‌گر / برآوردکننده",
                         "https://app.example.com/invitations/accept?token=t%20k"):
            self.assertIn(expected, body)
        self.assertEqual(project_mail["To"], "guest@example.com")
        self.assertIn("سازمان «دفتر نمونه»", org_mail["Subject"])


if __name__ == "__main__":
    unittest.main()
