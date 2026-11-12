# TRIP GAME

Flask + SQLite로 만든 3팀 실시간 점수판입니다.

## 1. 준비

Python 3.10 이상을 권장합니다.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

패키지 설치:
```bash
pip install -r requirements.txt
```

## 2. 관리자 비밀번호 설정

기본 관리자 비밀번호는 `1234`입니다. 실제 사용 전 반드시 변경하세요.

Windows PowerShell:
```powershell
$env:ADMIN_PASSWORD="원하는_관리자_비밀번호"
$env:FLASK_SECRET_KEY="길고_무작위인_비밀문자열"
python app.py
```

macOS/Linux:
```bash
export ADMIN_PASSWORD="원하는_관리자_비밀번호"
export FLASK_SECRET_KEY="길고_무작위인_비밀문자열"
python app.py
```

환경변수를 설정하지 않으면 기본 비밀번호 `1234`가 사용됩니다. 공개 주소(ngrok)를 열기 전에는 꼭 변경하세요.

## 3. 접속

노트북:
- 참가자 점수판: http://127.0.0.1:5000
- 관리자: http://127.0.0.1:5000/admin

ngrok 터미널을 하나 더 열고:
```bash
ngrok http 5000
```

ngrok가 보여주는 HTTPS 주소를 참가자에게 공유하면 됩니다.

## 4. 사용 방법

- 참가자는 메인 주소에서 점수와 최근 기록을 조회합니다.
- 관리자는 `/admin`에서 비밀번호로 로그인합니다.
- 노트북과 휴대폰에서 같은 관리자 계정으로 로그인할 수 있습니다.
- 기본 팀 이름은 1팀, 2팀, 3팀이며 관리자 화면에서 변경할 수 있습니다.
- 점수 입력은 팀 선택 → ▲▼ 버튼으로 점수 조절(1씩 증감, 0점은 등록 불가, 최대 ±1000) → 등록 순서입니다.
- 점수 변경은 기록으로 저장되며, 마지막 점수 취소가 가능합니다.
- 전체 초기화는 모든 기존 점수 기록을 취소 처리합니다. 기록 자체는 보존됩니다.

## 주의

- 노트북이 켜져 있고 Flask가 실행 중이어야 접속할 수 있습니다.
- 노트북 절전 모드를 끄세요.
- Windows 방화벽에서 Python의 네트워크 접근을 허용해야 할 수 있습니다.
- SQLite 데이터베이스 파일 `database.db`는 이 프로젝트 폴더에 생성됩니다. 여행 전 백업을 권장합니다.
- 관리자 비밀번호는 기본값에서 반드시 변경하세요.
- 이 앱은 소규모 신뢰 기반 이벤트용입니다. ngrok 주소를 아는 누구나 점수판은 볼 수 있으므로 민감한 정보를 저장하지 마세요.
