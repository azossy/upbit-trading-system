# ============================================================
# 프론트엔드 (React) 멀티스테이지 Docker 빌드
# 1단계: Node.js로 React 빌드
# 2단계: Nginx로 정적 파일 서빙
# ============================================================

# ─── 1단계: React 빌드 ───
FROM node:20-alpine AS builder

# 작업 디렉토리 설정
WORKDIR /app

# 패키지 파일만 먼저 복사 (의존성 캐싱 최적화)
COPY package.json ./

# 의존성 설치 (package-lock.json이 없으므로 npm install 사용)
RUN npm install --silent

# 소스코드 전체 복사
COPY . .

# React 빌드 시 환경변수 주입 (빌드 타임에 값이 결정됨)
ARG REACT_APP_API_URL=http://localhost:8000/api/v1
ARG REACT_APP_WS_URL=ws://localhost:8000/ws
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_WS_URL=$REACT_APP_WS_URL

# React 프로덕션 빌드 (ESLint 플러그인 오류 방지)
ENV DISABLE_ESLINT_PLUGIN=true
ENV GENERATE_SOURCEMAP=false
RUN npm run build

# ─── 2단계: Nginx 서빙 ───
FROM nginx:1.25-alpine

# 빌드된 정적 파일을 Nginx 루트로 복사
COPY --from=builder /app/build /usr/share/nginx/html

# Nginx 설정 (SPA 라우팅을 위한 설정)
# React Router 사용 시 모든 경로를 index.html로 리다이렉트 필요
RUN echo 'server { \
    listen 3000; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# 3000번 포트 노출
EXPOSE 3000

# Nginx 포어그라운드 실행
CMD ["nginx", "-g", "daemon off;"]
