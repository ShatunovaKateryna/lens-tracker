# -*- coding: utf-8 -*-
"""
Lens Tracker - застосунок для відстеження днів носіння контактних лінз.
Візуально оновлена версія із заокругленим UI, календарем та аналоговим годинником.
"""

import json
import os
import math
import calendar
from datetime import date

from kivy.app import App
from kivy.utils import platform
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty, StringProperty
from kivy.metrics import dp

TOTAL_DAYS = 30
DATA_FILE_NAME = "lens_data.json"
MONTHS_UKR = ['Січень', 'Лютий', 'Березень', 'Квітень', 'Травень', 'Червень', 
              'Липень', 'Серпень', 'Вересень', 'Жовтень', 'Листопад', 'Грудень']

# Візуальний стиль (KV Language)
KV = '''
#:import math math

<RoundedButton@Button>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    color: 1, 1, 1, 1
    # Захист від виходу тексту за межі:
    text_size: self.width - dp(10), self.height - dp(10)
    halign: 'center'
    valign: 'middle'
    font_size: '14sp'
    canvas.before:
        Color:
            rgba: (0.1, 0.5, 0.7, 1) if self.state == 'normal' else (0.05, 0.35, 0.5, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<DayToggleButton@ToggleButton>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    background_down: ''
    color: 1, 1, 1, 1
    font_size: '15sp'
    bold: True
    text_size: self.width - dp(4), self.height - dp(4)
    halign: 'center'
    valign: 'middle'
    canvas.before:
        Color:
            rgba: (0.2, 0.7, 0.4, 1) if self.state == 'down' else (0.3, 0.3, 0.35, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

<AnalogClock>:
    canvas:
        # Фон циферблата
        Color:
            rgba: 0.85, 0.9, 0.95, 1
        Ellipse:
            pos: self.center_x - min(self.width, self.height)/2, self.center_y - min(self.width, self.height)/2
            size: min(self.width, self.height), min(self.width, self.height)
        
        # Годинна стрілка
        Color:
            rgba: 0.2, 0.2, 0.2, 1
        PushMatrix
        Rotate:
            angle: - (self.hour % 12 * 30 + self.minute * 0.5)
            axis: 0, 0, 1
            origin: self.center
        Line:
            points: [self.center_x, self.center_y, self.center_x, self.center_y + min(self.width, self.height)*0.25]
            width: dp(4)
            cap: 'round'
        PopMatrix
        
        # Хвилинна стрілка
        Color:
            rgba: 0.1, 0.5, 0.7, 1
        PushMatrix
        Rotate:
            angle: - (self.minute * 6)
            axis: 0, 0, 1
            origin: self.center
        Line:
            points: [self.center_x, self.center_y, self.center_x, self.center_y + min(self.width, self.height)*0.4]
            width: dp(2)
            cap: 'round'
        PopMatrix
        
        # Центр стрілок
        Color:
            rgba: 0.9, 0.3, 0.3, 1
        Ellipse:
            pos: self.center_x - dp(6), self.center_y - dp(6)
            size: dp(12), dp(12)

<DatePickerPopup>:
    title: "Вибір дати відкриття"
    size_hint: 0.95, 0.7
    title_align: 'center'
    BoxLayout:
        orientation: 'vertical'
        spacing: dp(10)
        padding: dp(10)
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            RoundedButton:
                text: '<'
                size_hint_x: 0.2
                on_release: root.change_month(-1)
            Label:
                id: month_year_label
                text: ''
                bold: True
                font_size: '18sp'
            RoundedButton:
                text: '>'
                size_hint_x: 0.2
                on_release: root.change_month(1)
        GridLayout:
            id: days_grid
            cols: 7
            spacing: dp(4)
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            RoundedButton:
                text: 'Скасувати'
                canvas.before:
                    Color:
                        rgba: 0.5, 0.5, 0.5, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(12)]
                on_release: root.dismiss()
            RoundedButton:
                text: 'Зберегти'
                on_release: root.save_date()

<TimePickerPopup>:
    title: "Налаштування сповіщень"
    size_hint: 0.95, 0.85
    title_align: 'center'
    BoxLayout:
        orientation: 'vertical'
        spacing: dp(15)
        padding: dp(10)
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            Label:
                text: "Увімкнути нагадування:"
                text_size: self.size
                halign: 'left'
                valign: 'middle'
            Switch:
                id: enable_switch
                active: root.reminder_enabled
        Label:
            text: f"{root.hour:02d}:{root.minute:02d}"
            font_size: '42sp'
            bold: True
            size_hint_y: None
            height: dp(50)
            color: 0.1, 0.5, 0.7, 1
        BoxLayout:
            size_hint_y: None
            height: dp(40)
            spacing: dp(10)
            RoundedButton:
                text: 'Години'
                on_release: clock.time_mode = 'hour'
                canvas.before:
                    Color:
                        rgba: (0.1, 0.5, 0.7, 1) if clock.time_mode == 'hour' else (0.3, 0.3, 0.3, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(10)]
            RoundedButton:
                text: 'Хвилини'
                on_release: clock.time_mode = 'minute'
                canvas.before:
                    Color:
                        rgba: (0.1, 0.5, 0.7, 1) if clock.time_mode == 'minute' else (0.3, 0.3, 0.3, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(10)]
        AnalogClock:
            id: clock
            hour: root.hour
            minute: root.minute
            on_hour: root.hour = self.hour
            on_minute: root.minute = self.minute
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            RoundedButton:
                text: 'Скасувати'
                canvas.before:
                    Color:
                        rgba: 0.5, 0.5, 0.5, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(12)]
                on_release: root.dismiss()
            RoundedButton:
                text: 'Зберегти'
                on_release: root.save_time()

<ConfirmPopup>:
    title: "Підтвердження"
    size_hint: 0.85, 0.35
    title_align: 'center'
    BoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(10)
        Label:
            text: "Ви справді хочете скинути дані?\\nВесь прогрес буде видалено."
            halign: "center"
            valign: "middle"
            text_size: self.size
        BoxLayout:
            spacing: dp(10)
            size_hint_y: None
            height: dp(50)
            RoundedButton:
                text: "Скасувати"
                canvas.before:
                    Color:
                        rgba: 0.5, 0.5, 0.5, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(12)]
                on_release: root.dismiss()
            RoundedButton:
                text: "Так, скинути"
                canvas.before:
                    Color:
                        rgba: 0.8, 0.2, 0.2, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(12)]
                on_release: root.confirm_action()

<LensTrackerRoot>:
    orientation: "vertical"
    spacing: dp(10)
    padding: dp(15)
    canvas.before:
        Color:
            rgba: 0.08, 0.1, 0.12, 1  # Темний сучасний фон
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        id: date_label
        text: ""
        size_hint_y: None
        height: dp(30)
        font_size: "16sp"
        color: 0.7, 0.8, 0.9, 1

    Label:
        id: days_left_label
        text: ""
        size_hint_y: None
        height: dp(60)
        font_size: "24sp"
        bold: True
        color: 0.2, 0.8, 0.4, 1
        text_size: self.size
        halign: 'center'
        valign: 'middle'

    RoundedButton:
        text: "Змінити дату відкриття коробки"
        size_hint_y: None
        height: dp(50)
        on_release: root.open_date_popup()

    ScrollView:
        GridLayout:
            id: checkbox_grid
            cols: 5
            spacing: dp(8)
            size_hint_y: None
            height: self.minimum_height
            padding: dp(5)

    BoxLayout:
        size_hint_y: None
        height: dp(55)
        spacing: dp(10)
        RoundedButton:
            text: "Сповіщення"
            on_release: root.open_reminder_popup()
        RoundedButton:
            text: "Скинути дані"
            canvas.before:
                Color:
                    rgba: (0.8, 0.3, 0.3, 1) if self.state == 'normal' else (0.6, 0.2, 0.2, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(12)]
            on_release: root.open_reset_popup()
'''

Builder.load_string(KV)

# ---------- Функції зберігання даних ----------

def get_data_path(app):
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

# ---------- Логіка Кастомних Віджетів ----------

class AnalogClock(Widget):
    """Віджет аналогового годинника для інтерактивного вибору часу."""
    hour = NumericProperty(12)
    minute = NumericProperty(0)
    time_mode = StringProperty('hour')

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.update_time(touch)
            return True

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self.update_time(touch)
            return True

    def update_time(self, touch):
        cx, cy = self.center
        dx = touch.x - cx
        dy = touch.y - cy
        
        # Обчислюємо кут відносно 12 годин (верх)
        angle = math.degrees(math.atan2(dx, dy))
        if angle < 0: 
            angle += 360

        if self.time_mode == 'hour':
            h = int((angle + 15) // 30) % 12
            if h == 0: 
                h = 12
            self.hour = h
        else:
            m = int((angle + 3) // 6) % 60
            self.minute = m

class DatePickerPopup(Popup):
    """Календар для вибору дати."""
    def __init__(self, current_data, on_save_callback, **kwargs):
        super().__init__(**kwargs)
        self.on_save_callback = on_save_callback
        self.selected_date = date(
            current_data["open_year"], 
            current_data["open_month"], 
            current_data["open_day"]
        )
        self.display_date = self.selected_date
        self.populate_grid()

    def populate_grid(self):
        grid = self.ids.days_grid
        grid.clear_widgets()
        
        month_str = MONTHS_UKR[self.display_date.month - 1]
        self.ids.month_year_label.text = f"{month_str} {self.display_date.year}"

        for d in ['Пн', 'Вв', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']:
            grid.add_widget(Label(text=d, bold=True, size_hint_y=None, height=dp(30)))

        first_day, num_days = calendar.monthrange(self.display_date.year, self.display_date.month)
        
        for _ in range(first_day):
            grid.add_widget(Label()) 

        for day in range(1, num_days + 1):
            btn = ToggleButton(
                text=str(day),
                group='calendar_days',
                state='down' if (day == self.selected_date.day and 
                                 self.display_date.month == self.selected_date.month and 
                                 self.display_date.year == self.selected_date.year) else 'normal'
            )
            # Прив'язка лямбда-функції
            btn.bind(on_release=lambda b, d=day: self.select_day(d))
            
            # Стиль для кнопок календаря
            btn.background_color = (0,0,0,0)
            btn.background_normal = ''
            btn.background_down = ''
            grid.add_widget(btn)

    def select_day(self, day):
        self.selected_date = self.display_date.replace(day=day)

    def change_month(self, step):
        m = self.display_date.month - 1 + step
        y = self.display_date.year + m // 12
        m = m % 12 + 1
        self.display_date = date(y, m, 1)
        self.populate_grid()

    def save_date(self):
        self.on_save_callback(self.selected_date.day, self.selected_date.month, self.selected_date.year)
        self.dismiss()

class TimePickerPopup(Popup):
    """Спливаюче вікно для налаштувань часу та сповіщень."""
    reminder_enabled = BooleanProperty(False)
    hour = NumericProperty(12)
    minute = NumericProperty(0)

    def __init__(self, current_data, on_save_callback, **kwargs):
        super().__init__(**kwargs)
        self.on_save_callback = on_save_callback
        self.reminder_enabled = current_data["reminder_enabled"]
        self.hour = current_data["reminder_hour"]
        self.minute = current_data["reminder_minute"]

    def save_time(self):
        self.on_save_callback(self.ids.enable_switch.active, self.hour, self.minute)
        self.dismiss()

class ConfirmPopup(Popup):
    def __init__(self, on_confirm_callback, **kwargs):
        super().__init__(**kwargs)
        self.on_confirm_callback = on_confirm_callback

    def confirm_action(self):
        self.on_confirm_callback()
        self.dismiss()

# ---------- Головний інтерфейс ----------

class LensTrackerRoot(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.data = None
        self.checkboxes = []
        
        self.load_data()
        self.build_grid()
        self.refresh_ui()

    def build_grid(self):
        grid = self.ids.checkbox_grid
        grid.bind(minimum_height=grid.setter("height"))
        for i in range(TOTAL_DAYS):
            # Використовуємо ToggleButton замість дрібного CheckBox
            cb = Factory.DayToggleButton()
            cb.text = f"День\\n{i + 1}"
            cb.size_hint_y = None
            cb.height = dp(75)
            cb.bind(state=self.make_checkbox_callback(i))
            grid.add_widget(cb)
            self.checkboxes.append(cb)

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

    def make_checkbox_callback(self, index):
        def callback(checkbox, value):
            self.data["checked"][index] = (value == 'down')
            self.save_data()
            self.update_days_left()
        return callback

    def refresh_ui(self):
        d, m, y = self.data["open_day"], self.data["open_month"], self.data["open_year"]
        self.ids.date_label.text = f"Відкрито: {d:02d}.{m:02d}.{y}"
        
        for i, cb in enumerate(self.checkboxes):
            cb.state = 'down' if self.data["checked"][i] else 'normal'
        self.update_days_left()

    def update_days_left(self):
        worn = sum(1 for v in self.data["checked"] if v)
        left = max(0, TOTAL_DAYS - worn)
        if left == 0:
            self.ids.days_left_label.text = "Час замінити лінзи!"
            self.ids.days_left_label.color = (1, 0.4, 0.4, 1)
        else:
            self.ids.days_left_label.text = f"Залишилось днів: {left}"
            self.ids.days_left_label.color = (0.2, 0.8, 0.4, 1)

    def open_date_popup(self):
        def on_save(d, m, y):
            self.data["open_day"] = d
            self.data["open_month"] = m
            self.data["open_year"] = y
            self.save_data()
            self.refresh_ui()
        DatePickerPopup(self.data, on_save).open()

    def open_reminder_popup(self):
        def on_save(enabled, hour, minute):
            self.data["reminder_enabled"] = enabled
            self.data["reminder_hour"] = hour
            self.data["reminder_minute"] = minute
            self.save_data()
        TimePickerPopup(self.data, on_save).open()

    def open_reset_popup(self):
        def on_confirm():
            self.data = default_data()
            self.save_data()
            self.refresh_ui()
        ConfirmPopup(on_confirm).open()


class LensTrackerApp(App):
    def build(self):
        self.title = "Lens Tracker"
        self.root_widget = LensTrackerRoot(self)
        self.start_notifier_service()
        return self.root_widget

    def start_notifier_service(self):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            service = autoclass("org.example.lenstracker.ServiceNotifier")
            python_activity = autoclass("org.kivy.android.PythonActivity")
            service.start(python_activity.mActivity, "")
        except Exception:
            pass


if __name__ == "__main__":
    LensTrackerApp().run()
