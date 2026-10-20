#!/usr/bin/env python3
"""Week 5 · Task 3 — Make longest-prefix match fast.

Textbook §4.3.3.

`LinearTable` is correct and it is what you probably wrote in Task 1: keep the
prefixes in a list, check every one, remember the longest that matched. On six
entries that is fine. A real router holds close to a million, and it has to
answer while the packet is still in the buffer.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first: `bench.py` checks every one of your answers against the
linear table. A fast router that forwards to the wrong next hop is not a
router, it is an outage.
"""


class LinearTable:
    """Correct, and slow in the obvious way."""

    def __init__(self):
        self.entries = []                     # (prefix_len, network, next_hop)

    def add(self, network, prefix_len, next_hop):
        self.entries.append((prefix_len, network, next_hop))

    def lookup(self, address):
        best = None
        for plen, net, hop in self.entries:
            mask = (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF
            if address & mask == net and (best is None or plen > best[0]):
                best = (plen, hop)
        return best[1] if best else None


class YourTable:
    """Your table. Same three methods, same answers, fewer comparisons.

    Addresses and networks are plain 32-bit ints here - no strings, no parsing,
    so that the benchmark measures your lookup and nothing else.

    Two directions worth knowing about before you pick one:

      * group by prefix length. There are only 33 possible lengths, and you can
        ask them in an order that lets you stop early.
      * walk the address one bit at a time. Each bit takes you to at most one
        child, so the work is bounded by the address width, not by the table size.

    The second is what hardware does. The first is easier and often enough.
    Say which you chose and what it cost you in memory.
    """

    def __init__(self):
        self.groups = {}
        self.search = ()
        self.missing = object()

    def add(self, network, prefix_len, next_hop):
        if not isinstance(prefix_len, int) or not 0 <= prefix_len <= 32:
            raise ValueError("Prefix must be 0 through 32")
        if not isinstance(network, int) or not 0 <= network <= 0xFFFFFFFF:
            raise ValueError("Network must be an unsigned 32-bit integer")
        mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
        if network & mask != network:
            raise ValueError("Host bits must be zero")
        if prefix_len not in self.groups:
            self.groups[prefix_len] = {}
            self.search = tuple(
                ((0xFFFFFFFF << (32 - p)) & 0xFFFFFFFF, self.groups[p].get)
                for p in sorted(self.groups, reverse=True)
            )
        # The reference retains the first next hop for duplicate prefixes.
        self.groups[prefix_len].setdefault(network, next_hop)

    def lookup(self, address):
        missing = self.missing
        for mask, get in self.search:
            hop = get(address & mask, missing)
            if hop is not missing:
                return hop
        return None
