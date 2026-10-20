"""Boundary and independent randomized comparisons beyond the supplied cases."""
import random
import unittest
from task1_forward import address_int, parse_cidr, network_range, ForwardingTable
from task3_lpm import LinearTable, YourTable


class SubnetTests(unittest.TestCase):
    def test_invalid_inputs(self):
        for value in ("1.2.3.4/33", "0.0.0.0/-1", "163.152.6.5/24",
                      "256.0.0.0/8", "1.2.3/24", "1.2.3.4/24/1",
                      "01.2.3.4/32", "1.2.3.4/2.0", "1.2.3.4/ 32"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_cidr(value)

    def test_edges(self):
        cases = {
            "0.0.0.0/0": ("0.0.0.1", "255.255.255.254", "255.255.255.255"),
            "192.0.2.0/30": ("192.0.2.1", "192.0.2.2", "192.0.2.3"),
            "192.0.2.0/31": ("192.0.2.0", "192.0.2.1", "192.0.2.1"),
            "255.255.255.255/32": ("255.255.255.255",) * 3,
        }
        for cidr, expected in cases.items():
            self.assertEqual(network_range(cidr), expected)

    def test_forwarding_ties_and_misses(self):
        table = ForwardingTable()
        self.assertIsNone(table.lookup("1.2.3.4"))
        table.add("10.0.0.0/8", "first")
        table.add("10.0.0.0/8", "second")
        table.add("11.0.0.0/8", "separate")
        self.assertEqual(table.lookup("10.1.2.3"), "first")
        self.assertEqual(table.lookup("11.1.2.3"), "separate")
        table.add("10.1.2.3/32", "host")
        self.assertEqual(table.lookup("10.1.2.3"), "host")
        self.assertEqual(table.lookup("10.1.2.4"), "first")


class FastTableTests(unittest.TestCase):
    def test_randomized_all_prefix_lengths(self):
        rng = random.Random(20261020)
        for scenario in range(5):
            fast, reference = YourTable(), LinearTable()
            self.assertIsNone(fast.lookup(123))
            queries = []
            for i in range(330):
                plen = i % 33
                net = (rng.getrandbits(32) >> (32 - plen)) << (32 - plen)
                hop = None if i % 31 == 0 else f"hop-{i}"
                for table in (fast, reference):
                    table.add(net, plen, hop)
                    if i % 7 == 0:
                        table.add(net, plen, "duplicate-must-not-win")
                queries.extend((net, net | ((1 << (32 - plen)) - 1)))
            queries.extend(rng.getrandbits(32) for _ in range(2000))
            for addr in queries:
                self.assertEqual(fast.lookup(addr), reference.lookup(addr))
        print("13,300 comparisons: all prefix lengths, duplicate prefixes, None hops, boundaries")

    def test_add_after_lookup(self):
        t = YourTable()
        t.add(0, 0, "default")
        self.assertEqual(t.lookup(0xC0000201), "default")
        t.add(0xC0000200, 24, "network")
        t.add(0xC0000201, 32, "host")
        self.assertEqual(t.lookup(0xC0000201), "host")
        self.assertEqual(t.lookup(0xC0000202), "network")


if __name__ == "__main__":
    unittest.main()
