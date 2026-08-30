from uuid import UUID

from django.test import SimpleTestCase

from hoard.campaigns.models import Campaign
from hoard.campaigns.protocol import (
    OperationKind,
    error_type,
    is_uuid7,
    operation_kind,
    result_type,
)


class WebSocketProtocolTests(SimpleTestCase):
    def test_query_operations_have_query_result_envelopes(self) -> None:
        kind = operation_kind("campaign.get")

        self.assertEqual(kind, OperationKind.QUERY)
        self.assertEqual(result_type(kind), "query.result")
        self.assertEqual(error_type(kind), "query.error")

    def test_commands_have_acknowledgement_and_error_envelopes(self) -> None:
        kind = operation_kind("characters.update")

        self.assertEqual(kind, OperationKind.COMMAND)
        self.assertEqual(result_type(kind), "command.ack")
        self.assertEqual(error_type(kind), "command.error")

    def test_only_uuid7_request_identifiers_are_accepted(self) -> None:
        request_id = "0197d6c5-6a24-7000-8000-000000000000"

        self.assertEqual(UUID(request_id).version, 7)
        self.assertTrue(is_uuid7(request_id))
        self.assertFalse(is_uuid7("calendar-1"))
        self.assertFalse(is_uuid7("550e8400-e29b-41d4-a716-446655440000"))

    def test_calendar_payload_is_a_json_ready_pydantic_contract(self) -> None:
        from hoard.campaigns.payloads import CampaignCalendarData

        payload = CampaignCalendarData.from_campaign(
            Campaign(
                name="Protocol test",
                calendar_era_abbreviation="AE",
                calendar_era_name="After Example",
                calendar_year=42,
                calendar_day=12,
            )
        )

        self.assertEqual(
            payload.model_dump(mode="json"),
            {
                "era_abbreviation": "AE",
                "era_name": "After Example",
                "year": 42,
                "day": 12,
            },
        )
