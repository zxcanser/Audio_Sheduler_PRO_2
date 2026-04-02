import os
import platform
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from tkinter import ttk
from typing import Callable, List, Optional

from PIL import Image, ImageTk

from models import ClientCall, ScheduleEntry
from config import APP_ICON_FILE, WINDOW_TITLE


class MainWindow:
    WEEKDAY_LABELS: list[tuple[int, str]] = [
        (0, "Пн"),
        (1, "Вт"),
        (2, "Ср"),
        (3, "Чт"),
        (4, "Пт"),
        (5, "Сб"),
        (6, "Вс"),
    ]
    EDIT_SHORTCUT_KEYS = {
        "select_all": {"a", "A", "ф", "Ф"},
        "copy": {"c", "C", "с", "С"},
        "paste": {"v", "V", "м", "М"},
        "cut": {"x", "X", "ч", "Ч"},
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self._is_windows = platform.system() == "Windows"
        self._window_icon_image: Optional[ImageTk.PhotoImage] = None
        self.root.title(WINDOW_TITLE)
        self.root.resizable(False, False)
        self._apply_window_icon(self.root)

        self.selected_file_path = tk.StringVar()
        self.selected_file_display = tk.StringVar()
        self.hours_var = tk.StringVar()
        self.minutes_var = tk.StringVar()
        self.volume_var = tk.DoubleVar(value=0.8)
        self.volume_display_var = tk.StringVar(value="0.8")
        self.notification_volume_var = tk.DoubleVar(value=0.8)
        self.notification_volume_display_var = tk.StringVar(value="0.8")
        self.device_var = tk.StringVar()
        self.notification_sound_file_path = tk.StringVar()
        self.notification_sound_display = tk.StringVar()
        self.autostart_var = tk.BooleanVar(value=False)
        self.scheduler_notification_var = tk.BooleanVar(value=False)
        self.client_calls_notification_var = tk.BooleanVar(value=False)
        self.client_calls_file_path = tk.StringVar()
        self.client_calls_file_display = tk.StringVar()
        self.client_calls_voice_message_file_path = tk.StringVar()
        self.client_calls_voice_message_file_display = tk.StringVar()
        self.client_calls_volume_var = tk.DoubleVar(value=0.8)
        self.client_calls_volume_display_var = tk.StringVar(value="0.8")
        self.client_calls_voice_message_volume_var = tk.DoubleVar(value=1.0)
        self.client_calls_voice_message_volume_display_var = tk.StringVar(value="1.0")
        self.client_calls_speech_rate_var = tk.DoubleVar(value=1.0)
        self.client_calls_speech_rate_display_var = tk.StringVar(value="1.0")
        self.client_calls_device_var = tk.StringVar()
        self.client_calls_voice_message_device_var = tk.StringVar()
        self.client_calls_interval_var = tk.StringVar(value="5")
        self.client_calls_repeat_var = tk.BooleanVar(value=False)
        self.client_calls_repeat_interval_var = tk.StringVar(value="3")
        self.client_calls_repeat_notification_var = tk.BooleanVar(value=False)
        self.client_calls_text_voice_var = tk.StringVar()
        self.client_calls_text_language_var = tk.StringVar(value="Русский")
        self.client_calls_text_voice_preview_button_var = tk.StringVar(value="Послушать")
        self.generator_api_file_path = tk.StringVar()
        self.generator_api_file_display = tk.StringVar()
        self.generator_volume_var = tk.DoubleVar(value=0.8)
        self.generator_volume_display_var = tk.StringVar(value="0.8")
        self.generator_device_var = tk.StringVar()
        self.generator_language_var = tk.StringVar(value="Русский")
        self.generator_voice_var = tk.StringVar(value="")
        self.generator_file_name_var = tk.StringVar()
        self.scheduler_weekday_vars: dict[int, tk.BooleanVar] = {
            day: tk.BooleanVar(value=True) for day, _ in self.WEEKDAY_LABELS
        }
        self._current_client_call: Optional[ClientCall] = None
        self._queued_client_calls: list[ClientCall] = []
        self._current_client_call_progress = 0.0
        self._client_calls_settings_window: Optional[tk.Toplevel] = None
        self._generator_window: Optional[tk.Toplevel] = None
        self._employees_window: Optional[tk.Toplevel] = None
        self._generator_text_widget: Optional[tk.Text] = None
        self._employee_entry: Optional[tk.Entry] = None
        self._employee_entry_font = tkfont.nametofont("TkDefaultFont").copy()
        self._employee_entry_placeholder_font = self._employee_entry_font.copy()
        self._employee_entry_placeholder_font.configure(slant="italic")
        self._employees_help_tooltip: Optional[tk.Toplevel] = None
        self._settings_window_requested_visible = False
        self._generator_window_requested_visible = False
        self._employees_window_requested_visible = False
        self._employee_placeholder_text = "Фамилия Имя"
        self._employee_placeholder_visible = False

        self._entry_ids_by_index: list[str] = []

        self.on_add: Optional[Callable[[], None]] = None
        self.on_delete: Optional[Callable[[], None]] = None
        self.on_browse: Optional[Callable[[], None]] = None
        self.on_play: Optional[Callable[[], None]] = None
        self.on_refresh_devices: Optional[Callable[[], None]] = None
        self.on_device_change: Optional[Callable[[str], None]] = None
        self.on_volume_change: Optional[Callable[[float], None]] = None
        self.on_notification_volume_change: Optional[Callable[[float], None]] = None
        self.on_select_entry: Optional[Callable[[], None]] = None
        self.on_browse_client_calls_file: Optional[Callable[[], None]] = None
        self.on_browse_client_calls_voice_message_file: Optional[Callable[[], None]] = None
        self.on_browse_employees_file: Optional[Callable[[], None]] = None
        self.on_client_calls_volume_change: Optional[Callable[[float], None]] = None
        self.on_client_calls_voice_message_volume_change: Optional[Callable[[float], None]] = None
        self.on_client_calls_speech_rate_change: Optional[Callable[[float], None]] = None
        self.on_client_calls_device_change: Optional[Callable[[str], None]] = None
        self.on_client_calls_voice_message_device_change: Optional[Callable[[str], None]] = None
        self.on_client_calls_interval_change: Optional[Callable[[], None]] = None
        self.on_client_calls_repeat_toggle: Optional[Callable[[], None]] = None
        self.on_client_calls_repeat_interval_change: Optional[Callable[[], None]] = None
        self.on_client_calls_repeat_notification_toggle: Optional[Callable[[], None]] = None
        self.on_client_calls_text_language_change: Optional[Callable[[str], None]] = None
        self.on_client_calls_text_voice_change: Optional[Callable[[str], None]] = None
        self.on_preview_client_calls_text_voice: Optional[Callable[[], None]] = None
        self.on_request_client_calls_text_voices: Optional[Callable[[], None]] = None
        self.on_scheduler_weekdays_change: Optional[Callable[[], None]] = None
        self.on_browse_notification_sound_file: Optional[Callable[[], None]] = None
        self.on_play_notification_sound: Optional[Callable[[], None]] = None
        self.on_show_generator: Optional[Callable[[], None]] = None
        self.on_show_employees: Optional[Callable[[], None]] = None
        self.on_browse_generator_api_file: Optional[Callable[[], None]] = None
        self.on_generator_device_change: Optional[Callable[[str], None]] = None
        self.on_generator_volume_change: Optional[Callable[[float], None]] = None
        self.on_generator_language_change: Optional[Callable[[str], None]] = None
        self.on_generator_voice_change: Optional[Callable[[str], None]] = None
        self.on_request_generator_voices: Optional[Callable[[], None]] = None
        self.on_generate_ai_speech: Optional[Callable[[], None]] = None
        self.on_save_generated_ai_speech: Optional[Callable[[], None]] = None
        self.on_add_employee: Optional[Callable[[], None]] = None
        self.on_delete_employee: Optional[Callable[[], None]] = None
        self.on_preview_employee: Optional[Callable[[], None]] = None
        self.on_autostart_toggle: Optional[Callable[[], None]] = None
        self.on_scheduler_notification_toggle: Optional[Callable[[], None]] = None
        self.on_client_calls_notification_toggle: Optional[Callable[[], None]] = None
        self.on_hide_to_tray: Optional[Callable[[], None]] = None
        self.on_quit_application: Optional[Callable[[], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
        self.on_window_unmap: Optional[Callable[[], None]] = None
        self.on_window_configure: Optional[Callable[[], None]] = None

        self._build()
        self._fit_window_to_content(self.root)
        self._register_window_group_behavior()

    def _build(self) -> None:
        frame = tk.Frame(self.root, padx=10, pady=6)
        frame.pack(fill="both", expand=True)

        scheduler_frame = tk.LabelFrame(frame, text="Планировщик оповещений", padx=10, pady=10)
        scheduler_frame.grid(row=0, column=0, sticky="nsew")

        tk.Label(scheduler_frame, text="Аудиофайл:").grid(row=0, column=0, sticky="w")
        tk.Entry(scheduler_frame, textvariable=self.selected_file_display, width=32, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(scheduler_frame, text="Выбрать", width=12, command=self._browse_clicked).grid(row=0, column=2, padx=5)

        tk.Label(scheduler_frame, text="Время (ЧЧ:ММ):").grid(row=1, column=0, sticky="w", pady=(3, 0))

        time_frame = tk.Frame(scheduler_frame)
        time_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(3, 0))
        tk.Entry(time_frame, textvariable=self.hours_var, width=3).pack(side="left")
        tk.Label(time_frame, text=":").pack(side="left")
        tk.Entry(time_frame, textvariable=self.minutes_var, width=3).pack(side="left")

        tk.Button(scheduler_frame, text="Добавить", width=12, command=self._add_clicked).grid(row=1, column=2, padx=5, pady=(3, 0))

        tk.Label(scheduler_frame, text="Расписание:").grid(row=2, column=0, sticky="w", pady=(10, 4))
        self.listbox = tk.Listbox(scheduler_frame, width=52, height=10)
        self.listbox.grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", lambda event: self._select_entry())

        actions = tk.Frame(scheduler_frame)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=6)

        actions_left = tk.Frame(actions)
        actions_left.pack(side="left")
        actions_right = tk.Frame(actions)
        actions_right.pack(side="right")

        tk.Button(actions_left, text="▶/■", width=6, command=self._play_clicked).pack(side="left")
        tk.Button(actions_right, text="Удалить", width=9, command=self._delete_clicked).pack(side="right")

        calls_frame = tk.LabelFrame(frame, text="Очередь вызовов", padx=10, pady=10)
        calls_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        calls_frame.columnconfigure(0, weight=1)

        self.client_calls_rows_frame = tk.Frame(calls_frame, bd=1, relief="sunken", bg="#ffffff")
        self.client_calls_rows_frame.grid(row=0, column=0, sticky="ew")
        self.client_call_row_canvases = []
        self.client_call_row_fill_ids = []
        self.client_call_row_text_ids = []

        for _ in range(3):
            row_canvas = tk.Canvas(
                self.client_calls_rows_frame,
                height=24,
                highlightthickness=0,
                bd=0,
                bg="#ffffff",
            )
            row_canvas.pack(fill="x")
            fill_id = row_canvas.create_rectangle(0, 0, 0, 24, fill="#63c174", width=0, state="hidden")
            text_id = row_canvas.create_text(6, 12, anchor="w", text="", fill="#1f2933", font=("TkDefaultFont", 10))
            self.client_call_row_canvases.append(row_canvas)
            self.client_call_row_fill_ids.append(fill_id)
            self.client_call_row_text_ids.append(text_id)

        self.client_calls_rows_frame.bind("<Configure>", lambda event: self._resize_client_call_rows())

        stamp_label = tk.Label(
            frame,
            text="Builded by sega",
            font=("TkDefaultFont", 8, "italic"),
            fg="#555555",
        )
        stamp_label.grid(row=2, column=0, pady=(4, 0))

        self.device_var.trace_add("write", self._device_changed)
        self.client_calls_device_var.trace_add("write", self._client_calls_device_changed)
        self.client_calls_voice_message_device_var.trace_add("write", self._client_calls_voice_message_device_changed)
        self.generator_device_var.trace_add("write", self._generator_device_changed)

        self.root.bind("<Return>", lambda event: self._add_clicked())
        self.root.bind_all("<Delete>", self._delete_key_pressed)
        self.root.bind_all("<KP_Delete>", self._delete_key_pressed)
        self.root.bind_all("<Command-BackSpace>", self._delete_shortcut_pressed)
        self.root.bind_all("<Command-Delete>", self._delete_shortcut_pressed)
        self.root.bind_all("<space>", self._space_pressed)
        self.root.bind_all("<Button-1>", self._global_left_click, add="+")
        self.root.bind("<Configure>", self._window_configured)
        self.root.bind("<Unmap>", self._window_unmapped)
        self.root.protocol("WM_DELETE_WINDOW", self._close_requested)

        frame.columnconfigure(0, weight=1)
        scheduler_frame.columnconfigure(1, weight=1)
        self._build_menu()
        self._build_client_calls_settings_window()
        self._build_generator_window()
        self._build_employees_window()
        self._bind_edit_shortcuts_recursively(self.root)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        program_menu = tk.Menu(menubar, tearoff=0)
        program_menu.add_command(label="Убрать в трей", command=self._hide_to_tray_clicked)
        program_menu.add_command(label="Сохранить и закрыть", command=self._quit_application_clicked)
        menubar.add_cascade(label="Программа", menu=program_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        hotkeys_menu = tk.Menu(settings_menu, tearoff=0)
        hotkeys_menu.add_command(label="Enter - добавить запись", state="disabled")
        hotkeys_menu.add_command(label="Delete - удалить запись", state="disabled")
        hotkeys_menu.add_command(label="Пробел - Play/Stop", state="disabled")

        settings_menu.add_command(label="Настройки", command=self.show_client_calls_settings_window)
        settings_menu.add_command(label="Генератор", command=self._show_generator_clicked)
        settings_menu.add_command(label="Сотрудники", command=self._show_employees_clicked)
        settings_menu.add_cascade(label="Горячие клавиши", menu=hotkeys_menu)
        menubar.add_cascade(label="Опции", menu=settings_menu)

        self.root.config(menu=menubar)

    def _build_client_calls_settings_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Настройки")
        window.resizable(False, False)
        window.withdraw()
        self._apply_window_icon(window)
        window.protocol("WM_DELETE_WINDOW", self._hide_client_calls_settings_window)

        content = tk.Frame(window, padx=10, pady=10)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        notebook = ttk.Notebook(content)
        notebook.grid(row=0, column=0, sticky="nsew")

        audio_tab = tk.Frame(notebook, padx=6, pady=6)
        planner_tab = tk.Frame(notebook, padx=6, pady=6)
        notification_tab = tk.Frame(notebook, padx=6, pady=6)
        queue_tab = tk.Frame(notebook, padx=6, pady=6)

        notebook.add(audio_tab, text="Аудио")
        notebook.add(planner_tab, text="Планировщик")
        notebook.add(notification_tab, text="Звук уведомления")
        notebook.add(queue_tab, text="Вызовы")

        audio_tab.columnconfigure(0, weight=1)
        planner_tab.columnconfigure(0, weight=1)
        notification_tab.columnconfigure(0, weight=1)
        queue_tab.columnconfigure(0, weight=1)

        devices_frame = tk.LabelFrame(audio_tab, text="Выбор аудио устройства", padx=10, pady=10)
        devices_frame.grid(row=0, column=0, sticky="ew")
        devices_frame.columnconfigure(1, weight=1)

        tk.Label(devices_frame, text="Планировщик:").grid(row=0, column=0, sticky="w")
        self.device_menu = tk.OptionMenu(devices_frame, self.device_var, "")
        self.device_menu.grid(row=0, column=1, sticky="ew", padx=5)

        tk.Label(devices_frame, text="Очередь вызовов:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.client_calls_device_menu = tk.OptionMenu(devices_frame, self.client_calls_device_var, "")
        self.client_calls_device_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=(10, 0))

        tk.Label(devices_frame, text="Голосовое сообщение:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.client_calls_voice_message_device_menu = tk.OptionMenu(devices_frame, self.client_calls_voice_message_device_var, "")
        self.client_calls_voice_message_device_menu.grid(row=2, column=1, sticky="ew", padx=5, pady=(10, 0))

        tk.Label(devices_frame, text="Генератор:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.generator_device_menu = tk.OptionMenu(devices_frame, self.generator_device_var, "")
        self.generator_device_menu.grid(row=3, column=1, sticky="ew", padx=5, pady=(10, 0))

        tk.Button(devices_frame, text="Обновить устройства", width=18, command=self._refresh_devices_clicked).grid(
            row=4,
            column=1,
            sticky="e",
            padx=5,
            pady=(12, 0),
        )

        volumes_frame = tk.LabelFrame(audio_tab, text="Настройка громкости", padx=10, pady=10)
        volumes_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        volumes_frame.columnconfigure(1, weight=1)

        tk.Label(volumes_frame, text="Планировщик:").grid(row=0, column=0, sticky="w")
        scheduler_volume_frame = tk.Frame(volumes_frame)
        scheduler_volume_frame.grid(row=0, column=1, sticky="w", padx=5)
        self._create_settings_scale(
            scheduler_volume_frame,
            variable=self.volume_var,
            command=self._volume_changed,
            from_=0.0,
            to=1.0,
            resolution=0.1,
        ).pack(side="left")
        tk.Label(scheduler_volume_frame, textvariable=self.volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        tk.Label(volumes_frame, text="Очередь вызовов:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        calls_volume_frame = tk.Frame(volumes_frame)
        calls_volume_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(10, 0))
        self._create_settings_scale(
            calls_volume_frame,
            variable=self.client_calls_volume_var,
            command=self._client_calls_volume_changed,
            from_=0.0,
            to=1.0,
            resolution=0.1,
        ).pack(side="left")
        tk.Label(calls_volume_frame, textvariable=self.client_calls_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        tk.Label(volumes_frame, text="Звук уведомления:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        notification_volume_frame = tk.Frame(volumes_frame)
        notification_volume_frame.grid(row=2, column=1, sticky="w", padx=5, pady=(10, 0))
        self._create_settings_scale(
            notification_volume_frame,
            variable=self.notification_volume_var,
            command=self._notification_volume_changed,
            from_=0.0,
            to=1.0,
            resolution=0.1,
        ).pack(side="left")
        tk.Label(notification_volume_frame, textvariable=self.notification_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        tk.Label(volumes_frame, text="Генератор:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        generator_volume_frame = tk.Frame(volumes_frame)
        generator_volume_frame.grid(row=3, column=1, sticky="w", padx=5, pady=(10, 0))
        self._create_settings_scale(
            generator_volume_frame,
            variable=self.generator_volume_var,
            command=self._generator_volume_changed,
            from_=0.0,
            to=1.0,
            resolution=0.1,
        ).pack(side="left")
        tk.Label(generator_volume_frame, textvariable=self.generator_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        notification_frame = tk.LabelFrame(notification_tab, text="Звук уведомления", padx=10, pady=10)
        notification_frame.grid(row=0, column=0, sticky="ew")
        notification_frame.columnconfigure(1, weight=1)

        tk.Label(notification_frame, text="Файл:").grid(row=0, column=0, sticky="w")
        tk.Entry(notification_frame, textvariable=self.notification_sound_display, width=30, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(notification_frame, text="Выбрать", width=12, command=self._browse_notification_sound_file_clicked).grid(row=0, column=2, padx=5)
        tk.Button(notification_frame, text="Прослушать", width=12, command=self._play_notification_sound_clicked).grid(row=1, column=2, padx=5, pady=(8, 0), sticky="n")

        tk.Checkbutton(
            notification_frame,
            text="Перед планировщиком",
            variable=self.scheduler_notification_var,
            command=self._scheduler_notification_toggled,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        tk.Checkbutton(
            notification_frame,
            text="Перед очередью вызовов",
            variable=self.client_calls_notification_var,
            command=self._client_calls_notification_toggled,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        tk.Checkbutton(
            notification_frame,
            text="Звук перед повтором",
            variable=self.client_calls_repeat_notification_var,
            command=self._client_calls_repeat_notification_toggled,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        weekdays_frame = tk.LabelFrame(planner_tab, text="Дни работы планировщика", padx=10, pady=10)
        weekdays_frame.grid(row=0, column=0, sticky="ew")

        for column, (day, label) in enumerate(self.WEEKDAY_LABELS):
            tk.Checkbutton(
                weekdays_frame,
                text=label,
                variable=self.scheduler_weekday_vars[day],
                command=self._scheduler_weekdays_changed,
            ).grid(row=0, column=column, padx=4, sticky="w")

        startup_frame = tk.LabelFrame(planner_tab, text="Запуск программы", padx=10, pady=10)
        startup_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        tk.Checkbutton(
            startup_frame,
            text="Запускать вместе с системой",
            variable=self.autostart_var,
            command=self._autostart_toggled,
        ).grid(row=0, column=0, sticky="w")

        queue_frame = tk.LabelFrame(queue_tab, text="Настройки вызовов", padx=10, pady=10)
        queue_frame.grid(row=0, column=0, sticky="nsew")
        queue_frame.columnconfigure(1, weight=1)

        tk.Label(queue_frame, text="Файл данных:").grid(row=0, column=0, sticky="w")
        tk.Entry(queue_frame, textvariable=self.client_calls_file_display, width=30, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(queue_frame, text="Выбрать", width=12, command=self._browse_client_calls_file_clicked).grid(row=0, column=2, padx=5)

        tk.Label(queue_frame, text="Интервал (сек):").grid(row=1, column=0, sticky="w", pady=(12, 0))
        interval_entry = tk.Entry(queue_frame, textvariable=self.client_calls_interval_var, width=2)
        interval_entry.grid(row=1, column=1, sticky="w", padx=5, pady=(12, 0))
        interval_entry.bind("<FocusOut>", lambda event: self._client_calls_interval_changed())
        interval_entry.bind("<Return>", self._client_calls_interval_submitted)

        tk.Checkbutton(
            queue_frame,
            text="Повторный вызов клиента",
            variable=self.client_calls_repeat_var,
            command=self._client_calls_repeat_toggled,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))

        tk.Label(queue_frame, text="Интервал повтора (сек):").grid(row=3, column=0, sticky="w", pady=(12, 0))
        repeat_interval_entry = tk.Entry(queue_frame, textvariable=self.client_calls_repeat_interval_var, width=2)
        repeat_interval_entry.grid(row=3, column=1, sticky="w", padx=5, pady=(12, 0))
        repeat_interval_entry.bind("<FocusOut>", lambda event: self._client_calls_repeat_interval_changed())
        repeat_interval_entry.bind("<Return>", self._client_calls_repeat_interval_submitted)

        tk.Label(queue_frame, text="Скорость воспроизведения:").grid(row=4, column=0, sticky="w", pady=(12, 0))
        speech_rate_frame = tk.Frame(queue_frame)
        speech_rate_frame.grid(row=4, column=1, columnspan=2, sticky="w", padx=5, pady=(12, 0))
        self._create_settings_scale(
            speech_rate_frame,
            variable=self.client_calls_speech_rate_var,
            command=self._client_calls_speech_rate_changed,
            from_=0.5,
            to=2.0,
            resolution=0.1,
        ).pack(side="left")
        tk.Label(speech_rate_frame, textvariable=self.client_calls_speech_rate_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        voice_message_frame = tk.LabelFrame(queue_tab, text="Голосовое сообщение", padx=10, pady=10)
        voice_message_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        voice_message_frame.columnconfigure(1, weight=1)

        tk.Label(voice_message_frame, text="Файл:").grid(row=0, column=0, sticky="w")
        tk.Entry(voice_message_frame, textvariable=self.client_calls_voice_message_file_display, width=30, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(voice_message_frame, text="Выбрать", width=12, command=self._browse_client_calls_voice_message_file_clicked).grid(row=0, column=2, padx=5)

        tk.Label(voice_message_frame, text="Громкость голосового сообщения:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        voice_message_volume_frame = tk.Frame(voice_message_frame)
        voice_message_volume_frame.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=(12, 0))
        self._create_settings_scale(
            voice_message_volume_frame,
            variable=self.client_calls_voice_message_volume_var,
            command=self._client_calls_voice_message_volume_changed,
            from_=0.0,
            to=2.0,
            resolution=0.1,
        ).pack(side="left")
        tk.Label(voice_message_volume_frame, textvariable=self.client_calls_voice_message_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        generator_frame = tk.LabelFrame(queue_tab, text="AI Генератор", padx=10, pady=10)
        generator_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        generator_frame.columnconfigure(1, weight=1)

        tk.Label(generator_frame, text="API файл:").grid(row=0, column=0, sticky="w")
        tk.Entry(generator_frame, textvariable=self.generator_api_file_display, width=30, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(generator_frame, text="Выбрать", width=12, command=self._browse_generator_api_file_clicked).grid(row=0, column=2, padx=5)

        tk.Label(generator_frame, text="Список сотрудников:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.employees_file_path = tk.StringVar()
        self.employees_file_display = tk.StringVar()
        tk.Entry(generator_frame, textvariable=self.employees_file_display, width=30, state="readonly").grid(row=1, column=1, sticky="we", padx=5, pady=(12, 0))
        tk.Button(generator_frame, text="Выбрать", width=12, command=self._browse_employees_file_clicked).grid(row=1, column=2, padx=5, pady=(12, 0))

        tk.Label(generator_frame, text="Язык произвольного текста:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        self.client_calls_text_language_combobox = ttk.Combobox(
            generator_frame,
            textvariable=self.client_calls_text_language_var,
            state="normal",
            width=27,
        )
        self.client_calls_text_language_combobox.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=(12, 0))
        self.client_calls_text_language_combobox.bind("<<ComboboxSelected>>", self._client_calls_text_language_selected)
        self.client_calls_text_language_combobox.bind("<KeyRelease>", self._client_calls_text_language_typed)

        tk.Label(generator_frame, text="Голос для произвольного текста:").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.client_calls_text_voice_combobox = ttk.Combobox(
            generator_frame,
            textvariable=self.client_calls_text_voice_var,
            state="normal",
            width=27,
        )
        self.client_calls_text_voice_combobox.grid(row=3, column=1, sticky="ew", padx=5, pady=(12, 0))
        self.client_calls_text_voice_combobox.bind("<<ComboboxSelected>>", self._client_calls_text_voice_selected)
        self.client_calls_text_voice_combobox.bind("<KeyRelease>", self._client_calls_text_voice_typed)
        self.client_calls_text_voice_combobox.bind("<Button-1>", self._client_calls_text_voice_dropdown_clicked)
        self.client_calls_text_voice_combobox.bind("<FocusIn>", self._client_calls_text_voice_dropdown_clicked)
        tk.Button(
            generator_frame,
            textvariable=self.client_calls_text_voice_preview_button_var,
            width=12,
            command=self._preview_client_calls_text_voice_clicked,
        ).grid(row=3, column=2, padx=5, pady=(12, 0), sticky="e")

        tk.Button(content, text="Закрыть", width=12, command=self._hide_client_calls_settings_window).grid(row=1, column=0, sticky="e", pady=(18, 0))
        self._client_calls_settings_window = window
        self._fit_window_to_content(window)

    def _build_generator_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Генератор")
        window.resizable(False, False)
        window.withdraw()
        self._apply_window_icon(window)
        window.protocol("WM_DELETE_WINDOW", self._hide_generator_window)

        content = tk.Frame(window, padx=10, pady=10)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)

        generator_frame = tk.LabelFrame(content, text="AI Генератор речи", padx=10, pady=10)
        generator_frame.grid(row=0, column=0, sticky="ew")
        generator_frame.columnconfigure(1, weight=1)

        tk.Label(generator_frame, text="Язык:", anchor="w", width=12).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.generator_language_combobox = ttk.Combobox(
            generator_frame,
            textvariable=self.generator_language_var,
            state="normal",
            width=32,
        )
        self.generator_language_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=(0, 10))
        self.generator_language_combobox.bind("<<ComboboxSelected>>", self._generator_language_selected)
        self.generator_language_combobox.bind("<KeyRelease>", self._generator_language_typed)

        tk.Label(generator_frame, text="Голос:", anchor="w", width=12).grid(row=1, column=0, sticky="w", pady=(0, 10))
        self.generator_voice_combobox = ttk.Combobox(
            generator_frame,
            textvariable=self.generator_voice_var,
            state="normal",
            width=32,
        )
        self.generator_voice_combobox.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 10))
        self.generator_voice_combobox.bind("<<ComboboxSelected>>", self._generator_voice_selected)
        self.generator_voice_combobox.bind("<KeyRelease>", self._generator_voice_typed)
        self.generator_voice_combobox.bind("<Button-1>", self._generator_voice_dropdown_clicked)
        self.generator_voice_combobox.bind("<FocusIn>", self._generator_voice_dropdown_clicked)

        tk.Label(generator_frame, text="Текст:").grid(row=2, column=0, sticky="nw")
        self._generator_text_widget = tk.Text(generator_frame, width=34, height=8, wrap="word")
        self._generator_text_widget.grid(row=2, column=1, sticky="ew", padx=5)
        self._bind_standard_edit_shortcuts(self._generator_text_widget)

        tk.Label(generator_frame, text="Название файла:").grid(row=3, column=0, sticky="w", pady=(12, 0))
        file_name_frame = tk.Frame(generator_frame)
        file_name_frame.grid(row=3, column=1, sticky="w", padx=5, pady=(12, 0))
        generator_file_name_entry = tk.Entry(file_name_frame, textvariable=self.generator_file_name_var, width=32)
        generator_file_name_entry.pack(side="left")
        self._bind_standard_edit_shortcuts(generator_file_name_entry)
        tk.Label(file_name_frame, text=".mp3").pack(side="left", padx=(6, 0))

        buttons_frame = tk.Frame(content)
        buttons_frame.grid(row=1, column=0, sticky="e", pady=(14, 0))
        tk.Button(buttons_frame, text="Сгенерировать", width=14, command=self._generate_ai_speech_clicked).pack(side="left")
        tk.Button(buttons_frame, text="Сохранить в...", width=14, command=self._save_generated_ai_speech_clicked).pack(side="left", padx=(8, 0))
        tk.Button(buttons_frame, text="Закрыть", width=12, command=self._hide_generator_window).pack(side="left", padx=(8, 0))

        window.bind("<Return>", self._generator_enter_pressed)
        self._generator_text_widget.bind("<Return>", self._generator_enter_pressed)

        self._generator_window = window
        self._fit_window_to_content(window)

    def _build_employees_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Сотрудники")
        window.resizable(False, False)
        window.withdraw()
        self._apply_window_icon(window)
        window.protocol("WM_DELETE_WINDOW", self._hide_employees_window)

        content = tk.Frame(window, padx=10, pady=10)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)

        employees_frame = tk.LabelFrame(content, text="Список сотрудников", padx=10, pady=10)
        employees_frame.grid(row=0, column=0, sticky="ew")
        employees_frame.columnconfigure(0, weight=1)

        list_frame = tk.Frame(employees_frame)
        list_frame.grid(row=0, column=0, sticky="w")
        self.employees_listbox = tk.Listbox(list_frame, width=26, height=20)
        self.employees_listbox.pack(side="left", fill="y")
        self.employees_listbox.bind("<Double-Button-1>", self._employee_listbox_double_clicked)
        self.employees_listbox.bind("<space>", self._employee_listbox_space_pressed)
        employees_scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.employees_listbox.yview)
        employees_scrollbar.pack(side="left", fill="y")
        self.employees_listbox.config(yscrollcommand=employees_scrollbar.set)

        add_frame = tk.Frame(employees_frame)
        add_frame.grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.employee_input_var = tk.StringVar()
        employee_entry = tk.Entry(
            add_frame,
            textvariable=self.employee_input_var,
            width=26,
            font=self._employee_entry_font,
        )
        employee_entry.pack(anchor="w")
        employee_entry.bind("<Return>", self._employee_enter_pressed)
        employee_entry.bind("<FocusIn>", self._employee_entry_focused)
        employee_entry.bind("<FocusOut>", self._employee_entry_unfocused)
        add_actions_frame = tk.Frame(add_frame)
        add_actions_frame.pack(anchor="w", pady=(8, 0))
        tk.Button(add_actions_frame, text="Добавить сотрудника", width=18, command=self._add_employee_clicked).pack(side="left")
        help_button = tk.Label(
            add_actions_frame,
            text="?",
            width=2,
            relief="ridge",
            cursor="question_arrow",
        )
        help_button.pack(side="left", padx=(8, 0))
        help_button.bind("<Enter>", self._show_employees_help_tooltip)
        help_button.bind("<Leave>", self._hide_employees_help_tooltip)
        self._employee_entry = employee_entry
        self._show_employee_placeholder()

        buttons_frame = tk.Frame(employees_frame)
        buttons_frame.grid(row=2, column=0, sticky="w", pady=(10, 0))
        tk.Button(buttons_frame, text="Удалить", width=9, command=self._delete_employee_clicked).pack(side="left")
        tk.Button(buttons_frame, text="Закрыть", width=12, command=self._hide_employees_window).pack(side="left", padx=(8, 0))

        window.bind("<Return>", self._employee_enter_pressed)
        self._employees_window = window
        self._fit_window_to_content(window)

    def _browse_clicked(self) -> None:
        if self.on_browse:
            self.on_browse()

    def _add_clicked(self) -> None:
        if self.on_add:
            self.on_add()

    def _delete_clicked(self) -> None:
        if self.on_delete:
            self.on_delete()

    def _play_clicked(self) -> None:
        if self.on_play:
            self.on_play()

    def _browse_client_calls_file_clicked(self) -> None:
        if self.on_browse_client_calls_file:
            self.on_browse_client_calls_file()

    def _browse_client_calls_voice_message_file_clicked(self) -> None:
        if self.on_browse_client_calls_voice_message_file:
            self.on_browse_client_calls_voice_message_file()

    def _browse_employees_file_clicked(self) -> None:
        if self.on_browse_employees_file:
            self.on_browse_employees_file()

    def _refresh_devices_clicked(self) -> None:
        if self.on_refresh_devices:
            self.on_refresh_devices()

    def _browse_notification_sound_file_clicked(self) -> None:
        if self.on_browse_notification_sound_file:
            self.on_browse_notification_sound_file()

    def _play_notification_sound_clicked(self) -> None:
        if self.on_play_notification_sound:
            self.on_play_notification_sound()

    def _browse_generator_api_file_clicked(self) -> None:
        if self.on_browse_generator_api_file:
            self.on_browse_generator_api_file()

    def _show_generator_clicked(self) -> None:
        if self.on_show_generator:
            self.on_show_generator()

    def _show_employees_clicked(self) -> None:
        if self.on_show_employees:
            self.on_show_employees()

    def _hide_to_tray_clicked(self) -> None:
        if self.on_hide_to_tray:
            self.on_hide_to_tray()

    def _quit_application_clicked(self) -> None:
        if self.on_quit_application:
            self.on_quit_application()

    def _client_calls_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.client_calls_volume_display_var, self.on_client_calls_volume_change)

    def _client_calls_voice_message_volume_changed(self, value: str) -> None:
        self._handle_volume_change(
            value,
            self.client_calls_voice_message_volume_display_var,
            self.on_client_calls_voice_message_volume_change,
        )

    def _client_calls_speech_rate_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.client_calls_speech_rate_display_var, self.on_client_calls_speech_rate_change)

    def _notification_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.notification_volume_display_var, self.on_notification_volume_change)

    def _generator_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.generator_volume_display_var, self.on_generator_volume_change)

    def _client_calls_device_changed(self, *args) -> None:
        if self.on_client_calls_device_change:
            self.on_client_calls_device_change(self.client_calls_device_var.get())

    def _client_calls_voice_message_device_changed(self, *args) -> None:
        if self.on_client_calls_voice_message_device_change:
            self.on_client_calls_voice_message_device_change(self.client_calls_voice_message_device_var.get())

    def _generator_device_changed(self, *args) -> None:
        if self.on_generator_device_change:
            self.on_generator_device_change(self.generator_device_var.get())

    def _generator_voice_changed(self) -> None:
        if self.on_generator_voice_change:
            self.on_generator_voice_change(self.generator_voice_var.get())

    def _generator_language_selected(self, event: tk.Event) -> None:
        if self.on_generator_language_change:
            self.on_generator_language_change(self.generator_language_var.get())

    def _generator_voice_selected(self, event: tk.Event) -> None:
        self._generator_voice_changed()

    def _client_calls_text_voice_selected(self, event: tk.Event) -> None:
        if self.on_client_calls_text_voice_change:
            self.on_client_calls_text_voice_change(self.client_calls_text_voice_var.get())

    def _client_calls_text_language_selected(self, event: tk.Event) -> None:
        if self.on_client_calls_text_language_change:
            self.on_client_calls_text_language_change(self.client_calls_text_language_var.get())

    def _preview_client_calls_text_voice_clicked(self) -> None:
        if self.on_preview_client_calls_text_voice:
            self.on_preview_client_calls_text_voice()

    def _generator_voice_dropdown_clicked(self, event: tk.Event) -> None:
        if self.on_request_generator_voices:
            self.on_request_generator_voices()

    def _client_calls_text_voice_dropdown_clicked(self, event: tk.Event) -> None:
        if self.on_request_client_calls_text_voices:
            self.on_request_client_calls_text_voices()

    def _generator_language_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.generator_language_combobox,
            getattr(self, "_generator_language_options", []),
            self.generator_language_var.get(),
        )

    def _client_calls_text_language_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.client_calls_text_language_combobox,
            getattr(self, "_client_calls_text_language_options", []),
            self.client_calls_text_language_var.get(),
        )

    def _generator_voice_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.generator_voice_combobox,
            getattr(self, "_generator_voice_options", []),
            self.generator_voice_var.get(),
        )

    def _client_calls_text_voice_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.client_calls_text_voice_combobox,
            getattr(self, "_client_calls_text_voice_options", []),
            self.client_calls_text_voice_var.get(),
        )

    def _client_calls_interval_changed(self) -> None:
        if self.on_client_calls_interval_change:
            self.on_client_calls_interval_change()

    def _client_calls_interval_submitted(self, event: tk.Event) -> str:
        self._client_calls_interval_changed()
        return "break"

    def _client_calls_repeat_interval_changed(self) -> None:
        if self.on_client_calls_repeat_interval_change:
            self.on_client_calls_repeat_interval_change()

    def _client_calls_repeat_interval_submitted(self, event: tk.Event) -> str:
        self._client_calls_repeat_interval_changed()
        return "break"

    def _scheduler_weekdays_changed(self) -> None:
        if self.on_scheduler_weekdays_change:
            self.on_scheduler_weekdays_change()

    def _scheduler_notification_toggled(self) -> None:
        if self.on_scheduler_notification_toggle:
            self.on_scheduler_notification_toggle()

    def _client_calls_notification_toggled(self) -> None:
        if self.on_client_calls_notification_toggle:
            self.on_client_calls_notification_toggle()

    def _client_calls_repeat_toggled(self) -> None:
        if self.on_client_calls_repeat_toggle:
            self.on_client_calls_repeat_toggle()

    def _client_calls_repeat_notification_toggled(self) -> None:
        if self.on_client_calls_repeat_notification_toggle:
            self.on_client_calls_repeat_notification_toggle()

    def _autostart_toggled(self) -> None:
        if self.on_autostart_toggle:
            self.on_autostart_toggle()

    def _hide_client_calls_settings_window(self) -> None:
        self._settings_window_requested_visible = False
        if self._client_calls_settings_window is not None:
            self._client_calls_settings_window.withdraw()

    def _hide_generator_window(self) -> None:
        self._generator_window_requested_visible = False
        if self._generator_window is not None:
            self._generator_window.withdraw()

    def _hide_employees_window(self) -> None:
        self._employees_window_requested_visible = False
        if self._employees_window is not None:
            self._employees_window.withdraw()

    def _close_requested(self) -> None:
        if self.on_close:
            self.on_close()

    def _window_unmapped(self, event: tk.Event) -> None:
        if event.widget is self.root:
            if self.on_window_unmap:
                self.on_window_unmap()

    def _window_configured(self, event: tk.Event) -> None:
        if event.widget is self.root:
            if self.on_window_configure:
                self.on_window_configure()

    def _global_left_click(self, event: tk.Event) -> None:
        widget = self._resolve_widget(event.widget)
        if widget is None:
            return
        try:
            if widget.winfo_toplevel() is not self.root:
                return
        except tk.TclError:
            return
        if self._is_widget_inside_listbox(widget):
            return
        if self._is_interactive_widget(widget):
            return

        self.listbox.selection_clear(0, tk.END)
        self.listbox.activate(tk.END)
        self.employees_listbox.selection_clear(0, tk.END)
        self.employees_listbox.activate(tk.END)
        self._clear_text_selection(widget)
        self.root.focus_set()

    def _space_pressed(self, event: tk.Event) -> str:
        focused_widget = self.root.focus_get()
        if focused_widget is self._generator_text_widget:
            return "break"
        if focused_widget is self.employees_listbox:
            if self.on_preview_employee:
                self.on_preview_employee()
            return "break"
        if isinstance(focused_widget, (tk.Entry, ttk.Entry, ttk.Combobox, tk.Text)):
            return "break"
        if self.on_play:
            self.on_play()
        return "break"

    def _delete_key_pressed(self, event: tk.Event) -> str:
        if self._is_editable_text_widget(event.widget):
            return "break"
        if self._should_handle_employee_shortcut(event):
            self._delete_employee_clicked()
            return "break"
        self._delete_clicked()
        return "break"

    def _delete_shortcut_pressed(self, event: tk.Event) -> str:
        if self._is_editable_text_widget(event.widget):
            return "break"
        if self._should_handle_employee_shortcut(event):
            self._delete_employee_clicked()
            return "break"
        self._delete_clicked()
        return "break"

    def _employee_listbox_double_clicked(self, event: tk.Event) -> str:
        if self.on_preview_employee:
            self.on_preview_employee()
        return "break"

    def _employee_listbox_space_pressed(self, event: tk.Event) -> str:
        if self.on_preview_employee:
            self.on_preview_employee()
        return "break"

    def _show_employees_help_tooltip(self, event: tk.Event) -> None:
        self._hide_employees_help_tooltip()
        tooltip = tk.Toplevel(self.root)
        tooltip.wm_overrideredirect(True)
        tooltip.transient(self._employees_window)
        tooltip.configure(bg="#fff8dc")
        message = (
            "Этот список отображается при вызове сотрудника в ТГ боте.\n"
            "Произношение имени создается сразу при добавлении.\n"
            "Если требуется поменять произношение или голос для воспроизведения\n"
            "перейдите в \"Генератор\", создайте нужное произношение и замените им файл\n"
            "с соответствующим названием (название должно совпадать с именем в списке)."
        )
        tk.Label(
            tooltip,
            text=message,
            justify="left",
            bg="#fff8dc",
            relief="solid",
            bd=1,
            padx=8,
            pady=6,
        ).pack()
        tooltip.update_idletasks()
        screen_width = event.widget.winfo_screenwidth()
        screen_height = event.widget.winfo_screenheight()
        widget_x = event.widget.winfo_rootx()
        widget_y = event.widget.winfo_rooty()
        widget_width = event.widget.winfo_width()
        widget_height = event.widget.winfo_height()
        tooltip_width = tooltip.winfo_width()
        tooltip_height = tooltip.winfo_height()

        x = widget_x + widget_width + 8
        if x + tooltip_width > screen_width - 12:
            x = widget_x - tooltip_width - 8
        if x < 12:
            x = 12

        y = widget_y
        if y + tooltip_height > screen_height - 12:
            y = max(12, screen_height - tooltip_height - 12)
        tooltip.geometry(f"+{x}+{y}")
        self._employees_help_tooltip = tooltip

    def _hide_employees_help_tooltip(self, event: Optional[tk.Event] = None) -> None:
        if self._employees_help_tooltip is None:
            return
        try:
            self._employees_help_tooltip.destroy()
        except tk.TclError:
            pass
        self._employees_help_tooltip = None

    def _device_changed(self, *args) -> None:
        if self.on_device_change:
            self.on_device_change(self.device_var.get())

    def _volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.volume_display_var, self.on_volume_change)

    def _select_entry(self) -> None:
        if self.on_select_entry:
            self.on_select_entry()

    def _resize_client_call_rows(self) -> None:
        if not self.client_calls_rows_frame.winfo_exists():
            return

        self.render_client_calls(
            self._current_client_call,
            self._queued_client_calls,
            self._current_client_call_progress,
        )

    def show_client_calls_settings_window(self) -> None:
        if self._client_calls_settings_window is None:
            return

        self._settings_window_requested_visible = True
        self._fit_window_to_content(self._client_calls_settings_window)
        self._show_side_window(self._client_calls_settings_window)

    def show_generator_window(self) -> None:
        if self._generator_window is None:
            return

        self._generator_window_requested_visible = True
        self._fit_window_to_content(self._generator_window)
        self._show_side_window(self._generator_window)

    def show_employees_window(self) -> None:
        if self._employees_window is None:
            return

        self._employees_window_requested_visible = True
        self._fit_window_to_content(self._employees_window)
        self._show_side_window(self._employees_window)

    def set_selected_file(self, file_path: str) -> None:
        self._set_file_value(self.selected_file_path, self.selected_file_display, file_path)

    def set_client_calls_file(self, file_path: str) -> None:
        self._set_file_value(self.client_calls_file_path, self.client_calls_file_display, file_path)

    def set_client_calls_voice_message_file(self, file_path: str) -> None:
        self._set_file_value(self.client_calls_voice_message_file_path, self.client_calls_voice_message_file_display, file_path)

    def set_notification_sound_file(self, file_path: str) -> None:
        self._set_file_value(self.notification_sound_file_path, self.notification_sound_display, file_path)

    def set_generator_api_file(self, file_path: str) -> None:
        self._set_file_value(self.generator_api_file_path, self.generator_api_file_display, file_path)

    def set_employees_file(self, file_path: str) -> None:
        self._set_file_value(self.employees_file_path, self.employees_file_display, file_path)

    def get_selected_file(self) -> str:
        return self.selected_file_path.get()

    def get_client_calls_file(self) -> str:
        return self.client_calls_file_path.get()

    def get_notification_sound_file(self) -> str:
        return self.notification_sound_file_path.get()

    def get_generator_text(self) -> str:
        if self._generator_text_widget is None:
            return ""
        return self._generator_text_widget.get("1.0", "end-1c")

    def get_generator_file_name(self) -> str:
        return self.generator_file_name_var.get()

    def get_employee_input(self) -> str:
        if self._employee_placeholder_visible:
            return ""
        return self.employee_input_var.get()

    def clear_employee_input(self) -> None:
        self.employee_input_var.set("")
        self._show_employee_placeholder()

    def focus_employees_list(self) -> None:
        try:
            self.employees_listbox.focus_set()
        except tk.TclError:
            return

    def get_selected_employee(self) -> str:
        selected = self.employees_listbox.curselection()
        if not selected:
            return ""
        return self.employees_listbox.get(selected[0])

    def get_time_input(self) -> tuple[str, str]:
        return self.hours_var.get().strip(), self.minutes_var.get().strip()

    def set_time_input(self, time_str: str) -> None:
        hours, minutes = time_str.split(":")
        self.hours_var.set(hours)
        self.minutes_var.set(minutes)

    def get_selected_index(self) -> Optional[int]:
        selected = self.listbox.curselection()
        return selected[0] if selected else None

    def get_selected_entry_id(self) -> Optional[str]:
        index = self.get_selected_index()
        if index is None:
            return None
        if 0 <= index < len(self._entry_ids_by_index):
            return self._entry_ids_by_index[index]
        return None

    def fill_schedule_list(self, entries: List[ScheduleEntry]) -> None:
        self.listbox.delete(0, tk.END)
        self._entry_ids_by_index.clear()

        for entry in entries:
            self.listbox.insert(tk.END, f"{entry.time_str} | {entry.file_name}")
            self._entry_ids_by_index.append(entry.entry_id)

    def fill_employees_list(self, employees: List[str]) -> None:
        self.employees_listbox.delete(0, tk.END)
        for employee_name in employees:
            self.employees_listbox.insert(tk.END, employee_name)

    def render_client_calls(self, current_call: Optional[ClientCall], queued_calls: List[ClientCall], progress: float) -> None:
        self._current_client_call = current_call
        self._queued_client_calls = queued_calls[:]
        self._current_client_call_progress = progress
        rows: list[tuple[str, float]] = []
        if current_call is not None:
            rows.append((current_call.display_text, max(0.0, min(progress, 1.0))))

        for call in queued_calls[: max(0, 3 - len(rows))]:
            rows.append((call.display_text, 0.0))

        while len(rows) < 3:
            rows.append(("", 0.0))

        for index, (text, fill_ratio) in enumerate(rows):
            canvas = self.client_call_row_canvases[index]
            if not canvas.winfo_exists():
                continue

            fill_id = self.client_call_row_fill_ids[index]
            text_id = self.client_call_row_text_ids[index]
            width = max(canvas.winfo_width(), 1)
            height = max(canvas.winfo_height(), 24)

            canvas.config(bg="#ffffff")
            canvas.coords(fill_id, 0, 0, width * fill_ratio, height)
            canvas.itemconfigure(fill_id, state="normal" if text and fill_ratio > 0 else "hidden")
            canvas.coords(text_id, 6, height / 2)
            canvas.itemconfigure(text_id, text=text, fill="#ffffff" if fill_ratio > 0.6 else "#1f2933")

            if not text:
                canvas.itemconfigure(fill_id, state="hidden")

    def set_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(self.device_menu, self.device_var, device_names, selected)

    def set_client_calls_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(self.client_calls_device_menu, self.client_calls_device_var, device_names, selected)

    def set_client_calls_voice_message_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(
            self.client_calls_voice_message_device_menu,
            self.client_calls_voice_message_device_var,
            device_names,
            selected,
        )

    def set_generator_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(self.generator_device_menu, self.generator_device_var, device_names, selected)

    def set_generator_voice_options(self, voice_names: List[str], selected: str = "") -> None:
        self._generator_voice_options = voice_names[:]
        self.generator_voice_combobox["values"] = tuple(voice_names)
        if selected:
            self.generator_voice_var.set(selected)
        elif voice_names:
            self.generator_voice_var.set(voice_names[0])
        else:
            self.generator_voice_var.set("")

    def set_client_calls_text_voice_options(self, voice_names: List[str], selected: str = "") -> None:
        self._client_calls_text_voice_options = voice_names[:]
        self.client_calls_text_voice_combobox["values"] = tuple(voice_names)
        if selected:
            self.client_calls_text_voice_var.set(selected)
        elif voice_names:
            self.client_calls_text_voice_var.set(voice_names[0])
        else:
            self.client_calls_text_voice_var.set("")

    def set_client_calls_text_language_options(self, language_names: List[str], selected: str = "") -> None:
        self._client_calls_text_language_options = language_names[:]
        self.client_calls_text_language_combobox["values"] = tuple(language_names)
        if selected:
            self.client_calls_text_language_var.set(selected)
        elif language_names:
            self.client_calls_text_language_var.set(language_names[0])
        else:
            self.client_calls_text_language_var.set("")

    def set_client_calls_text_voice_preview_playing(self, is_playing: bool) -> None:
        self.client_calls_text_voice_preview_button_var.set("Стоп" if is_playing else "Послушать")

    def set_generator_language_options(self, language_names: List[str], selected: str = "") -> None:
        self._generator_language_options = language_names[:]
        self.generator_language_combobox["values"] = tuple(language_names)
        if selected:
            self.generator_language_var.set(selected)
        elif language_names:
            self.generator_language_var.set(language_names[0])
        else:
            self.generator_language_var.set("")

    def set_volume(self, value: float) -> None:
        self.volume_var.set(value)
        self.volume_display_var.set(f"{value:.1f}")

    def set_client_calls_volume(self, value: float) -> None:
        self.client_calls_volume_var.set(value)
        self.client_calls_volume_display_var.set(f"{value:.1f}")

    def set_client_calls_voice_message_volume(self, value: float) -> None:
        self.client_calls_voice_message_volume_var.set(value)
        self.client_calls_voice_message_volume_display_var.set(f"{value:.1f}")

    def set_client_calls_speech_rate(self, value: float) -> None:
        self.client_calls_speech_rate_var.set(value)
        self.client_calls_speech_rate_display_var.set(f"{value:.1f}")

    def set_notification_volume(self, value: float) -> None:
        self.notification_volume_var.set(value)
        self.notification_volume_display_var.set(f"{value:.1f}")

    def set_generator_volume(self, value: float) -> None:
        self.generator_volume_var.set(value)
        self.generator_volume_display_var.set(f"{value:.1f}")

    def set_generator_voice(self, voice_name: str) -> None:
        self.generator_voice_var.set(voice_name)

    def set_generator_language(self, language_name: str) -> None:
        self.generator_language_var.set(language_name)

    def _bind_standard_edit_shortcuts(self, widget: tk.Widget) -> None:
        for sequence in ("<Command-a>", "<Control-a>"):
            widget.bind(sequence, self._select_all_shortcut)
        for sequence in ("<Command-c>", "<Control-c>"):
            widget.bind(sequence, self._copy_shortcut)
        for sequence in ("<Command-v>", "<Control-v>"):
            widget.bind(sequence, self._paste_shortcut)
        for sequence in ("<Command-x>", "<Control-x>"):
            widget.bind(sequence, self._cut_shortcut)
        widget.bind("<KeyPress>", self._handle_edit_shortcuts_on_any_layout, add="+")

    def _bind_edit_shortcuts_recursively(self, widget: tk.Widget) -> None:
        if isinstance(widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
            self._bind_standard_edit_shortcuts(widget)

        for child in widget.winfo_children():
            self._bind_edit_shortcuts_recursively(child)

    def _handle_edit_shortcuts_on_any_layout(self, event: tk.Event) -> str | None:
        if not self._has_edit_shortcut_modifier(event):
            return None

        key = getattr(event, "keysym", "")
        if key in self.EDIT_SHORTCUT_KEYS["select_all"]:
            return self._select_all_shortcut(event)
        if key in self.EDIT_SHORTCUT_KEYS["copy"]:
            return self._copy_shortcut(event)
        if key in self.EDIT_SHORTCUT_KEYS["paste"]:
            return self._paste_shortcut(event)
        if key in self.EDIT_SHORTCUT_KEYS["cut"]:
            return self._cut_shortcut(event)
        return None

    def _has_edit_shortcut_modifier(self, event: tk.Event) -> bool:
        state = getattr(event, "state", 0)
        if self._is_windows:
            return bool(state & 0x4)
        return bool(state & 0x4 or state & 0x8)

    def _select_all_shortcut(self, event: tk.Event) -> str:
        widget = event.widget
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
        elif isinstance(widget, (tk.Entry, ttk.Entry)):
            widget.selection_range(0, tk.END)
            widget.icursor(tk.END)
        return "break"

    def _copy_shortcut(self, event: tk.Event) -> str:
        event.widget.event_generate("<<Copy>>")
        return "break"

    def _paste_shortcut(self, event: tk.Event) -> str:
        event.widget.event_generate("<<Paste>>")
        return "break"

    def _cut_shortcut(self, event: tk.Event) -> str:
        event.widget.event_generate("<<Cut>>")
        return "break"

    def get_client_calls_interval(self) -> str:
        return self.client_calls_interval_var.get().strip()

    def set_client_calls_interval(self, value: float) -> None:
        if float(value).is_integer():
            self.client_calls_interval_var.set(str(int(value)))
        else:
            self.client_calls_interval_var.set(str(value).replace(".", ","))

    def set_client_calls_repeat_enabled(self, enabled: bool) -> None:
        self.client_calls_repeat_var.set(enabled)

    def get_client_calls_repeat_interval(self) -> str:
        return self.client_calls_repeat_interval_var.get().strip()

    def set_client_calls_repeat_interval(self, value: float) -> None:
        if float(value).is_integer():
            self.client_calls_repeat_interval_var.set(str(int(value)))
        else:
            self.client_calls_repeat_interval_var.set(str(value).replace(".", ","))

    def get_scheduler_weekdays(self) -> list[int]:
        return [day for day, _ in self.WEEKDAY_LABELS if self.scheduler_weekday_vars[day].get()]

    def set_scheduler_weekdays(self, weekdays: list[int]) -> None:
        selected = set(weekdays)
        for day, _ in self.WEEKDAY_LABELS:
            self.scheduler_weekday_vars[day].set(day in selected)

    def set_scheduler_notification_enabled(self, enabled: bool) -> None:
        self.scheduler_notification_var.set(enabled)

    def set_autostart_enabled(self, enabled: bool) -> None:
        self.autostart_var.set(enabled)

    def set_client_calls_notification_enabled(self, enabled: bool) -> None:
        self.client_calls_notification_var.set(enabled)

    def set_client_calls_repeat_notification_enabled(self, enabled: bool) -> None:
        self.client_calls_repeat_notification_var.set(enabled)

    def is_scheduler_notification_enabled(self) -> bool:
        return self.scheduler_notification_var.get()

    def is_client_calls_notification_enabled(self) -> bool:
        return self.client_calls_notification_var.get()

    def is_client_calls_repeat_enabled(self) -> bool:
        return self.client_calls_repeat_var.get()

    def is_client_calls_repeat_notification_enabled(self) -> bool:
        return self.client_calls_repeat_notification_var.get()

    def is_autostart_enabled(self) -> bool:
        return self.autostart_var.get()

    def show_error(self, text: str) -> None:
        messagebox.showerror("Ошибка", text)

    def set_main_window_geometry(self, geometry: str) -> None:
        self._fit_window_to_content(self.root)
        position = self._extract_window_position(geometry)
        if position:
            self.root.geometry(position)

    def get_main_window_geometry(self) -> str:
        return self._extract_window_position(self.root.geometry())

    def _fit_window_to_content(self, window: tk.Misc) -> None:
        window.update_idletasks()
        width = window.winfo_reqwidth()
        height = window.winfo_reqheight()
        if window is self._client_calls_settings_window:
            width = min(width, self.root.winfo_width())
        window.geometry(f"{width}x{height}")

    def _show_side_window(self, window: tk.Toplevel) -> None:
        window.deiconify()
        window.lift()
        window.focus_set()

    def _register_window_group_behavior(self) -> None:
        for window in self._get_app_windows():
            window.bind("<Button-1>", self._app_window_activated, add="+")
            window.bind("<FocusIn>", self._app_window_activated, add="+")

    def _get_app_windows(self) -> list[tk.Misc]:
        windows: list[tk.Misc] = [self.root]
        for window in (
            self._client_calls_settings_window,
            self._generator_window,
            self._employees_window,
        ):
            if window is not None:
                windows.append(window)
        return windows

    def _app_window_activated(self, event: tk.Event) -> None:
        active_window = self._resolve_widget(getattr(event, "widget", None))
        if active_window is None:
            return

        try:
            active_toplevel = active_window.winfo_toplevel()
        except tk.TclError:
            return

        app_windows = self._get_app_windows()
        for window in app_windows:
            if window is active_toplevel:
                continue
            if window is self.root and active_toplevel is not self.root:
                continue
            try:
                if window.winfo_viewable():
                    window.lift()
            except tk.TclError:
                continue

        try:
            if active_toplevel.winfo_viewable():
                active_toplevel.lift()
        except tk.TclError:
            return

    def _extract_window_position(self, geometry: str) -> str:
        if not geometry:
            return ""

        parts = geometry.split("+")
        if len(parts) < 3:
            return ""

        x_pos = parts[-2].strip()
        y_pos = parts[-1].strip()
        if not x_pos or not y_pos:
            return ""

        return f"+{x_pos}+{y_pos}"

    def _apply_window_icon(self, window: tk.Misc) -> None:
        if not os.path.exists(APP_ICON_FILE):
            return

        if self._is_windows:
            try:
                window.iconbitmap(APP_ICON_FILE)
            except tk.TclError:
                pass

        try:
            icon_image = Image.open(APP_ICON_FILE)
            self._window_icon_image = ImageTk.PhotoImage(icon_image)
            window.iconphoto(True, self._window_icon_image)
        except Exception:
            pass

    def _set_option_menu_values(
        self,
        option_menu: tk.OptionMenu,
        variable: tk.StringVar,
        options: List[str],
        selected: str = "",
    ) -> None:
        menu = option_menu["menu"]
        menu.delete(0, "end")

        for name in options:
            menu.add_command(label=name, command=lambda value=name: variable.set(value))

        if self._is_windows:
            longest_option = max((len(name) for name in options), default=24)
            option_menu.config(width=min(max(longest_option, 24), 48))

        if options:
            variable.set(selected if selected in options else options[0])
        else:
            variable.set("")

    def _handle_volume_change(
        self,
        value: str,
        display_var: tk.StringVar,
        callback: Optional[Callable[[float], None]],
    ) -> None:
        volume = float(value)
        display_var.set(f"{volume:.1f}")
        if callback:
            callback(volume)

    def _create_settings_scale(
        self,
        parent: tk.Misc,
        variable: tk.Variable,
        command,
        from_: float,
        to: float,
        resolution: float,
    ) -> tk.Scale:
        return tk.Scale(
            parent,
            from_=from_,
            to=to,
            resolution=resolution,
            orient="horizontal",
            variable=variable,
            command=command,
            showvalue=False,
            length=210,
            width=10,
            sliderlength=16,
            highlightthickness=0,
            bd=0,
        )

    def _set_file_value(self, path_var: tk.StringVar, display_var: tk.StringVar, file_path: str) -> None:
        path_var.set(file_path)
        display_var.set(os.path.basename(file_path) if file_path else "")

    def _filter_combobox_values(self, combobox: ttk.Combobox, all_values: List[str], query: str) -> None:
        normalized_query = query.strip().lower()
        if not normalized_query:
            combobox["values"] = tuple(all_values)
            return

        filtered = [value for value in all_values if normalized_query in value.lower()]
        combobox["values"] = tuple(filtered if filtered else all_values)

    def _resolve_widget(self, widget) -> tk.Misc | None:
        if isinstance(widget, str):
            try:
                return self.root.nametowidget(widget)
            except KeyError:
                return None
        return widget

    def _is_editable_text_widget(self, widget) -> bool:
        resolved_widget = self._resolve_widget(widget)
        return isinstance(resolved_widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox))

    def _should_handle_employee_shortcut(self, event: tk.Event) -> bool:
        if self._employees_window is None or not self._employees_window.winfo_viewable():
            return False
        if self.employees_listbox.curselection():
            return True

        widget = self._resolve_widget(getattr(event, "widget", None))
        if widget is None:
            widget = self.root.focus_get()
        if widget is None:
            return False

        try:
            return widget.winfo_toplevel() is self._employees_window
        except tk.TclError:
            return False

    def _is_widget_inside_listbox(self, widget: tk.Misc) -> bool:
        current_widget: tk.Misc | None = widget
        while current_widget is not None:
            if current_widget is self.listbox or current_widget is self.employees_listbox:
                return True
            parent_name = current_widget.winfo_parent()
            if not parent_name:
                break
            try:
                current_widget = current_widget.nametowidget(parent_name)
            except KeyError:
                break
        return False

    def _clear_text_selection(self, widget: tk.Misc) -> None:
        focus_widget = self.root.focus_get()
        for current_widget in {widget, focus_widget}:
            if current_widget is None:
                continue
            if isinstance(current_widget, (tk.Entry, ttk.Entry)):
                try:
                    current_widget.selection_clear()
                except tk.TclError:
                    pass
            elif isinstance(current_widget, ttk.Combobox):
                try:
                    current_widget.selection_clear()
                except tk.TclError:
                    pass
            elif isinstance(current_widget, tk.Text):
                current_widget.tag_remove("sel", "1.0", "end")

    def _is_interactive_widget(self, widget: tk.Misc) -> bool:
        interactive_types = (
            tk.Entry,
            tk.Text,
            tk.Listbox,
            tk.Button,
            tk.Checkbutton,
            tk.Scale,
            tk.Scrollbar,
            tk.Menubutton,
            ttk.Entry,
            ttk.Combobox,
            ttk.Notebook,
            ttk.Button,
            ttk.Checkbutton,
            ttk.Scale,
            ttk.Scrollbar,
        )
        if isinstance(widget, interactive_types):
            return True

        widget_class = str(widget.winfo_class()).lower()
        if "combobox" in widget_class or "listbox" in widget_class or "menu" in widget_class or "notebook" in widget_class:
            return True

        widget_name = str(widget)
        if "popdown" in widget_name:
            return True

        return False

    def _generate_ai_speech_clicked(self) -> None:
        if self.on_generate_ai_speech:
            self.on_generate_ai_speech()

    def _save_generated_ai_speech_clicked(self) -> None:
        if self.on_save_generated_ai_speech:
            self.on_save_generated_ai_speech()

    def _add_employee_clicked(self) -> None:
        if self.on_add_employee:
            self.on_add_employee()

    def _delete_employee_clicked(self) -> None:
        if self.on_delete_employee:
            self.on_delete_employee()

    def _employee_enter_pressed(self, event: tk.Event) -> str:
        self._add_employee_clicked()
        return "break"

    def _employee_entry_focused(self, event: tk.Event) -> None:
        if not self._employee_placeholder_visible or self._employee_entry is None:
            return
        self.employee_input_var.set("")
        self._employee_entry.config(fg="#111111", font=self._employee_entry_font)
        self._employee_placeholder_visible = False

    def _employee_entry_unfocused(self, event: tk.Event) -> None:
        if self.employee_input_var.get().strip():
            return
        self._show_employee_placeholder()

    def _show_employee_placeholder(self) -> None:
        if self._employee_entry is None:
            return
        self.employee_input_var.set(self._employee_placeholder_text)
        self._employee_entry.config(fg="#8a8a8a", font=self._employee_entry_placeholder_font)
        self._employee_entry.icursor(0)
        self._employee_placeholder_visible = True

    def _generator_enter_pressed(self, event: tk.Event) -> str:
        self._generate_ai_speech_clicked()
        return "break"
