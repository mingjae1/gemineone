#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemineone Autonomous Collaboration Pipeline
오케스트레이터가 작업 컨텍스트와 쿼터 상태를 감지하여 적절한 외부 코워커(Codex, Copilot 등)를
자율적으로 판단하고 실행하는 자동 협업 엔진.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(BASE_DIR, "orca-config.json")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from coworker_bus import CoworkerEventBus


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


class AutoCollaborator:
    """
    자율 협업 파이프라인 매니저.
    1. 자동 2차 교차 검증 (Auto Cross-Verification via Codex)
    2. 자동 깃/PR 컨텍스트 생성 (Auto Git PR via Copilot)
    3. 쿼터 고갈 방지 자동 오프로딩 (Auto Quota Offloading)
    """

    @classmethod
    def evaluate_task(cls, prompt: str, files: Optional[List[str]] = None, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        작업 프롬프트와 쿼터 상태를 평가하여 권장되는 자동 협업 전략을 반환합니다.
        """
        config = load_config()
        collab = config.get("autonomousCollaboration", {})
        if not collab.get("enabled", True):
            return {"recommended": False, "reason": "자율 협업 비활성화"}

        prompt_lower = (prompt or "").lower()

        # 1. 2차 교차 검증 트리거 점검 (Codex)
        cv_cfg = collab.get("autoCrossVerification", {})
        if cv_cfg.get("enabled", True):
            keywords = cv_cfg.get("triggerKeywords", [
                "architect", "concurrency", "security", "deadlock", "critical",
                "심층", "보안", "동시성", "교차 검증", "에지케이스"
            ])
            matched = [k for k in keywords if k in prompt_lower]
            if matched:
                target = cv_cfg.get("target", "codex")
                mod = CoworkerEventBus.get_module(target)
                if mod and mod.probe().get("loggedIn"):
                    return {
                        "recommended": True,
                        "action": "cross_verification",
                        "target": target,
                        "reason": f"심층 아키텍처/동시성/보안 키워드 감지 ({', '.join(matched[:3])}) -> {mod.display_name} 2차 교차 검증 권장",
                    }

        # 2. 깃/PR 작업 트리거 점검 (Copilot)
        git_cfg = collab.get("autoGitCopilot", {})
        if git_cfg.get("enabled", True):
            keywords = git_cfg.get("triggerKeywords", ["pr", "pull request", "commit", "git", "커밋", "풀리퀘스트"])
            matched = [k for k in keywords if k in prompt_lower]
            if matched:
                target = git_cfg.get("target", "copilot")
                mod = CoworkerEventBus.get_module(target)
                if mod and mod.probe().get("loggedIn"):
                    return {
                        "recommended": True,
                        "action": "git_integration",
                        "target": target,
                        "reason": f"깃/PR 키워드 감지 ({', '.join(matched[:2])}) -> {mod.display_name} 깃허브 네이티브 작업 권장",
                    }

        # 3. 쿼터 고갈 상태 점검
        if telemetry:
            p_5h = telemetry.get("fiveHourRemainingPercent", 100.0)
            offload_cfg = collab.get("autoQuotaOffloading", {})
            th = offload_cfg.get("thresholdPercent", 10.0)
            if p_5h <= th:
                target = offload_cfg.get("preferredFallback", "copilot")
                mod = CoworkerEventBus.get_module(target)
                if mod and mod.probe().get("loggedIn"):
                    return {
                        "recommended": True,
                        "action": "quota_offload",
                        "target": target,
                        "reason": f"Antigravity 5시간 쿼터 소진 주의 ({p_5h:.1f}% <= {th:.1f}%) -> {mod.display_name} 작업 오프로딩 권장",
                    }

        return {"recommended": False, "reason": "단독 수행 적합"}

    @classmethod
    def execute_cross_verification(cls, original_prompt: str, solution_code: str, files: Optional[str] = None) -> Dict[str, Any]:
        """
        작성된 코드에 대해 OpenAI Codex(gpt-6-luna)를 통한 2차 교차 검증을 자동 수행합니다.
        """
        prompt = (
            "다음 작업 지시와 솔루션 코드에 대해 잠재적 버그, 동시성 경합/데드락, "
            "메모리 누수, 에지 케이스를 비판적으로 검토하고 개선점을 간결히 보고하세요.\n\n"
            f"[작업 지시]:\n{original_prompt}\n\n"
            f"[솔루션 코드/내용]:\n{solution_code}"
        )
        return CoworkerEventBus.dispatch(target="codex", task=prompt, files=files, read_only=True)


if __name__ == "__main__":
    test_prompt = "분산 캐시 환경에서 동시성 데드락 해결"
    eval_res = AutoCollaborator.evaluate_task(test_prompt)
    print("🧭 [Auto Collaborator Evaluation Test]")
    print(json.dumps(eval_res, indent=2, ensure_ascii=False))
