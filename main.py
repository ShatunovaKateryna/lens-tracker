# -*- coding: utf-8 -*-
"""
Lens Tracker - застосунок для відстеження днів носіння контактних лінз.
Бібліотеки: kivy (UI, повністю сумісний з buildozer), plyer (сповіщення).
"""

import json
import os
from datetime import date, datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

try:
    from plyer import notification
except Exception:
    notification = None

TOTAL_DAYS = 30
DATA_FILE_NAME = "lens_data.json"


def get_data_path(app):
    """
    Шлях до файлу даних у ПРИВАТНОМУ внутрішньому сховищі застосунку.

    app.user_data_dir - це офіційний механізм Kivy:
    - на Android це внутрішня папка застосунку
      (аналог /data/data/<package.domain>.<package.name>/files),
      куди дозволено писати БЕЗ будь-яких дозволів (permissions);
    - на Windows/Linux/Mac це папка типу
      ~/.local/share/<AppName> або %APPDATA%/<AppName>.
    Ніякого доступу до "кореня програми" (APK, який лише для читання)
    тут немає і не використовується.
    """
    base = app.user_data_dir
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, DATA_FILE_NAME)


def default_data():
    today = date.today()
    return {
        "open_day": today.day,
        "open_month": today.month,
        "open_year": today.year,
        "checked": [False] * TOTAL_DAYS,
        "reminder_enabled": False,
        "reminder_hour": 20,
        "reminder_minute": 0,
        "last_notified_date": "",
    }


class ConfirmPopup(Popup):
    """Спливаюче вікно підтвердження дії (для скидання даних)."""

    def __init__(self, on_confirm, **kwargs):
        super().__init__(**kwargs)
        self.title = "Підтвердження"
        self.size_hint = (0.85, 0.35)
        self.auto_dismiss = False

        layout = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        layout.add_widget(Label(
            text="Ви справді хочете скинути дані?\nВесь прогрес носіння лінз буде видалено.",
            halign="center"
        ))

        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        yes_btn = Button(text="Так, скинути")
        no_btn = Button(text="Скасувати")

        def confirm(_instance):
            self.dismiss()
            on_confirm()

        def cancel(_instance):
            self.dismiss()

        yes_btn.bind(on_release=confirm)
        no_btn.bind(on_release=cancel)

        btn_row.add_widget(no_btn)
        btn_row.add_widget(yes_btn)

        layout.add_widget(btn_row)
        self.content = layout


class DatePopup(Popup):
    """Вибір дати відкриття коробки лінз."""

    def __init__(self, current, on_save, **kwargs):
        super().__init__(**kwargs)
        self.title = "Дата відкриття коробки"
        self.size_hint = (0.9, 0.5)
        self.auto_dismiss = False

        layout = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))

        row = BoxLayout(spacing=dp(5), size_hint_y=None, height=dp(48))
        days = [str(d) for d in range(1, 32)]
        months = [str(m) for m in range(1, 13)]
        years = [str(y) for y in range(date.today().year - 1, date.today().year + 2)]

        self.day_spinner = Spinner(text=str(current["open_day"]), values=days)
        self.month_spinner = Spinner(text=str(current["open_month"]), values=months)
        self.year_spinner = Spinner(text=str(current["open_year"]), values=years)

        row.add_widget(Label(text="День:"))
        row.add_widget(self.day_spinner)
        row.add_widget(Label(text="Місяць:"))
        row.add_widget(self.month_spinner)
        row.add_widget(Label(text="Рік:"))
        row.add_widget(self.year_spinner)

        layout.add_widget(row)

        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        save_btn = Button(text="Зберегти")
        cancel_btn = Button(text="Скасувати")

        def save(_instance):
            self.dismiss()
            on_save(
                int(self.day_spinner.text),
                int(self.month_spinner.text),
                int(self.year_spinner.text),
            )

        def cancel(_instance):
            self.dismiss()

        save_btn.bind(on_release=save)
        cancel_btn.bind(on_release=cancel)
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(save_btn)
        layout.add_widget(btn_row)

        self.content = layout


class ReminderPopup(Popup):
    """Налаштування сповіщень (час і увімкнення/вимкнення)."""

    def __init__(self, current, on_save, **kwargs):
        super().__init__(**kwargs)
        self.title = "Налаштування сповіщень"
        self.size_hint = (0.9, 0.5)
        self.auto_dismiss = False

        layout = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))

        enable_row = BoxLayout(size_hint_y=None, height=dp(48))
        self.enable_checkbox = CheckBox(active=current["reminder_enabled"])
        enable_row.add_widget(Label(text="Увімкнути щоденне нагадування"))
        enable_row.add_widget(self.enable_checkbox)
        layout.add_widget(enable_row)

        time_row = BoxLayout(size_hint_y=None, height=dp(48))
        hours = [f"{h:02d}" for h in range(24)]
        minutes = [f"{m:02d}" for m in range(0, 60, 5)]
        self.hour_spinner = Spinner(text=f'{current["reminder_hour"]:02d}', values=hours)
        self.minute_spinner = Spinner(text=f'{current["reminder_minute"]:02d}', values=minutes)
        time_row.add_widget(Label(text="Час нагадування:"))
        time_row.add_widget(self.hour_spinner)
        time_row.add_widget(Label(text=":"))
        time_row.add_widget(self.minute_spinner)
        layout.add_widget(time_row)

        layout.add_widget(Label(
            text="Нагадування спрацьовує, поки застосунок відкритий\n"
                 "або працює у фоні на пристрої.",
            font_size="12sp"
        ))

        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        save_btn = Button(text="Зберегти")
        cancel_btn = Button(text="Скасувати")

        def save(_instance):
            self.dismiss()
            on_save(
                self.enable_checkbox.active,
                int(self.hour_spinner.text),
                int(self.minute_spinner.text),
            )

        def cancel(_instance):
            self.dismiss()

        save_btn.bind(on_release=save)
        cancel_btn.bind(on_release=cancel)
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(save_btn)
        layout.add_widget(btn_row)

        self.content = layout


class LensTrackerRoot(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(12), **kwargs)
        self.app = app
        self.data = None
        self.checkboxes = []

        self.date_label = Label(
            text="", size_hint_y=None, height=dp(30), font_size="16sp"
        )
        self.days_left_label = Label(
            text="", size_hint_y=None, height=dp(40), font_size="22sp", bold=True
        )

        self.add_widget(self.date_label)
        self.add_widget(self.days_left_label)

        date_btn = Button(
            text="Змінити дату відкриття коробки", size_hint_y=None, height=dp(44)
        )
        date_btn.bind(on_release=lambda _i: self.open_date_popup())
        self.add_widget(date_btn)

        # Сітка 30 чекбоксів (5 колонок x 6 рядків)
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=5, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for i in range(TOTAL_DAYS):
            cell = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(70))
            lbl = Label(text=f"День {i + 1}", font_size="12sp", size_hint_y=None, height=dp(20))
            cb = CheckBox(size_hint_y=None, height=dp(40))
            cb.bind(active=self.make_checkbox_callback(i))
            cell.add_widget(lbl)
            cell.add_widget(cb)
            grid.add_widget(cell)
            self.checkboxes.append(cb)

        scroll.add_widget(grid)
        self.add_widget(scroll)

        bottom_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        reminder_btn = Button(text="Налаштування сповіщень")
        reset_btn = Button(text="Скинути дані")
        reminder_btn.bind(on_release=lambda _i: self.open_reminder_popup())
        reset_btn.bind(on_release=lambda _i: self.open_reset_popup())
        bottom_row.add_widget(reminder_btn)
        bottom_row.add_widget(reset_btn)
        self.add_widget(bottom_row)

        self.load_data()
        self.refresh_ui()

    # ---------- Дані ----------

    def load_data(self):
        path = get_data_path(self.app)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                    if len(self.data.get("checked", [])) != TOTAL_DAYS:
                        self.data["checked"] = [False] * TOTAL_DAYS
            except Exception:
                self.data = default_data()
        else:
            self.data = default_data()

    def save_data(self):
        path = get_data_path(self.app)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ---------- UI-логіка ----------

    def make_checkbox_callback(self, index):
        def callback(_checkbox, value):
            self.data["checked"][index] = value
            self.save_data()
            self.update_days_left()
        return callback

    def refresh_ui(self):
        d, m, y = self.data["open_day"], self.data["open_month"], self.data["open_year"]
        self.date_label.text = f"Дата відкриття коробки: {d:02d}.{m:02d}.{y}"
        for i, cb in enumerate(self.checkboxes):
            cb.active = self.data["checked"][i]
        self.update_days_left()

    def update_days_left(self):
        worn = sum(1 for v in self.data["checked"] if v)
        left = max(0, TOTAL_DAYS - worn)
        if left == 0:
            self.days_left_label.text = "Термін носіння лінз завершено! Час замінити лінзи."
        else:
            self.days_left_label.text = f"Залишилось днів носіння: {left}"

    # ---------- Попапи ----------

    def open_date_popup(self):
        def on_save(d, m, y):
            self.data["open_day"] = d
            self.data["open_month"] = m
            self.data["open_year"] = y
            self.save_data()
            self.refresh_ui()

        DatePopup(self.data, on_save).open()

    def open_reminder_popup(self):
        def on_save(enabled, hour, minute):
            self.data["reminder_enabled"] = enabled
            self.data["reminder_hour"] = hour
            self.data["reminder_minute"] = minute
            self.save_data()

        ReminderPopup(self.data, on_save).open()

    def open_reset_popup(self):
        def on_confirm():
            self.data = default_data()
            self.save_data()
            self.refresh_ui()

        ConfirmPopup(on_confirm).open()

    # ---------- Перевірка нагадувань ----------

    def check_reminder(self, _dt):
        if not self.data.get("reminder_enabled"):
            return
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        if (
            now.hour == self.data.get("reminder_hour")
            and now.minute == self.data.get("reminder_minute")
            and self.data.get("last_notified_date") != today_str
        ):
            self.data["last_notified_date"] = today_str
            self.save_data()
            self.send_notification()

    def send_notification(self):
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


class LensTrackerApp(App):
    def build(self):
        self.title = "Lens Tracker"
        self.root_widget = LensTrackerRoot(self)
        Clock.schedule_interval(self.root_widget.check_reminder, 30)
        return self.root_widget


if __name__ == "__main__":
    LensTrackerApp().run()
