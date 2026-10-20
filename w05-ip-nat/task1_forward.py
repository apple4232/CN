#!/usr/bin/env python3
"""Week 5 · Task 1 — Subnets and longest-prefix match.

Textbook §4.3.2 (IPv4 addressing, CIDR) and §4.3.3 (forwarding).

Two things a router does with every packet: work out which prefixes the
destination falls inside, and pick the longest one. The second is the whole
of "longest prefix match", and it is the reason the internet's routing table
can hold a million entries and still be answerable.

You build both, from integers up. No `ipaddress` module - that library is
exactly the thing you are supposed to understand this week.

    python3 task1_forward.py --verify
"""
import argparse


def address_int(address):
    """Strict dotted-decimal IPv4, assembled with shifts."""
    if not isinstance(address, str):
        raise ValueError("IPv4 address must be a string")
    parts = address.split(".")
    if len(parts) != 4:
        raise ValueError("IPv4 needs four octets")
    result = 0
    for part in parts:
        if not part or not part.isascii() or not part.isdecimal():
            raise ValueError("Invalid octet")
        if len(part) > 1 and part[0] == "0":
            raise ValueError("Leading zeros are ambiguous")
        value = int(part)
        if value > 255:
            raise ValueError("Octet out of range")
        result = (result << 8) | value
    return result


def address_text(value):
    return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))


def parse_cidr(cidr):
    """'163.152.6.0/24' -> (network as int, prefix length).

    Requirements: reject a prefix length outside 0-32, and reject an address
    whose host bits are set when they should not be (163.152.6.5/24 is a
    common way to write a host, but it is not a network).
    """
    if not isinstance(cidr, str) or cidr.count("/") != 1:
        raise ValueError("Expected address/prefix")
    address, length = cidr.split("/")
    if not length or not length.isascii() or not length.isdecimal():
        raise ValueError("Prefix must be 0 through 32")
    prefix = int(length)
    if not 0 <= prefix <= 32:
        raise ValueError("Prefix must be 0 through 32")
    network = address_int(address)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    if network & mask != network:
        raise ValueError("Host bits must be zero")
    return network, prefix


def network_range(cidr):
    """'163.152.6.0/24' -> (first usable, last usable, broadcast) as strings.

    Careful at the edges. /31 and /32 do not have a usable host range in the
    ordinary sense - decide what you return and say so in observation.md.
    """
    network, prefix = parse_cidr(cidr)
    upper = network | ((1 << (32 - prefix)) - 1)
    # /31: both point-to-point endpoints; /32: the single host.
    # The third value is the arithmetic upper address, not an operative
    # directed broadcast on /31 or /32.
    first, last = (network, upper) if prefix >= 31 else (network + 1, upper - 1)
    return tuple(address_text(value) for value in (first, last, upper))


class ForwardingTable:
    """Longest-prefix-match forwarding.

    add(cidr, next_hop)  ·  lookup(address) -> next_hop or None

    The default route 0.0.0.0/0 matches everything and is the shortest prefix,
    so it must lose to any other match. Different networks may share a length;
    duplicate identical network/prefix entries retain the first next hop.
    """

    def __init__(self):
        self.entries = []

    def add(self, cidr, next_hop):
        network, prefix = parse_cidr(cidr)
        self.entries.append((network, prefix, next_hop))

    def lookup(self, address):
        value = address_int(address)
        best_length, best_hop = -1, None
        for network, prefix, hop in self.entries:
            mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
            if value & mask == network and prefix > best_length:
                best_length, best_hop = prefix, hop
        return best_hop  # Equal identical prefixes: first insertion wins.


# ------------------------------------------------------------------- harness
RANGE_CASES = [
    ("192.168.0.0/24",  "192.168.0.1",   "192.168.0.254",  "192.168.0.255"),
    ("10.0.0.0/8",      "10.0.0.1",      "10.255.255.254", "10.255.255.255"),
    ("172.16.32.0/20",  "172.16.32.1",   "172.16.47.254",  "172.16.47.255"),
    ("203.0.113.64/26", "203.0.113.65",  "203.0.113.126",  "203.0.113.127"),
]

TABLE = [
    ("0.0.0.0/0",       "default-gw"),
    ("10.0.0.0/8",      "campus"),
    ("10.20.0.0/16",    "eng-building"),
    ("10.20.30.0/24",   "lab-floor"),
    ("10.20.30.64/26",  "lab-rack-2"),
    ("192.168.1.0/24",  "home"),
]

LOOKUP_CASES = [
    ("10.20.30.70",   "lab-rack-2"),     # inside all four 10.x entries
    ("10.20.30.10",   "lab-floor"),
    ("10.20.99.1",    "eng-building"),
    ("10.99.0.1",     "campus"),
    ("8.8.8.8",       "default-gw"),
    ("192.168.1.77",  "home"),
]


def verify():
    fails = 0
    for cidr, first, last, bcast in RANGE_CASES:
        try:
            got = network_range(cidr)
        except NotImplementedError:
            print("  network_range is still a stub"); return 1
        except Exception as e:
            print(f"  FAIL  {cidr:<18} raised {e!r}"); fails += 1; continue
        ok = tuple(got) == (first, last, bcast)
        print(f"  {'ok  ' if ok else 'FAIL'}  {cidr:<18} {got}")
        fails += not ok

    t = ForwardingTable()
    try:
        for cidr, hop in TABLE:
            t.add(cidr, hop)
    except NotImplementedError:
        print("  ForwardingTable is still a stub"); return 1

    for addr, expect in LOOKUP_CASES:
        got = t.lookup(addr)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {addr:<16} -> {got}  (want {expect})")
        fails += not ok

    print(f"\n  {len(RANGE_CASES) + len(LOOKUP_CASES) - fails}"
          f"/{len(RANGE_CASES) + len(LOOKUP_CASES)} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
