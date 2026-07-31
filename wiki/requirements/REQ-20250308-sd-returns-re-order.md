---
req_id: REQ-20250308-sd-returns-re-order
date: 2025-03-08
requestor: 김PM
source: bench:T1
keywords: [SD, Returns, RE Order Type, Sales & Distribution]
decision: SD 출하 프로세스 내 반품 시나리오 및 RE 오더 타입 적용을 승인하되, 타 모듈(FI/MM/QM) 인터페이스 영향도 분석을 병행함.
status: approved
---

## 요건
- SD 출하 프로세스 내 반품 시나리오 및 단계 추가
- RE(Return) 오더 타입 적용 가능성 검토 및 프로세스 반영

## 결정
- SD 출하/반품 프로세스 고도화를 위한 반품 로직 추가 승인.
- RE 오더 타입 도입을 통해 반품 프로세스 표준화 추진.
- 단, 기존 REQ-SEED-1 등 기존 로직과의 정합성 및 FI/MM/QM 모듈 간 인터페이스 복잡도 증가에 대한 정밀 검토를 병행할 것.

## 영향 산출물
- SD 프로세스 설계서 (BBP): [SD 출하 프로세스 섹션] 수정/추가
- 오더 타입 정의서: RE 오더 타입 신규 정의
- 기능정의서: [SD 출하/반품] 상세 기능 정의 신규 추가

## 리스크
- 기존 SD 출하 및 반품 로직(REQ-SEED-1 등)과의 정합성 충돌 가능성
- RE 타입 적용 시 재고(Inventory) 및 회계(Accounting) 모듈 간 데이터 인터페이스 복잡도 증가

## 오픈 퀘스천
- RE 오더 타입 적용 시 사용할 구체적인 재고 이동 유형(Movement Type) 확정 필요
- 반품 처리 시 원본 출하 문서(Delivery/Order)와의 참조(Reference) 관계 정의 방식 확인 필요

## 링크
- [decisions.md](../decisions.md)
- [REQ-SEED-1](REQ-SEED-1.md)
