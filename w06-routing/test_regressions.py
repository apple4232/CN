"""Shortest path, exact tie behavior, incremental frontier and disconnection tests."""
import random
import unittest
import task3_reconverge as T
from task1_linkstate import dijkstra, forwarding_table


def link(graph, a, b, cost):
    graph[a][b] = cost
    graph[b][a] = cost


class RoutingTests(unittest.TestCase):
    def test_unreachable_and_source_exclusion(self):
        graph = {'s': {'a': 2}, 'a': {'s': 2}, 'island': {}}
        self.assertEqual(dijkstra(graph, 's'), {'a': 2})
        self.assertEqual(forwarding_table(graph, 's'), {'a': 'a'})
        self.assertEqual(forwarding_table(graph, 'island'), {})

    def test_equal_cost_tie_depends_on_first_predecessor_not_smallest_hop(self):
        graph = {node: {} for node in ('s', 'a', 'b', 't')}
        link(graph, 's', 'a', 4)
        link(graph, 's', 'b', 1)
        link(graph, 'a', 't', 1)
        link(graph, 'b', 't', 4)
        self.assertEqual(forwarding_table(graph, 's')['t'], 'b')
        self.assertEqual(forwarding_table(graph, 's'), T.dijkstra_table(graph, 's'))

    def test_incremental_equal_cost_switch_propagates_to_descendants(self):
        graph = {node: {} for node in ('s', 'a', 'b', 't', 'z')}
        for a, b, cost in [('s', 'a', 1), ('s', 'b', 1), ('a', 't', 3), ('b', 't', 2), ('t', 'z', 1)]:
            link(graph, a, b, cost)
        router = T.YourRouter(graph, 's')
        before = T.SPF_RUNS
        router.link_change('a', 't', 2)
        self.assertEqual(T.SPF_RUNS, before)
        self.assertEqual(router.table['z'], 'a')
        link(graph, 'a', 't', 2)
        self.assertEqual(router.table, T.dijkstra_table(graph, 's'))

    def test_disconnect_and_reconnect_component(self):
        graph = {'s': {'a': 2}, 'a': {'s': 2}, 'b': {'c': 1}, 'c': {'b': 1}}
        router = T.YourRouter(graph, 's')
        router.link_change('a', 'b', 3)
        link(graph, 'a', 'b', 3)
        self.assertEqual(router.table, T.dijkstra_table(graph, 's'))
        router.link_change('s', 'a', None)
        self.assertEqual(router.table, {})

    def test_zero_cost_links_use_conservative_counted_rebuild(self):
        graph = {'s': {'a': 0, 'b': 3}, 'a': {'s': 0, 'b': 1}, 'b': {'s': 3, 'a': 1}}
        router = T.YourRouter(graph, 's')
        before = T.SPF_RUNS
        router.link_change('s', 'b', 1)
        self.assertEqual(T.SPF_RUNS, before + 1)
        link(graph, 's', 'b', 1)
        self.assertEqual(router.table, T.dijkstra_table(graph, 's'))

    def test_negative_cost_rejected(self):
        with self.assertRaises(ValueError):
            dijkstra({'s': {'a': -1}, 'a': {}}, 's')

    def test_seeded_event_sequences_match_reference_after_every_event(self):
        for seed in range(20):
            rng = random.Random(seed)
            names = [f'n{i:02}' for i in range(20)]
            graph = {name: {} for name in names}
            for _ in range(35):
                a, b = rng.sample(names, 2)
                link(graph, a, b, rng.randint(1, 8))
            router = T.YourRouter(graph, names[0])
            for event in range(200):
                a, b = rng.sample(names, 2)
                cost = None if rng.random() < 0.35 else rng.randint(1, 8)
                router.link_change(a, b, cost)
                if cost is None:
                    graph[a].pop(b, None)
                    graph[b].pop(a, None)
                else:
                    link(graph, a, b, cost)
                self.assertEqual(router.table, T.dijkstra_table(graph, names[0]), (seed, event, a, b, cost))


if __name__ == '__main__':
    unittest.main(verbosity=2)
