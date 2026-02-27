# 업비트 자동매매 시스템 (Upbit Auto Trading System) (제작자 : 챠리)

업비트 암호화폐 거래소를 위한 완전 자동화 트레이딩 시스템입니다.
FastAPI 백엔드 + React 프론트엔드 + Docker 원클릭 배포를 지원합니다.

---

## 🚀 빠른 시작 (Windows - 원클릭 설치)

> **Git, Docker 등 아무것도 설치 안 되어 있어도 됩니다. 스크립트가 전부 자동 설치합니다.**

### 1단계: 저장소 다운로드

아래 중 하나를 선택하세요.

**방법 A) ZIP으로 다운로드 (Git 불필요)**
👉 이 페이지 우측 상단 **`Code`** 버튼 → **`Download ZIP`** → 압축 해제

**방법 B) Git으로 클론 (Git이 설치된 경우)**
```powershell
git clone https://github.com/azossy/upbit-trading-system.git
cd upbit-trading-system
```

---

### 2단계: 설치 스크립트 실행

다운로드/압축 해제한 폴더에서 **PowerShell을 관리자 권한으로 열고** 아래 명령어를 실행하세요.

#### PowerShell 여는 방법
1. 폴더 안에서 주소창 클릭
2. `powershell` 입력 후 Enter
3. 또는: 시작 메뉴 → `PowerShell` 우클릭 → **관리자 권한으로 실행**

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; .\setup.ps1
```

#### 스크립트가 자동으로 설치하는 것들

| 단계 | 내용 |
|------|------|
| ① | **winget** 확인 (없으면 Microsoft Store 안내) |
| ② | **Git** 자동 설치 |
| ③ | **Docker Desktop** 자동 설치 및 시작 |
| ④ | **`.env` 파일** 생성 + Notepad로 설정 열기 |
| ⑤ | **`docker compose up --build`** 실행 → 전체 서비스 시작 |

> ⚠️ Docker Desktop 설치 후 **재부팅이 필요**할 수 있습니다. 재부팅 후 setup.ps1을 다시 실행하면 이어서 진행됩니다.

---

### 3단계: 접속

| 서비스 | 주소 |
|--------|------|
| 🖥 프론트엔드 (웹) (제작자 : 챠리) | http://localhost:3000 |
| 📖 API 문서 (Swagger) (제작자 : 챠리) | http://localhost:8000/docs |
| 👤 관리자 계정 (제작자 : 챠리) | `admin@example.com` / `Admin1234!` |

---

## ⚙️ 업비트 API 키 설정

업비트에서 API 키를 발급받아 `.env` 파일에 입력하거나, 로그인 후 **대시보드 → API 키 관리** 메뉴에서 입력하세요.

```env
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here
```

업비트 API 키 발급: https://upbit.com/mypage/api_management

---

## 📋 수동 설치 방법 (Docker만 있는 경우)

Docker Desktop이 이미 설치되어 있다면:

```powershell
# 1. .env 파일 생성
copy .env.example .env
# .env 파일을 열어 필요한 값 입력

# 2. 실행
docker compose up -d --build
```

---

## 🗂 프로젝트 구조

```
upbit-trading-system/
├── setup.ps1               ← Windows 원클릭 설치 스크립트
├── docker-compose.yml      ← 전체 서비스 구성
├── .env.example            ← 환경변수 템플릿
│
├── backend/
│   ├── main.py             ← FastAPI 앱 진입점
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── models/         ← DB 모델 (User, Bot, Trade, Position, Alert)
│       ├── routers/        ← API 라우터 (auth, bot, admin)
│       ├── trading/        ← 매매 로직
│       │   ├── upbit_client.py       ← 업비트 API
│       │   ├── strategy.py           ← 매매 전략
│       │   ├── signal_generator.py   ← 신호 생성
│       │   ├── risk_manager.py       ← 리스크 관리
│       │   ├── order_executor.py     ← 주문 실행
│       │   ├── market_analyzer.py    ← 시장 분석
│       │   └── telegram_notifier.py  ← 텔레그램 알림
│       ├── celery_app.py   ← 비동기 작업 스케줄러
│       ├── database.py     ← DB 연결
│       └── config.py       ← 설정
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── pages/          ← 페이지 컴포넌트
│       ├── components/     ← 공통 컴포넌트
│       ├── store/          ← Zustand 상태 관리
│       └── services/       ← API 서비스 (axios)
│
└── nginx/
    └── nginx.conf          ← 리버스 프록시 설정
```

---

## 🛠 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | FastAPI (Python 3.11) |
| 프론트엔드 | React 18 + Tailwind CSS + Zustand |
| 데이터베이스 | PostgreSQL 15 |
| 캐시 / 메시지 큐 | Redis 7 |
| 비동기 작업 | Celery + Celery Beat |
| 웹 서버 | Nginx (리버스 프록시) |
| 배포 | Docker Compose |
| 인증 | JWT (Access Token + Refresh Token) |
| 암호화 | Fernet (API 키 암호화 저장) |

---

## 📊 지원 매매 전략

| 전략 | 설명 |
|------|------|
| RSI | 과매수/과매도 역추세 |
| MACD | 이동평균 수렴·발산 추세 추종 |
| Bollinger Band | 밴드 이탈·회귀 전략 |
| Moving Average | 단기/장기 이동평균 교차 |
| Composite | 복합 지표 조합 전략 |

---

## 🔧 개발 환경 로컬 실행

```powershell
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm start
```

---

## 🐳 Docker 유용한 명령어

```powershell
# 서비스 상태 확인
docker compose ps

# 실시간 로그 보기
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f backend

# 서비스 중지
docker compose down

# 서비스 재시작
docker compose restart

# 전체 초기화 (데이터 포함 삭제)
docker compose down -v
```

---

## 🔒 보안 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요 (`.gitignore`에 포함됨)
- 프로덕션 배포 시 `JWT_SECRET_KEY`, `ENCRYPTION_KEY`를 반드시 새로 생성하세요
- 업비트 API 키는 DB에 Fernet 암호화되어 저장됩니다
- 관리자 초기 비밀번호(`Admin1234!`)를 반드시 변경하세요

---

## ❓ 자주 묻는 문제

**Q: Docker Desktop 설치 후 실행이 안 돼요**
A: 재부팅 후 Docker Desktop을 먼저 실행하고 고래 아이콘이 트레이에 뜰 때까지 기다린 후 `setup.ps1`을 다시 실행하세요.

**Q: `port is already allocated` 오류가 나요**
A: 3000, 8000, 5432, 6379 포트를 사용하는 프로그램을 종료하거나 `docker compose down` 후 재시도하세요.

**Q: 매매 봇이 실제로 매수/매도를 하나요?**
A: API 키를 입력하고 봇을 활성화해야 실제 거래가 됩니다. 처음에는 API 키 없이 UI만 탐색 가능합니다.

---

## ⚠️ 면책 조항

이 소프트웨어는 교육 및 연구 목적으로 제공됩니다.
실제 투자 손실에 대해 개발자는 책임을 지지 않습니다.
암호화폐 투자는 원금 손실 위험이 있습니다.

---

## 📝 라이선스

MIT License
