# Week 6 관찰 기록

## Task 1
인접 노드를 정렬하고 heap의 (거리, 노드 이름) 순서로 처리하되 동일 cost에는 기존 first hop을 유지했다. 이는 먼저 확정된 predecessor를 택하는 단일 경로 규칙이며, 실제 FRR은 동등 비용의 복수 next hop을 설치하는 ECMP를 관측했다.
u에서 w는 직접 링크 cost 5 대신 u–x–y–w의 cost 3이므로 next hop은 x다. 전달표에는 전체 경로가 아니라 실제 직접 이웃 하나만 넣었다.
u–x 단절 후 w/x/y/z의 hop이 각각 w/v/v/v로 바뀌었고 v는 그대로 v였다. 기본 검증과 비연결·동일 비용·0-cost·4,000개 추가 이벤트 비교 테스트를 통과했다.

## Task 2
집 네트워크여서 캠퍼스 이탈 홉은 관측하지 않았다. Stanford 경로에는 큰 RTT 점프가 없었고 추가 UMass probe의 hop 6→7은 중앙값 7→129ms로 장거리 구간을 시사하지만 특정 해저 케이블은 식별할 수 없다. 1.1.1.1은 9홉·중앙값 6ms였으며, *는 ICMP 응답 억제와 실제 probe/복귀 손실을 구분해야 한다.
세 FRR 모두 직접 연결되지 않은 /29를 OSPF metric 20으로 학습했다. 실제 interface-down 경로 수정은 2.100s였고, 링크는 UP인 채 hello만 차단한 경우 39.528s여서 runtime Hello 10s / Dead 40s와 일관됐다. 전자는 로컬 link-state/LSA를 이용할 수 있으므로 dead timer를 반드시 기다리는 장애가 아니다.
링크 복구는 7.841s로 hello와 인접·DB 재수립이 필요해 단절과 비대칭이었다. cost 10→100 변경은 2.134s로 silent 장애보다 빨랐으나 직접 interface-down과의 차이는 관측 해상도 이하였다. raw 표·측정 구간·세부 한계는 routing-report.md와 ospf-measurements.json에 기록했다.

## Task 3
이전 거리와 parent를 O(V)로 유지하고 사용하지 않는 edge의 증가/단절, 새 최단경로·동일 비용 우선순위를 만들지 않는 감소/복구는 건너뛴다. 실제 개선은 변경 edge에서만 부분 relaxation하며 사용 중인 tree edge 증가/단절은 계수되는 전체 SPF로 재계산한다. 추가 상태의 recursive sizeof 예시는 44,770 B이며 순수 추가 RSS가 아니다.
공식 1,000개 이벤트 모두 정답이었고 SPF 1001→212회(78.82% 회피)로 strong이었다. 초기 1회와 tree 영향 재계산 211회는 제공 함수로 계수했고, 부분 복구 134회가 건드린 노드는 총 458개·회당 최대 37개였다.
공식 wall은 3.36→3.53초지만 개선 쪽만 1,000회 oracle 검사 시간이 포함된다. 추가 동조건 검사는 2.589→0.635초였다. Python bookkeeping 비용과 하니스 검증 시간을 분리해야 하며, 실제 라우터에서는 메모리·LSA 빈도와 SPF CPU 부담을 함께 보고 선택한다.
