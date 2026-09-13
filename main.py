import json
import os
import threading
import time
import tkinter as tk
import winsound
from datetime import datetime
from tkinter import messagebox, ttk

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarms.json")
DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def load_alarms():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_alarms(alarms):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(alarms, f, ensure_ascii=False, indent=2)


class Ringer:
    def __init__(self):
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            winsound.Beep(1000, 500)
            time.sleep(0.2)

    def stop(self):
        self._stop.set()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("윈도우 알람")
        self.geometry("480x360")
        self.alarms = load_alarms()
        self.last_triggered = {}

        self._build_ui()
        self._refresh_list()
        self.after(1000, self._check_alarms)

    def _build_ui(self):
        columns = ("time", "days", "label", "enabled")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("time", text="시각")
        self.tree.heading("days", text="반복 요일")
        self.tree.heading("label", text="이름")
        self.tree.heading("enabled", text="사용")
        self.tree.column("time", width=80, anchor="center")
        self.tree.column("days", width=140, anchor="center")
        self.tree.column("label", width=140, anchor="center")
        self.tree.column("enabled", width=60, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", lambda e: self._toggle_selected())

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="추가", command=self._open_add_dialog).pack(side="left")
        ttk.Button(btn_frame, text="삭제", command=self._delete_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="켜기/끄기", command=self._toggle_selected).pack(side="left")

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for alarm in self.alarms:
            if alarm["days"]:
                days_text = ",".join(DAY_LABELS[d] for d in alarm["days"])
            else:
                days_text = "한 번만"
            self.tree.insert(
                "",
                "end",
                iid=alarm["id"],
                values=(alarm["time"], days_text, alarm["label"], "ON" if alarm["enabled"] else "OFF"),
            )

    def _open_add_dialog(self):
        AddAlarmDialog(self, on_save=self._add_alarm)

    def _add_alarm(self, time_str, days, label):
        new_id = str(int(time.time() * 1000))
        self.alarms.append(
            {"id": new_id, "time": time_str, "days": days, "label": label, "enabled": True}
        )
        save_alarms(self.alarms)
        self._refresh_list()

    def _get_selected_id(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return selection[0]

    def _delete_selected(self):
        alarm_id = self._get_selected_id()
        if alarm_id is None:
            return
        self.alarms = [a for a in self.alarms if a["id"] != alarm_id]
        save_alarms(self.alarms)
        self._refresh_list()

    def _toggle_selected(self):
        alarm_id = self._get_selected_id()
        if alarm_id is None:
            return
        for alarm in self.alarms:
            if alarm["id"] == alarm_id:
                alarm["enabled"] = not alarm["enabled"]
        save_alarms(self.alarms)
        self._refresh_list()

    def _check_alarms(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_weekday = now.weekday()
        current_stamp = now.strftime("%Y-%m-%d %H:%M")

        for alarm in self.alarms:
            if not alarm["enabled"] or alarm["time"] != current_time:
                continue
            if alarm["days"] and current_weekday not in alarm["days"]:
                continue
            if self.last_triggered.get(alarm["id"]) == current_stamp:
                continue

            self.last_triggered[alarm["id"]] = current_stamp
            if not alarm["days"]:
                alarm["enabled"] = False
                save_alarms(self.alarms)
                self._refresh_list()
            self._trigger_alarm(alarm)

        self.after(1000, self._check_alarms)

    def _trigger_alarm(self, alarm):
        ringer = Ringer()
        ringer.start()

        popup = tk.Toplevel(self)
        popup.title("알람")
        popup.attributes("-topmost", True)
        popup.geometry("300x150")

        message = alarm["label"] or "알람 시간입니다"
        ttk.Label(popup, text=message, font=("맑은 고딕", 14)).pack(pady=(20, 5))
        ttk.Label(popup, text=alarm["time"]).pack()

        def stop():
            ringer.stop()
            popup.destroy()

        ttk.Button(popup, text="끄기", command=stop).pack(pady=15)
        popup.protocol("WM_DELETE_WINDOW", stop)


class AddAlarmDialog(tk.Toplevel):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.title("알람 추가")
        self.geometry("300x260")
        self.on_save = on_save
        self.resizable(False, False)

        ttk.Label(self, text="시각 (시:분)").pack(pady=(15, 0))
        time_frame = ttk.Frame(self)
        time_frame.pack(pady=5)
        self.hour_var = tk.StringVar(value="07")
        self.minute_var = tk.StringVar(value="00")
        ttk.Spinbox(
            time_frame, from_=0, to=23, wrap=True, width=3, format="%02.0f",
            textvariable=self.hour_var,
        ).pack(side="left")
        ttk.Label(time_frame, text=":").pack(side="left")
        ttk.Spinbox(
            time_frame, from_=0, to=59, wrap=True, width=3, format="%02.0f",
            textvariable=self.minute_var,
        ).pack(side="left")

        ttk.Label(self, text="반복 요일 (선택 없으면 한 번만 실행)").pack(pady=(15, 0))
        day_frame = ttk.Frame(self)
        day_frame.pack(pady=5)
        self.day_vars = []
        for label in DAY_LABELS:
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(day_frame, text=label, variable=var).pack(side="left")
            self.day_vars.append(var)

        ttk.Label(self, text="이름 (선택)").pack(pady=(15, 0))
        self.label_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.label_var).pack(pady=5)

        ttk.Button(self, text="저장", command=self._save).pack(pady=15)

    def _save(self):
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            time_str = f"{hour:02d}:{minute:02d}"
        except ValueError:
            messagebox.showerror("오류", "시각을 올바르게 입력하세요.")
            return

        days = [i for i, var in enumerate(self.day_vars) if var.get()]
        label = self.label_var.get().strip()
        self.on_save(time_str, days, label)
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
