# -*- coding: utf-8 -*-
"""
Фонова служба (Android Foreground Service).

Працює НЕЗАЛЕЖНО від головного застосунку - продовжує перевіряти час
і надсилати сповіщення, навіть якщо користувач повністю закрив застосунок.

Важливо: назва підпапки APP_DIR_NAME має збігатися з тим, що Kivy
автоматично використовує для App.user_data_dir (це похідне від назви
класу застосунку LensTrackerApp -> "lenstracker"), щоб служба читала
той самий файл даних, що й головний застосунок.
"""

import json
import os
import time
from datetime import datetime

from jnius import autoclass

try:
    from plyer import notification
except Exception:
    notification = None

DATA_FILE_NAME = "lens_data.json"
APP_DIR_NAME = "lenstracker"
CHECK_INTERVAL_SECONDS = 30


def get_data_path():
    """Той самий шлях до файлу даних, що використовує головний застосунок."""
    PythonService = autoclass("org.kivy.android.PythonService")
    context = PythonService.mService
    files_dir = context.getFilesDir().getAbsolutePath()
    app_dir = os.path.join(files_dir, APP_DIR_NAME)
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, DATA_FILE_NAME)


def load_data():
    path = get_data_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_data(data):
    path = get_data_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def send_notification():
    if notification is None:
        return
    try:
        notification.notify(
            title="Нагадування про лінзи",
            message="Не забудьте відмітити сьогоднішній день носіння лінз!",
            timeout=10,
        )
    except Exception:
        pass


def main_loop():
    # Дозволяє Android перезапустити службу автоматично, якщо систему
    # довелось "вбити" через нестачу пам'яті
    try:
        PythonService = autoclass("org.kivy.android.PythonService")
        PythonService.mService.setAutoRestartService(True)
    except Exception:
        pass

    while True:
        data = load_data()
        if data and data.get("reminder_enabled"):
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if (
                now.hour == data.get("reminder_hour")
                and now.minute == data.get("reminder_minute")
                and data.get("last_notified_date") != today_str
            ):
                data["last_notified_date"] = today_str
                save_data(data)
                send_notification()
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main_loop()
