# 🚀 gemineone (제미너네) `v0.3.0-beta`

**gemineone**은 Google Antigravity 에이전트를 위한 경량 고성능 멀티모델 오케스트레이션 하네스(Harness)입니다.

---

## 🌟 핵심 아키텍처

1. **1D Fast Intake (전면 대화 고속 접수)**
   - 사용자와의 모든 직접 대화는 `gemini-3.8-flash-high`가 전담합니다.
   - 첫 명령 접수 시 불필요한 사전 파일 스캔을 생략하여 지연 시간(Latency) 없이 즉각 반응합니다.

2. **Adaptive Effort Swarm Workers (후면 적응형 노력치 워커 위임)**
   - 실제 코드 분석, `ask_question` 선택지 설계, 빌드/테스트, 버그 수정은 백그라운드 Swarm 워커에게 위임됩니다.
   - 쿼터 소모를 최적화하고 추론력을 극대화하기 위해 Gemini 계열(Flash, Hydrogen, Neon, Argon)의 **적응형 노력치(Adaptive Effort)**를 지원합니다:
     - **명시적 지정 존중**: `low`, `medium`, `high`, `xhigh` 또는 구체적 모델 ID 지정 시 강제 승격 없이 그대로 존중.
     - **태스크 기반 자동 감지 (`auto`)**: 작업 설명(brief) 및 키워드를 자동 분석하여 최적 모델 티어 동적 라우팅:
       - `gemini-4-argon-high` (Carbon 활성화 시 `gemini-4-carbon`): 동시성, 분산 시스템, 데드락, RMI, 심층 아키텍처
       - `gemini-4-neon-xhigh` / `gemini-4-hydrogen-xhigh`: 대규모 복합 구현, 벤치마크, 풀 테스트 스위트
       - `gemini-4-neon-high` / `gemini-4-hydrogen-high` (기본값): 표준 기능 구현, 컴포넌트 개발, 유닛 테스트
       - `gemini-4-neon-low` / `gemini-4-hydrogen-low`: 경량 스크립트 수정, 단순 변경
       - `gemini-3.8-flash-high`: 단순 설정, `.gitignore`, 포맷팅, 문서 정리
     - **Carbon 미래 호환성**: `gemini-4-carbon` 패밀리 사전 등록 및 Graceful Fallback 지원 (`enableCarbon: true/false`). 미지원 환경에서는 안전하게 `gemini-4-argon-high`로 자동 전환.

3. **Parallel Fan-out (독립 태스크 병렬 멀티프로세싱)**
   - 상호 의존성이 없는 독립 작업은 순차적으로 처리하지 않고, 한 턴에 여러 워커를 동시 투입하여 병렬로 처리합니다.
   - 컴포넌트/파일 단위로 소유권을 분리하여 레이스 컨디션을 방지합니다.

4. **Lifecycle PreToolUse Guard**
   - 코디네이터가 작업 파일을 직접 수정하려 하면 `.agents/hooks.json`이 차단하고 Swarm 워커 위임을 강제합니다.

5. **Self-Bootstrapping Installer & Setup Harness (`v0.3.0-beta`)**
   - `install.bat` 실행 시 `.agents/scripts/bootstrap.py --probe-and-configure`가 자동 실행되어 호스트 환경(Antigravity, Cursor, Claude Code), 실시간 가용 모델, MCP 서버, 플러그인을 감지하고 맞춤형 `orca-config.json` 및 `.orca-state.json`을 생성합니다.
   - 첫 AI 세션을 위한 임시 가이드 `SETUP.md`를 생성하며, 셋업 확정 시 `--finalize` 명령으로 `SETUP.md`를 자가 청소(Self-Cleanup)하고 경량 운영 모드로 전환합니다.

6. **Live API Model Sync (실시간 API 모델 동기화)**
   - `python -X utf8 .agents/scripts/sync_models.py` 실행 시 Antigravity 공식 CLI(`agy.exe models`)를 통해 현재 계정의 실시간 가용 모델을 자동 동기화합니다.
   - Pro 사용자가 안전하게 사용할 수 있도록 공유 설정은 Pro-Safe 기본값을 유지하며, Ultra 머신의 권한은 로컬 상태 파일에만 안전하게 격리 저장됩니다.

7. **Iron Man Single-Markdown Genesis Engine (`templates/`)**
   - 별도 설치 스크립트 없이 **단일 마크다운/룰 파일 하나**(`templates/GEMINI.md`, `templates/.cursorrules`, `templates/CLAUDE.md`)만 새 프로젝트 루트에 복사해 두고 첫 대화를 시작하면 에이전트가 스스로 하네스를 조립합니다.
   - **Turn 1 자동 판별**:
     - `.agents/scripts/orca_hook.py`가 없으면 `https://github.com/mingjae1/gemineone.git`에서 `.agents/`를 임시 클론/복사·자가 정리한 뒤 `sync_models.py`로 로컬 모델/기능을 자동 동기화하고 즉시 본 운영 모드로 전환합니다.
     - 이미 설치되어 있으면 부트스트랩을 생략하고 지연 없이 Production Orchestrator Rules(1D Fast Intake, Adaptive Effort, Parallel Fan-out)를 바로 적용합니다.

---

## 📦 프로젝트에 적용하는 방법 (`v0.3.0-beta`)

### 방법 A: Iron Man Single-Markdown Genesis (권장 · Zero-Install)
사용하는 AI 코딩 에이전트에 맞는 템플릿 **파일 1개**만 대상 프로젝트 루트에 복사한 뒤 대화를 시작하세요:

| 에이전트 | 복사할 템플릿 | 대상 경로 |
| :--- | :--- | :--- |
| **Google Antigravity** | `templates/GEMINI.md` | `<project>/GEMINI.md` |
| **Cursor** | `templates/.cursorrules` | `<project>/.cursorrules` |
| **Claude Code** | `templates/CLAUDE.md` | `<project>/CLAUDE.md` |

Turn 1에서 에이전트가 `.agents/scripts/orca_hook.py` 유무를 자동 확인하여 미설치 시 하네스 조립 및 `sync_models.py` 동기화를 완료하고 즉시 오케스트레이션 모드로 전환합니다.

### 방법 B: 로컬 `install.bat` 2단계 설치

#### Phase 1: 자동 설치 및 환경 프로브
새 프로젝트 폴더(예: `my-project`)에서 `install.bat`을 실행합니다:

```cmd
C:\path\to\gemineone\install.bat .
```

설치가 완료되면 `.agents/`, `GEMINI.md`(기존 파일 보존), 환경 맞춤형 `.agents/orca-config.json`, 임시 온보딩 가이드 `SETUP.md`가 생성됩니다.

#### Phase 2: 첫 세션 확인 및 자가 청소 (Finalize)
Antigravity에서 상단 모델을 **`Gemini 3.8 Flash (High)`**로 설정한 뒤, `SETUP.md`에 보고된 환경 진단 결과를 확인하고 아래 명령으로 셋업을 마무리합니다:

```cmd
python -X utf8 .agents/scripts/bootstrap.py --finalize --target .
```

실행 후 임시 `SETUP.md`는 자동 삭제되며, `.agents/.orca-state.json`에 완료 상태(`setupCompleted: true`)가 기록되어 본 운영 모드가 활성화됩니다.

---

## 🧪 검증 테스트 실행

```cmd
python -X utf8 .agents/scripts/test_orca_hook.py
python -X utf8 .agents/scripts/test_bootstrap.py
python -X utf8 .agents/scripts/test_genesis.py
```
