# Week 6 routing measurement report

## Environment, provenance and scope

Part A was measured on the student Windows PC on a home/personal network, confirmed by the user. This was not a campus-network experiment. Raw public-network addresses remain outside the Git repository; traceroute.txt preserves hop numbers, RTTs and timeout markers, replacing intermediate addresses with stable labels. Public destination addresses are retained. Synthetic 10.206.x lab addresses and OSPF router IDs are not personal addresses.
Parts B/C used real FRR 9.1 containers on local Ubuntu 24.04 WSL2 (Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39). No classmate tables or simulated convergence times were used. The host Internet adapter was not disabled.

## Part A: paths from this PC

| Target | Role | Observed hops | First destination-address response | Terminal interpretation |
|---|---|---:|---:|---|
| www.korea.ac.kr | domestic | 30 | — | not reached within observed TTLs |
| www.stanford.edu | overseas-site | 16 | 16 | destination observed once at final hop |
| 1.1.1.1 | anycast | 9 | 9 | destination observed once at final hop |
| gaia.cs.umass.edu | additional-overseas-probe | 30 | 20 | address repeats at multiple TTLs; not an unambiguous terminal hop |

**A2 — campus boundary:** not measured because this PC was on a home network. Hop 1 is a private-addressed local gateway; hop 2 does not answer and hop 3 is the first public-addressed reply. This brackets the observed local-network-to-public-path transition, but does not identify any campus exit.
**A3 — ocean-crossing evidence:** the Stanford-domain trace ended at hop 16 with 6/9/7 ms samples. A university domain does not imply a US physical replica; this run provides no 100-ms ocean jump for that target. The additional gaia.cs.umass.edu probe shows hop 6 at 7/6/7 ms and hop 7 at 130/129/128 ms (median +122 ms), followed by persistent high RTTs. This is consistent with a long-distance/transoceanic section between the responding hops, but RTTs also include return-path and ICMP processing effects. An exact physical crossing or named submarine cable cannot be established from this trace. The destination address repeats from TTL 20 through 30 with missing samples; do not interpret that alone as a forwarding loop or a clean terminal response.
**A4 — anycast:** 1.1.1.1 responded at hop 9 with 16/6/6 ms (median 6 ms). This suggests a nearby network instance, not a fixed distant location implied by the service owner. Hop count and RTT do not identify its city or data centre.
**A5 — stars:** (1) a router can forward packets while suppressing, filtering or rate-limiting ICMP TTL-expired replies; (2) the probe or its return response can actually be lost, or the path can be unavailable. These are different mechanisms. Later hops responding after hop 2 demonstrates that a missing ICMP reply does not by itself mean forwarding stopped. A 300-ms per-probe timeout can also miss slow replies.

## Part B: three real OSPF routers

| Router | Direct subnets | OSPF-learned non-direct subnet before failure | Metric | Initial next hops |
|---|---|---|---:|---|
| r1 | 10.206.61.0/29, 10.206.62.0/29 | 10.206.63.0/29 | 20 | 10.206.61.3, 10.206.62.3 |
| r2 | 10.206.62.0/29, 10.206.63.0/29 | 10.206.61.0/29 | 20 | 10.206.62.2, 10.206.63.3 |
| r3 | 10.206.63.0/29, 10.206.61.0/29 | 10.206.62.0/29 | 20 | 10.206.61.2, 10.206.63.2 |

These routes are marked `O>*` in route-before.txt: selected OSPF/FIB routes, not directly connected routes. In `[110/20]`, 110 is the administrative distance and 20 is the OSPF path metric. FRR installs equal-cost next hops, whereas Task 1 intentionally chooses a single next hop.

### Timing method

A monotonic clock starts before each actual change command. Each poll reads real OSPF JSON from all three routers, checks the expected selected/FIB next-hop sets for the non-direct prefixes, and requires two consecutive matches. Changing route ages are ignored. The 0.25-s sleep is only part of the polling interval: three Docker queries add roughly 1–2 seconds. Six seconds of quiescence before each action are excluded from the timing. These are observed table-correction times, not precise intrinsic protocol latencies or proof that every stale neighbor entry has expired.

| Event | Last incorrect observation(s) | First correct observation(s) | Second confirmation(s) | Command completed(s) |
|---|---:|---:|---:|---:|
| interface_down | 0.000 | 2.100 | 4.170 | 0.403 |
| interface_restore | 6.000 | 7.841 | 9.821 | 0.470 |
| cost_10_to_100 | 0.000 | 2.134 | 4.165 | 0.526 |
| cost_restore | 0.000 | 2.231 | 4.183 | 0.582 |
| silent_hello_loss | 37.880 | 39.528 | 41.283 | 0.796 |
| silent_restore | 17.160 | 18.950 | 20.910 | 0.772 |

Runtime interface JSON reports Hello=10s and Dead=40s. The supplied frr.conf leaves these at their FRR defaults. [FRR documentation: timers and hardware-assisted reachability](https://docs.frrouting.org/en/stable-9.1/ospfd.html).
**B3/B4:** r1–r2 interface-down produced correct route sets at 2.100s. r1 lost its connected net_b route and learned it through r3 with metric 30; the non-direct net_c route kept only r3. r2 still displayed a stale Full neighbor entry for r1 in route-after.txt, yet its selected net_a route already used r3. An explicit local link-state notification and the resulting LSAs can repair routing before a remote dead timer expires.
To separately observe timer detection, only IP protocol 89 was dropped on the r1–r2 container interfaces while IP links stayed UP. This silent-hello-loss test converged at 39.528s, consistent with a 40s dead interval measured from the last received hello (approximately Dead−Hello=30s through Dead, plus flooding/SPF/observation delay). It models loss of OSPF communication, not a physical unplug or a measured end-user outage.
**B5:** interface restoration took 7.841s. A returning neighbor needs hello exchange, two-way discovery, adjacency/database synchronization and route installation. Disappearance and return therefore have different waiting conditions; the exact contribution of each phase was not separately packet-timed.

## Part C: move traffic with links still up

Increasing r1’s net_a cost from 10 to 100 removed the next hop through r3 for net_c and retained r2; correction was observed at 2.134s. The before/after tables are route-cost-before.txt and route-cost-after.txt. No interface was taken down. Returning the cost to 10 restored ECMP, also recorded.
This was much faster than the 39.528s silent-failure detection because it did not wait for a dead timer. It was not demonstrably faster than the 2.100s explicit interface-down case: their difference is below polling resolution. Thus “cost changes are always faster than failures” is too broad; the failure-detection method matters.

## Isolation and reproducibility

All three Docker bridges remained `internal: true`. Docker’s internal-address rule also blocked OSPF link-local multicast. The runner temporarily allowed only protocol 89 to 224.0.0.5/6 between ports on the same task bridge and from that bridge’s lab subnet. External egress isolation, default policies, and the Windows Internet adapter were not weakened. These six narrowly scoped rules were removed, and the task’s containers/networks were taken down after recording results.
The original Docker Hub tag frrouting/frr:v9.1.0 was unavailable. The runner uses the same version from [FRR’s official Quay registry](https://docs.frrouting.org/projects/dev-guide/en/latest/frr-release-procedure.html); the exact image digest and runtime timers are in ospf-measurements.json. vtysh.conf and LF line endings are included for Linux startup. Interface roles are resolved from actual addresses, not assumed eth-number ordering.

## Task 3: counted work and wall-clock interpretation

Official benchmark: 1001 → 212 counted full SPF runs, 78.82% avoided, zero wrong tables after all 1,000 events. Official wall times were 3.36s / 3.53s.
Extra state consists of distances and selected parents, O(V), alongside graph O(V+E) and table O(V). The initial recursive getsizeof snapshot was 44,770 B; it includes referenced key/value objects once and is not an incremental process-RSS measurement.
Failures/increases outside the selected tree and non-winning improvements are skipped. Winning decreases/restorations relax only the changed-edge frontier using retained old state; used-tree failures/increases and zero-weight dependency cases use the counted dijkstra_table function. Optional metadata is collected inside that same counted SPF, not by running another hidden full Dijkstra.
There were 134 local repairs touching 458 vertices in total, maximum 37 of the 400 vertices in one repair. This is partial repair, not rebuilding from the source while bypassing the meter.
The supplied harness times baseline without an oracle but YourRouter with 1,000 additional reference checks inside its wall clock. Those checks are removed from the SPF score, not the elapsed time. Hence the official slower checked time cannot be attributed entirely to bookkeeping.
In an additional same-condition run without the oracle, baseline=2.589s and YourRouter=0.635s. Router suitability depends on actual SPF CPU pressure, memory, event patterns and implementation cost. Reducing full-area computation is useful under frequent updates, but does not remove failure detection/LSA delays.
