import json
import unittest
import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import patch
from network_privacy import REPOSITORY, private_output_dir, public_address_record


class PrivacyTests(unittest.TestCase):
    def test_summary_does_not_copy_identifiers(self):
        record = {"label": "SENSITIVE_SSID", "when": "2026-10-20T00:00:00+09:00",
                  "public": "203.0.113.99",
                  "local": {"os": "Windows", "ipconfig": "HOST_SECRET 192.0.2.99 aa:bb:cc:dd:ee:ff",
                            "route": "198.51.100.99"}}
        result = public_address_record(record, 3)
        serialized = json.dumps(result)
        for secret in (record['label'], record['public'], 'HOST_SECRET', '192.0.2.99',
                       'aa:bb:cc:dd:ee:ff', '198.51.100.99'):
            self.assertNotIn(secret, serialized)
        self.assertEqual(result['label'], 'network-3')
        self.assertTrue(result['privacy']['redacted'])

    def test_private_directory_is_outside_checkout(self):
        self.assertFalse(private_output_dir('w05-ip-nat').is_relative_to(REPOSITORY))
        with self.assertRaises(ValueError):
            private_output_dir('../../out')

    def test_collector_archives_raw_but_publishes_only_summary(self):
        spec = importlib.util.spec_from_file_location('address_collector',
                    REPOSITORY / 'w05-ip-nat' / 'task2_myaddr.py')
        collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector)
        facts = {'os': 'Windows', 'ipconfig': 'SECRET_HOST 192.0.2.99 aa:bb:cc:dd:ee:ff'}
        with tempfile.TemporaryDirectory(dir=REPOSITORY) as directory:
            with patch.object(collector, 'OUT', directory), \
                 patch.object(collector, 'local_facts', return_value=facts), \
                 patch.object(collector, 'public_address', return_value='203.0.113.99'), \
                 patch.object(collector, 'append_private_address', return_value=Path(directory)/'private') as archive, \
                 patch('builtins.print'):
                collector.collect('SECRET_SSID')
            raw = archive.call_args.args[0]
            self.assertEqual(raw['local'], facts)
            self.assertEqual(raw['public'], '203.0.113.99')
            public = (Path(directory)/'addresses.json').read_text(encoding='utf-8')
            for secret in ('SECRET_HOST', '192.0.2.99', '203.0.113.99',
                           'aa:bb:cc:dd:ee:ff', 'SECRET_SSID'):
                self.assertNotIn(secret, public)


if __name__ == '__main__':
    unittest.main()
