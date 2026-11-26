#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORCA Native GUI Settings Hub
로컬 환경에서 직접 실행되어 복사-붙여넣기 없이 .agents/orca-config.json을 즉시 저장하는 독립 GUI 창.
"""

import json
import os
import sys
import time
import glob
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONFIG_PATH = os.path.join(PROJECT_ROOT, ".agents", "orca-config.json")
BRAIN_DIR = os.path.expanduser(r"~\.gemini\antigravity\brain")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(config):
    tmp_path = f"{CONFIG_PATH}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        for _ in range(5):
            try:
                os.replace(tmp_path, CONFIG_PATH)
                return True
            except PermissionError:
                time.sleep(0.05)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return True
    except Exception:
        return False

def sync_active_artifacts():
    try:
        import orca
        orca.stage_ui_artifacts()
    except Exception:
        pass

class OrcaSettingsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🧭 ORCA Settings Hub (로컬 즉시 저장)")
        self.root.geometry("480x620")
        self.root.resizable(False, False)

        # Dark Modern Theme
        self.bg_color = "#181825"
        self.card_color = "#1e1e2e"
        self.text_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.success_color = "#a6e3a1"
        self.muted_color = "#a6adc8"
        self.border_color = "#313244"

        self.root.configure(bg=self.bg_color)
        self.config = load_config()

        self.setup_ui()

    def setup_ui(self):
        # 1. Header
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill="x", padx=16, pady=(14, 8))

        title = tk.Label(header_frame, text="🧭 ORCA Settings Hub", font=("Segoe UI", 13, "bold"),
                         fg=self.text_color, bg=self.bg_color)
        title.pack(anchor="w")

        sub = tk.Label(header_frame, text="설정 변경 시 .agents/orca-config.json에 즉시 영구 저장됩니다.",
                       font=("Segoe UI", 9), fg=self.muted_color, bg=self.bg_color)
        sub.pack(anchor="w", pady=(1, 0))

        # 2. Card: Coordinator & Worker Models
        card_models = tk.LabelFrame(self.root, text=" 🧭 모델 라우팅 구성 ", font=("Segoe UI", 9, "bold"),
                                    fg=self.accent_color, bg=self.card_color, relief="flat", padx=12, pady=6)
        card_models.pack(fill="x", padx=14, pady=4)

        # Coordinator Model
        tk.Label(card_models, text="메인 대화 모델 (Coordinator):", font=("Segoe UI", 8, "bold"),
                 fg=self.text_color, bg=self.card_color).pack(anchor="w")
        self.coord_var = tk.StringVar(value=self.config.get("coordinatorModel", "gemini-3.8-flash-high"))
        coord_cb = ttk.Combobox(card_models, textvariable=self.coord_var, state="readonly", font=("Segoe UI", 9))
        coord_cb["values"] = (
            "gemini-3.8-flash-high",
            "gemini-4-neon-high",
            "gemini-4-hydrogen-high",
            "gemini-4-carbon-high"
        )
        coord_cb.pack(fill="x", pady=(2, 6))

        # Worker Default Tier
        tk.Label(card_models, text="기본 서브에이전트 작업 티어 (defaultTier):", font=("Segoe UI", 8, "bold"),
                 fg=self.text_color, bg=self.card_color).pack(anchor="w")
        self.tier_var = tk.StringVar(value=self.config.get("defaultTier", "hydrogen-high"))
        tier_cb = ttk.Combobox(card_models, textvariable=self.tier_var, state="readonly", font=("Segoe UI", 9))
        tier_cb["values"] = (
            "hydrogen-high",
            "neon-high",
            "neon-low",
            "hydrogen-low",
            "carbon-high",
            "argon-high",
            "flash-high"
        )
        tier_cb.pack(fill="x", pady=(2, 2))

        # 3. Card: Quota Alert Thresholds
        card_quota = tk.LabelFrame(self.root, text=" ⚠️ 쿼터 경고 알림 임계치 ", font=("Segoe UI", 9, "bold"),
                                   fg=self.accent_color, bg=self.card_color, relief="flat", padx=12, pady=6)
        card_quota.pack(fill="x", padx=14, pady=4)

        q_cfg = self.config.get("quotaMonitoring", {})
        a_cfg = q_cfg.get("alertSettings", {})

        # 5h Threshold
        f_5h = tk.Frame(card_quota, bg=self.card_color)
        f_5h.pack(fill="x", pady=2)
        tk.Label(f_5h, text="Antigravity 5시간 한도 임계치:", font=("Segoe UI", 8),
                 fg=self.text_color, bg=self.card_color).pack(side="left")
        curr_5h = str(int(a_cfg.get("fiveHourThresholdPercent", 25.0)))
        self.th_5h_var = tk.StringVar(value=curr_5h)
        for val in ["25", "20", "15", "10"]:
            tk.Radiobutton(f_5h, text=f"{val}%", variable=self.th_5h_var, value=val,
                           font=("Segoe UI", 8), fg=self.text_color, bg=self.card_color,
                           selectcolor=self.bg_color, activebackground=self.card_color,
                           activeforeground=self.text_color).pack(side="left", padx=4)

        # Weekly Threshold
        f_w = tk.Frame(card_quota, bg=self.card_color)
        f_w.pack(fill="x", pady=2)
        tk.Label(f_w, text="Antigravity 주간 한도 임계치:", font=("Segoe UI", 8),
                 fg=self.text_color, bg=self.card_color).pack(side="left")
        curr_w = str(int(a_cfg.get("weeklyThresholdPercent", 25.0)))
        self.th_w_var = tk.StringVar(value=curr_w)
        for val in ["25", "20", "15", "10"]:
            tk.Radiobutton(f_w, text=f"{val}%", variable=self.th_w_var, value=val,
                           font=("Segoe UI", 8), fg=self.text_color, bg=self.card_color,
                           selectcolor=self.bg_color, activebackground=self.card_color,
                           activeforeground=self.text_color).pack(side="left", padx=4)

        # Alert Scope
        f_scope = tk.Frame(card_quota, bg=self.card_color)
        f_scope.pack(fill="x", pady=(4, 2))
        tk.Label(f_scope, text="알림 표시 범위 (alertScope):", font=("Segoe UI", 8),
                 fg=self.text_color, bg=self.card_color).pack(side="left")
        self.scope_var = tk.StringVar(value=a_cfg.get("alertScope", "all"))
        tk.Radiobutton(f_scope, text="all (전체)", variable=self.scope_var, value="all",
                       font=("Segoe UI", 8), fg=self.text_color, bg=self.card_color,
                       selectcolor=self.bg_color, activebackground=self.card_color,
                       activeforeground=self.text_color).pack(side="left", padx=4)
        tk.Radiobutton(f_scope, text="low_only (부족 시에만)", variable=self.scope_var, value="low_only",
                       font=("Segoe UI", 8), fg=self.text_color, bg=self.card_color,
                       selectcolor=self.bg_color, activebackground=self.card_color,
                       activeforeground=self.text_color).pack(side="left", padx=4)

        # 4. Card: Guardrails
        card_guard = tk.LabelFrame(self.root, text=" 🛡️ 오케스트레이션 보호 가드레일 ", font=("Segoe UI", 9, "bold"),
                                   fg=self.accent_color, bg=self.card_color, relief="flat", padx=12, pady=6)
        card_guard.pack(fill="x", padx=14, pady=4)

        self.enforce_var = tk.BooleanVar(value=self.config.get("enforceWorkerForEdits", True))
        chk1 = tk.Checkbutton(card_guard, text="코디네이터 직접 파일 수정 차단 (작업자 위임 강제)",
                              variable=self.enforce_var, font=("Segoe UI", 8),
                              fg=self.text_color, bg=self.card_color, selectcolor=self.bg_color,
                              activebackground=self.card_color, activeforeground=self.text_color)
        chk1.pack(anchor="w", pady=1)

        adaptive_enabled = self.config.get("adaptiveEffort", {}).get("enabled", True)
        self.adaptive_var = tk.BooleanVar(value=adaptive_enabled)
        chk2 = tk.Checkbutton(card_guard, text="키워드 기반 적응형 추론 노력치 라우팅 활성화",
                              variable=self.adaptive_var, font=("Segoe UI", 8),
                              fg=self.text_color, bg=self.card_color, selectcolor=self.bg_color,
                              activebackground=self.card_color, activeforeground=self.text_color)
        chk2.pack(anchor="w", pady=1)

        # 5. Status readout label
        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 9, "bold"),
                                     fg=self.success_color, bg=self.bg_color)
        self.status_label.pack(pady=(4, 0))

        # 6. Bottom Buttons
        btn_frame = tk.Frame(self.root, bg=self.bg_color)
        btn_frame.pack(fill="x", padx=14, pady=(8, 12))

        save_btn = tk.Button(btn_frame, text="💾 설정 즉시 저장 (원클릭 반영)", font=("Segoe UI", 10, "bold"),
                             fg="#11111b", bg=self.accent_color, activebackground="#b4befe",
                             relief="flat", padx=14, pady=7, command=self.on_save, cursor="hand2")
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        close_btn = tk.Button(btn_frame, text="닫기", font=("Segoe UI", 9),
                              fg=self.text_color, bg=self.card_color, activebackground="#313244",
                              relief="flat", padx=14, pady=7, command=self.root.destroy, cursor="hand2")
        close_btn.pack(side="right", padx=(6, 0))

    def on_save(self):
        new_coord = self.coord_var.get()
        new_tier = self.tier_var.get()
        try:
            new_5h = float(self.th_5h_var.get())
        except ValueError:
            new_5h = 25.0
        try:
            new_w = float(self.th_w_var.get())
        except ValueError:
            new_w = 25.0

        new_scope = self.scope_var.get()
        new_enforce = self.enforce_var.get()
        new_adaptive = self.adaptive_var.get()

        # Update dictionary
        self.config["coordinatorModel"] = new_coord
        self.config["defaultTier"] = new_tier
        self.config["enforceWorkerForEdits"] = new_enforce
        self.config.setdefault("adaptiveEffort", {})["enabled"] = new_adaptive

        q_cfg = self.config.setdefault("quotaMonitoring", {})
        a_cfg = q_cfg.setdefault("alertSettings", {})
        t_cfg = q_cfg.setdefault("thresholds", {})
        ag_dict = a_cfg.setdefault("agents", {})

        a_cfg["alertScope"] = new_scope
        a_cfg["fiveHourThresholdPercent"] = new_5h
        a_cfg["weeklyThresholdPercent"] = new_w
        t_cfg["fiveHourLimitPercent"] = new_5h
        t_cfg["weeklyLimitPercent"] = new_w
        q_cfg["lowQuotaThresholdPercent"] = new_5h

        ag_dict.setdefault("antigravity_5h", {})["threshold"] = new_5h
        ag_dict.setdefault("antigravity_weekly", {})["threshold"] = new_w

        success = save_config(self.config)
        if success:
            sync_active_artifacts()
            self.status_label.config(text="✓ 설정이 성공적으로 저장되었습니다! (대시보드 동기화 완료)")
            self.root.after(1000, self.root.destroy)
        else:
            messagebox.showerror("오류", "설정 파일을 저장하는 중 오류가 발생했습니다.")

def main():
    root = tk.Tk()
    app = OrcaSettingsApp(root)
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.mainloop()

if __name__ == "__main__":
    main()
