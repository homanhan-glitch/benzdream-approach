# BenzDream 계약·재고 파이프라인

## 매일 하는 일

새 재고현황 엑셀을 받으면 이거 한 줄이면 끝납니다.

```bash
cd /tmp && rm -rf bd && \
git clone https://<TOKEN>@github.com/homanhan-glitch/benzdream-approach.git bd && \
cd bd && python3 pipeline/parse_contracts.py "<새 엑셀 경로>.xlsx"
```

그 다음 push:

```bash
git add contracts_web.json pipeline/contracts_daily.json pipeline/contracts_state.json.gz
git commit -m "계약 업데이트 YYYYMMDD - 모터원 +N / 타파트너 N"
git push origin main
```

여러 날짜가 밀렸으면 파일을 한꺼번에 넘기면 됩니다 (날짜순 자동 정렬, 이미 반영된 날짜는 자동 skip).

```bash
python3 pipeline/parse_contracts.py ~/Downloads/2026-08-*_차량_재고현황*.xlsx
```

## 파일 구조

| 파일 | 역할 | 주의 |
|---|---|---|
| `pipeline/parse_contracts.py` | 파서 본체 | 로직 수정 시 과거 수치도 같이 바뀌므로 신중히 |
| `pipeline/contracts_daily.json` | 일자별 집계 (**append-only**) | 절대 rebuild 하지 말 것 — 과거 엑셀 없으면 복구 불가 |
| `pipeline/contracts_state.json.gz` | 직전일 VIN 스냅샷 | diff 계산용, 1개만 유지 |
| `contracts_web.json` | 대시보드가 fetch 하는 경량 데이터 | 매 실행 시 자동 재생성 |
| `BenzDream_Inventory.html` | 영업용 대시보드 (비공개, 랜딩 미연결) | |

전체 재구축이 꼭 필요하면 (로직을 바꿨을 때만):

```bash
python3 pipeline/parse_contracts.py --bootstrap <엑셀들이_모여있는_폴더>
```

## 지표 정의

allocation 시트를 VIN 단위로 전일과 비교해서 상태 전이를 잡습니다.

| 지표 | 정의 |
|---|---|
| **모터원 신규계약** | 전국재고/미배정 → `가계약 체결`·`계약 확정`·`결제 완료` |
| **계약 확정 전환** | `가계약 체결` → `계약 확정`/`결제 완료` |
| **계약 해지** | 계약 상태 → `미배정` (VIN 교체 포함) |
| **출고 완료** | 계약 상태 VIN 이 파일에서 사라짐 |
| **타 파트너 소진** | 전국재고/미배정 VIN 이 파일에서 사라짐 = 타 딜러가 계약 |
| **신규 입고** | 직전 스냅샷에 없던 VIN = 본사 재고 오픈 |
| **DOS (소진예상일수)** | 현재 판매가능 재고 ÷ 일평균 소진량(모터원+타파트너) |
| **모터원 점유율** | 모터원 신규계약 ÷ (모터원 + 타 파트너) |

### 반드시 지킬 것

- **`배정 완료`는 계약이 아님.** 전시차·위탁 배정이라 고객 계약에서 제외합니다.
- **`재고 유형` = `예정 물량`(버추얼빈)은 소진 집계에서 제외.** 실물이 아니라 사라져도 계약이 아닙니다.
- **`gap` 필드**는 직전 스냅샷과의 달력 일수입니다. 주말·연휴가 끼면 3~4가 되므로 일평균 계산은 반드시 gap 합계로 나눕니다.
- **색상코드 변환 테이블 쓰지 말 것.** allocation 시트의 한글 색상명을 그대로 씁니다.

### 알아둘 특성

- 이 엑셀은 **모터원 관점**입니다. 타 딜러의 계약은 상태값으로 찍히지 않고 VIN 이탈로만 나타납니다.
  그래서 "타 파트너 소진"에는 본사 회수분이 일부 섞일 수 있습니다 — 방향성 지표로 보세요.
- **계약 해지 건수가 높게 나옵니다** (기간 749건 중 464건). 실제 해지보다는 같은 고객의 VIN 교체가 상당수입니다.
  순계약(신규−해지)이 실질 지표입니다.
- **G클래스 PDD 12월**은 Virtual VIN 시스템 디폴트값이라 실제 출고 시점이 아닙니다.
- 8/4처럼 신규입고가 1,000대 넘게 튀는 날은 본사 재고 오픈일입니다.

## 검증

수치가 맞는지 확인하는 항등식:

```
기초 미출고 계약 − 출고 + (신규계약 − 해지) = 기말 미출고 계약
```

2026-07-13 ~ 08-14 기준: `321 − 424 + 285 = 182` ✓
