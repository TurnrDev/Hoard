from django.test import SimpleTestCase

from hoard.campaigns.models import format_campaign_date, ordinal


class CampaignDateFormattingTests(SimpleTestCase):
    def test_shared_ordinal_rule_and_required_format(self) -> None:
        self.assertEqual(
            [ordinal(day) for day in (1, 2, 3, 4, 11, 12, 13, 21)],
            ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st"],
        )
        self.assertEqual(format_campaign_date("PD", 81, 21), "PD 81, 21st")
