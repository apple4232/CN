# Week 5 observations

## Task 1
정수 shift/mask로 CIDR를 해석하고 host bit와 0–32 밖의 prefix를 거부했다. /31은 RFC 3021의 point-to-point 두 주소를 모두 usable로, /32는 단일 host로 반환하며 세 번째 값은 이 두 경우 실제 broadcast가 아닌 산술적 최상위 주소다.
10.20.30.70은 10.0.0.0/8, 10.20.0.0/16, 10.20.30.0/24, 10.20.30.64/26에 들어가므로 가장 긴 /26의 lab-rack-2를 택한다. 기본 경로 /0까지 포함하면 일치 항목은 5개다.
동일 network/prefix의 next hop 충돌은 먼저 추가한 값을 유지한다. 같은 길이지만 서로 다른 network는 정상적인 별도 경로이며, 기본 10개 검증과 /0·/30·/31·/32 및 중복·경계 테스트를 통과했다.

## Task 2
두 네트워크의 원본은 RFC 1918 사설 주소였고 단말 IP와 외부 관측 공인 IP가 달라 최소 한 NAT를 시사한다. 정확한 계층 수는 WAN/이동통신 측 주소를 확인하지 않아 미확정이다. 공개본의 192.0.2.x/198.51.100.x는 실제 주소가 아닌 문서용 대체값이며 공인 IP와 장치 식별자는 제거했다.
첫 네트워크와 테더링은 사설 IP·마스크(/24→/28)·게이트웨이·공인 IP가 모두 달랐고, 서로 다른 DHCP 주소 풀과 출구를 사용했다. 대체 주소로 나타낸 usable 범위 192.0.2.1–.254와 198.51.100.1–.14는 원래 호스트 비트 관계를 보존하며 Task 1 계산과 일치한다. 원본은 로컬 비공개 보관한다.
경로 B 공식 trace의 Discover #5는 아직 임대가 없는 0.0.0.0에서 255.255.255.255로 전송된다. Offer #12/Request #16/Ack #17은 같은 xid이고 서버 임대 86400초, T1 43200초, T2 75600초다. 서버는 제안 주소와 client MAC을 알고 broadcast flag=0인 클라이언트에 Ack를 unicast했다.

## Task 3
접두사 길이별 dict와 내림차순 검색 순서를 택했다. 5000개 경로 벤치마크의 lookup은 linear 28.498초→0.015초, 약 1964.3배이며 20000개 답이 모두 일치해 strong 기준을 만족했다(시간은 실행 환경에 따라 달라짐).
조회는 경로 수 N 대신 사용 중인 prefix 길이 수 L≤33에 비례하는 평균 O(L) 해시 조회이고, 이번 표에는 7개 길이가 있다. 저장 공간은 O(N+L)이며 이번 dict 본체만 217296 B(키·문자열 등 제외)였다. 충돌 때문에 엄밀한 hash 조회의 최악 시간은 상수라고 단정할 수 없다.
Python dict 연산은 C에서 실행되어 Python 객체를 비트마다 따라가는 trie보다 유리할 수 있다. 하드웨어는 고정 폭 비트 연산·병렬 비교·파이프라인으로 prefix 조회를 구현할 수 있어 Python의 상수 비용 비교가 그대로 적용되지 않는다. 추가 13300개 비교에서도 /0–/32·중복 prefix·None next hop·경계 주소가 일치했다.


> Privacy: host addresses in this public copy use documentation-only substitutions; actual public IPs and device identifiers are withheld. Original measurements are retained locally outside Git.
