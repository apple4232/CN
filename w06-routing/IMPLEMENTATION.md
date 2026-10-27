# Week 6 실행과 구현

제출 결과는 `out/observation.md`, `out/routing-report.md`, `out/bench.txt` 및 실제 실험 출력 파일들이다.
Task 1/3은 표준 Python만으로 실행한다. Task 2의 경로 측정은 실제 PC, FRR 실험은 그 PC의 Ubuntu WSL2에서 수행했다.

```bash
cd w06-routing
python3 task1_linkstate.py --verify
python3 bench.py --yours
python3 test_regressions.py
python3 test_tasks.py
python3 ../check.py w06
```

## 실제 OSPF 측정 재현

로컬 Linux 또는 Ubuntu WSL 안에 Docker Engine, Docker Compose v2, iptables, Python 3가 필요하다. 이 runner는 Docker daemon과 같은 Linux host에서 실행해야 하며, 별도 VM의 daemon을 쓰는 Docker Desktop 원격 연결 방식과 구분한다.

```bash
sudo python3 measure_ospf.py
```

세 전용 bridge는 모두 `internal: true`이며 외부 연결이나 Windows 네트워크 어댑터 변경을 요구하지 않는다.
Docker의 내부망 방화벽이 같은 bridge 내 OSPF link-local multicast도 차단하므로, runner는 해당 bridge/subnet 내부의 protocol 89 → 224.0.0.5/6만 임시 허용한다. 외부 연결을 여는 규칙이나 정책 변경은 하지 않는다.
종료 시 이 규칙과 실습 컨테이너·네트워크를 제거한다. 기본 hello/dead 값은 runtime JSON으로 검증하며 임의로 단축하지 않았다.

과제의 기존 `scenario.sh`는 원본 참고용이다. 그대로 사용하는 경우 다음 한계가 있다.

- root compose의 Docker Hub 이미지 태그가 없어서 같은 FRR 버전의 공식 Quay 이미지로 변경이 필요하다. 이번 runner는 `quay.io/frrouting/frr:9.1.0`을 사용하고 실제 digest를 기록했다.
- 인터페이스 번호는 네트워크 연결 순서에 따라 달라질 수 있다. runner는 주소로 역할을 식별한다.
- 기존 스크립트의 ‘표 문자열이 달라졌는가’ 비교는 route age가 변해도 반응한다. runner는 세 라우터의 실제 selected/FIB next-hop 집합이 예상 결과와 일치하는지 검사한다.
- 복구와 cost 변경도 각각 시계를 재어 before/after를 저장한다. interface-down과 silent hello loss는 서로 다른 장애 감지 실험으로 기록한다.

## 인터넷 경로와 공개본

Windows에서는 `python collect_traces.py`로 국내/해외/anycast와 추가 UMass probe를 측정했다. raw 출력은 저장소 밖 `private-network-records/collected/w06-routing/`에 보관한다. 공개본에는 중간 주소를 안정적인 별칭으로 바꾸고 실제 RTT·홉·timeout은 유지한다. `--reanalyze`는 비공개 원본을 다시 해석할 뿐 재측정하지 않는다.
현재 네트워크는 사용자 확인에 따라 집/개인 네트워크이며, 캠퍼스 이탈 홉은 미관측이다. 해외 도메인, RTT 점프, 특정 해저 케이블의 식별은 동일한 주장이 아니므로 근거가 없는 케이블 이름은 쓰지 않았다.

## SPF 계수와 tie 규칙

`bench.py`, `test_tasks.py`, `check.py`는 수정하지 않았다. 제공된 `dijkstra_table`은 기존 계산·tie 동작과 SPF counter를 유지하고, 선택적 `state` 인자로 같은 실행 중의 거리·parent만 노출한다. 별도의 숨겨진 전체 Dijkstra는 없다.
양의 비용에서 predecessor 후보는 `(distance, node name)` 순서로 확정되므로 동일 비용의 새 edge도 이 우선순위를 비교한다. 실제 개선은 이전 상태를 보존하고 변경 edge에서 시작한 영향 frontier만 갱신한다. 이번 작업에서 회당 최대 37/400개 정점만 부분 갱신했다.
선택한 tree edge의 증가/단절은 제공 함수로 전체 재계산하며, zero-cost 경계는 보수적으로 전체 계수 재계산을 사용한다. 추가 테스트는 동일 비용의 hop 변경 전파, 비연결/복구, zero-cost와 4,000개 이벤트를 reference와 비교한다.

공식 harness는 개선 쪽 wall time 안에 정답 oracle 1,000회를 추가한다. CPU 성능 비교에는 이 차이를 명시하고, `analyze_routing.py`에서 정답 검증과 별도로 동일 조건의 no-oracle 시간도 기록했다. SPF 수가 최종 채점 지표다.
