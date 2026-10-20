# 공개 과제 자료의 개인정보 처리

실제 측정은 보존하되 공개 저장소에는 공인 IP, PC 이름, MAC, DUID, 단말 IPv6와 원문 네트워크 설정을 게시하지 않는다. 5주차의 사설 단말·서브넷 주소는 RFC 5737 문서용 예시 주소로 일관되게 치환했다. 마스크, 호스트 비트, 주소가 바뀌었는지 여부와 분석 결과를 유지한다. 문서용 주소를 실제 측정 주소 또는 RFC 1918 주소라고 해석하면 안 된다.

현재 파일과 모든 공개 브랜치의 과거 기록에 같은 처리를 적용했다. 실제 단말 주소가 포함된 3주차 본인 DNS 캡처도 공개 기록에서 제거했다. 4·5주차의 교재 공식 TCP/DHCP trace는 타인이 이미 공개한 교육 자료이므로 출처 표기와 함께 유지한다.

원본 파일과 정리 전 Git 백업은 이 PC의 저장소 밖 `private-network-records` 폴더에만 보관한다. 이는 비공개 과제 제출용 로컬 보관이며 암호화 보관을 의미하지 않는다. 원본과 정리 전 Git bundle을 공개 저장소에 업로드하지 않는다.

`task2_myaddr.py --collect`는 앞으로 원문을 저장소 밖에 쓰고 `out/addresses.json`에는 식별자를 복사하지 않은 요약만 추가한다. 본인 DNS 캡처·분석도 저장소 밖에 저장한다. 공개 summary의 IP 존재 검사는 원본의 정확성이나 개인정보 제거를 검증하는 검사가 아니므로 별도 개인정보 회귀 검사를 둔다.

## 기존 복사본을 사용하는 경우

과거 커밋을 재작성했으므로 다른 PC에서는 기존 브랜치를 merge/push하지 말고 새로 clone한다. 기존 clone·fork·GitHub 캐시·이 채팅의 이전 메시지까지 자동으로 지워지는 것은 아니다. 과거 SHA를 통한 캐시 접근이 남으면 GitHub Support의 추가 처리가 필요할 수 있다.

[GitHub의 민감 정보 제거 안내](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
