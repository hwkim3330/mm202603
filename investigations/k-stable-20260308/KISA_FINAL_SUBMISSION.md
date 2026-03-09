# KISA Final Submission

제목: k-stable.org 금융감독원 사칭 의심 사이트 차단 검토 요청

`https://k-stable.org/` 사이트는 금융감독원, 은행연합회, 한국인공지능협회가 참여하는 공식 금융 프로젝트인 것처럼 보이게 하는 문구를 사용하고 있습니다.

동시에 다음 정황이 확인됩니다.
- 회원가입 시 전화번호, 은행명, 계좌번호 수집
- 예치, 상품가입, 투자현황 구조 제시
- 수익금 지급 사례를 홍보하는 후기 게시
- 로그인/회원가입/상품가입 API 운영 (`/api/login.php`, `/api/register.php`, `/api/join_product.php`)

공개 페이지 기준으로 기관 사칭 및 투자유인 성격이 강하므로, 피싱/사칭 사이트 여부 검토 및 필요한 기술 조치 검토를 요청드립니다.

첨부자료:
- REPORT.md
- raw/homepage.html
- raw/register.html
- raw/service.html
- raw/reviews.html
- SHA256SUMS.txt
