# Week 5 — Addresses, Subnets, NAT, DHCP

제출 저장소: <https://github.com/apple4232/computer-network-labs>

- [관찰 기록](w05-ip-nat/out/observation.md): 과제별 3줄.
- [주소·NAT·DHCP 보고서](w05-ip-nat/out/report.md), [두 네트워크의 공개 요약](w05-ip-nat/out/addresses.json), [손계산 대조](w05-ip-nat/out/subnet-checks.json).
- [공식 DHCP trace](w05-ip-nat/out/dhcp.pcapng), [원본 frame 번호별 분석](w05-ip-nat/out/dhcp-analysis.json).
- [벤치마크](w05-ip-nat/out/bench.txt), [자료구조와 메모리](w05-ip-nat/out/table-structure.json).
- [기본 검증](w05-ip-nat/out/verify.txt), [추가 검증](w05-ip-nat/out/regression-tests.txt), [전체 테스트](w05-ip-nat/out/test-tasks.txt), [제출 형식 검사](w05-ip-nat/out/check.txt).

2026-10-20 이 Windows PC에서 Home Wi-Fi와 사용자가 연결한 휴대폰 테더링을 실제 수집했다. 문서용 대체 주소/원본 마스크는 192.0.2.21/24 → 198.51.100.2/28, 게이트웨이는 192.0.2.1 → 198.51.100.1로 바뀌었고 외부 관측 주소도 달라졌다. NAT 계층 수는 주소 두 개만으로 확정하지 않았다. DHCP는 과제가 허용한 경로 B의 교재 9판 공식 trace를 분석했으며 본인 캡처로 서술하지 않았다.

Task 1은 정수 shift/mask를 사용하고, /31은 두 point-to-point endpoint를, /32는 단일 host를 usable로 반환한다. 동일 network/prefix를 중복 추가하면 첫 next hop을 유지한다. Task 3은 prefix 길이별 dict로 조회를 평균 O(L), L≤33에 제한한다. 원본 벤치마크에서 20,000개 답이 모두 일치하고 1964.3배 속도 향상으로 strong 기준을 만족했다. 별도 13,300개 비교는 모든 prefix 길이, 중복, 경계, None next hop을 포함한다.

최종 `test_tasks.py`: **7 passed, 0 failed, 1 skipped**. `check.py w05`: 통과. 전체 테스트에서 재측정한 조회 속도 향상도 1892.3배로 strong 기준을 만족했다.

`bench.py`, `test_tasks.py`, `check.py`와 기준 `LinearTable`은 원본 그대로다. Python 3.12에서 추가 패키지 없이 실행한다. tshark가 없어 제공된 DHCP 검사만 SKIP되며, `analyze_dhcp.py`에서 동일 xid의 Discover/Offer/Request/Ack를 별도로 확인했다.

```powershell
cd w05-ip-nat
python task1_forward.py --verify
python bench.py --yours
python analyze_dhcp.py
python test_regressions.py
python test_tasks.py
python ../check.py w05
```

`python task2_myaddr.py --report`로 저장된 보고서를 읽을 수 있다. 새 실측을 추가하려면 실제 네트워크에 연결한 뒤 `python task2_myaddr.py --collect "실제 연결 이름"`을 실행한다.


> Privacy: host addresses in this public copy use documentation-only substitutions; actual public IPs and device identifiers are withheld. Original measurements are retained locally outside Git.

공개본 개인정보 처리: 공인 IP와 장치 식별자는 비공개로 이동했고, 단말·서브넷 주소는 RFC 5737 예시 주소로 치환했다. 실제 주소의 RFC 1918 분류와 두 네트워크의 변화 여부는 원본에서 확인했으며 대체 주소를 실측값으로 주장하지 않는다.
