"""
====================================================
   Neki Macro v.1
   Keyboard Macro Program with Key Binding & Delay
   Written By Neki v.1
====================================================

Features:
- Custom key binding (trigger key -> sequence of actions)
- Custom keys per step (press key / type text / delay)
- Adjustable delay (ms) between steps
- Modern sidebar-navigation UI (Dark Mode)
- Backup & Restore center: export/import macro profiles as JSON,
  drag & drop a backup file to restore, reset to factory defaults
  - every risky action shows a clear pros/cons confirmation dialog

Requirements (see requirements.txt):
    pip install customtkinter keyboard tkinterdnd2

NOTE:
- On Windows, run as Administrator so "keyboard" can hook global
  keys reliably in all apps.
- On Linux, global key hooks usually require sudo.
- tkinterdnd2 enables real drag & drop of backup files. If it is not
  installed, the app still works fully via the "เลือกไฟล์" browse button.
"""

import json
import os
import shutil
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    import keyboard  # global hotkeys + key sending
except ImportError:
    keyboard = None

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

APP_TITLE = "Neki Macro v.1"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "neki_macros.json")
BACKUP_DIR = os.path.join(APP_DIR, "backups")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ---------------------------------------------------------------------------
# Modern color palette
# ---------------------------------------------------------------------------
BG_APP = "#0F1117"
BG_SIDEBAR = "#12141C"
BG_CARD = "#1A1D29"
BG_CARD_ALT = "#1F2333"
BG_INPUT = "#11131C"

ACCENT = "#8B5CF6"
ACCENT_HOVER = "#7C4FE0"
ACCENT_SOFT = "#241B3D"

SUCCESS = "#22C55E"
SUCCESS_HOVER = "#1CA84E"
DANGER = "#EF4444"
DANGER_HOVER = "#D93D3D"
WARNING = "#F59E0B"
INFO = "#3B82F6"

TEXT_MAIN = "#F1F2F6"
TEXT_MUTED = "#8B8FA3"
TEXT_FAINT = "#5B5F73"


# ---------------------------------------------------------------------------
# Data model helpers
# ---------------------------------------------------------------------------

def load_macros():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_macros(macros):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(macros, f, ensure_ascii=False, indent=2)


def validate_macro_list(data):
    """Return True if data looks like a valid Neki Macro backup list."""
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, dict):
            return False
        if "name" not in item or "trigger" not in item or "steps" not in item:
            return False
        if not isinstance(item["steps"], list):
            return False
    return True


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Reusable: Confirm Action Dialog (with pros / cons)
# ---------------------------------------------------------------------------

class ConfirmActionDialog(ctk.CTkToplevel):
    """
    A modern confirmation dialog that clearly explains what will happen,
    including a pros list (สิ่งที่ได้) and a cons list (ข้อควรระวัง / สิ่งที่เสียไป).
    """

    def __init__(self, master, title, message, pros=None, cons=None,
                 confirm_text="ยืนยัน", confirm_color=DANGER,
                 confirm_hover=DANGER_HOVER, icon="⚠️", on_confirm=None):
        super().__init__(master)
        self.title(title)
        self.geometry("460x520")
        self.resizable(False, False)
        self.configure(fg_color=BG_APP)
        self.grab_set()
        self.on_confirm = on_confirm

        header = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=icon, font=ctk.CTkFont(size=32)).pack(side="left", padx=(24, 12), pady=20)
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", pady=20)
        ctk.CTkLabel(title_box, text=title, font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        ctk.CTkLabel(body, text=message, font=ctk.CTkFont(size=13), text_color=TEXT_MUTED,
                     wraplength=390, justify="left").pack(anchor="w", pady=(0, 16))

        if pros:
            ctk.CTkLabel(body, text="✅ สิ่งที่จะได้ (ข้อดี)", font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=SUCCESS).pack(anchor="w", pady=(4, 6))
            for p in pros:
                row = ctk.CTkFrame(body, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text="•", text_color=SUCCESS, font=ctk.CTkFont(size=13, weight="bold")).pack(
                    side="left", padx=(4, 8))
                ctk.CTkLabel(row, text=p, font=ctk.CTkFont(size=12), text_color=TEXT_MAIN,
                             wraplength=360, justify="left").pack(side="left", fill="x")

        if cons:
            ctk.CTkLabel(body, text="⚠️ ข้อควรระวัง (ผลเสีย)", font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=DANGER).pack(anchor="w", pady=(16, 6))
            for c in cons:
                row = ctk.CTkFrame(body, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text="•", text_color=DANGER, font=ctk.CTkFont(size=13, weight="bold")).pack(
                    side="left", padx=(4, 8))
                ctk.CTkLabel(row, text=c, font=ctk.CTkFont(size=12), text_color=TEXT_MAIN,
                             wraplength=360, justify="left").pack(side="left", fill="x")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=20)
        ctk.CTkButton(btn_row, text="ยกเลิก", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, text_color=TEXT_MUTED,
                      command=self.destroy).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btn_row, text=confirm_text, fg_color=confirm_color, hover_color=confirm_hover,
                      font=ctk.CTkFont(weight="bold"),
                      command=self._confirm).pack(side="left", expand=True, fill="x", padx=(6, 0))

    def _confirm(self):
        self.destroy()
        if self.on_confirm:
            self.on_confirm()


# ---------------------------------------------------------------------------
# Key capture dialog
# ---------------------------------------------------------------------------

class KeyCaptureDialog(ctk.CTkToplevel):
    def __init__(self, master, title="กดปุ่มที่ต้องการ..."):
        super().__init__(master)
        self.title(title)
        self.geometry("380x180")
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        self.configure(fg_color=BG_APP)

        ctk.CTkLabel(self, text="🎯 กดปุ่มคีย์บอร์ดที่ต้องการตั้งค่า",
                     font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_MAIN).pack(pady=(28, 10))

        self.key_label = ctk.CTkLabel(
            self, text="รอการกดปุ่ม...", font=ctk.CTkFont(size=24, weight="bold"), text_color=ACCENT
        )
        self.key_label.pack(pady=8)

        ctk.CTkButton(self, text="ยกเลิก", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=self.destroy).pack(pady=(10, 14))

        self.bind("<Key>", self._on_key)
        self.after(100, lambda: self.focus_force())

    def _on_key(self, event):
        keysym = event.keysym
        self.key_label.configure(text=keysym)
        self.result = keysym
        self.after(250, self.destroy)


# ---------------------------------------------------------------------------
# Step editor dialog
# ---------------------------------------------------------------------------

class StepDialog(ctk.CTkToplevel):
    def __init__(self, master, step=None):
        super().__init__(master)
        self.title("แก้ไข Step")
        self.geometry("440x340")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=BG_APP)
        self.result = None

        step = step or {"type": "key", "value": "", "delay_after": 100}

        ctk.CTkLabel(self, text="ประเภท Step", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(22, 6))

        self.type_var = tk.StringVar(value=step["type"])
        seg = ctk.CTkSegmentedButton(
            self, values=["key", "text", "delay"], variable=self.type_var,
            command=self._on_type_change, fg_color=BG_CARD, selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER
        )
        seg.pack(fill="x", padx=24)

        ctk.CTkLabel(self, text="ค่า (ปุ่ม / ข้อความ / มิลลิวินาที)",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(
            anchor="w", padx=24, pady=(20, 6))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24)

        self.value_entry = ctk.CTkEntry(row, placeholder_text="เช่น enter, ctrl+c, สวัสดี, 500",
                                         fg_color=BG_INPUT, border_color=BG_CARD_ALT)
        self.value_entry.insert(0, str(step["value"]))
        self.value_entry.pack(side="left", fill="x", expand=True)

        self.capture_btn = ctk.CTkButton(
            row, text="🎯 จับปุ่ม", width=90, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._capture_key
        )
        self.capture_btn.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(self, text="หน่วงเวลาหลัง Step นี้ (ms)",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(
            anchor="w", padx=24, pady=(20, 6))
        self.delay_entry = ctk.CTkEntry(self, placeholder_text="เช่น 100", fg_color=BG_INPUT,
                                         border_color=BG_CARD_ALT)
        self.delay_entry.insert(0, str(step.get("delay_after", 100)))
        self.delay_entry.pack(fill="x", padx=24)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=24)
        ctk.CTkButton(btn_row, text="ยกเลิก", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=self.destroy).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btn_row, text="บันทึก", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      command=self._save).pack(side="left", expand=True, fill="x", padx=(6, 0))

        self._on_type_change(step["type"])

    def _on_type_change(self, value):
        if value == "delay":
            self.value_entry.configure(placeholder_text="มิลลิวินาที เช่น 500")
            self.capture_btn.configure(state="disabled")
        elif value == "text":
            self.value_entry.configure(placeholder_text="ข้อความที่จะพิมพ์")
            self.capture_btn.configure(state="disabled")
        else:
            self.value_entry.configure(placeholder_text="เช่น enter, ctrl+c, a")
            self.capture_btn.configure(state="normal")

    def _capture_key(self):
        dlg = KeyCaptureDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.value_entry.delete(0, "end")
            self.value_entry.insert(0, dlg.result)

    def _save(self):
        value = self.value_entry.get().strip()
        if not value:
            messagebox.showwarning(APP_TITLE, "กรุณากรอกค่าให้ Step นี้")
            return
        try:
            delay_after = int(self.delay_entry.get().strip() or "0")
        except ValueError:
            messagebox.showwarning(APP_TITLE, "หน่วงเวลาต้องเป็นตัวเลข (ms)")
            return

        self.result = {"type": self.type_var.get(), "value": value, "delay_after": delay_after}
        self.destroy()


# ---------------------------------------------------------------------------
# Macro editor dialog
# ---------------------------------------------------------------------------

class MacroEditorDialog(ctk.CTkToplevel):
    def __init__(self, master, macro=None):
        super().__init__(master)
        self.title("ตั้งค่ามาโคร")
        self.geometry("540x600")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=BG_APP)
        self.result = None

        self.macro = macro or {
            "name": "New Macro", "trigger": "", "repeat": 1, "steps": [], "enabled": True,
        }
        self.steps = list(self.macro["steps"])

        ctk.CTkLabel(self, text="ชื่อมาโคร", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(22, 6))
        self.name_entry = ctk.CTkEntry(self, fg_color=BG_INPUT, border_color=BG_CARD_ALT)
        self.name_entry.insert(0, self.macro["name"])
        self.name_entry.pack(fill="x", padx=24)

        ctk.CTkLabel(self, text="ปุ่ม Trigger (ปุ่มที่กดเพื่อเริ่มมาโคร)",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(
            anchor="w", padx=24, pady=(16, 6))
        trig_row = ctk.CTkFrame(self, fg_color="transparent")
        trig_row.pack(fill="x", padx=24)
        self.trigger_entry = ctk.CTkEntry(trig_row, placeholder_text="เช่น f6, ctrl+shift+m",
                                           fg_color=BG_INPUT, border_color=BG_CARD_ALT)
        self.trigger_entry.insert(0, self.macro["trigger"])
        self.trigger_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(trig_row, text="🎯 จับปุ่ม", width=90, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, command=self._capture_trigger).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(self, text="จำนวนรอบที่ทำซ้ำ (0 = จนกว่าจะกดหยุด)",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(
            anchor="w", padx=24, pady=(16, 6))
        self.repeat_entry = ctk.CTkEntry(self, placeholder_text="1", fg_color=BG_INPUT,
                                          border_color=BG_CARD_ALT)
        self.repeat_entry.insert(0, str(self.macro.get("repeat", 1)))
        self.repeat_entry.pack(fill="x", padx=24)

        ctk.CTkLabel(self, text="ลำดับขั้นตอน (Steps)", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(16, 6))

        list_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        list_frame.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        self.steps_box = tk.Listbox(
            list_frame, bg=BG_CARD, fg=TEXT_MAIN, bd=0, highlightthickness=0,
            selectbackground=ACCENT, font=("Segoe UI", 11), activestyle="none"
        )
        self.steps_box.pack(fill="both", expand=True, padx=8, pady=8)
        self._refresh_steps()

        step_btn_row = ctk.CTkFrame(self, fg_color="transparent")
        step_btn_row.pack(fill="x", padx=24)
        ctk.CTkButton(step_btn_row, text="+ เพิ่ม Step", fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, command=self._add_step).pack(side="left", padx=(0, 6))
        ctk.CTkButton(step_btn_row, text="แก้ไข", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=self._edit_step).pack(side="left", padx=6)
        ctk.CTkButton(step_btn_row, text="ลบ", fg_color=DANGER, hover_color=DANGER_HOVER,
                      command=self._delete_step).pack(side="left", padx=6)
        ctk.CTkButton(step_btn_row, text="⬆", width=36, fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=lambda: self._move_step(-1)).pack(side="left", padx=6)
        ctk.CTkButton(step_btn_row, text="⬇", width=36, fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=lambda: self._move_step(1)).pack(side="left")

        bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        bottom_row.pack(fill="x", padx=24, pady=20)
        ctk.CTkButton(bottom_row, text="ยกเลิก", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=self.destroy).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(bottom_row, text="บันทึกมาโคร", fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, command=self._save).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

    def _refresh_steps(self):
        self.steps_box.delete(0, "end")
        for i, s in enumerate(self.steps, 1):
            if s["type"] == "delay":
                text = f"{i}. ⏱ หน่วงเวลา {s['value']} ms"
            elif s["type"] == "text":
                text = f"{i}. ⌨ พิมพ์ข้อความ: \"{s['value']}\"  (+{s['delay_after']}ms)"
            else:
                text = f"{i}. 🔘 กดปุ่ม: {s['value']}  (+{s['delay_after']}ms)"
            self.steps_box.insert("end", text)

    def _capture_trigger(self):
        dlg = KeyCaptureDialog(self, title="กดปุ่ม Trigger")
        self.wait_window(dlg)
        if dlg.result:
            self.trigger_entry.delete(0, "end")
            self.trigger_entry.insert(0, dlg.result)

    def _add_step(self):
        dlg = StepDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.steps.append(dlg.result)
            self._refresh_steps()

    def _edit_step(self):
        sel = self.steps_box.curselection()
        if not sel:
            return
        idx = sel[0]
        dlg = StepDialog(self, step=self.steps[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.steps[idx] = dlg.result
            self._refresh_steps()

    def _delete_step(self):
        sel = self.steps_box.curselection()
        if not sel:
            return
        del self.steps[sel[0]]
        self._refresh_steps()

    def _move_step(self, direction):
        sel = self.steps_box.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.steps):
            self.steps[idx], self.steps[new_idx] = self.steps[new_idx], self.steps[idx]
            self._refresh_steps()
            self.steps_box.selection_set(new_idx)

    def _save(self):
        name = self.name_entry.get().strip()
        trigger = self.trigger_entry.get().strip()
        if not name or not trigger:
            messagebox.showwarning(APP_TITLE, "กรุณากรอกชื่อมาโครและปุ่ม Trigger")
            return
        if not self.steps:
            messagebox.showwarning(APP_TITLE, "กรุณาเพิ่มอย่างน้อย 1 Step")
            return
        try:
            repeat = int(self.repeat_entry.get().strip() or "1")
        except ValueError:
            messagebox.showwarning(APP_TITLE, "จำนวนรอบต้องเป็นตัวเลข")
            return

        self.result = {
            "name": name, "trigger": trigger, "repeat": repeat,
            "steps": self.steps, "enabled": self.macro.get("enabled", True),
        }
        self.destroy()


# ---------------------------------------------------------------------------
# Macro execution engine
# ---------------------------------------------------------------------------

class MacroEngine:
    def __init__(self, log_callback):
        self.macros = []
        self.running = False
        self.log_callback = log_callback
        self._registered_handles = []  # เก็บ handle ของ hotkey ที่ลงทะเบียนไว้เอง

    def set_macros(self, macros):
        self.macros = macros

    def _unregister_all(self):
        """ยกเลิก hotkey ที่เราลงทะเบียนไว้เอง ทีละตัว (เลี่ยงบั๊กของ keyboard.unhook_all_hotkeys())"""
        for handle in self._registered_handles:
            try:
                keyboard.remove_hotkey(handle)
            except (KeyError, ValueError):
                pass
            except Exception:
                pass
        self._registered_handles = []

    def start(self):
        if keyboard is None:
            self.log_callback("⚠ ไม่พบไลบรารี 'keyboard' กรุณาติดตั้งก่อนใช้งาน (pip install keyboard)")
            self.running = False
            return
        try:
            self._unregister_all()
            for macro in self.macros:
                if macro.get("enabled", True) and macro.get("trigger"):
                    handle = keyboard.add_hotkey(
                        macro["trigger"], lambda m=macro: self._run_macro(m), suppress=False
                    )
                    self._registered_handles.append(handle)
            self.running = True
            self.log_callback("▶ เริ่มทำงานแล้ว (Engine Running) — กดปุ่ม Trigger เพื่อใช้งานมาโคร")
        except Exception as e:
            self.running = False
            self.log_callback(
                f"❌ เริ่มทำงานไม่สำเร็จ: {e}\n"
                f"   💡 สาเหตุที่พบบ่อย: ต้องรันโปรแกรม/exe แบบ \"Run as administrator\" "
                f"เพื่อให้ไลบรารี keyboard ดักจับปุ่มได้ (โดยเฉพาะบน Windows)"
            )

    def stop(self):
        if keyboard is not None:
            self._unregister_all()
        self.running = False
        self.log_callback("⏸ หยุดทำงานแล้ว (Engine Stopped)")

    def _run_macro(self, macro):
        if keyboard is None:
            return
        threading.Thread(target=self._execute, args=(macro,), daemon=True).start()

    def _execute(self, macro):
        self.log_callback(f"⚡ ทำงานมาโคร: {macro['name']}")
        repeat = macro.get("repeat", 1)
        count = 0
        try:
            while True:
                for step in macro["steps"]:
                    if step["type"] == "key":
                        keyboard.send(step["value"])
                    elif step["type"] == "text":
                        keyboard.write(step["value"])
                    delay_ms = step.get("delay_after", 0)
                    if step["type"] == "delay":
                        delay_ms = int(step["value"])
                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)
                count += 1
                if repeat != 0 and count >= repeat:
                    break
        except Exception as e:
            self.log_callback(f"❌ เกิดข้อผิดพลาด: {e}")
        self.log_callback(f"✅ เสร็จสิ้นมาโคร: {macro['name']} (ทำงาน {count} รอบ)")


# ---------------------------------------------------------------------------
# Sidebar navigation button
# ---------------------------------------------------------------------------

class NavButton(ctk.CTkButton):
    def __init__(self, master, text, icon, command):
        super().__init__(
            master, text=f"  {icon}   {text}", anchor="w",
            fg_color="transparent", hover_color=BG_CARD_ALT, text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=13, weight="bold"), height=42, corner_radius=8,
            command=command
        )

    def set_active(self, active):
        if active:
            self.configure(fg_color=ACCENT_SOFT, text_color=ACCENT)
        else:
            self.configure(fg_color="transparent", text_color=TEXT_MUTED)


# ---------------------------------------------------------------------------
# View: Macros (main page)
# ---------------------------------------------------------------------------

class MacrosView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=28, pady=(24, 12))
        ctk.CTkLabel(top, text="🎮 มาโครทั้งหมด", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT_MAIN).pack(side="left")

        self.engine_btn = ctk.CTkButton(
            top, text="▶  เริ่มทำงาน", fg_color=SUCCESS, hover_color=SUCCESS_HOVER,
            text_color="#0C1F16", font=ctk.CTkFont(weight="bold"), width=150, height=38,
            command=self._toggle_engine
        )
        self.engine_btn.pack(side="right")
        ctk.CTkButton(top, text="+ มาโครใหม่", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      width=130, height=38, command=self._new_macro).pack(side="right", padx=(0, 10))

        note = ctk.CTkLabel(
            self, text="💡 หมายเหตุ: เมื่อกด \"เริ่มทำงาน\" ปุ่ม Trigger ที่ตั้งไว้จะถูกดักจับทั่วทั้งเครื่อง "
                       "ใช้ได้ทุกโปรแกรม — แต่ถ้าตั้งปุ่มซ้ำกับ shortcut ของโปรแกรมอื่น อาจเกิดการชนกันได้",
            font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, wraplength=760, justify="left"
        )
        note.pack(fill="x", padx=28, pady=(0, 12))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        left = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=14)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(left, text="รายการมาโคร", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(16, 8))
        self.scroll_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        bottom_actions = ctk.CTkFrame(left, fg_color="transparent")
        bottom_actions.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkButton(bottom_actions, text="💾 บันทึกไฟล์", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=self.app.save_macros).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bottom_actions, text="📂 โหลดไฟล์ใหม่", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, command=self.app.reload_macros).pack(side="left")

        right = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=14, width=300)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        ctk.CTkLabel(right, text="📜 Log กิจกรรม", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(16, 8))
        self.log_box = ctk.CTkTextbox(right, fg_color=BG_INPUT, corner_radius=8, text_color=TEXT_MAIN)
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 16))
        self.log_box.configure(state="disabled")

    def append_log(self, text):
        self.log_box.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def refresh_macro_list(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        if not self.app.macros:
            ctk.CTkLabel(self.scroll_frame, text="ยังไม่มีมาโคร กด '+ มาโครใหม่' เพื่อเริ่มต้น",
                         text_color=TEXT_FAINT).pack(pady=30)
            return

        for i, macro in enumerate(self.app.macros):
            card = ctk.CTkFrame(self.scroll_frame, fg_color=BG_CARD_ALT, corner_radius=10)
            card.pack(fill="x", pady=6, padx=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(10, 2))

            enabled_var = tk.BooleanVar(value=macro.get("enabled", True))
            ctk.CTkCheckBox(
                top_row, text="", variable=enabled_var, width=20, fg_color=ACCENT,
                hover_color=ACCENT_HOVER, command=lambda idx=i, v=enabled_var: self._toggle_enabled(idx, v)
            ).pack(side="left")

            ctk.CTkLabel(top_row, text=macro["name"], font=ctk.CTkFont(size=15, weight="bold"),
                         text_color=TEXT_MAIN).pack(side="left", padx=(6, 0))
            ctk.CTkLabel(top_row, text=f"Trigger: [{macro['trigger']}]", text_color=ACCENT,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side="right")

            info_row = ctk.CTkFrame(card, fg_color="transparent")
            info_row.pack(fill="x", padx=14, pady=(0, 10))
            repeat_txt = "จนกว่าจะหยุด" if macro.get("repeat", 1) == 0 else f"{macro.get('repeat', 1)} รอบ"
            ctk.CTkLabel(info_row, text=f"{len(macro['steps'])} steps  •  ทำซ้ำ {repeat_txt}",
                         text_color=TEXT_MUTED, font=ctk.CTkFont(size=11)).pack(side="left")

            ctk.CTkButton(info_row, text="แก้ไข", width=60, height=26, fg_color="transparent",
                          border_width=1, border_color=TEXT_FAINT,
                          command=lambda idx=i: self._edit_macro(idx)).pack(side="right", padx=4)
            ctk.CTkButton(info_row, text="ลบ", width=50, height=26, fg_color=DANGER,
                          hover_color=DANGER_HOVER, command=lambda idx=i: self._delete_macro(idx)).pack(
                side="right", padx=4)

    def _new_macro(self):
        dlg = MacroEditorDialog(self.app)
        self.wait_window(dlg)
        if dlg.result:
            self.app.macros.append(dlg.result)
            self.app.save_macros()
            self.refresh_macro_list()
            self.append_log(f"➕ เพิ่มมาโครใหม่: {dlg.result['name']}")

    def _edit_macro(self, idx):
        dlg = MacroEditorDialog(self.app, macro=self.app.macros[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.app.macros[idx] = dlg.result
            self.app.save_macros()
            self.refresh_macro_list()
            self.append_log(f"✏ แก้ไขมาโคร: {dlg.result['name']}")

    def _delete_macro(self, idx):
        name = self.app.macros[idx]["name"]

        def do_delete():
            del self.app.macros[idx]
            self.app.save_macros()
            self.refresh_macro_list()
            self.append_log(f"🗑 ลบมาโคร: {name}")

        ConfirmActionDialog(
            self.app, title="ยืนยันการลบมาโคร",
            message=f"คุณกำลังจะลบมาโคร \"{name}\" การกระทำนี้ไม่สามารถย้อนกลับได้ผ่านหน้าจอนี้",
            pros=["รายการมาโครจะสะอาดขึ้น ไม่มีของที่ไม่ใช้แล้ว"],
            cons=["ขั้นตอนและปุ่ม Trigger ของมาโครนี้จะหายไปทันที",
                  "ถ้ายังไม่เคย Export Backup ไว้ จะกู้คืนไม่ได้อีก"],
            confirm_text="ลบมาโครนี้", confirm_color=DANGER, confirm_hover=DANGER_HOVER,
            icon="🗑️", on_confirm=do_delete
        )

    def _toggle_enabled(self, idx, var):
        self.app.macros[idx]["enabled"] = var.get()
        self.app.save_macros()
        if self.app.engine.running:
            self.app.engine.set_macros(self.app.macros)
            self.app.engine.start()

    def _toggle_engine(self):
        if self.app.engine.running:
            self.app.engine.stop()
            self.engine_btn.configure(text="▶  เริ่มทำงาน", fg_color=SUCCESS, hover_color=SUCCESS_HOVER)
        else:
            self.app.engine.set_macros(self.app.macros)
            self.app.engine.start()
            if self.app.engine.running:
                self.engine_btn.configure(text="⏸  หยุดทำงาน", fg_color=DANGER, hover_color=DANGER_HOVER)
            else:
                messagebox.showerror(
                    APP_TITLE,
                    "ไม่สามารถเริ่มทำงาน Engine ได้\n\n"
                    "สาเหตุที่พบบ่อยที่สุด: ต้องรันโปรแกรมแบบ \"Run as administrator\" "
                    "(คลิกขวาที่ไฟล์ .exe หรือเปิด Command Prompt/Terminal แบบ Admin ก่อนรัน python)\n\n"
                    "ดูรายละเอียด error เต็มๆ ได้ที่ช่อง Log กิจกรรมด้านขวา"
                )


# ---------------------------------------------------------------------------
# View: Backup & Restore
# ---------------------------------------------------------------------------

class BackupView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _section_card(self, parent, title, icon):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=14)
        card.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(card, text=f"{icon}  {title}", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(18, 10))
        return card

    def _bullet(self, parent, text, color):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(row, text="●", text_color=color, font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row, text=text, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED,
                     wraplength=680, justify="left").pack(side="left", fill="x")

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 6))
        ctk.CTkLabel(header, text="💾 Backup & Restore Center", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(header, text="สำรองและกู้คืนมาโครทั้งหมดของคุณอย่างปลอดภัย",
                     font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=28, pady=(12, 20))

        # --- Card 1: What is backup (always-visible explanation) ---
        c1 = self._section_card(scroll, "Backup คืออะไร?", "ℹ️")
        ctk.CTkLabel(c1, text="Backup คือการบันทึกมาโครทั้งหมดที่ตั้งค่าไว้ ณ ตอนนั้น เก็บเป็นไฟล์ .json "
                              "แยกต่างหาก เพื่อให้กู้คืนกลับมาได้ภายหลัง แม้จะลบ หรือรีเซ็ตโปรแกรมไปแล้ว",
                     font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, wraplength=680, justify="left").pack(
            anchor="w", padx=20, pady=(0, 10))
        self._bullet(c1, "ข้อดี: ป้องกันข้อมูลสูญหายจากการลบผิด รีเซ็ตผิด หรือเครื่องมีปัญหา", SUCCESS)
        self._bullet(c1, "ข้อดี: ย้ายมาโครไปใช้กับเครื่องอื่นได้ทันที แค่เอาไฟล์ไปวาง", SUCCESS)
        self._bullet(c1, "ข้อควรระวัง: ไฟล์ backup ไม่ได้เข้ารหัส ถ้ามีข้อมูลอ่อนไหวในข้อความมาโคร ควรเก็บไฟล์ให้ปลอดภัย", WARNING)
        ctk.CTkLabel(c1, text="", height=6).pack()

        # --- Card 2: Export ---
        c2 = self._section_card(scroll, "ส่งออกไฟล์ Backup (Export)", "📤")
        ctk.CTkLabel(c2, text="บันทึกมาโครทั้งหมดที่มีอยู่ตอนนี้ ให้เป็นไฟล์ .json เพื่อเก็บไว้เป็นหลักฐาน",
                     font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, wraplength=680, justify="left").pack(
            anchor="w", padx=20, pady=(0, 10))
        self._bullet(c2, "ข้อดี: ทำได้ไม่จำกัดจำนวนครั้ง ไม่กระทบมาโครที่ใช้งานอยู่เลย", SUCCESS)
        self._bullet(c2, "ข้อควรระวัง: ต้องมากด Export เองทุกครั้งที่แก้ไขมาโคร ระบบไม่ backup ให้อัตโนมัติ", WARNING)
        ctk.CTkButton(c2, text="📤 Export Backup ตอนนี้", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      height=40, command=self._export_backup).pack(anchor="w", padx=20, pady=(6, 20))

        # --- Card 3: Import / Restore (drag & drop) ---
        c3 = self._section_card(scroll, "กู้คืนจากไฟล์ Backup (Restore)", "📥")
        dnd_hint = "ลากไฟล์ .json มาวางในกล่องด้านล่างได้เลย" if DND_AVAILABLE else \
            "เครื่องนี้ยังไม่รองรับลากไฟล์วางโดยตรง (ไม่พบ tkinterdnd2) กรุณาใช้ปุ่มเลือกไฟล์แทน"
        ctk.CTkLabel(c3, text=dnd_hint, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED,
                     wraplength=680, justify="left").pack(anchor="w", padx=20, pady=(0, 10))
        self._bullet(c3, "ข้อดี: กู้คืนมาโครทั้งหมดกลับมาเหมือนตอนที่ backup ไว้ได้ในไม่กี่วินาที", SUCCESS)
        self._bullet(c3, "ข้อควรระวัง: มาโครปัจจุบันทั้งหมดจะถูกแทนที่ด้วยข้อมูลในไฟล์ backup ทันที", DANGER)
        self._bullet(c3, "ข้อควรระวัง: ถ้ามาโครที่เพิ่งแก้ไขล่าสุดยังไม่ได้ backup ไว้ จะหายไปหลังกู้คืน", DANGER)

        self.drop_zone = ctk.CTkFrame(c3, fg_color=BG_INPUT, corner_radius=12, height=110,
                                       border_width=2, border_color=TEXT_FAINT)
        self.drop_zone.pack(fill="x", padx=20, pady=(10, 6))
        self.drop_zone.pack_propagate(False)
        ctk.CTkLabel(self.drop_zone, text="📁  ลากไฟล์ Backup (.json) มาวางที่นี่",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MUTED).pack(expand=True)

        if DND_AVAILABLE:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        ctk.CTkButton(c3, text="📁 เลือกไฟล์ Backup...", fg_color="transparent", border_width=1,
                      border_color=TEXT_FAINT, height=38,
                      command=self._browse_backup).pack(anchor="w", padx=20, pady=(0, 20))

        # --- Card 4: Reset to default ---
        c4 = self._section_card(scroll, "รีเซ็ตกลับเป็นค่าเริ่มต้น (Factory Reset)", "🔄")
        ctk.CTkLabel(c4, text="ล้างมาโครทั้งหมดในโปรแกรม กลับไปเป็นสถานะว่างเปล่าเหมือนเปิดใช้งานครั้งแรก",
                     font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, wraplength=680, justify="left").pack(
            anchor="w", padx=20, pady=(0, 10))
        self._bullet(c4, "ข้อดี: เริ่มต้นใหม่แบบสะอาด เหมาะเวลามาโครเยอะจนสับสน หรือมีปัญหาที่แก้ไม่ได้", SUCCESS)
        self._bullet(c4, "ข้อดี: ระบบจะสร้าง Safety Backup ให้อัตโนมัติก่อนล้างข้อมูลเสมอ", SUCCESS)
        self._bullet(c4, "ข้อควรระวัง: มาโครทั้งหมดในหน้าจอหลักจะหายไปทันทีหลังยืนยัน", DANGER)
        ctk.CTkButton(c4, text="🔄 รีเซ็ตเป็นค่าเริ่มต้น", fg_color=DANGER, hover_color=DANGER_HOVER,
                      height=40, command=self._reset_to_default).pack(anchor="w", padx=20, pady=(6, 20))

    # -- Export --------------------------------------------------------
    def _export_backup(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        default_name = f"neki_backup_{timestamp()}.json"
        path = filedialog.asksaveasfilename(
            title="บันทึกไฟล์ Backup", initialdir=BACKUP_DIR, initialfile=default_name,
            defaultextension=".json", filetypes=[("JSON files", "*.json")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.app.macros, f, ensure_ascii=False, indent=2)
            self.app.log(f"📤 Export Backup สำเร็จ: {os.path.basename(path)}")
            messagebox.showinfo(APP_TITLE, f"บันทึกไฟล์ Backup สำเร็จแล้ว:\n{path}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"ไม่สามารถบันทึกไฟล์ได้: {e}")

    # -- Import / Restore ----------------------------------------------
    def _browse_backup(self):
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ Backup", initialdir=BACKUP_DIR if os.path.isdir(BACKUP_DIR) else APP_DIR,
            filetypes=[("JSON files", "*.json")]
        )
        if path:
            self._handle_backup_file(path)

    def _on_drop(self, event):
        path = event.data.strip("{}")
        self._handle_backup_file(path)

    def _handle_backup_file(self, path):
        if not path.lower().endswith(".json") or not os.path.isfile(path):
            messagebox.showerror(APP_TITLE, "กรุณาเลือกไฟล์ .json ที่เป็น Backup ของ Neki Macro เท่านั้น")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"ไม่สามารถอ่านไฟล์นี้ได้: {e}")
            return

        if not validate_macro_list(data):
            messagebox.showerror(APP_TITLE, "ไฟล์นี้ไม่ใช่รูปแบบ Backup ของ Neki Macro ที่ถูกต้อง")
            return

        count = len(data)

        def do_restore():
            if self.app.engine.running:
                self.app.engine.stop()
                self.app.macros_view.engine_btn.configure(
                    text="▶  เริ่มทำงาน", fg_color=SUCCESS, hover_color=SUCCESS_HOVER)
            self.app.macros = data
            self.app.save_macros()
            self.app.macros_view.refresh_macro_list()
            self.app.log(f"📥 กู้คืน Backup สำเร็จ: {os.path.basename(path)} ({count} มาโคร)")
            messagebox.showinfo(APP_TITLE, f"กู้คืนมาโครสำเร็จแล้ว ({count} รายการ)")

        ConfirmActionDialog(
            self.app, title="ยืนยันการกู้คืน Backup",
            message=f"ไฟล์นี้มีมาโครทั้งหมด {count} รายการ หากยืนยัน มาโครปัจจุบันทั้งหมดในโปรแกรมจะถูกแทนที่ทันที",
            pros=[f"มาโคร {count} รายการจากไฟล์ backup จะกลับมาใช้งานได้ทันที",
                  "Engine จะถูกหยุดชั่วคราวเพื่อความปลอดภัย ก่อนโหลดข้อมูลใหม่"],
            cons=["มาโครที่มีอยู่ในโปรแกรมตอนนี้ (ที่ยังไม่ได้ backup) จะหายไปถาวร",
                  "ต้องกด \"เริ่มทำงาน\" ใหม่อีกครั้งหลังกู้คืนเสร็จ"],
            confirm_text="ยืนยันกู้คืน", confirm_color=WARNING, confirm_hover="#D98C0A",
            icon="📥", on_confirm=do_restore
        )

    # -- Reset -----------------------------------------------------------
    def _reset_to_default(self):
        current_count = len(self.app.macros)

        def do_reset():
            # Safety auto-backup before wiping
            os.makedirs(BACKUP_DIR, exist_ok=True)
            safety_path = os.path.join(BACKUP_DIR, f"neki_autobackup_{timestamp()}.json")
            try:
                with open(safety_path, "w", encoding="utf-8") as f:
                    json.dump(self.app.macros, f, ensure_ascii=False, indent=2)
            except Exception:
                safety_path = None

            if self.app.engine.running:
                self.app.engine.stop()
                self.app.macros_view.engine_btn.configure(
                    text="▶  เริ่มทำงาน", fg_color=SUCCESS, hover_color=SUCCESS_HOVER)

            self.app.macros = []
            self.app.save_macros()
            self.app.macros_view.refresh_macro_list()
            if safety_path:
                self.app.log(f"🔄 รีเซ็ตเป็นค่าเริ่มต้นแล้ว (สร้าง safety backup: {os.path.basename(safety_path)})")
            else:
                self.app.log("🔄 รีเซ็ตเป็นค่าเริ่มต้นแล้ว")

        ConfirmActionDialog(
            self.app, title="ยืนยันการรีเซ็ตเป็นค่าเริ่มต้น",
            message=f"ขณะนี้มีมาโครอยู่ทั้งหมด {current_count} รายการ หากยืนยัน ระบบจะล้างมาโครทั้งหมด "
                     "กลับไปเป็นค่าว่างเปล่าเหมือนเปิดโปรแกรมครั้งแรก",
            pros=["ระบบจะสร้าง Safety Backup ให้อัตโนมัติก่อนล้างข้อมูลเสมอ (กู้คืนได้ภายหลังจากหน้า Restore)",
                  "เริ่มต้นใหม่แบบสะอาด ไม่มีมาโครเก่าที่ไม่ใช้แล้วรบกวน"],
            cons=[f"มาโครทั้งหมด {current_count} รายการจะหายไปจากหน้าจอหลักทันที",
                  "ต้องตั้งค่ามาโครใหม่ทั้งหมด หรือกู้คืนจาก Safety Backup เอง"],
            confirm_text="ยืนยันรีเซ็ต", confirm_color=DANGER, confirm_hover=DANGER_HOVER,
            icon="🔄", on_confirm=do_reset
        )


# ---------------------------------------------------------------------------
# Root window base (adds drag & drop support if available)
# ---------------------------------------------------------------------------

if DND_AVAILABLE:
    class _RootBase(TkinterDnD.DnDWrapper, ctk.CTk):
        def __init__(self, *args, **kwargs):
            ctk.CTk.__init__(self, *args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    _RootBase = ctk.CTk


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

class NekiMacroApp(_RootBase):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x640")
        self.minsize(860, 560)
        self.configure(fg_color=BG_APP)

        self.macros = load_macros()
        self.engine = MacroEngine(self.log)

        self._build_ui()
        self.macros_view.refresh_macro_list()
        self.show_view("macros")

    # -- UI construction -----------------------------------------------
    def _build_ui(self):
        root_row = ctk.CTkFrame(self, fg_color="transparent")
        root_row.pack(fill="both", expand=True)

        # Sidebar
        sidebar = ctk.CTkFrame(root_row, fg_color=BG_SIDEBAR, corner_radius=0, width=230)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_box.pack(fill="x", padx=20, pady=(26, 30))
        ctk.CTkLabel(logo_box, text="⌨ Neki Macro", font=ctk.CTkFont(size=19, weight="bold"),
                     text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(logo_box, text="v.1 — Written By Neki", font=ctk.CTkFont(size=11),
                     text_color=TEXT_FAINT).pack(anchor="w")

        nav_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_box.pack(fill="x", padx=14)

        self.nav_buttons = {}
        self.nav_buttons["macros"] = NavButton(nav_box, "มาโคร", "🎮", lambda: self.show_view("macros"))
        self.nav_buttons["macros"].pack(fill="x", pady=3)
        self.nav_buttons["backup"] = NavButton(nav_box, "Backup & Restore", "💾", lambda: self.show_view("backup"))
        self.nav_buttons["backup"].pack(fill="x", pady=3)

        # Status footer in sidebar
        status_box = ctk.CTkFrame(sidebar, fg_color=BG_CARD, corner_radius=10)
        status_box.pack(side="bottom", fill="x", padx=14, pady=20)
        kb_ok = keyboard is not None
        dnd_ok = DND_AVAILABLE
        ctk.CTkLabel(status_box, text="สถานะระบบ", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(status_box, text=f"{'✅' if kb_ok else '⚠️'} คีย์บอร์ด hook",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MAIN).pack(anchor="w", padx=12)
        ctk.CTkLabel(status_box, text=f"{'✅' if dnd_ok else '⚠️'} ลากไฟล์วาง",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MAIN).pack(anchor="w", padx=12, pady=(0, 10))

        # Content container
        self.content = ctk.CTkFrame(root_row, fg_color=BG_APP, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.macros_view = MacrosView(self.content, self)
        self.backup_view = BackupView(self.content, self)
        self.macros_view.grid(row=0, column=0, sticky="nsew")
        self.backup_view.grid(row=0, column=0, sticky="nsew")

    def show_view(self, name):
        for key, btn in self.nav_buttons.items():
            btn.set_active(key == name)
        if name == "macros":
            self.macros_view.tkraise()
        else:
            self.backup_view.tkraise()

    # -- Shared actions ---------------------------------------------------
    def save_macros(self):
        save_macros(self.macros)

    def reload_macros(self):
        self.macros = load_macros()
        self.macros_view.refresh_macro_list()
        self.log("📂 โหลดมาโครจากไฟล์เรียบร้อย")

    def log(self, text):
        def append():
            self.macros_view.append_log(text)
        try:
            self.after(0, append)
        except Exception:
            pass


if __name__ == "__main__":
    app = NekiMacroApp()
    app.mainloop()
