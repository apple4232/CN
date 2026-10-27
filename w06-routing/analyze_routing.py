"""Record official scoring, same-condition timing, and incremental work counts."""
import contextlib
import io
import json
from pathlib import Path
import platform
import sys
import bench
import task3_reconverge as T
from task1_linkstate import TOPOLOGY, forwarding_table, dijkstra, link_down

OUT = Path(__file__).parent / 'out'


def owned_bytes(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    total = sys.getsizeof(value)
    if isinstance(value, dict):
        total += sum(owned_bytes(k, seen) + owned_bytes(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set)):
        total += sum(owned_bytes(item, seen) for item in value)
    return total


def main():
    graph, events = bench.build()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        baseline = bench.run(T.FullRecompute, 'baseline', graph, events)
        checked = bench.run(T.YourRouter, 'yours', graph, events, check=True)
        fair = bench.run(T.YourRouter, 'yours-no-oracle', graph, events, check=False)
    print(captured.getvalue())
    router = T.YourRouter(graph, sorted(graph)[0])
    metadata_bytes = owned_bytes(router.state)
    for a, b, cost in events:
        router.link_change(a, b, cost)
    before = forwarding_table(TOPOLOGY, 'u')
    after = forwarding_table(link_down(TOPOLOGY, 'u', 'x'), 'u')
    data = {'platform': platform.platform(), 'python': platform.python_version(),
            'baseline': baseline, 'checked': checked, 'same_condition_without_oracle': fair,
            'spf_avoided_fraction': 1 - checked['spf']/baseline['spf'],
            'event_counters': router.events, 'initial_metadata_deep_bytes': metadata_bytes,
            'metadata_note': 'getsizeof recursive snapshot for distances+parents; shared values counted once; excludes graph, table, code and transient heap',
            'task1': {'costs': dijkstra(TOPOLOGY, 'u'), 'before': before, 'after': after,
                      'changed': [node for node in before if before[node] != after.get(node)],
                      'unchanged': [node for node in before if before[node] == after.get(node)]}}
    (OUT / 'routing-analysis.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
