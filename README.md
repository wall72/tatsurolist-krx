# tatsurolist-krx

KRX 데이터(`pykrx`)를 사용해 Tatsuro 방식의 중소형 가치주를 선별하고, Windows GUI로 조회하는 프로젝트입니다.

## 기능

- 시장 선택: `KOSPI` 또는 `KOSDAQ`
- 기준일 조회: 특정 날짜 기준 산출 (`YYYYMMDD` 또는 `YYYY-MM-DD`)
- 기준일 미입력 시: Today 기준 조회
- 파라미터 입력
  - 시가총액 하한/상한 입력 (`cap_min`, `cap_max`, 기본 `5,000억 ~ 1조`)
  - Top N 입력 (기본 `10`, 허용 범위 `1~100`)
  - 극단치 방어: `PER 상한`, `PBR 상한`(선택 입력)
  - DIV 결측 정책 선택: `zero`(0 처리) 또는 `exclude`(결측 종목 제외)
  - `기본값 복원` 버튼으로 파라미터 초기화
- 입력값 유효성 검사
  - 시총/Top N 숫자 여부 확인
  - 시총 하한/상한 범위 검증 (하한 ≤ 상한, 0 이상)
- 휴장일 자동 처리: 최근 영업일로 최대 14일 백트래킹
- 백트래킹 로그: 상태바에 마지막 백트래킹 결과 요약 표시
- 선별 조건
  - `PER > 0`
  - `PBR > 0`
  - 시가총액 `5,000억 ~ 1조`
- 점수 산식 (TAT)
  - `(1 / PER) + (1 / PBR) + (DIV / 100)`
- 결과 해석 컬럼
  - `PER 기여`, `PBR 기여`, `DIV 기여`를 별도 표시
- 조회 통계
  - 하단 상태바에 `전체/조건통과/최종` 건수 표시
  - 조회 소요 시간(초) 및 캐시 사용 여부(`신규조회`/`캐시사용`) 표시
- 결과 헤더
  - 현재 표시 중인 결과의 `시장`/`기준일`을 고정 표시
- CSV 저장
  - `CSV 저장` 버튼으로 결과 내보내기
  - 기본 파일명: `market_date_timestamp.csv`
- 성능 개선
  - 티커명 조회 메모리 캐시 적용
  - 동일 파라미터 재조회 시 결과 재사용 캐시 적용
- 백테스트/리포트
  - 월간 리밸런싱 백테스트 실행 스크립트 (`backtest_cli.py`)
  - GUI에서 백테스트 실행/요약 확인 및 리포트 저장 지원
  - 벤치마크 대비 성과 요약 (누적수익률, MDD)
  - KOSPI/KOSDAQ 시장별 비교 리포트 생성

## 프로젝트 구조

- `app_gui.py`: tkinter 기반 Windows GUI 앱
- `krx_value_service.py`: 데이터 조회/필터/점수 계산 서비스 로직
- `krx_backtest.py`: 월간 리밸런싱 백테스트 및 리포트 생성 로직
- `backtest_cli.py`: 백테스트 실행 CLI
- `test_pykrx.py`: 초기 콘솔 기반 실험 스크립트
- `requirements.txt`: 의존성 목록

## 환경 설정

PowerShell 기준:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 실행

```powershell
.\.venv\Scripts\Activate.ps1
python app_gui.py
```

## GUI 사용법

1. `시장`에서 `KOSPI` 또는 `KOSDAQ` 선택
2. `기준일` 입력 (선택)
   - 예: `20260219` 또는 `2026-02-19`
   - 비워두면 Today
3. `목록 조회` 클릭
4. 필요 시 시가총액 하한/상한, Top N, PER/PBR 상한, DIV 결측 정책을 조정
5. `기본값 복원`으로 파라미터를 기본값으로 되돌릴 수 있음
6. 백테스트 시작일/종료일 및 범위(`all` 또는 `selected`)를 지정 후 `백테스트 실행`
7. 하단 `백테스트 요약` 표에서 시장별 누적수익률/MDD 확인 후 `리포트 저장`

조회 완료 후 하단 상태바에 실제 사용된 기준일이 표시됩니다.
상태바에는 필터링 통계(전체/조건통과/최종), 캐시 사용 여부, 조회 시간, 마지막 백트래킹 요약이 함께 표시됩니다.

`CSV 저장` 버튼으로 현재 조회 결과를 저장할 수 있으며, 저장 성공/실패 메시지가 표시됩니다.

## 서비스 함수 직접 사용

```python
from krx_value_service import get_tatsuro_small_mid_value_top10

# KOSDAQ, 특정 날짜 기준
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


## 테스트

아래 명령으로 핵심 서비스 로직 테스트를 실행할 수 있습니다.

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest -v
```

현재 테스트 범위:
- `normalize_market`
- `normalize_date`
- `get_tatsuro_score`
- 필터 조건(PER/PBR/시가총액/상한)
- DIV 결측 정책(exclude)
- 동일 파라미터 재조회 캐시
- 백테스트 월말 리밸런싱 날짜 생성
- 백테스트 요약(누적수익률/MDD)
- 백테스트 리포트 파일 생성

## 백테스트 실행

아래 예시로 월간 리밸런싱 백테스트를 실행할 수 있습니다.

```powershell
.\.venv\Scripts\Activate.ps1
python backtest_cli.py --start-date 2023-01-01 --end-date 2025-12-31 --top-n 10 --output-dir reports
```

생성 결과:
- `reports/backtest_summary.csv` (KOSPI/KOSDAQ 비교 요약)
- `reports/backtest_kospi_monthly.csv`
- `reports/backtest_kosdaq_monthly.csv`
- `reports/backtest_report.md`

## PyInstaller 배포 (Windows)

### 1) PyInstaller 설치

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install pyinstaller
```

### 2) 단일 exe 빌드

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name tatsurolist-krx app_gui.py
```

- 결과물: `dist\tatsurolist-krx.exe`

### 3) 실행 확인

```powershell
.\dist\tatsurolist-krx.exe
```

### 4) (선택) 아이콘 지정

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name tatsurolist-krx --icon assets\app.ico app_gui.py
```

## 참고

- 네트워크 상태 및 KRX 데이터 제공 상태에 따라 조회 시간이 달라질 수 있습니다.
- 입력한 날짜가 휴장일이면 가장 가까운 이전 영업일 데이터를 사용합니다.
- 백신/보안 설정에 따라 처음 실행 시 SmartScreen 경고가 표시될 수 있습니다.


## 로드맵

- 실행 가능한 상세 체크리스트는 `WORKLIST.md`를 참고하세요.
