"""Write observations from completed real measurements and scored results."""
import json
from pathlib import Path
import re
import statistics

OUT = Path(__file__).parent / 'out'


def main():
    real = json.loads((OUT / 'ospf-measurements.json').read_text(encoding='utf-8'))
    if real['status'] != 'completed':
        raise RuntimeError('Do not report an incomplete real OSPF experiment as completed')
    analysis = json.loads((OUT / 'routing-analysis.json').read_text(encoding='utf-8'))
    traces = json.loads((OUT / 'traceroute-summary.json').read_text(encoding='utf-8'))
    event = real['events']
    down, restore, cost, silent = [event[name]['first_correct_s'] for name in
                                  ('interface_down', 'interface_restore', 'cost_10_to_100', 'silent_hello_loss')]
    official = (OUT / 'bench.txt').read_text(encoding='utf-8-sig')
    base = re.search(r'baseline\s+SPF runs\s+(\d+)\s+wall\s+([\d.]+)s', official)
    mine = re.search(r'yours\s+SPF runs\s+(\d+)\s+wall\s+([\d.]+)s', official)
    saved = 1-int(mine[1])/int(base[1])
    iface = real['interface_state_before']['r1']['interfaces'][real['interfaces']['r1_to_r2']]
    hello, dead = iface['timerMsecs']/1000, iface['timerDeadSecs']
    lines = ['# Week 6 routing measurement report', '',
             '## Environment, provenance and scope', '',
             'Part A was measured on the student Windows PC on a home/personal network, confirmed by the user. '
             'This was not a campus-network experiment. Raw public-network addresses remain outside the Git repository; '
             'traceroute.txt preserves hop numbers, RTTs and timeout markers, replacing intermediate addresses with stable labels. '
             'Public destination addresses are retained. Synthetic 10.206.x lab addresses and OSPF router IDs are not personal addresses.',
             f"Parts B/C used real FRR 9.1 containers on local Ubuntu 24.04 WSL2 ({real['runtime']}). "
             'No classmate tables or simulated convergence times were used. The host Internet adapter was not disabled.', '',
             '## Part A: paths from this PC', '',
             '| Target | Role | Observed hops | First destination-address response | Terminal interpretation |',
             '|---|---|---:|---:|---|']
    for trace in traces:
        note = ('address repeats at multiple TTLs; not an unambiguous terminal hop'
                if trace['repeated_destination_at_multiple_ttls'] else
                'destination observed once at final hop' if trace['reached'] else 'not reached within observed TTLs')
        lines.append(f"| {trace['target']} | {trace['kind']} | {len(trace['hops'])} | "
                     f"{trace['first_destination_hop'] or '—'} | {note} |")
    lines += ['', '**A2 — campus boundary:** not measured because this PC was on a home network. '
              'Hop 1 is a private-addressed local gateway; hop 2 does not answer and hop 3 is the first public-addressed reply. '
              'This brackets the observed local-network-to-public-path transition, but does not identify any campus exit.',
              '**A3 — ocean-crossing evidence:** the Stanford-domain trace ended at hop 16 with 6/9/7 ms samples. '
              'A university domain does not imply a US physical replica; this run provides no 100-ms ocean jump for that target. '
              'The additional gaia.cs.umass.edu probe shows hop 6 at 7/6/7 ms and hop 7 at 130/129/128 ms '
              '(median +122 ms), followed by persistent high RTTs. This is consistent with a long-distance/transoceanic section '
              'between the responding hops, but RTTs also include return-path and ICMP processing effects. '
              'An exact physical crossing or named submarine cable cannot be established from this trace. '
              'The destination address repeats from TTL 20 through 30 with missing samples; do not interpret that alone as a forwarding loop or a clean terminal response.',
              '**A4 — anycast:** 1.1.1.1 responded at hop 9 with 16/6/6 ms (median 6 ms). '
              'This suggests a nearby network instance, not a fixed distant location implied by the service owner. '
              'Hop count and RTT do not identify its city or data centre.',
              '**A5 — stars:** (1) a router can forward packets while suppressing, filtering or rate-limiting ICMP TTL-expired replies; '
              '(2) the probe or its return response can actually be lost, or the path can be unavailable. '
              'These are different mechanisms. Later hops responding after hop 2 demonstrates that a missing ICMP reply does not by itself mean forwarding stopped. '
              'A 300-ms per-probe timeout can also miss slow replies.', '',
              '## Part B: three real OSPF routers', '',
              '| Router | Direct subnets | OSPF-learned non-direct subnet before failure | Metric | Initial next hops |',
              '|---|---|---|---:|---|',
              '| r1 | 10.206.61.0/29, 10.206.62.0/29 | 10.206.63.0/29 | 20 | 10.206.61.3, 10.206.62.3 |',
              '| r2 | 10.206.62.0/29, 10.206.63.0/29 | 10.206.61.0/29 | 20 | 10.206.62.2, 10.206.63.3 |',
              '| r3 | 10.206.63.0/29, 10.206.61.0/29 | 10.206.62.0/29 | 20 | 10.206.61.2, 10.206.63.2 |', '',
              'These routes are marked `O>*` in route-before.txt: selected OSPF/FIB routes, not directly connected routes. '
              'In `[110/20]`, 110 is the administrative distance and 20 is the OSPF path metric. '
              'FRR installs equal-cost next hops, whereas Task 1 intentionally chooses a single next hop.', '',
              '### Timing method', '',
              'A monotonic clock starts before each actual change command. Each poll reads real OSPF JSON from all three routers, '
              'checks the expected selected/FIB next-hop sets for the non-direct prefixes, and requires two consecutive matches. '
              'Changing route ages are ignored. The 0.25-s sleep is only part of the polling interval: three Docker queries add roughly 1–2 seconds. '
              'Six seconds of quiescence before each action are excluded from the timing. '
              'These are observed table-correction times, not precise intrinsic protocol latencies or proof that every stale neighbor entry has expired.', '',
              '| Event | Last incorrect observation(s) | First correct observation(s) | Second confirmation(s) | Command completed(s) |',
              '|---|---:|---:|---:|---:|']
    for name, row in event.items():
        lines.append(f"| {name} | {row['last_incorrect_s']:.3f} | {row['first_correct_s']:.3f} | "
                     f"{row['confirmed_s']:.3f} | {row['action_completed_s']:.3f} |")
    lines += ['', f'Runtime interface JSON reports Hello={hello:g}s and Dead={dead:g}s. '
              'The supplied frr.conf leaves these at their FRR defaults. '
              '[FRR documentation: timers and hardware-assisted reachability](https://docs.frrouting.org/en/stable-9.1/ospfd.html).',
              f'**B3/B4:** r1–r2 interface-down produced correct route sets at {down:.3f}s. '
              'r1 lost its connected net_b route and learned it through r3 with metric 30; the non-direct net_c route kept only r3. '
              'r2 still displayed a stale Full neighbor entry for r1 in route-after.txt, yet its selected net_a route already used r3. '
              'An explicit local link-state notification and the resulting LSAs can repair routing before a remote dead timer expires.',
              f'To separately observe timer detection, only IP protocol 89 was dropped on the r1–r2 container interfaces while IP links stayed UP. '
              f'This silent-hello-loss test converged at {silent:.3f}s, consistent with a {dead:g}s dead interval measured from the last received hello '
              f'(approximately Dead−Hello={dead-hello:g}s through Dead, plus flooding/SPF/observation delay). '
              'It models loss of OSPF communication, not a physical unplug or a measured end-user outage.',
              f'**B5:** interface restoration took {restore:.3f}s. A returning neighbor needs hello exchange, two-way discovery, '
              'adjacency/database synchronization and route installation. Disappearance and return therefore have different waiting conditions; '
              'the exact contribution of each phase was not separately packet-timed.', '',
              '## Part C: move traffic with links still up', '',
              f'Increasing r1’s net_a cost from 10 to 100 removed the next hop through r3 for net_c and retained r2; '
              f'correction was observed at {cost:.3f}s. The before/after tables are route-cost-before.txt and route-cost-after.txt. '
              'No interface was taken down. Returning the cost to 10 restored ECMP, also recorded.',
              f'This was much faster than the {silent:.3f}s silent-failure detection because it did not wait for a dead timer. '
              f'It was not demonstrably faster than the {down:.3f}s explicit interface-down case: their difference is below polling resolution. '
              'Thus “cost changes are always faster than failures” is too broad; the failure-detection method matters.', '',
              '## Isolation and reproducibility', '',
              'All three Docker bridges remained `internal: true`. Docker’s internal-address rule also blocked OSPF link-local multicast. '
              'The runner temporarily allowed only protocol 89 to 224.0.0.5/6 between ports on the same task bridge and from that bridge’s lab subnet. '
              'External egress isolation, default policies, and the Windows Internet adapter were not weakened. '
              'These six narrowly scoped rules were removed, and the task’s containers/networks were taken down after recording results.',
              'The original Docker Hub tag frrouting/frr:v9.1.0 was unavailable. The runner uses the same version from '
              '[FRR’s official Quay registry](https://docs.frrouting.org/projects/dev-guide/en/latest/frr-release-procedure.html); '
              'the exact image digest and runtime timers are in ospf-measurements.json. '
              'vtysh.conf and LF line endings are included for Linux startup. Interface roles are resolved from actual addresses, not assumed eth-number ordering.', '',
              '## Task 3: counted work and wall-clock interpretation', '',
              f'Official benchmark: {base[1]} → {mine[1]} counted full SPF runs, {saved:.2%} avoided, zero wrong tables after all 1,000 events. '
              f'Official wall times were {base[2]}s / {mine[2]}s.',
              f"Extra state consists of distances and selected parents, O(V), alongside graph O(V+E) and table O(V). "
              f"The initial recursive getsizeof snapshot was {analysis['initial_metadata_deep_bytes']:,} B; "
              'it includes referenced key/value objects once and is not an incremental process-RSS measurement.',
              'Failures/increases outside the selected tree and non-winning improvements are skipped. '
              'Winning decreases/restorations relax only the changed-edge frontier using retained old state; '
              'used-tree failures/increases and zero-weight dependency cases use the counted dijkstra_table function. '
              'Optional metadata is collected inside that same counted SPF, not by running another hidden full Dijkstra.',
              f"There were {analysis['event_counters']['incremental_repairs']} local repairs touching "
              f"{analysis['event_counters']['incremental_vertices_total']} vertices in total, maximum "
              f"{analysis['event_counters']['incremental_vertices_max']} of the 400 vertices in one repair. "
              'This is partial repair, not rebuilding from the source while bypassing the meter.',
              'The supplied harness times baseline without an oracle but YourRouter with 1,000 additional reference checks inside its wall clock. '
              'Those checks are removed from the SPF score, not the elapsed time. Hence the official slower checked time cannot be attributed entirely to bookkeeping.',
              f"In an additional same-condition run without the oracle, baseline={analysis['baseline']['time']:.3f}s and "
              f"YourRouter={analysis['same_condition_without_oracle']['time']:.3f}s. "
              'Router suitability depends on actual SPF CPU pressure, memory, event patterns and implementation cost. '
              'Reducing full-area computation is useful under frequent updates, but does not remove failure detection/LSA delays.']
    (OUT / 'routing-report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')

    observation = f'''# Week 6 관찰 기록

## Task 1
인접 노드를 정렬하고 heap의 (거리, 노드 이름) 순서로 처리하되 동일 cost에는 기존 first hop을 유지했다. 이는 먼저 확정된 predecessor를 택하는 단일 경로 규칙이며, 실제 FRR은 동등 비용의 복수 next hop을 설치하는 ECMP를 관측했다.
u에서 w는 직접 링크 cost 5 대신 u–x–y–w의 cost 3이므로 next hop은 x다. 전달표에는 전체 경로가 아니라 실제 직접 이웃 하나만 넣었다.
u–x 단절 후 w/x/y/z의 hop이 각각 w/v/v/v로 바뀌었고 v는 그대로 v였다. 기본 검증과 비연결·동일 비용·0-cost·4,000개 추가 이벤트 비교 테스트를 통과했다.

## Task 2
집 네트워크여서 캠퍼스 이탈 홉은 관측하지 않았다. Stanford 경로에는 큰 RTT 점프가 없었고 추가 UMass probe의 hop 6→7은 중앙값 7→129ms로 장거리 구간을 시사하지만 특정 해저 케이블은 식별할 수 없다. 1.1.1.1은 9홉·중앙값 6ms였으며, *는 ICMP 응답 억제와 실제 probe/복귀 손실을 구분해야 한다.
세 FRR 모두 직접 연결되지 않은 /29를 OSPF metric 20으로 학습했다. 실제 interface-down 경로 수정은 {down:.3f}s였고, 링크는 UP인 채 hello만 차단한 경우 {silent:.3f}s여서 runtime Hello {hello:g}s / Dead {dead:g}s와 일관됐다. 전자는 로컬 link-state/LSA를 이용할 수 있으므로 dead timer를 반드시 기다리는 장애가 아니다.
링크 복구는 {restore:.3f}s로 hello와 인접·DB 재수립이 필요해 단절과 비대칭이었다. cost 10→100 변경은 {cost:.3f}s로 silent 장애보다 빨랐으나 직접 interface-down과의 차이는 관측 해상도 이하였다. raw 표·측정 구간·세부 한계는 routing-report.md와 ospf-measurements.json에 기록했다.

## Task 3
이전 거리와 parent를 O(V)로 유지하고 사용하지 않는 edge의 증가/단절, 새 최단경로·동일 비용 우선순위를 만들지 않는 감소/복구는 건너뛴다. 실제 개선은 변경 edge에서만 부분 relaxation하며 사용 중인 tree edge 증가/단절은 계수되는 전체 SPF로 재계산한다. 추가 상태의 recursive sizeof 예시는 {analysis['initial_metadata_deep_bytes']:,} B이며 순수 추가 RSS가 아니다.
공식 1,000개 이벤트 모두 정답이었고 SPF {base[1]}→{mine[1]}회({saved:.2%} 회피)로 strong이었다. 초기 1회와 tree 영향 재계산 {analysis['event_counters']['recomputed']}회는 제공 함수로 계수했고, 부분 복구 {analysis['event_counters']['incremental_repairs']}회가 건드린 노드는 총 {analysis['event_counters']['incremental_vertices_total']}개·회당 최대 {analysis['event_counters']['incremental_vertices_max']}개였다.
공식 wall은 {base[2]}→{mine[2]}초지만 개선 쪽만 1,000회 oracle 검사 시간이 포함된다. 추가 동조건 검사는 {analysis['baseline']['time']:.3f}→{analysis['same_condition_without_oracle']['time']:.3f}초였다. Python bookkeeping 비용과 하니스 검증 시간을 분리해야 하며, 실제 라우터에서는 메모리·LSA 빈도와 SPF CPU 부담을 함께 보고 선택한다.
'''
    (OUT / 'observation.md').write_text(observation, encoding='utf-8')


if __name__ == '__main__':
    main()
