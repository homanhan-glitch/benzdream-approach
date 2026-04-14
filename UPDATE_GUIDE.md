# BenzDream 재고 자동 업데이트 지침

매일 받게 되는 메르세데스-벤츠 재고현황 xlsx를 파이프라인에 통과시켜 BenzDream 사이트의 재고표와 분석 대시보드를 자동 갱신하는 절차입니다. 이 파일을 Claude (Cowork)에게 보여주면 전체 절차를 바로 실행할 수 있어요.

---

## 0. 저장소·배포 정보

- **Repo**: `homanhan-glitch/benzdream-approach`
- **Pages**: https://homanhan-glitch.github.io/benzdream-approach/
  - 고객용 재고표: `/BenzDream_Stock.html`
  - 내부 분석 대시보드: `/BenzDream_Inventory.html`
- **Git commit 계정**: `benzdream@auto.com` / `BenzDream Claude`
- **GitHub PAT**: (repo에 커밋 금지 — GitHub secret scanning이 차단함. Claude에게 지침 전달 시 별도 메시지로 토큰 붙여넣기)
- **로컬 저장소**: `/sessions/sleepy-friendly-tesla/benzdream-approach`

---

## 1. 일일 업데이트 전체 흐름

1. 새 재고현황 xlsx 파일을 다운로드 폴더에 저장 (파일명은 `YYYY-MM-DD_차량_재고현황*.xlsx` 형태)
2. 아래 명령을 순서대로 실행
3. 결과 확인 후 커밋·푸시

```bash
cd /sessions/sleepy-friendly-tesla/benzdream-approach

# (1) 스냅샷 생성 — 날짜만 바꿔서 실행
python3 pipeline/build_snapshot.py \
  "/sessions/sleepy-friendly-tesla/mnt/Downloads/2026-MM-DD_차량_재고현황*.xlsx" \
  2026-MM-DD

# (2) 히스토리 재생성 (모든 스냅샷 자동 집계)
python3 pipeline/build_history.py

# (3) 커밋 + 푸시
git add pipeline/snapshots/2026-MM-DD.json inventory_history.json latest_stock.json
git -c user.email="benzdream@auto.com" -c user.name="BenzDream Claude" \
    -c commit.gpgsign=false commit -m "재고 업데이트 2026-MM-DD"
git push "https://homanhan-glitch:<TOKEN>@github.com/homanhan-glitch/benzdream-approach.git" main
```

> xlsx 파일명에 공백(`차량 재고현황`)이 들어가 있으면 반드시 쌍따옴표로 감싸세요.

---

## 2. 파이프라인 구조

```
매일 받는 xlsx
      │
      ▼
build_snapshot.py        ← allocation 시트 + 위탁/전시차 시트 병합
      │                     · Virtual VIN 제외
      │                     · 모델명 정규화 (ABBR_MAP, SUFFIX_DROP)
      │                     · DataCard 색상코드 → 한글 변환
      ▼
pipeline/snapshots/YYYY-MM-DD.json
      │
      ▼
build_history.py         ← 스냅샷들을 VIN 단위로 day-over-day 비교
      │                     · 전국 계약 / 모터원 계약 / 해약 / 신규입고
      │                     · 미확인 코드/이탈 VIN 추적
      ▼
inventory_history.json   (대시보드용 - 전체 히스토리 + 최신 배정 상세)
latest_stock.json        (고객용 재고표 - 최신 판매가능만)
```

산출물 두 개가 정적 JSON으로 repo에 들어가고, HTML 페이지가 fetch로 읽어 렌더합니다.

---

## 3. Snapshot 스키마 핵심

```json
{
  "date": "2026-04-14",
  "sellable_total": 3615,
  "assigned_total": 179,
  "sellable_vins": ["WDB..."],
  "assigned_vins": ["WDB..."],
  "assigned_details": {
    "VIN": {"model":"...","branch":"...","team":"...","salesman":"...","ext":"...","int":"...","pdd":"..."}
  },
  "models": {
    "E 300 4MATIC AMG Line": {
      "cat": "E클래스",
      "sellable": 42,
      "assigned": 7,
      "colors": {"폴라 화이트|마키아토 베이지/블랙": 9, ...}
    }
  },
  "vin_model": {"VIN":"canonical model name"}
}
```

`build_history.py`가 이전 스냅샷 VIN과 비교해서 아래 항목을 계산합니다:

| 필드 | 정의 |
|---|---|
| `national_contract` | 전일 판매가능 → 오늘 사라진 VIN 수 (타사 + 모터원 전체) |
| `national_cancel` | 과거에 사라졌던 VIN이 오늘 다시 판매가능에 복귀 |
| `motorone_contract` | 전일 판매가능 ∩ 오늘 배정재고 (전국→배정 전환) |
| `motorone_cancel` | 전일 배정재고 ∩ 오늘 판매가능 (배정→전국 복귀) |
| `motorone_delivered` | 전일 배정재고에서 완전히 사라진 VIN (출고 완료 추정) |
| `new_in` | 오늘 판매가능에 처음 등장한 VIN (cumulative_seen에도 없음) |
| `model_contracts` | 전국 계약 VIN을 전일 모델 기준으로 집계 |
| `model_motorone` | 모터원 계약 VIN을 모델 기준으로 집계 |

검증: `이전 sellable − national_contract + motorone_cancel + national_cancel + new_in == 오늘 sellable` 이 성립해야 합니다. 안 맞으면 build_history.py의 집합 연산을 의심하세요.

---

## 4. 모델명 정규화 규칙 (build_snapshot.py)

- **ABBR_MAP**: `AV → AVANTGARDE`, `EX → EXCLUSIVE`, `4M → 4MATIC`, `HYBRID → Hybrid`, `COUPE → Coupé` 등 약어 확장
- **SUFFIX_DROP**: 날짜별 서류에서 서로 다른 표기를 canonical (4/14 기준 이름)로 맞추기
  - 예: `CLE 200 Cabriolet AMG Line → CLE 200 Cabriolet`, `S 450 4MATIC → S 450 4MATIC Sedan`, `Maybach S 580 → Maybach S 580 4MATIC`
- 새 xlsx에서 **같은 차종인데 다른 이름으로 집계된 모델**이 보이면 여기에 항목 추가

---

## 5. DataCard 색상코드 매핑

`allocation` 시트는 한글로 내려오지만 `위탁재고,전시차재고` 시트는 공장 DataCard 코드(149, 197, 104 등)를 raw로 내려줍니다. `build_snapshot.py`의 `EXT_CODE_MAP` / `INT_CODE_MAP`에서 한글로 변환합니다.

- 변환되지 않은 코드는 `"코드 XXX"` 형태로 표시됩니다 — 보이면 매핑에 추가하세요.
- **매핑 확인 필요한 코드** (추정치):
  - EXT: `662, 885, 956, 191, 696`
  - INT: `214, 215, 511, 514, 515, 671, 804, 805, 851, 855, 887`

새 코드가 나오면 Claude에게 "코드 XXX는 ○○야" 알려주면 즉시 매핑 추가.

---

## 6. 사이트 구조

### `BenzDream_Stock.html` (고객용)
- `latest_stock.json` fetch
- 카테고리 칩 + 모델 카드 + 외장/내장 CSS 색상 스와치
- 수량은 표시하지 않음 (색상 조합만 노출)
- CTA: 카카오톡 · 유튜브 · 상담신청

### `BenzDream_Inventory.html` (내부 대시보드)
- `inventory_history.json` fetch
- 상단 **날짜 탭**으로 과거 스냅샷 전환
- 6개 KPI 카드 (판매가능 / 전국계약 / 전국해약 / 모터원계약 / 모터원해약 / 신규입고)
- 5개 메인 탭
  1. **오늘 요약** — 카테고리 목록형, 행 클릭 시 트림별 계약 현황 펼침
  2. **전국 트렌드** — Top 20, 집중 공략, 프로모션 필요 대상
  3. **모터원 트렌드** — 모델별 / 지점별 / 영업사원별 Top 15
  4. **추이** — Chart.js 라인·막대 (스냅샷 누적될수록 풍부해짐)
  5. **전체 재고** — 카테고리별 전체 모델 재고표

---

## 7. 자주 나오는 이슈 · 대응

| 증상 | 원인 | 대응 |
|---|---|---|
| `sellable_total` 값이 이상하게 많음 | Virtual VIN 필터 미작동 | `재고구분2`에 `Virtual` 포함된 행 스킵되는지 확인 |
| 같은 차종이 여러 줄로 나옴 | 모델명 정규화 누락 | `SUFFIX_DROP`에 매핑 추가 |
| 색상이 `코드 XXX`로 보임 | 새 DataCard 코드 | `EXT_CODE_MAP` / `INT_CODE_MAP` 추가 |
| 3일 합산 검증 안 맞음 | build_history 집합 연산 순위 | `returned = fresh_vins & cumulative_disappeared` 순서 확인 |
| Pages 반영 안 됨 | 캐시 | 1~2분 대기, HTML 내부에서 `?v=Date.now()` 쿼리로 JSON 캐시 버스팅 중 |
| `git push` 401 | PAT 만료 | 위 섹션 0의 토큰 교체 |

---

## 8. Claude에게 업데이트 지시할 때 예시

> "오늘(4/15) 재고 업데이트했어. 파이프라인 돌리고 푸시해줘."

Claude는 이 지침을 보고 아래를 자동 실행:
1. Downloads 폴더에서 오늘 날짜 xlsx 찾기
2. `build_snapshot.py` 실행 → 새 스냅샷 생성
3. `build_history.py` 실행 → history/stock JSON 갱신
4. 결과 수치 (sellable / national / motorone / new) 보고
5. 이상 없으면 커밋 → 푸시
6. Pages 링크 공유

이상이 있는 경우(예: 미매핑 코드, 수학 불일치, 새 모델명)는 사용자에게 먼저 확인 요청.

---

## 9. 향후 확장 아이디어

- 7일 이상 누적되면 **주간 리포트 탭** 활성화 (요일 패턴, 모델 순위 변동)
- 30일 이상이면 **월간 리포트 탭** (월별 계약률, 판매 1위 변화)
- 영업사원별 월간 실적 집계 (배정재고 스냅샷 차분)
- 모델별 최초 입고 → 계약까지 평균 재고일수 (age of inventory)
- Kakao/이메일 알림: 내 담당 모델에 신규 입고/계약 발생 시 푸시

필요한 순간에 이 지침과 함께 Claude에게 요청하세요.
