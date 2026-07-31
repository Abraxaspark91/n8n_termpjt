## Sheet: 계정매핑 (7행 × 5열)
| GL계정 | 계정명 | PA특성값 | 퍼널단계 | 매핑비고
| 610100 | 광고선전비 | VF_FUNNEL_AWR | 인지 | 매체비
| 610200 | 판촉비 | VF_FUNNEL_CVT | 전환 | 프로모션
| 610300 | 콘텐츠제작비 | VF_FUNNEL_INT | 관심 | 제작비
| 610400 | CRM운영비 | VF_FUNNEL_RET | 유지 | 인건비
…
## Sheet: 퍼널단계정의 (5행 × 4열)
| 단계 | 정의 | 대표비용항목 | KPI
| 인지 | 브랜드 노출 확대 단계 | 매체비, PR비 | 도달률, 브랜드인지도
| 관심 | 잠재고객 유입 단계 | 콘텐츠제작비, SEO | 체류시간, 페이지뷰
| 전환 | 구매 전환 유도 단계 | 퍼포먼스광고, 프로모션 | 전환율, CPA
| 유지 | 재구매/충성도 강화 단계 | CRM, 멤버십 | 재구매율, LTV
## Sheet: 리포트항목 (5행 × 4열)
| 리포트영역 | 항목 | 데이터소스 | 갱신주기
| 요약 | 퍼널단계별 기여이익 | CO-PA | 월 1회
| 상세 | 채널별 매체비 집행현황 | CO-PA + 매체플랫폼 | 주 1회
| 상세 | 캠페인별 전환율 | CRM | 일 1회
| 예산 | 퍼널단계별 예산 대비 집행률 | CO-PA | 월 1회
## Sheet: RTM (7행 × 10열)
| req_id | 일시 | 요청자 | 소스 | 결정 | 요약 | 영향 산출물 | 변경유형
| REQ-20260725-marketing-f | 2026-07-31T22:55:31.472+ | 경영관리 김PM | bench:S04:B00000 | 진행을 승인하고 CO-PA 리포트, Mark | Marketing Funnel 단계별 매출· | CO-PA 리포트 구조 정의서; Market | modify/add
| REQ-20260725-marketing-f | 2026-07-31T23:12:45.254+ | 경영관리 김PM | bench:S04:B00001 | 승인 페이로드에 따라 CO-PA 리포트 및  | CO-PA 리포트를 Marketing Fun | CO-PA 리포트 구조 정의서; Market | modify/add
| REQ-20260725-marketing-f | 2026-07-31T23:09:51.896+ | 경영관리 김PM | bench:S04:B00010 | CO-PA 리포트 및 관련 산출물의 갱신 완 | CO-PA 리포트를 인지·고려·전환 단계별  | CO-PA 리포트 구조 정의서; Market | modify/add
| REQ-20260725-marketing-f | 2026-07-31T14:07:11.929Z | 경영관리 김PM | bench:S04:B00100 | CO-PA 리포트 개편 및 관련 설계서·추적 | 승인 페이로드에 따라 Marketing Fu | CO-PA 리포트 구조 정의서; Market | modify; add; add; modify
…
