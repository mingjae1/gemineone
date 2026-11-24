# Changelog

All notable changes to **gemineone** will be documented in this file.

## [0.4.0] - 2026-11-24

### Added
- **구세대 모델 서비스 종료(EOL) 대응 및 자동 승계 (Self-Healing Fallback)**:
  - 구독형 AI 플랫폼 특성상 구세대 모델(예: Gemini 3.8 Flash 등)이 퇴역/서비스 제외되더라도, 사라진 모델을 찾아 에러를 내지 않고 실시간 인벤토리(`liveModels`) 대조를 통해 현세대 가성비/고속 모델(`gemini-4-neon-low` 등)로 자동 승계되는 자가 치유(Self-Healing) 로직 도입
  - 특정 모델명 하드코딩에서 탈피하여 가용 모델 기반의 유연한 역할 중심 구조로 개편
- **Gemini 4 Carbon 공식 모델 ID 정규화 및 실시간 활성화 지원**:
  - `gemini-4-carbon-high`, `gemini-4-carbon-medium`, `gemini-4-carbon-low` 및 오케스트레이터 모델 풀 정규화
  - Carbon 권한이 활성화된 로컬 머신에서의 동적 에스컬레이션 완벽 지원

### Security (보안 강화)
- **공개(Public) 저장소 전환 대비 엔터프라이즈급 보안 패치**:
  - **명령어 인자 주입 차단**: `install.bat`에서 대상 경로의 특수문자(`&`, `|`, `<`, `>`, `^`, `%`) 검증 및 뒷슬래시 따옴표 이스케이프 버그 수정
  - **민감정보 유출 원천 차단**: `bootstrap.py`의 MCP 서버 정보 수집 시 API 키, 비밀번호, 인증 토큰 자동 마스킹/제거(`_sanitize_mcp_config`)
  - **경로 우회 취약점 해결**: `orca_hook.py`의 `is_exempt_path()`를 단순 서브스트링 검사에서 `os.path.normpath` 기반의 정확한 경로/파일명 단위 검사로 강화하여 소스 수정 가드 우회 차단
  - **바이너리 가로채기(PATH Hijacking) 방어**: 작업 폴더 내 악성 파이썬 실행 파일 가로채기 방지(`NoDefaultCurrentDirectoryInExePath=1` 및 고유 시스템 경로 우선 검증)
  - **정션 순환 및 탈출 차단**: `robocopy` 실행 시 정션/심볼릭 링크 탐색 제외 옵션(`/XJ`) 전면 적용
  - **원자적 파일 쓰기(Atomic Write)**: 상태 파일 저장 시 `os.replace` 기반 원자적 저장을 적용해 동시성 충돌 및 파일 손상 방지
  - **표준 `.gitignore` 대폭 강화**: 개인 식별 정보, 로컬 로그, 가상환경, 임시 상태 파일 완전 격리

### Changed
- **문서화 및 사용자 경험(UX) 전면 개편 (`README.md`)**:
  - 비유적/모호한 표현과 중복 문구를 전면 걷어내고, 누구나 직관적으로 이해할 수 있는 표준 기술 용어로 재정의
  - 하이퍼링크 목차(TOC) 신설: 1. 제미너네란? ➡️ 2. 설치 요령 ➡️ 3. 핵심 동작 원리 ➡️ 4. 맞춤 설정 가이드 ➡️ 5. 검증 테스트 ➡️ 6. 배포 가이드
  - 특정 모델 ID 나열을 배제하고, 작업 난이도 및 역할 기반의 직관적인 분업 가이드로 개편
- **버전 식별자 업데이트**:
  - 전체 하네스 설정 및 템플릿 버전 식별자를 `v0.4.0`으로 갱신

---

## [0.3.0-beta] - 2026-11-20

### Added
- **단일 파일 무설치 자동 셋업 엔진 (Single-File Auto-Setup Engine, `templates/`, `GEMINI.md`)**:
  - 멀티 에이전트 단일 파일 자가 조립 템플릿 5종 추가:
    - `templates/GEMINI.md` (Google Antigravity Genesis)
    - `templates/.cursorrules` (Cursor Genesis)
    - `templates/CLAUDE.md` (Claude Code Genesis)
    - `templates/CODEX.md` (OpenAI Codex / GitHub Copilot Genesis)
    - `templates/AGENTS.md` (Universal Agent Genesis — OpenAI Codex CLI, Copilot 등 `AGENTS.md` 호환 에이전트 범용 지원)
  - 루트 `GEMINI.md`에 Turn 1 Genesis Protocol 반영 (`templates/GEMINI.md`와 동기화)
  - **Turn 1 자동 판별 및 무설치 부트스트랩**:
    - `.agents/scripts/orca_hook.py` 미존재 시 `https://github.com/mingjae1/gemineone.git`에서 임시 클론/풀(`.gemineone-tmp`) -> `.agents/` 복사 -> 임시 폴더 자동 제거 -> `sync_models.py` 로컬 모델·권한 동기화(비-Antigravity 환경은 `bootstrap.py` 프로브/자가청소 폴백) 후 즉시 Production Orchestrator 모드로 전환
    - 이미 설치된 프로젝트에서는 부트스트랩을 생략하고 1D Fast Intake, Adaptive Effort, Parallel Fan-out 규칙을 지연 없이 즉시 적용
- **Genesis 자동화 검증 테스트 스위트 (`.agents/scripts/test_genesis.py`)**:
  - 5종 템플릿(`GEMINI.md`, `.cursorrules`, `CLAUDE.md`, `CODEX.md`, `AGENTS.md`) 및 루트 `GEMINI.md` 프로토콜 마커 검증, 격리 목(Mock) 프로젝트에서의 git clone/pull·`.agents/` 조립·`sync_models.py` 동기화·Production 훅 라우팅/편집 가드 검증, Turn 2+ 스킵 및 크로스 에이전트(Cursor/Claude/Codex/Universal) 폴백 검증
- **Self-Bootstrapping Installer & Setup Engine (`.agents/scripts/bootstrap.py`)**:
  - `install.bat` 설치 시 자동으로 `bootstrap.py --probe-and-configure` 프로브를 실행하여 대상 프로젝트 환경을 자동 진단 및 구성
  - 호스트 AI 에이전트 환경 자동 감지 (Antigravity CLI, Cursor, Claude Code) 및 `agy.exe` 동적 경로 탐색
  - 실시간 가용 모델(`agy models`), 연결된 MCP 서버(`agy mcp list`, `~/.cursor/mcp.json`), 활성 플러그인(`agy plugin list`) 자동 수집
  - 환경 맞춤형 `.agents/orca-config.json` (Neon 자동 감지, Pro-Safe `enableCarbon: false`, 오프라인 기본 모델 폴백) 및 로컬 격리 상태 파일(`.agents/.orca-state.json`) 자동 생성
  - **2단계 온보딩 및 자가 청소(Self-Cleanup) 워크플로우**:
    - Phase 1: 첫 AI 세션 안내용 임시 `SETUP.md` 자동 생성
    - Phase 2: `python -X utf8 .agents/scripts/bootstrap.py --finalize --target .` 실행 시 `SETUP.md` 영구 삭제 및 `.orca-state.json`에 `setupCompleted: true` / `finalizedAt` 기록
- **부트스트랩 자동화 테스트 스위트 (`.agents/scripts/test_bootstrap.py`)**:
  - `install.bat` 엔드투엔드 설치, 기존 `GEMINI.md` 보존, `--probe-and-configure`, `--finalize` 자가 청소, 생성된 설정과 `orca_hook.py` 연동, 오프라인 폴백 시나리오 검증
- 하네스 설정 버전 식별자 (`version: 0.3.0-beta`) 및 `exemptPathSubstrings`에 `SETUP.md` 추가

---

## [0.2.1-beta] - 2026-11-20

### Added
- **Gemini 4 Neon 패밀리 완벽 지원 (Antigravity v1.5.12 패치 대응)**:
  - `gemini-4-neon-low`, `medium`, `high`, `xhigh` 전 티어 및 `gemini-pro-orchestrator-neon` 모델 풀 및 별칭(`neon`, `neon-*`) 등록
  - 실전 Swarm 워커 생성 및 18종 적응형 노력치 단위 테스트 검증 완료 (쿼터 100% 가용)
- 하네스 설정 버전 식별자 (`version: 0.2.1-beta`)

---

## [0.2.0-beta] - 2026-11-19

### Added
- **실시간 API 모델 동기화 및 자동 업데이트 기능 (`sync_models.py`)**:
  - Antigravity 공식 CLI(`agy.exe models`)를 통해 Google 백엔드 API로부터 계정별 실시간 가용 모델 목록을 원클릭으로 동기화
  - **Pro 안전성 보장 (Pro-Safe Isolation)**: 공유 저장소의 `orca-config.json`은 언제나 `enableCarbon: false` 안전 기본값을 유지하고, Ultra/Carbon 머신별 권한은 gitignore된 `.orca-state.json`에만 로컬 격리 저장하여 Pro 사용자가 pull하거나 배포받아도 충돌/에러가 전혀 발생하지 않도록 보호
  - **전 모델 범용 Graceful Fallback**: 계정에 없는 미지원/권한제한 모델이 요청되어도 에러 없이 상위 가용 모델(`gemini-4-argon-high` 등)로 안전하게 자동 전환
- **Carbon Forward-Compatibility (미래 호환성)**:
  - `gemini-4-carbon` 공식 모델 ID 및 티어 매핑 정규화
  - 권한 미보유/비활성화 환경을 위한 Graceful Fallback (`carbonFallback`: `gemini-4-argon-high`)
- 하네스 설정 버전 식별자 (`version: 0.2.0-beta`)

---

## [0.1.0-beta] - 2026-11-19

### Added
- **적응형 노력치 (Adaptive Thinking Effort) 시스템 도입**:
  - 명시적 요청 존중: `low`, `medium`, `high`, `xhigh` 및 개별 티어 모델 요청을 강제 승격 없이 그대로 수용
  - 작업 내용(brief/tasks) 키워드 기반 자동 동적 모델 라우팅:
    - 심층 아키텍처 / 동시성 / 분산 / RMI: `gemini-4-argon-high`
    - 대규모 복합 구현 / 벤치마크 / 풀 테스트: `gemini-4-hydrogen-xhigh`
    - 표준 기능 개발 / 컴포넌트 / 단위 테스트 (기본값): `gemini-4-hydrogen-high`
    - 경량 스크립트 수정 / 단순 변경: `gemini-4-hydrogen-low`
    - 단순 설정 / .gitignore / 문서 / 포맷팅: `gemini-3.8-flash-high`
  - Gemini 모델 패밀리 전 티어 매트릭스 지원 (Flash Low~High, Hydrogen Low~XHigh, Argon Low~High)
- 단위 테스트 스위트 추가 (`.agents/scripts/test_orca_hook.py`, 16종 테스트 통과)
- 하네스 설정 버전 식별자 (`version: 0.1.0-beta`)

---

## [0.1.0] - 2026-11-19

### Added
- gemineone 코어 오케스트레이션 엔진 초기 구축
- 1D Fast Intake 프론트엔드 대화 레이어 (`gemini-3.8-flash-high`)
- Swarm 위임 가드 훅 (`.agents/scripts/orca_hook.py`, `hooks.json`)
- 멀티모델 라우터 스킬 (`orca-router`)
- 프로젝트 설치 스크립트 (`install.bat`)
