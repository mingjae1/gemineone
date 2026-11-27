# 🚀 gemineone (제미너네) `v0.4.1`

AI 코딩 에이전트를 위한 작업 분업 및 오케스트레이션 도구입니다. 대화 접수와 코드 작성을 분리하여 속도를 높이고 사용 쿼터를 절약합니다.

---

## 📑 목차

1. [제미너네란?](#1-제미너네란)
2. [설치 요령](#2-설치-요령)
   - [파일 복사 (권장)](#파일-복사-권장)
   - [CLI 설치](#cli-설치)
   - [요구 사항](#요구-사항)
3. [핵심 동작 원리](#3-핵심-동작-원리)
   - [3.1 고속 접수](#31-고속-접수)
   - [3.2 적응형 작업 위임](#32-적응형-작업-위임)
   - [3.3 병렬 처리](#33-병렬-처리)
   - [3.4 안전 가드](#34-안전-가드)
4. [맞춤 설정 가이드](#4-맞춤-설정-가이드)
   - [4.1 설정 파일](#41-설정-파일-agentsorca-configjson)
   - [4.2 키워드 규칙 추가](#42-키워드-규칙-추가)
   - [4.3 모델 동기화](#43-모델-동기화-sync_modelspy)
5. [검증 테스트](#5-검증-테스트)
6. [배포 가이드](#6-배포-가이드)

---

## 1. 제미너네란?

에이전트의 역할을 둘로 나눕니다.

- **접수**: 사용자와의 대화를 즉각 처리합니다.
- **작업**: 코드 분석, 구현, 테스트는 작업별 보조 작업자에게 넘깁니다.

불필요한 고비용 호출을 줄이고, 메인 에이전트가 코드를 직접 고치다 발생하는 빌드 깨짐을 막습니다.

---

## 2. 설치 요령

### 파일 복사 (권장)

프로젝트 루트에 템플릿 파일 1개를 넣고 대화를 시작합니다.

| 도구 | 템플릿 파일 | 대상 경로 |
| :--- | :--- | :--- |
| **Google Antigravity** | `templates/GEMINI.md` | `GEMINI.md` |
| **Cursor** | `templates/.cursorrules` | `.cursorrules` |
| **Claude Code** | `templates/CLAUDE.md` | `CLAUDE.md` |
| **OpenAI Codex / Copilot** | `templates/CODEX.md` | `CODEX.md` |
| **Universal** | `templates/AGENTS.md` | `AGENTS.md` |

#### 원클릭 다운로드

**PowerShell**:
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/mingjae1/gemineone/main/templates/GEMINI.md" -OutFile "GEMINI.md"
```

**Bash**:
```bash
curl -sSL "https://raw.githubusercontent.com/mingjae1/gemineone/main/templates/GEMINI.md" -o GEMINI.md
```

파일 배치 후 질문을 던지면 첫 대화에서 필요한 환경(`.agents/`)을 스스로 구성하고 요청 작업을 바로 수행합니다.

---

### CLI 설치

```cmd
# 1. 설치 및 진단
C:\path\to\gemineone\install.bat .

# 2. 셋업 완료 및 임시 파일 정리
python -X utf8 .agents/scripts/bootstrap.py --finalize --target .
```

---

### 요구 사항

- Python 3.8 이상
- Git 2.20 이상

---

## 3. 핵심 동작 원리

### 3.1 고속 접수
코드베이스 전체 스캔을 건너뛰고 사용자 질문을 즉시 수신합니다.

### 3.2 적응형 작업 위임
지시문의 키워드를 분석해 적합한 모델의 작업자를 배정합니다.

| 작업 유형 | 할당 기준 | 대표 예시 |
| :--- | :--- | :--- |
| **심층 아키텍처** | 고난도 추론 모델 | 분산 시스템, 데드락, 경합 조건 |
| **복합 구현** | 고성능 구현 모델 | 다중 모듈 개발, 벤치마크, 풀 테스트 |
| **표준 기능 개발** | 균형 모델 | 신규 기능, API 연동, 컴포넌트 |
| **경량 수정** | 고속 경량 모델 | 스크립트 수정, 변수명 변경 |
| **문서 및 설정** | 초경량 모델 | .gitignore, 포맷팅, 주석 정리 |

- 등급(`low`, `high` 등)을 직접 명시하면 그 요청을 우선합니다.
- 계정에 없는 모델이 호출되면 지원되는 상위 모델로 자동 전환됩니다.

### 3.3 병렬 처리
서로 독립적인 여러 작업은 순차 대기 없이 작업자를 동시에 투입해 처리합니다.

### 3.4 안전 가드
메인 대화창의 직접적인 소스 코드 수정을 차단합니다. 모든 코드 변경은 보조 작업자가 수행해야 합니다. (설정 및 문서는 제외)

---

## 4. 맞춤 설정 가이드

### 4.1 설정 파일 (`.agents/orca-config.json`)

```json
{
  "enabled": true,               // 활성화 여부
  "enforceWorkerForEdits": true, // 직접 수정 차단 가드
  "defaultTier": "hydrogen-high",// 기본 작업자 등급
  "exemptPathSubstrings": [      // 직접 수정 허용 경로
    ".agents", "GEMINI.md", "README.md", "CHANGELOG.md", "templates"
  ]
}
```

### 4.2 키워드 규칙 추가
`adaptiveEffort.rules`에 키워드를 추가해 원하는 유형으로 라우팅할 수 있습니다.

```json
{
  "name": "deep_architecture_concurrency",
  "keywords": ["동시성", "분산", "아키텍처", "내_키워드"]
}
```

### 4.3 모델 동기화 (`sync_models.py`)

```bash
python -X utf8 .agents/scripts/sync_models.py
```
계정의 실시간 가용 모델 목록을 조회해 로컬 상태(`.orca-state.json`)에 기록합니다. 서비스에서 제외된 모델이 있더라도 에러 없이 현세대의 적합한 모델로 연결을 유지합니다.

---

## 5. 검증 테스트

```bash
# 라우팅 및 안전 가드 테스트
python -X utf8 .agents/scripts/test_orca_hook.py

# CLI 인스톨러 테스트
python -X utf8 .agents/scripts/test_bootstrap.py

# 단일 파일 셋업 테스트
python -X utf8 .agents/scripts/test_genesis.py
```

---

## 6. 배포 가이드

```bash
# 1. 태그 푸시
git tag v0.4.1
git push origin v0.4.1

# 2. 릴리즈 발행
gh release create v0.4.1 --title "v0.4.1" --notes-file CHANGELOG.md
```
