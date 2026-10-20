# Week 5 — 실제 주소, NAT, DHCP

상태: Home Wi-Fi와 사용자가 연결한 휴대폰 테더링의 실제 주소 수집·비교, 손계산 검증, 공식 DHCP trace 분석을 완료했다. 네트워크 프로필은 각각 KT와 [REDACTED_SSID]로 확인했다.

## A. 원문에서 읽은 주소와 직접 계산

`addresses.json`의 `local.ipconfig`와 `local.route`는 이 Windows PC의 명령 출력 원문이다. 첫 수집은 2026-10-20 14:23 KST에 수행했으며 원본 수집기는 timestamp를 저장하지 않아 정확한 초 단위 시각은 기록하지 않았다. 테더링 수집은 2026-10-20T14:28:25+09:00에 완료했고 개선한 수집기가 timestamp를 저장했다. 외부 주소는 원본 지정 서비스 `https://api.ipify.org`의 실제 응답이다.

| 항목 | Home Wi-Fi | 휴대폰 테더링 |
|---|---|---|
| 인터페이스 IPv4 | 192.0.2.21 | 198.51.100.2 |
| subnet mask | 255.255.255.0 (/24) | 255.255.255.240 (/28) |
| default gateway | 192.0.2.1 | 198.51.100.1 |
| DHCP server | 192.0.2.1 | 198.51.100.1 |
| 외부 관측 IPv4 | [REDACTED_PUBLIC_A] | [REDACTED_PUBLIC_B] |

KT 주소 계산: mask의 1 bit는 8+8+8+0=24개이고 host bit는 8개다. 마지막 octet 21은 `00010101`, mask 마지막 octet은 `00000000`이므로 AND 결과는 0이다.
따라서 `192.0.2.21 AND 255.255.255.0 = 192.0.2.0`; host bit를 전부 1로 채우면 `192.0.2.255`다. 전체 2^8=256개 중 network/broadcast를 빼면 usable은 **192.0.2.1–192.0.2.254, 254개**다.
테더링의 mask 마지막 octet 240은 `11110000`이므로 /28, host bit는 4개다. 주소 마지막 octet 2=`00000010`과 AND하면 0이고 host 4 bit를 1로 채우면 15다. network는 **198.51.100.0/28**, broadcast는 **198.51.100.15**, usable은 **198.51.100.1–198.51.100.14, 14개**다.
두 손계산을 각각 `network_range("192.0.2.0/24")`, `network_range("198.51.100.0/28")`와 대조하여 모두 일치함을 확인했다. 결과는 `subnet-checks.json`에 저장했다.

게이트웨이 192.0.2.1과 198.51.100.1은 각 usable 범위 안에 있다. 테더링 default route 역시 198.51.100.1을 next hop, 198.51.100.2를 interface로 사용한다. 원문 default route는 0.0.0.0/0의 next hop을 192.0.2.1, interface를 192.0.2.21로 지정한다. 이 일반적인 Ethernet/Wi-Fi 구성에서는 PC가 ARP로 next-hop MAC을 얻어 직접 프레임을 보내야 하므로 gateway가 on-link여야 한다. 특수한 point-to-point나 별도 on-link route 같은 예외가 없는 이번 구성에 대한 설명이다.

## B. NAT 증거와 두 네트워크 비교

192.0.2.21은 RFC 1918의 192.0.2.0/16에 속하고 [REDACTED_PUBLIC_A]은 그 사설 범위가 아닌 외부 관측 주소다. 일반적인 직접 IPv4 접속이라면 주소가 달라 최소 한 NAT를 시사하지만 정확히 한 계층인지, 공유기와 통신사에서 두 번 변환하는지까지 알 수 없다. 프록시/VPN 출구를 사용하면 외부 서비스 주소는 그 출구일 수 있다는 관측 한계도 있다.

확인 방법은 (1) 공유기 WAN 주소 또는 휴대폰의 이동통신 측 IPv4를 읽고 (2) 외부 서비스의 IPv4와 비교하는 것이다. WAN이 공인 주소이며 외부 결과와 같으면 단일 NAT 설명과 맞고, WAN이 사설/공유 주소이고 외부와 다르면 상위 NAT의 증거다. traceroute에 사설 hop가 보인다는 이유만으로 NAT 개수를 세지는 않는다. 이번에는 공유기 관리 페이지나 이동통신 내부 주소를 읽지 않아 그 계층 수는 미확정이다.

100.64.0.0/10은 RFC 6598의 Shared Address Space이며 RFC 1918 주소가 아니다. 그런 주소는 CGN 배치의 단서지만 단말 주소 한 개만 보고 “반드시 두 NAT”라고 결론 낼 수 없다. 홈 NAT의 존재와 통신사 측 변환을 각각 확인해야 한다.

테더링의 198.51.100.2는 RFC 1918의 172.16.0.0/12 안에 있다. 사용자 확인 후 다른 무선 프로필로 전환하여 두 번째 기록을 수집했다. 사설 주소, mask(/24→/28), gateway/DHCP server, 공인 주소가 모두 바뀌었다. 홈 공유기와 휴대폰이 서로 다른 주소 풀에서 임대하고 다른 인터넷 출구를 사용하기 때문이다. 양쪽 모두 사설 IPv4와 NAT를 통한 인터넷 접속이라는 구조는 유지되지만, 휴대폰의 이동통신 측 IPv4를 읽지 않았으므로 테더링을 정확히 두 계층 NAT라고 단정하지 않는다.

## C. 공식 DHCP trace (경로 B)

본인 패킷 캡처가 아닌 **교재 9판 공식 `dhcp-wireshark-trace1-1.pcapng`**를 `out/dhcp.pcapng`로 원본 그대로 저장했다. 출처는 [교재 Wireshark 실습](https://gaia.cs.umass.edu/kurose_ross/wireshark.php)의 [9판 trace archive](https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces-9e.zip)이며 SHA-256은 `611169bdfdffc567d47eea2ff97d43538ec56cc516f92f2e4a468bb6f5f4419e`다.

`analyze_dhcp.py`는 pcapng/Ethernet/IPv4/UDP/BOOTP option을 표준 라이브러리로 읽는다. 원본 전체 1018 frame 중 DHCP 메시지는 6개이고 같은 transaction ID `0x56f415ed`의 완전한 DORA를 확인했다. 원본 frame 번호를 유지하여 `dhcp-analysis.json`에 저장한다.

| 메시지 | 원본 frame | IPv4 source → destination | 핵심 내용 |
|---|---:|---|---|
| Discover | 5 (9에서도 같은 xid 관측) | 0.0.0.0 → 255.255.255.255 | UDP 68→67, 아직 사용 가능한 임대 없음 |
| Offer | 12 (13에서도 관측) | 192.168.86.1 → 192.168.86.65 | yiaddr .65, lease 86400초 |
| Request | 16 | 0.0.0.0 → 255.255.255.255 | 요청 IP .65, 선택한 server .1 |
| Ack | 17 | 192.168.86.1 → 192.168.86.65 | lease 86400초, T1 43200초, T2 75600초 |

Discover의 source 0.0.0.0은 아직 자신이 사용할 IPv4를 확정하지 못했기 때문이다. 특정 DHCP 서버 주소를 아직 몰라도 같은 링크의 서버에 도달하도록 limited broadcast 255.255.255.255를 destination으로 쓴다. 이 trace에서는 broadcast flag가 0이어도 Discover 자체는 IP broadcast다.

Offer와 Ack는 unicast다. 서버는 client hardware address와 제안한 yiaddr을 알고, 클라이언트는 broadcast flag=0으로 사전 구성 상태의 unicast 수신 가능을 표시한다. 따라서 아직 Ack를 받기 전에 주소가 완전히 적용되었다고 가정하지 않아도 해당 MAC/IP로 전달할 수 있다. 다른 클라이언트가 broadcast flag를 설정하면 Ack도 broadcast일 수 있다.

**서버가 실제 제안·확인한 임대는 86400초=24시간**이다. Discover option 51의 7776000초는 클라이언트의 요청값이며 서버 임대와 혼동하지 않았다. T1은 43200초=12시간으로 임대의 절반이며, 클라이언트가 원래 서버에 DHCPREQUEST를 보내 갱신을 시도한다. 실패가 이어지면 T2=75600초=21시간에서 rebinding을 시도하고, 만료까지 갱신되지 않으면 주소 사용을 중단해야 한다.

## 출처

- [RFC 1918 — 사설 주소 범위](https://www.rfc-editor.org/rfc/rfc1918)
- [RFC 3021 — /31 point-to-point 주소](https://www.rfc-editor.org/rfc/rfc3021)
- [RFC 6598 — Shared Address Space](https://www.rfc-editor.org/rfc/rfc6598)
- [RFC 2131 — DHCP, 전송 방법과 임대 갱신](https://www.rfc-editor.org/rfc/rfc2131)

Wireshark lab trace files from J.F. Kurose and K.W. Ross,
*Computer Networking: A Top-Down Approach*, 9th ed.
<https://gaia.cs.umass.edu/kurose_ross/>
Copyright 1996-2025 J.F. Kurose, K.W. Ross. All Rights Reserved.


> Privacy: host addresses in this public copy use documentation-only substitutions; actual public IPs and device identifiers are withheld. Original measurements are retained locally outside Git.
