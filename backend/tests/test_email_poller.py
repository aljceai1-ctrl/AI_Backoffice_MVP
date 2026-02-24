"""Unit tests for email_poller robustness against MailHog edge cases."""
import base64
from unittest.mock import MagicMock, patch

import pytest

from app.workers.email_poller import (
    _extract_attachments,
    _extract_to_address,
    _find_tenant_by_inbound,
    poll_and_ingest,
)


# ── Fixtures: sample MailHog messages ──────────────────────────────────────────

SAMPLE_MSG_MIME_NULL = {
    "ID": "msg-001",
    "MIME": None,
    "Content": {"MIME": None, "Headers": {}, "Body": ""},
    "To": [{"Mailbox": "acme", "Domain": ""}],
    "Raw": {
        "Data": (
            "From: sender@example.com\r\n"
            "To: acme@inbound.local\r\n"
            "Subject: Invoice\r\n"
            "MIME-Version: 1.0\r\n"
            'Content-Type: application/pdf; name="inv.pdf"\r\n'
            'Content-Disposition: attachment; filename="inv.pdf"\r\n'
            "Content-Transfer-Encoding: base64\r\n"
            "\r\n"
            + base64.b64encode(b"%PDF-1.4 fake pdf content").decode()
            + "\r\n"
        )
    },
}

SAMPLE_MSG_MIME_NULL_NO_ATTACH = {
    "ID": "msg-002",
    "MIME": None,
    "Content": {"MIME": None, "Headers": {}, "Body": "plain text only"},
    "To": [{"Mailbox": "acme", "Domain": ""}],
    "Raw": {
        "Data": (
            "From: sender@example.com\r\n"
            "To: acme@inbound.local\r\n"
            "Subject: Hello\r\n"
            "\r\n"
            "Just a plain text email.\r\n"
        )
    },
}

SAMPLE_MSG_NO_TENANT = {
    "ID": "msg-003",
    "MIME": None,
    "Content": {"MIME": None, "Headers": {}, "Body": ""},
    "To": [{"Mailbox": "unknown", "Domain": ""}],
    "Raw": {"Data": ""},
}

# Exact shape from user's real MailHog /api/v2/messages response
SAMPLE_MSG_REAL_MAILHOG = {
    "ID": "real-mailhog-001@mailhog.example",
    "From": {"Mailbox": "tester", "Domain": "example.com"},
    "To": [{"Mailbox": "acme", "Domain": ""}],
    "Content": {
        "Headers": {
            "From": ["tester@example.com"],
            "To": ["acme"],
            "Subject": ["Invoice test (alias only)"],
        },
        "Body": "Test message for ingestion",
        "MIME": None,
    },
    "MIME": None,
    "Raw": {
        "From": "tester@example.com",
        "To": ["acme"],
        "Data": (
            "From: tester@example.com\r\n"
            "To: acme\r\n"
            "Subject: Invoice test (alias only)\r\n"
            "\r\n"
            "Test message for ingestion\r\n"
        ),
    },
}

SAMPLE_MSG_WITH_MIME_PARTS = {
    "ID": "msg-004",
    "MIME": {
        "Parts": [
            {
                "Headers": {
                    "Content-Type": ["application/pdf"],
                    "Content-Disposition": ['attachment; filename="report.pdf"'],
                    "Content-Transfer-Encoding": ["base64"],
                },
                "Body": base64.b64encode(b"%PDF-1.4 real pdf").decode(),
            }
        ]
    },
    "Content": {"Headers": {"To": ["acme@inbound.local"]}, "Body": ""},
    "To": [{"Mailbox": "acme", "Domain": "inbound.local"}],
    "Raw": {"Data": ""},
}


# ── _extract_to_address tests ─────────────────────────────────────────────────

class TestExtractToAddress:
    def test_alias_only_empty_domain(self):
        """MailHog To with empty Domain should return just the mailbox."""
        addr = _extract_to_address(SAMPLE_MSG_MIME_NULL)
        assert addr == "acme"

    def test_alias_with_domain(self):
        addr = _extract_to_address(SAMPLE_MSG_WITH_MIME_PARTS)
        assert addr == "acme@inbound.local"

    def test_fallback_to_content_headers(self):
        """When To array is missing, fall back to Content.Headers.To."""
        msg = {
            "Content": {"Headers": {"To": ["Acme <acme@inbound.local>"]}, "Body": ""},
        }
        addr = _extract_to_address(msg)
        assert addr == "acme@inbound.local"

    def test_empty_message(self):
        addr = _extract_to_address({})
        assert addr == ""

    def test_real_mailhog_alias_only(self):
        """Regression: exact MailHog payload with alias-only To and empty Domain."""
        addr = _extract_to_address(SAMPLE_MSG_REAL_MAILHOG)
        assert addr == "acme"


# ── _extract_attachments tests ─────────────────────────────────────────────────

class TestExtractAttachments:
    def test_mime_null_uses_raw_data(self):
        """When MIME is None, should parse Raw.Data and find the PDF attachment."""
        attachments = _extract_attachments(SAMPLE_MSG_MIME_NULL)
        assert len(attachments) == 1
        filename, content = attachments[0]
        assert filename == "inv.pdf"
        assert b"%PDF-1.4" in content

    def test_mime_null_no_attachments(self):
        """Plain text email with MIME=None should return no attachments."""
        attachments = _extract_attachments(SAMPLE_MSG_MIME_NULL_NO_ATTACH)
        assert attachments == []

    def test_normal_mime_parts(self):
        """When MIME parts exist, should use them directly."""
        attachments = _extract_attachments(SAMPLE_MSG_WITH_MIME_PARTS)
        assert len(attachments) == 1
        assert attachments[0][0] == "report.pdf"

    def test_completely_empty_message(self):
        attachments = _extract_attachments({"MIME": None, "Raw": None})
        assert attachments == []


# ── poll_and_ingest integration tests (mocked DB + HTTP) ──────────────────────

class TestPollAndIngest:
    """Tests that poll_and_ingest handles MIME-null messages without crashing."""

    @patch("app.workers.email_poller.validate_invoice", return_value=[])
    @patch("app.workers.email_poller._save_attachment", return_value="/tmp/fake.pdf")
    @patch("app.workers.email_poller.SessionLocal")
    @patch("app.workers.email_poller.MailHogProvider")
    def test_mime_null_no_crash(self, MockProvider, MockSession, mock_save, mock_validate):
        """Feed a MIME-null message and verify no crash + correct counters."""
        # Set up mocks
        provider_inst = MagicMock()
        provider_inst.fetch_messages.return_value = [SAMPLE_MSG_MIME_NULL]
        provider_inst.delete_message = MagicMock()
        MockProvider.return_value = provider_inst

        db = MagicMock()
        MockSession.return_value = db

        # Mock tenant lookup
        mock_tenant = MagicMock()
        mock_tenant.id = "tenant-uuid-1"
        db.query.return_value.filter.return_value.first.return_value = mock_tenant

        # Mock invoice flush — db.flush() is called with no args,
        # so we find the last-added Invoice via db.add call history.
        def on_flush():
            for call in db.add.call_args_list:
                obj = call[0][0]
                if hasattr(obj, "source_message_id") and getattr(obj, "id", None) is None:
                    obj.id = "inv-uuid-1"
        db.flush.side_effect = on_flush

        poll_and_ingest()

        # Should not crash, should commit
        db.commit.assert_called_once()
        db.close.assert_called_once()

        # Check that the IngestionRun was added with correct counters
        add_calls = db.add.call_args_list
        # Last add before commit is the IngestionRun
        run_obj = add_calls[-1][0][0]
        assert run_obj.emails_seen == 1
        assert run_obj.emails_processed == 1
        assert run_obj.failures_count == 0
        assert run_obj.status == "SUCCESS"

    @patch("app.workers.email_poller.SessionLocal")
    @patch("app.workers.email_poller.MailHogProvider")
    def test_no_tenant_increments_failure(self, MockProvider, MockSession):
        """Message with unknown tenant should increment failure, not crash."""
        provider_inst = MagicMock()
        provider_inst.fetch_messages.return_value = [SAMPLE_MSG_NO_TENANT]
        MockProvider.return_value = provider_inst

        db = MagicMock()
        MockSession.return_value = db
        db.query.return_value.filter.return_value.first.return_value = None

        poll_and_ingest()

        db.commit.assert_called_once()
        run_obj = db.add.call_args_list[-1][0][0]
        assert run_obj.failures_count == 1
        assert run_obj.status == "FAIL"

    @patch("app.workers.email_poller.SessionLocal")
    @patch("app.workers.email_poller.MailHogProvider")
    def test_mixed_success_and_failure(self, MockProvider, MockSession):
        """Mix of valid and invalid messages: partial success, no crash."""
        provider_inst = MagicMock()
        provider_inst.fetch_messages.return_value = [
            SAMPLE_MSG_NO_TENANT,   # will fail (no tenant)
            SAMPLE_MSG_MIME_NULL_NO_ATTACH,  # will succeed but no attachment
        ]
        MockProvider.return_value = provider_inst

        db = MagicMock()
        MockSession.return_value = db

        # First call returns None (no tenant), second returns a tenant
        mock_tenant = MagicMock()
        mock_tenant.id = "tenant-uuid-2"
        db.query.return_value.filter.return_value.first.side_effect = [None, mock_tenant]

        poll_and_ingest()

        db.commit.assert_called_once()
        run_obj = db.add.call_args_list[-1][0][0]
        assert run_obj.failures_count == 1
        assert run_obj.emails_processed == 1  # the no-attachment msg was processed
        assert run_obj.status == "FAIL"  # 1 failure, 0 invoices → FAIL

    @patch("app.workers.email_poller.SessionLocal")
    @patch("app.workers.email_poller.MailHogProvider")
    def test_real_mailhog_alias_only_no_crash(self, MockProvider, MockSession):
        """Regression: exact MailHog payload (MIME null, alias-only To, no attachment).

        Must NOT crash. Tenant 'acme' found → emails_processed=1, failures=0.
        """
        provider_inst = MagicMock()
        provider_inst.fetch_messages.return_value = [SAMPLE_MSG_REAL_MAILHOG]
        provider_inst.delete_message = MagicMock()
        MockProvider.return_value = provider_inst

        db = MagicMock()
        MockSession.return_value = db

        mock_tenant = MagicMock()
        mock_tenant.id = "tenant-acme-uuid"
        db.query.return_value.filter.return_value.first.return_value = mock_tenant

        poll_and_ingest()

        # Must not crash
        db.commit.assert_called_once()
        db.close.assert_called_once()

        run_obj = db.add.call_args_list[-1][0][0]
        assert run_obj.emails_seen == 1
        assert run_obj.emails_processed == 1
        assert run_obj.failures_count == 0
        assert run_obj.invoices_created == 0  # no attachment in this message
        assert run_obj.status == "SUCCESS"
        # Message should have been deleted from MailHog
        provider_inst.delete_message.assert_called_once_with("real-mailhog-001@mailhog.example")
