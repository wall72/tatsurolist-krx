# tatsurolist-krx

KRX 데이터(`pykrx`)를 사용해 Tatsuro 방식의 중소형 가치주를 선별하고,
GUI/CLI로 조회 및 백테스트를 수행하는 프로젝트입니다.

## 1. 주요 기능

### 종목 조회
- 시장 선택: `KOSPI` / `KOSDAQ`
- 기준일 조회: `YYYYMMDD` 또는 `YYYY-MM-DD` (미입력 시 Today)
- 휴장일 자동 백트래킹: 최대 14일
- 필터 조건
  - `PER > 0`
  - `PBR > 0`
  - 시가총액 범위(`cap_min`, `cap_max`)
  - 선택: `PER 상한`, `PBR 상한`
  - DIV 결측 정책: `zero` / `exclude`
- 점수(TAT): `(1 / PER) + (1 / PBR) + (DIV / 100)`
- 결과 컬럼: `PER 기여`, `PBR 기여`, `DIV 기여`, `TAT`
- 상태바 정보: 전체/조건통과/최종 건수, 조회 시간, 캐시 사용 여부, 백트래킹 요약
- 결과 CSV 저장 지원

### 백테스트
- 월간 리밸런싱 백테스트 실행 (KOSPI/KOSDAQ)
- 벤치마크 대비 성과 요약
  - 누적수익률
  - MDD
- 시장 비교 리포트 생성
- GUI 내 백테스트 실행/요약/리포트 저장 지원

### 운영(배포 후)
- 설정 자동 저장: `~/.tatsurolist-krx/config.json`
- 실행 로그 기록: `~/.tatsurolist-krx/app.log`
- 자동 업데이트는 즉시 도입 대신 단계적 전략 권장(문서 하단 참고)

---

## 2. 프로젝트 구조

- `app_gui.py`: tkinter 기반 GUI
- `krx_value_service.py`: 데이터 조회/필터/점수 계산 서비스
- `krx_backtest.py`: 백테스트 및 리포트 생성 로직
- `backtest_cli.py`: 백테스트 CLI 진입점
- `app_runtime.py`: 설정 파일/로그 파일 관리 유틸
- `test_krx_value_service.py`: 서비스 로직 테스트
- `test_krx_backtest.py`: 백테스트 로직 테스트
- `test_app_runtime.py`: 설정/로그 유틸 테스트
- `requirements.txt`: 의존성 목록

---

## 3. 설치

### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### bash

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 4. 실행

### GUI 실행

```bash
python app_gui.py
```

### 백테스트 CLI 실행 예시

```bash
python backtest_cli.py --start-date 2023-01-01 --end-date 2025-12-31 --top-n 10 --output-dir reports
```

생성 파일 예시:
- `reports/backtest_summary.csv`
- `reports/backtest_kospi_monthly.csv`
- `reports/backtest_kosdaq_monthly.csv`
- `reports/backtest_report.md`

---

## 5. GUI 사용 순서

1. 시장 선택 (`KOSPI` 또는 `KOSDAQ`)
2. 기준일 입력(선택)
3. 필요 시 파라미터 조정
   - 시총 하한/상한, Top N
   - PER/PBR 상한
   - DIV 결측 정책
4. `목록 조회` 실행
5. 결과 확인 후 필요 시 `CSV 저장`
6. 백테스트 기간/범위를 지정해 `백테스트 실행`
7. `리포트 저장`으로 백테스트 산출물 저장

---

## 6. 서비스 함수 사용 예시

```python
from krx_value_service import get_tatsuro_small_mid_value_top10

result_df, used_date, stats, logs = get_tatsuro_small_mid_value_top10(
    market="KOSDAQ",
    date="2026-02-19",
    per_max=15.0,
    pbr_max=2.0,
    div_policy="exclude",
)

print(used_date)
print(stats)
print(logs[-1] if logs else "no logs")
print(result_df)
```

---

## 7. 테스트

```bash
python -m unittest -v
```

현재 테스트 범위:
- `normalize_market`
- `normalize_date`
- `get_tatsuro_score`
- 필터 조건(PER/PBR/시가총액/상한)
- DIV 결측 정책(`exclude`)
- 동일 파라미터 재조회 캐시
- 백테스트 월말 리밸런싱 날짜 생성
- 백테스트 요약(누적수익률/MDD)
- 백테스트 리포트 파일 생성
- 런타임 설정/로그 유틸(`app_runtime.py`)

---

## 8. 운영 가이드

### 설정 파일 (`config.json`)
- 경로: `~/.tatsurolist-krx/config.json`
- 저장 시점
  - 조회 성공 후
  - 백테스트 성공 후
  - `기본값 복원` 클릭 시
  - 앱 종료 시
- 주요 저장 항목
  - 시장, 기준일, 시총 범위, Top N
  - PER/PBR 상한, DIV 정책
  - 백테스트 시작일/종료일/범위

### 로그 파일 (`app.log`)
- 경로: `~/.tatsurolist-krx/app.log`
- 기록 항목
  - 앱 시작/종료
  - 조회 시작/완료/실패
  - 백테스트 시작/완료/실패
  - CSV 저장 완료

### 자동 업데이트 전략(권장)
현재는 인앱 자동 업데이트를 즉시 도입하지 않고, 아래 순서를 권장합니다.
1. 배포 채널 분리(`stable` / `preview`)
2. 앱 시작 시 최신 버전 체크(향후)
3. 자동 다운로드/교체는 보류
4. 서명/롤백/복구 정책 정립 후 단계적 도입

---

## 9. 참고

- 네트워크 상태 및 KRX 데이터 제공 상태에 따라 조회 시간이 달라질 수 있습니다.
- 입력일이 휴장일이면 가장 가까운 이전 영업일 데이터를 사용합니다.
- 상세 작업 로드맵은 `WORKLIST.md`를 참고하세요.
