# Changelog

All notable changes to **gemineone** will be documented in this file.

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
- 단위 테스트 스위트 추가 (`.agents/scripts/test_orca_hook.py`, 12종 테스트 통과)
- 하네스 설정 버전 식별자 (`version: 0.1.0-beta`)

---

## [0.1.0] - 2026-11-19

### Added
- gemineone 코어 오케스트레이션 엔진 초기 구축
- 1D Fast Intake 프론트엔드 대화 레이어 (`gemini-3.8-flash-high`)
- Swarm 위임 가드 훅 (`.agents/scripts/orca_hook.py`, `hooks.json`)
- 멀티모델 라우터 스킬 (`orca-router`)
- 프로젝트 설치 스크립트 (`install.bat`)
