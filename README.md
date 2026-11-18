# 🚀 gemineone (제미너네)

**gemineone**은 Google Antigravity 에이전트를 위한 경량 고성능 멀티모델 오케스트레이션 하네스(Harness)입니다.

---

## 🌟 핵심 아키텍처

1. **1D Fast Intake (전면 대화 고속 접수)**
   - 사용자와의 모든 직접 대화는 `gemini-3.8-flash-high`가 전담합니다.
   - 첫 명령 접수 시 불필요한 사전 파일 스캔을 생략하여 지연 시간(Latency) 없이 즉각 반응합니다.

2. **Adaptive Effort Swarm Workers (후면 적응형 노력치 워커 위임)**
   - 실제 코드 분석, `ask_question` 선택지 설계, 빌드/테스트, 버그 수정은 백그라운드 Swarm 워커에게 위임됩니다.
   - 쿼터 소모를 최적화하고 추론력을 극대화하기 위해 Gemini 계열(Flash, Hydrogen, Argon)의 **적응형 노력치(Adaptive Effort)**를 지원합니다:
     - **명시적 지정 존중**: `low`, `medium`, `high`, `xhigh` 또는 구체적 모델 ID 지정 시 강제 승격 없이 그대로 존중.
     - **태스크 기반 자동 감지 (`auto`)**: 작업 설명(brief) 및 키워드를 자동 분석하여 최적 모델 티어 동적 라우팅:
       - `gemini-4-argon-high` (Carbon 활성화 시 `gemini-4-carbon`): 동시성, 분산 시스템, 데드락, RMI, 심층 아키텍처
       - `gemini-4-hydrogen-xhigh`: 대규모 복합 구현, 벤치마크, 풀 테스트 스위트
       - `gemini-4-hydrogen-high` (기본값): 표준 기능 구현, 컴포넌트 개발, 유닛 테스트
       - `gemini-4-hydrogen-low`: 경량 스크립트 수정, 단순 변경
       - `gemini-3.8-flash-high`: 단순 설정, `.gitignore`, 포맷팅, 문서 정리
     - **Carbon 미래 호환성**: `gemini-4-carbon` 패밀리 사전 등록 및 Graceful Fallback 지원 (`enableCarbon: true/false`). 미지원 환경에서는 안전하게 `gemini-4-argon-high`로 자동 전환.

3. **Parallel Fan-out (독립 태스크 병렬 멀티프로세싱)**
   - 상호 의존성이 없는 독립 작업은 순차적으로 처리하지 않고, 한 턴에 여러 워커를 동시 투입하여 병렬로 처리합니다.
   - 컴포넌트/파일 단위로 소유권을 분리하여 레이스 컨디션을 방지합니다.

4. **Lifecycle PreToolUse Guard**
   - 코디네이터가 작업 파일을 직접 수정하려 하면 `.agents/hooks.json`이 차단하고 Swarm 워커 위임을 강제합니다.

5. **Live API Model Sync (실시간 API 모델 동기화)**
   - `python -X utf8 .agents/scripts/sync_models.py` 실행 시 Antigravity 공식 CLI(`agy.exe models`)를 통해 현재 계정의 실시간 가용 모델을 자동 동기화합니다.
   - Pro 사용자가 안전하게 사용할 수 있도록 공유 설정은 Pro-Safe 기본값을 유지하며, Ultra 머신의 권한은 로컬 상태 파일에만 안전하게 격리 저장됩니다.

---

## 📦 프로젝트에 적용하는 방법

새 프로젝트 폴더(예: `my-project`)에서:

```cmd
C:\path\to\gemineone\install.bat .
```

실행 후 Antigravity에서 상단 모델을 **`Gemini 3.8 Flash (High)`**로 설정하면 바로 사용 가능합니다.
