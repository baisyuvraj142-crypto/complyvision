import unittest
import json
import os
from app import app

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_get_samples(self):
        res = self.client.get('/api/samples')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["samples"]), 5)

    def test_get_rules(self):
        res = self.client.get('/api/rules')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("rules", data["config"])

    def test_scan_sample_1_pass(self):
        res = self.client.post('/api/scan', data={'sample_filename': 'sample_1_clean_pass.png'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("COMPLIANT (PASS)", data["report"]["overall_verdict"])
        self.assertLess(data["report"]["processing_time_sec"], 5.0)

    def test_scan_sample_2_missing_mfg_fail(self):
        res = self.client.post('/api/scan', data={'sample_filename': 'sample_2_fail_missing_mfg.png'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("FAIL", data["report"]["overall_verdict"])

    def test_audit_history(self):
        res = self.client.get('/api/history')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["scans"], list)

if __name__ == '__main__':
    unittest.main()
