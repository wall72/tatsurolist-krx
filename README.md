# tatsurolist-krx

KRX 데이터(`pykrx`)를 사용해 Tatsuro 방식의 중소형 가치주를 선별하고, Windows GUI로 조회하는 프로젝트입니다.

## 기능

- 시장 선택: `KOSPI` 또는 `KOSDAQ`
- 기준일 조회: 특정 날짜 기준 산출 (`YYYYMMDD` 또는 `YYYY-MM-DD`)
- 기준일 미입력 시: Today 기준 조회
- 휴장일 자동 처리: 최근 영업일로 최대 14일 백트래킹
- 선별 조건
  - `PER > 0`
  - `PBR > 0`
  - 시가총액 `5,000억 ~ 1조`
- 점수 산식 (TAT)
  - `(1 / PER) + (1 / PBR) + (DIV / 100)`

## 프로젝트 구조

- `app_gui.py`: tkinter 기반 Windows GUI 앱
- `krx_value_service.py`: 데이터 조회/필터/점수 계산 서비스 로직
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

조회 완료 후 하단 상태바에 실제 사용된 기준일이 표시됩니다.

## 서비스 함수 직접 사용

```python
from krx_value_service import get_tatsuro_small_mid_value_top10

# KOSDAQ, 특정 날짜 기준
result_df, used_date = get_tatsuro_small_mid_value_top10(
    market="KOSDAQ",
    date="2026-02-19",
)

print(used_date)
print(result_df)
```

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
