#!/usr/bin/env python3
"""Week 6 · Task 3 — Reconverge without recomputing the world.

Textbook §5.2.1, §5.3.

A link flaps. Every router in the area has to decide what changed. `FullRecompute`
does the honest thing: throw the table away and run Dijkstra again, from scratch,
for every event. It is correct and it is what the first implementations did.

It is also why a single flapping link in a large area used to melt the CPU of
every router that could see it.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first. `bench.py` compares your table against a full recompute after
**every single event**. A router that is fast and wrong black-holes traffic.
"""
import heapq

# The harness counts how many times you run a full SPF. This is the score:
# wall-clock time in Python says more about dictionary overhead than about
# routing, but "how many times did the CPU have to recompute the world" is
# exactly what melted real routers.
SPF_RUNS = 0


def dijkstra_table(graph, source, *, state=None):
    """Reference shortest-path-first. Returns {destination: first_hop}.

    Use THIS function whenever you need a full recompute. Rolling your own to
    dodge the counter is not an optimisation, it is cheating the meter.
    """
    global SPF_RUNS
    SPF_RUNS += 1
    best = {source: (0, None)}
    parents = {} if state is not None else None
    pq, done = [(0, source, None)], set()
    while pq:
        cost, node, first_hop = heapq.heappop(pq)
        if node in done:
            continue
        done.add(node)
        best[node] = (cost, first_hop)
        for nbr, w in sorted(graph[node].items()):
            if nbr in done:
                continue
            hop = nbr if node == source else first_hop
            if cost + w < best.get(nbr, (float("inf"), None))[0]:
                best[nbr] = (cost + w, hop)
                if parents is not None:
                    parents[nbr] = node
                heapq.heappush(pq, (cost + w, nbr, hop))
    # Expose metadata from THIS counted SPF; no second Dijkstra is performed.
    if state is not None:
        state.clear()
        state.update(distances={node: best[node][0] for node in done},
                     parents={node: parent for node, parent in parents.items() if node in done})
    return {d: h for d, (_, h) in best.items() if d != source and h}


class FullRecompute:
    """On every event, forget everything and run SPF again."""

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self.table = dijkstra_table(self.graph, source)

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
        self.table = dijkstra_table(self.graph, self.source)


class YourRouter:
    """Your router. Same two methods, same table, less work per event.

    What is actually true after one link changes:

      * most destinations are not affected at all
      * a link that is not on any of your shortest paths, going *up*, can only
        matter if it creates something shorter
      * a link going *down* only matters if you were using it

    Deciding which of those applies, cheaply, without getting it wrong, is the
    task. Getting it wrong is worse than being slow - the harness will catch it
    on the event where it happens.
    """

    def __init__(self, graph, source):
        if any(cost < 0 for edges in graph.values() for cost in edges.values()):
            raise ValueError('nonnegative costs required')
        self.graph = {node: dict(edges) for node, edges in graph.items()}
        self.source = source
        self.state = {}
        self.zero_arcs = sum(cost == 0 for edges in self.graph.values() for cost in edges.values())
        self.events = {'noop': 0, 'unused_increase_or_failure': 0,
                       'non_improving_decrease_or_restore': 0, 'recomputed': 0,
                       'incremental_repairs': 0, 'incremental_vertices_total': 0,
                       'incremental_vertices_max': 0}
        self._recompute()

    def _recompute(self):
        self.table = dijkstra_table(self.graph, self.source, state=self.state)

    def _repair_decrease(self, a, b, cost):
        """Relax only the changed edge and its affected frontier, retaining old SPF state.

        No source-rooted rebuild and no clearing of distances/parents/table.
        A used-edge increase or failure still uses the counted reference SPF.
        """
        distances, parents = self.state['distances'], self.state['parents']
        queue, touched = [], set()

        def offer(parent, node, candidate):
            if parent not in distances or node == self.source:
                return
            current = distances.get(node, float('inf'))
            hop = node if parent == self.source else self.table[parent]
            old_parent = parents.get(node)
            better = candidate < current
            if candidate == current and old_parent is not None:
                better = ((distances[parent], parent) < (distances[old_parent], old_parent)
                          or (parent == old_parent and self.table.get(node) != hop))
            if better:
                distances[node] = candidate
                parents[node] = parent
                self.table[node] = hop
                heapq.heappush(queue, (candidate, node))

        for parent, node in ((a, b), (b, a)):
            if parent in distances:
                offer(parent, node, distances[parent] + cost)
        while queue:
            distance, node = heapq.heappop(queue)
            if distance != distances[node]:
                continue
            touched.add(node)
            for neighbor, weight in sorted(self.graph[node].items()):
                offer(node, neighbor, distance + weight)
        self.events['incremental_repairs'] += 1
        self.events['incremental_vertices_total'] += len(touched)
        self.events['incremental_vertices_max'] = max(self.events['incremental_vertices_max'], len(touched))

    def link_change(self, a, b, cost):
        if cost is not None and cost < 0:
            raise ValueError('nonnegative costs required')
        old = self.graph.get(a, {}).get(b)
        if old == cost:
            self.events['noop'] += 1
            return
        had_zero = self.zero_arcs > 0
        if old == 0:
            self.zero_arcs -= 2
        if cost == 0:
            self.zero_arcs += 2
        self.graph.setdefault(a, {})
        self.graph.setdefault(b, {})
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
        parents = self.state['parents']
        distances = self.state['distances']
        # Positive weights give a deterministic settlement order by distance/name.
        # For zero-weight tie dependencies, conservatively use the counted SPF.
        if had_zero or self.zero_arcs:
            need_spf = True
        elif old is not None and (cost is None or cost > old):
            need_spf = parents.get(a) == b or parents.get(b) == a
            if not need_spf:
                self.events['unused_increase_or_failure'] += 1
        else:
            def could_win(start, end):
                if start not in distances:
                    return False
                candidate = distances[start] + cost
                current = distances.get(end, float('inf'))
                if candidate != current:
                    return candidate < current
                parent = parents.get(end)
                # Positive weights settle all predecessor candidates first.
                # The first equal-distance candidate is the predecessor with
                # the smallest (distance, name), not necessarily smallest hop.
                return parent is not None and (distances[start], start) < (distances[parent], parent)
            need_spf = could_win(a, b) or could_win(b, a)
            if not need_spf:
                self.events['non_improving_decrease_or_restore'] += 1
            else:
                self._repair_decrease(a, b, cost)
                return
        if need_spf:
            self.events['recomputed'] += 1
            self._recompute()
