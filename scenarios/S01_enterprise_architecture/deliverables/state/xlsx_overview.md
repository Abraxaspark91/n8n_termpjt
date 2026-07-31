## Sheet: TCO비교 (8행 × 6열)
| 항목 | AWS | Azure | GCP | 자체구축 | 비고
| 3년 총소요비용(억원) | 42 | 45 | 40 | 38 | GPU 8기 기준
| 초기 CAPEX(억원) | 0 | 0 | 0 | 15 | 자체구축만 발생
| 연간 OPEX(억원) | 14 | 15 | 13.3 | 7.7 | 전력/인력 포함
| 확장 유연성 | 상 | 상 | 상 | 중 | 탄력 스케일링
…
## Sheet: 벤더평가 (6행 × 6열)
| 평가항목 | 가중치 | AWS점수 | Azure점수 | GCP점수 | 코멘트
| GPU 최신세대 접근성 | 0.25 | 9 | 7 | 8 | AWS p5 우선 배정
| 기존 자산 연동성 | 0.2 | 6 | 9 | 7 | Azure AD 재사용
| 비용 경쟁력 | 0.2 | 7 | 6 | 8 | GCP 커밋 유즈 할인
| 기술지원(SLA) | 0.15 | 8 | 8 | 7 | 
…
## Sheet: DB선정체크리스트 (6행 × 5열)
| 항목 | SAP HANA | Oracle | 우선순위 | 결정
| 실시간 분석 성능 | 상 | 중 | 높음 | 미정
| 기존 ERP 연동 | 상 | 중 | 높음 | 미정
| 라이선스 비용(코어당) | 고 | 중 | 중간 | 미정
| 운영 인력 숙련도 | 낮음(신규) | 높음(기존) | 중간 | 미정
…
## Sheet: RTM (16행 × 10열)
| req_id | 일시 | 요청자 | 소스 | 결정 | 요약 | 영향 산출물 | 변경유형
| REQ-20250214-cto-ai-arch | 2026-07-31T21:00:03.286+ | CTO실 | bench:S01:B00000 | 비교·선정안과 관련 산출물 업데이트를 승인한 | AWS·Azure·GCP 클라우드, GPU  | 전사 AI 아키텍처 비교·선정안; AI Se | add,modify
| REQ-20250214-cto-ai-arch | 2026-07-31T21:26:47.702+ | CTO실 | bench:S01:B00000 | AWS·Azure·GCP, GPU 자체구축· | AWS·Azure·GCP와 GPU 운영 방식 | 전사 AI 아키텍처 비교·선정안; AI Se | add,modify
| REQ-20250214-cto-ai-arch | 2026-07-31T12:53:11.248Z | CTO실 | bench:S01:B00000 | AWS·Azure·GCP, GPU 자체구축· | 승인된 전사 AI 아키텍처 비교·선정, GP | 전사 AI 아키텍처 비교·선정안; AI Se | add; add; add; add; modi
| REQ-20250214-cto-ai-arch | 2026-07-31T22:11:06.033+ | CTO실 | bench:S01:B00001 | 승인된 5개 영향 산출물과 기성 문서 3종의 | AWS·Azure·GCP 플랫폼, GPU 자 | 전사 AI 아키텍처 비교·선정안; AI Se | add/modify
…
