"""Offline tests for calendar fetching/validation and the generator CLI.

Run with::

    python3 -m unittest discover -s scripts -p 'test_quest*.py'
"""
import json
import os
import tempfile
import unittest
import xml.dom.minidom

import generate_quest
from quest import github
from test_quest_sim import PATTERN, TODAY, _calendar


def _graphql_body(days, total):
    weeks = [{"contributionDays": [{"date": d["date"], "contributionCount": d["count"]} for d in days[i:i + 7]]}
             for i in range(0, len(days), 7)]
    return {"data": {"user": {"contributionsCollection": {"contributionCalendar": {
        "totalContributions": total, "weeks": weeks}}}}}


class GraphqlBodyValidation(unittest.TestCase):
    VALID = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"totalContributions": 1, "weeks": []}}}}}

    def test_valid_body_passes_through(self):
        self.assertIs(github.validate_graphql_body(self.VALID, "someone"), self.VALID)

    def test_graphql_errors_are_surfaced(self):
        body = {"errors": [{"message": "Bad credentials"}], "data": None}
        with self.assertRaisesRegex(SystemExit, "Bad credentials"):
            github.validate_graphql_body(body, "someone")

    def test_null_data_rejected(self):
        with self.assertRaisesRegex(SystemExit, "no data object"):
            github.validate_graphql_body({"data": None}, "someone")

    def test_unknown_user_rejected(self):
        with self.assertRaisesRegex(SystemExit, "not found"):
            github.validate_graphql_body({"data": {"user": None}}, "ghost")

    def test_non_dict_body_rejected(self):
        with self.assertRaisesRegex(SystemExit, "unexpected"):
            github.validate_graphql_body(["nope"], "someone")


class CalendarExtraction(unittest.TestCase):
    def test_flattens_and_sorts_days(self):
        days = _calendar([1, 0, 3])
        body = _graphql_body(list(reversed(days)), 4)
        extracted, total = github.extract_days(body)
        self.assertEqual([d["date"] for d in extracted], sorted(d["date"] for d in days))
        self.assertEqual(total, 4)

    def test_bad_shape_fails_loudly(self):
        with self.assertRaisesRegex(SystemExit, "unexpected GraphQL response shape"):
            github.extract_days({"data": {"user": {}}})

    def test_malformed_dates_never_reach_the_markup(self):
        days = _calendar([1, 2])
        days[0]["date"] = '1" onload="x-01-01'
        with self.assertRaisesRegex(SystemExit, "unexpected GraphQL response shape"):
            github.extract_days(_graphql_body(days, 3))

    def test_empty_calendar_rejected(self):
        with self.assertRaisesRegex(SystemExit, "empty"):
            github.extract_days(_graphql_body([], 0))

    def test_negative_counts_rejected(self):
        with self.assertRaisesRegex(SystemExit, "negative"):
            github.extract_days(_graphql_body(_calendar([1, -2]), 1))


class GeneratorCli(unittest.TestCase):
    def test_end_to_end_from_local_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "contribs.json")
            output = os.path.join(tmp, "out", "quest.svg")
            with open(source, "w") as handle:
                json.dump(_graphql_body(_calendar(PATTERN), 5434), handle)
            generate_quest.main(["--input", source, "--output", output, "--date", TODAY.isoformat()])
            with open(output) as handle:
                svg = handle.read()
        xml.dom.minidom.parseString(svg)
        active = [c for c in PATTERN[:-1] if c > 0][-generate_quest.ROSTER_SIZE:]
        self.assertIn('id="game-title"', svg)
        self.assertIn(f'id="souls-{sum(active)}"', svg)

    def test_bad_date_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, "YYYY-MM-DD"):
            generate_quest._parse_date("16/09/2026")

    def test_missing_input_file_is_reported(self):
        with self.assertRaisesRegex(SystemExit, "cannot read"):
            generate_quest.main(["--input", "/nonexistent/contribs.json", "--output", "/tmp/x.svg"])

    def test_calendar_without_activity_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "contribs.json")
            with open(source, "w") as handle:
                json.dump(_graphql_body(_calendar([0, 0, 0]), 0), handle)
            with self.assertRaisesRegex(SystemExit, "roster"):
                generate_quest.main(["--input", source, "--output", os.path.join(tmp, "q.svg"),
                                     "--date", TODAY.isoformat()])


if __name__ == "__main__":
    unittest.main()
