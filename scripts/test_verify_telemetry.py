"""Offline unit tests for the fleet telemetry validator.

These exercise the pure validation functions with crafted payloads, so they run
deterministically in CI without touching the network. Run with::

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import unittest

import verify_telemetry as vt


def _errors(issues):
    return [i.message for i in issues if i.severity == "error"]


def _warnings(issues):
    return [i.message for i in issues if i.severity == "warn"]


VALID_LIVE = {
    "system": "evalops",
    "mode": "live",
    "workload": "benchmark",
    "status": "operational",
    "schema_version": 1,
    "generated_at": "2026-06-10T00:00:00Z",
    "metrics": {"eval_runs_total": 10, "eval_runs_24h": 2},
}

VALID_SHOWCASE = {
    "system": "repo-rag-debugger",
    "mode": "showcase",
    "status": "operational",
    "schema_version": 1,
    "generated_at": "2026-06-10T00:00:00Z",
    "metrics": {"commits_total": 100},
}


class EnvelopeTests(unittest.TestCase):
    def test_valid_envelope_has_no_errors(self):
        self.assertEqual(_errors(vt.validate_envelope(VALID_LIVE, "evalops")), [])

    def test_missing_field_is_error(self):
        payload = {k: v for k, v in VALID_LIVE.items() if k != "status"}
        self.assertTrue(any("status" in m for m in _errors(vt.validate_envelope(payload, "evalops"))))

    def test_slug_mismatch_is_error(self):
        self.assertTrue(_errors(vt.validate_envelope(VALID_LIVE, "wrong-slug")))

    def test_bad_mode_is_error(self):
        payload = {**VALID_LIVE, "mode": "banana"}
        self.assertTrue(any("mode" in m for m in _errors(vt.validate_envelope(payload, "evalops"))))

    def test_wrong_schema_version_is_error(self):
        payload = {**VALID_LIVE, "schema_version": 2}
        self.assertTrue(_errors(vt.validate_envelope(payload, "evalops")))

    def test_non_object_metrics_is_error(self):
        payload = {**VALID_LIVE, "metrics": []}
        self.assertTrue(_errors(vt.validate_envelope(payload, "evalops")))


class ModeWorkloadTests(unittest.TestCase):
    def test_live_requires_workload(self):
        payload = {k: v for k, v in VALID_LIVE.items() if k != "workload"}
        self.assertTrue(_errors(vt.validate_mode_workload(payload, {"slug": "evalops"})))

    def test_live_with_valid_workload_ok(self):
        cfg = {"expected_mode": "live", "expected_workload": "benchmark"}
        self.assertEqual(_errors(vt.validate_mode_workload(VALID_LIVE, cfg)), [])

    def test_invalid_workload_is_error(self):
        payload = {**VALID_LIVE, "workload": "mining"}
        self.assertTrue(_errors(vt.validate_mode_workload(payload, {})))

    def test_showcase_with_workload_warns(self):
        payload = {**VALID_SHOWCASE, "workload": "benchmark"}
        self.assertTrue(_warnings(vt.validate_mode_workload(payload, {})))

    def test_live_to_showcase_is_regression_error(self):
        payload = {**VALID_SHOWCASE}
        cfg = {"expected_mode": "live"}
        self.assertTrue(any("regression" in m for m in _errors(vt.validate_mode_workload(payload, cfg))))

    def test_graduation_only_warns(self):
        payload = {**VALID_LIVE}
        cfg = {"expected_mode": "showcase"}
        self.assertEqual(_errors(vt.validate_mode_workload(payload, cfg)), [])
        self.assertTrue(_warnings(vt.validate_mode_workload(payload, cfg)))


class MetricsTests(unittest.TestCase):
    def test_missing_required_metric_is_error(self):
        cfg = {"required_metrics": ["eval_runs_total", "missing_key"]}
        self.assertTrue(any("missing_key" in m for m in _errors(vt.validate_metrics(VALID_LIVE, cfg))))

    def test_all_present_ok(self):
        cfg = {"required_metrics": ["eval_runs_total", "eval_runs_24h"]}
        self.assertEqual(_errors(vt.validate_metrics(VALID_LIVE, cfg)), [])


class TimestampTests(unittest.TestCase):
    def test_z_suffix_ok(self):
        self.assertEqual(vt.validate_timestamp({"generated_at": "2026-06-10T12:00:00Z"}), [])

    def test_offset_ok(self):
        self.assertEqual(vt.validate_timestamp({"generated_at": "2026-06-10T12:00:00+00:00"}), [])

    def test_garbage_is_error(self):
        self.assertTrue(vt.validate_timestamp({"generated_at": "not-a-date"}))


class HeaderTests(unittest.TestCase):
    GOOD = {
        "access-control-allow-origin": "*",
        "cache-control": "public, max-age=30, stale-while-revalidate=60",
        "content-type": "application/json",
    }

    def test_good_headers_no_issues(self):
        self.assertEqual(vt.validate_headers(self.GOOD, strict=False), [])

    def test_missing_cors_warns_then_errors_in_strict(self):
        headers = {k: v for k, v in self.GOOD.items() if k != "access-control-allow-origin"}
        self.assertTrue(_warnings(vt.validate_headers(headers, strict=False)))
        self.assertTrue(_errors(vt.validate_headers(headers, strict=True)))


if __name__ == "__main__":
    unittest.main()
