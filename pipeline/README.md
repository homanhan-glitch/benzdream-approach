# BenzDream 계약·재고 파이프라인

## 2026-09-21 커미션넘버 대조 전환

신규 원본은 VIN이 없어도 `커미션 번호`로 대조한다. 번호 누락 또는 정규화 후 중복은 중단한다. 숫자 셀의 `.0`은 제거하며 문자열 앞자리 0은 보존한다. 판매 상태·재고 유형이 없는 행은 미확인으로 유지한다.

기존 VIN 스냅샷은 이전 원본의 VIN/커미션 대응으로 **키만** 변환한다. 기존 일별 집계와 스냅샷 상태값은 보존한다. 대응 누락·충돌·중복이 있으면 아무 집계도 저장하지 않는다. 최초 전환 때 이전 원본을 지정한다:

```text
python pipeline/parse_contracts.py --identity-source <직전원본.xlsx> <신규원본.xlsx>
```

원본을 여러 개 지정하려면 `--identity-source`를 반복한다. 검증되지 않은 모델·색상 유사성으로 차량을 연결하지 않는다. 전환 후 `identity_key=commission`을 저장하며 `vins` 필드명은 호환을 위해 유지한다. 고객용도 커미션넘버로 식별·중복 제거하며 공개 결과에 차량 번호를 추가하지 않는다.

검증: `python -m unittest discover -s pipeline -p test_vehicle_identity.py`


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
| **사전계약** | `재고 유형` == `예정 물량`(버추얼빈). 실물 미입고 배정 예정분 |
| **DOS (소진예상일수)** | 현재 판매가능 재고 ÷ 일평균 소진량(모터원+타파트너) |
| **모터원 점유율** | 모터원 신규계약 ÷ (모터원 + 타 파트너) |

### 반드시 지킬 것

- **`배정 완료`는 계약이 아님.** 전시차·위탁 배정이라 고객 계약에서 제외합니다.
- **`재고 유형` = `예정 물량`(버추얼빈)은 소진(`nat_other`) 집계에서 제외.** 실물이 아니라 사라져도 타 딜러 계약이 아닙니다.
  단, 예정 물량의 **계약 전이는 잡습니다** — `pre_new` 로 별도 집계되고 `mo_new` 에도 포함됩니다.
  현황은 `web.pre` (모델별 총/계약/잔여/PDD/전시장), 추이는 `web.pre_daily`.
- **`gap` 필드**는 직전 스냅샷과의 달력 일수입니다. 주말·연휴가 끼면 3~4가 되므로 일평균 계산은 반드시 gap 합계로 나눕니다.
- **색상코드 변환 테이블 쓰지 말 것.** allocation 시트의 한글 색상명을 그대로 씁니다.

### 알아둘 특성

- 이 엑셀은 **모터원 관점**입니다. 타 딜러의 계약은 상태값으로 찍히지 않고 VIN 이탈로만 나타납니다.
  그래서 "타 파트너 소진"에는 본사 회수분이 일부 섞일 수 있습니다 — 방향성 지표로 보세요.
- **계약 해지 건수가 높게 나옵니다** (기간 749건 중 464건). 실제 해지보다는 같은 고객의 VIN 교체가 상당수입니다.
  순계약(신규−해지)이 실질 지표입니다.
- **G클래스 PDD 12월**은 Virtual VIN 시스템 디폴트값이라 실제 출고 시점이 아닙니다.
- **MY27 GLC(300 AMG Line/+)·GLC 일렉트릭은 이 파일에 안 들어옵니다.** 2026-07-13~08-14 24일 전체 확인 결과 0건.
  본사 오더 시스템에만 있고 배정 단계로 내려오지 않은 상태라, 재고현황 엑셀로는 추적이 불가능합니다.
  파일에 잡히는 MY27은 EQA·GLA·G 450 d·S클래스·Maybach 뿐입니다 (8/14 기준 107대).
- 8/4처럼 신규입고가 1,000대 넘게 튀는 날은 본사 재고 오픈일입니다.

## 검증

수치가 맞는지 확인하는 항등식:

```
기초 미출고 계약 − 출고 + (신규계약 − 해지) = 기말 미출고 계약
```

2026-07-13 ~ 08-14 기준: `321 − 424 + 285 = 182` ✓


## BenzDream_Stock.html (고객용 재고표) 갱신

`build_stock.py`가 `parse_inventory_v3.build_snapshot()`을 호출해 `latest_stock.json`을 생성합니다.
(수량은 노출하지 않지만 latest_stock.json 자체에는 색상별 대수가 들어있음 — Stock.html은 배지만 렌더링)

```bash
python3 pipeline/build_stock.py "<새 엑셀 경로>" latest_stock.json
```

- G클래스는 `build_snapshot()`이 이미 별도 분리하므로 자동 제외.
- Virtual VIN(예정 물량/버추얼빈)은 `car_status`가 '판매 가능'이 되지 않으므로 자동 제외.
- 새 내장/외장 색상이 나오면 `BenzDream_Stock.html`의 `EXT_CLR`/`INT_CLR` JS 객체에 hex 추가 (없으면 회색 `#ccc`로 폴백, 깨지지는 않음).
- 커밋 대상에 `latest_stock.json`도 반드시 포함.
