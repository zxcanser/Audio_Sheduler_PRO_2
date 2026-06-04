import calendar
from datetime import date
import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional, Callable

from models import ScheduleEntry


def set_selected_file(window, file_path: str) -> None:
    window._set_file_value(window.selected_file_path, window.selected_file_display, file_path)
    if not file_path:
        window.set_time_input("00:00")


def clear_schedule_selection(window) -> None:
    window.listbox.selection_clear(0, tk.END)
    window.set_selected_file("")
    window.set_schedule_action_button_label("Добавить")


def set_main_playback_active(window, is_playing: bool) -> None:
    window._main_playback_active = is_playing
    if window._play_button is not None:
        window._play_button.configure(text="■" if is_playing else "▶")


def set_schedule_action_button_label(window, text: str) -> None:
    if window._schedule_add_button is not None:
        window._schedule_add_button.configure(text=text)


def set_client_calls_file(window, file_path: str) -> None:
    window._set_file_value(window.client_calls_file_path, window.client_calls_file_display, file_path)


def set_client_calls_api_enabled(window, enabled: bool) -> None:
    window.client_calls_api_enabled_var.set(enabled)


def set_client_calls_api_host(window, host: str) -> None:
    window.client_calls_api_host_var.set(host)


def set_client_calls_api_port(window, port: int) -> None:
    window.client_calls_api_port_var.set(str(port))


def set_client_calls_api_token(window, token: str) -> None:
    window.client_calls_api_token_var.set(token)
    masked = window._mask_api_token(token)
    window.client_calls_api_token_button_var.set(masked)
    if window._client_calls_api_token_entry is not None:
        window._client_calls_api_token_entry.configure(width=max(len(masked), 1))


def set_client_calls_voice_message_file(window, file_path: str) -> None:
    window._set_file_value(window.client_calls_voice_message_file_path, window.client_calls_voice_message_file_display, file_path)


def set_notification_sound_file(window, file_path: str) -> None:
    window._set_file_value(window.notification_sound_file_path, window.notification_sound_display, file_path)


def set_notification_sound_preview_playing(window, is_playing: bool) -> None:
    window.notification_sound_preview_button_var.set("Стоп" if is_playing else "Прослушать")


def _mask_secret(window, value: str, visible_suffix: int = 5) -> str:
    clean_value = value.strip()
    if not clean_value:
        return "Не указан"
    return f"••••••••••{clean_value[-visible_suffix:]}"


def set_generator_api_key(window, api_key: str) -> None:
    clean_key = (api_key or "").strip()
    window._generator_api_key_value = clean_key
    window._generator_api_key_masked = True
    masked = window._mask_secret(clean_key, visible_suffix=5)
    window.generator_api_key_var.set(masked)
    window.generator_api_key_button_var.set(masked)
    if window._generator_api_key_entry is not None:
        window._generator_api_key_entry.configure(width=max(len(masked), 10))


def get_generator_api_key(window) -> str:
    return window._generator_api_key_value.strip()


def set_employees_file(window, file_path: str) -> None:
    window._set_file_value(window.employees_file_path, window.employees_file_display, file_path)


def get_selected_file(window) -> str:
    return window.selected_file_path.get()


def get_client_calls_file(window) -> str:
    return window.client_calls_file_path.get()


def is_client_calls_api_enabled(window) -> bool:
    return window.client_calls_api_enabled_var.get()


def get_client_calls_api_host(window) -> str:
    return window.client_calls_api_host_var.get().strip()


def get_client_calls_api_port(window) -> str:
    return window.client_calls_api_port_var.get().strip()


def get_notification_sound_file(window) -> str:
    return window.notification_sound_file_path.get()


def get_generator_text(window) -> str:
    if window._generator_text_widget is None:
        return ""
    return window._generator_text_widget.get("1.0", "end-1c")


def get_generator_file_name(window) -> str:
    return window.generator_file_name_var.get()


def get_employee_input(window) -> str:
    if window._employee_placeholder_visible:
        return ""
    return window.employee_input_var.get()


def clear_employee_input(window) -> None:
    window.employee_input_var.set("")
    window._show_employee_placeholder()


def focus_employees_list(window) -> None:
    try:
        window.employees_listbox.focus_set()
    except tk.TclError:
        return


def get_selected_employee(window) -> str:
    selected = window.employees_listbox.curselection()
    if not selected:
        return ""
    return window.employees_listbox.get(selected[0])


def get_time_input(window) -> tuple[str, str]:
    window._normalize_time_value()
    hours, minutes = window.time_var.get().split(":")
    return hours, minutes


def set_time_input(window, time_str: str) -> None:
    window.time_var.set(time_str.strip() or "00:00")
    window._normalize_time_value()
    window._set_time_cursor(0)


def get_selected_index(window) -> Optional[int]:
    selected = window.listbox.curselection()
    return selected[0] if selected else None


def get_selected_entry_id(window) -> Optional[str]:
    index = window.get_selected_index()
    return window.get_entry_id_by_index(index)


def get_entry_id_by_index(window, index: Optional[int]) -> Optional[str]:
    if index is None:
        return None
    if 0 <= index < len(window._entry_ids_by_index):
        return window._entry_ids_by_index[index]
    return None


def fill_schedule_list(window, entries: List[ScheduleEntry], missing_entry_ids: Optional[set[str]] = None) -> None:
    window.listbox.delete(0, tk.END)
    window._entry_ids_by_index.clear()
    missing_ids = missing_entry_ids or set()

    for entry in entries:
        window.listbox.insert(tk.END, f"{entry.time_str} | {entry.file_name}")
        window._entry_ids_by_index.append(entry.entry_id)
        item_index = window.listbox.size() - 1
        try:
            window.listbox.itemconfig(item_index, fg="#b42318" if entry.entry_id in missing_ids else "#1f2933")
        except tk.TclError:
            pass


def fill_employees_list(window, employees: List[str]) -> None:
    window.employees_listbox.delete(0, tk.END)
    for employee_name in employees:
        window.employees_listbox.insert(tk.END, employee_name)


def set_device_options(window, device_names: List[str], selected: str = "") -> None:
    window._set_option_menu_values(window.device_menu, window.device_var, device_names, selected)


def set_client_calls_device_options(window, device_names: List[str], selected: str = "") -> None:
    window._set_option_menu_values(window.client_calls_device_menu, window.client_calls_device_var, device_names, selected)


def set_client_calls_voice_message_device_options(window, device_names: List[str], selected: str = "") -> None:
    window._set_option_menu_values(
        window.client_calls_voice_message_device_menu,
        window.client_calls_voice_message_device_var,
        device_names,
        selected,
    )


def set_generator_device_options(window, device_names: List[str], selected: str = "") -> None:
    window._set_option_menu_values(window.generator_device_menu, window.generator_device_var, device_names, selected)


def set_generator_voice_options(window, voice_names: List[str], selected: str = "") -> None:
    window._generator_voice_options = voice_names[:]
    window.generator_voice_combobox["values"] = tuple(voice_names)
    if selected:
        window.generator_voice_var.set(selected)
    elif voice_names:
        window.generator_voice_var.set(voice_names[0])
    else:
        window.generator_voice_var.set("")


def set_client_calls_text_voice_options(window, voice_names: List[str], selected: str = "") -> None:
    window._client_calls_text_voice_options = voice_names[:]
    window.client_calls_text_voice_combobox["values"] = tuple(voice_names)
    if selected:
        window.client_calls_text_voice_var.set(selected)
    elif voice_names:
        window.client_calls_text_voice_var.set(voice_names[0])
    else:
        window.client_calls_text_voice_var.set("")


def set_client_calls_text_language_options(window, language_names: List[str], selected: str = "") -> None:
    window._client_calls_text_language_options = language_names[:]
    window.client_calls_text_language_combobox["values"] = tuple(language_names)
    if selected:
        window.client_calls_text_language_var.set(selected)
    elif language_names:
        window.client_calls_text_language_var.set(language_names[0])
    else:
        window.client_calls_text_language_var.set("")


def set_client_calls_text_voice_preview_playing(window, is_playing: bool) -> None:
    window.client_calls_text_voice_preview_button_var.set("Стоп" if is_playing else "Прослушать")


def set_generator_language_options(window, language_names: List[str], selected: str = "") -> None:
    window._generator_language_options = language_names[:]
    window.generator_language_combobox["values"] = tuple(language_names)
    if selected:
        window.generator_language_var.set(selected)
    elif language_names:
        window.generator_language_var.set(language_names[0])
    else:
        window.generator_language_var.set("")


def set_generator_accent_options(window, accent_names: List[str], selected: str = "") -> None:
    window._generator_accent_options = accent_names[:]
    if hasattr(window, "generator_accent_combobox"):
        window.generator_accent_combobox["values"] = tuple(accent_names)
    if hasattr(window, "generator_accent_window_combobox"):
        window.generator_accent_window_combobox["values"] = tuple(accent_names)
    if selected:
        window.generator_accent_var.set(selected)
    else:
        window.generator_accent_var.set(accent_names[0] if accent_names else "")


def set_generator_accent_enabled(window, enabled: bool, message: str = "") -> None:
    state = "normal" if enabled else "disabled"
    if hasattr(window, "generator_accent_combobox"):
        window.generator_accent_combobox.configure(state=state)
    if hasattr(window, "generator_accent_window_combobox"):
        window.generator_accent_window_combobox.configure(state=state)
    if hasattr(window, "generator_accent_hint_label"):
        window.generator_accent_hint_label.config(text=message)
    if hasattr(window, "generator_accent_window_hint_label"):
        window.generator_accent_window_hint_label.config(text=message)


def set_volume(window, value: float) -> None:
    window.volume_var.set(value)
    window.volume_display_var.set(f"{value:.1f}")


def set_client_calls_volume(window, value: float) -> None:
    window.client_calls_volume_var.set(value)
    window.client_calls_volume_display_var.set(f"{value:.1f}")


def set_client_calls_voice_message_volume(window, value: float) -> None:
    window.client_calls_voice_message_volume_var.set(value)
    window.client_calls_voice_message_volume_display_var.set(f"{value:.1f}")


def set_client_calls_speech_rate(window, value: float) -> None:
    window.client_calls_speech_rate_var.set(value)
    window.client_calls_speech_rate_display_var.set(f"{value:.1f}")


def set_number_trim_silence_enabled(window, enabled: bool) -> None:
    window.number_trim_silence_var.set(enabled)


def set_number_silence_threshold(window, value: int) -> None:
    window.number_silence_threshold_var.set(value)
    window.number_silence_threshold_display_var.set(str(int(value)))


def set_number_trim_leading_padding(window, value: int) -> None:
    window.number_trim_leading_padding_var.set(value)
    window.number_trim_leading_padding_display_var.set(str(int(value)))


def set_number_trim_trailing_padding(window, value: int) -> None:
    window.number_trim_trailing_padding_var.set(value)
    window.number_trim_trailing_padding_display_var.set(str(int(value)))


def set_number_symbol_pause(window, value: int) -> None:
    window.number_symbol_pause_var.set(value)
    window.number_symbol_pause_display_var.set(str(int(value)))


def set_notification_volume(window, value: float) -> None:
    window.notification_volume_var.set(value)
    window.notification_volume_display_var.set(f"{value:.1f}")


def set_generator_volume(window, value: float) -> None:
    window.generator_volume_var.set(value)
    window.generator_volume_display_var.set(f"{value:.1f}")


def set_generator_master_volume(window, value: int) -> None:
    window.generator_master_volume_var.set(value)
    window.generator_master_volume_display_var.set(str(int(value)))


def set_generator_speed(window, value: int) -> None:
    window.generator_speed_var.set(value)
    window.generator_speed_display_var.set(str(int(value)))


def set_generator_voice(window, voice_name: str) -> None:
    window.generator_voice_var.set(voice_name)


def set_generator_language(window, language_name: str) -> None:
    window.generator_language_var.set(language_name)


def get_client_calls_interval(window) -> str:
    return window.client_calls_interval_var.get().strip()


def set_client_calls_interval(window, value: float) -> None:
    if float(value).is_integer():
        window.client_calls_interval_var.set(str(int(value)))
    else:
        window.client_calls_interval_var.set(str(value).replace(".", ","))


def set_client_calls_repeat_enabled(window, enabled: bool) -> None:
    window.client_calls_repeat_var.set(enabled)


def get_client_calls_repeat_interval(window) -> str:
    return window.client_calls_repeat_interval_var.get().strip()


def get_number_preview_text(window) -> str:
    return window.number_preview_var.get().strip()


def set_client_calls_repeat_interval(window, value: float) -> None:
    if float(value).is_integer():
        window.client_calls_repeat_interval_var.set(str(int(value)))
    else:
        window.client_calls_repeat_interval_var.set(str(value).replace(".", ","))


def set_workday_status(window, status: int | None) -> None:
    if status in {0, 2}:
        text = "Рабочий день"
        color = "#2f855a"
    elif status == 1:
        text = "Нерабочий день"
        color = "#c53030"
    else:
        text = "Проверка дня"
        color = "#8a8a8a"

    window.workday_status_var.set(text)
    if window._workday_lamp_canvas is not None and window._workday_lamp_id is not None:
        window._workday_lamp_canvas.itemconfigure(window._workday_lamp_id, fill=color)


def show_workday_calendar_loading(window, year: int) -> None:
    calendar_window = _prepare_workday_calendar_window(window, f"Календарь {year}")
    tk.Label(calendar_window, text="Загружаю производственный календарь...").pack(padx=24, pady=24)


def show_workday_calendar(window, year: int, day_statuses: dict[date, int]) -> None:
    calendar_window = _prepare_workday_calendar_window(window, f"Производственный календарь {year}")
    root_frame = tk.Frame(calendar_window, padx=10, pady=10)
    root_frame.pack(fill="both", expand=True)

    months_frame = tk.Frame(root_frame)
    months_frame.grid(row=0, column=0)

    month_names = [
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]
    weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    month_calendar = calendar.Calendar(firstweekday=0)
    today = date.today()

    for month_index, month_name in enumerate(month_names, start=1):
        month_frame = tk.LabelFrame(months_frame, text=month_name, padx=4, pady=4)
        month_frame.grid(row=(month_index - 1) // 3, column=(month_index - 1) % 3, padx=4, pady=4, sticky="n")

        for column, weekday_name in enumerate(weekday_names):
            tk.Label(month_frame, text=weekday_name, width=3, font=("TkDefaultFont", 8, "bold")).grid(
                row=0,
                column=column,
            )

        for row, week in enumerate(month_calendar.monthdatescalendar(year, month_index), start=1):
            for column, current_day in enumerate(week):
                if current_day.month != month_index:
                    tk.Label(month_frame, text="", width=3, font=("TkDefaultFont", 8)).grid(row=row, column=column)
                    continue

                status = day_statuses.get(current_day)
                bg = "#ffdede" if status == 1 else None
                relief = "solid" if current_day == today else "flat"
                day_label = tk.Label(
                    month_frame,
                    text=str(current_day.day),
                    width=3,
                    relief=relief,
                    bd=1 if current_day == today else 0,
                    font=("TkDefaultFont", 8),
                )
                if bg is not None:
                    day_label.configure(bg=bg)
                day_label.grid(row=row, column=column, padx=1, pady=1)

    calendar_window.resizable(False, False)
    calendar_window.update_idletasks()


def close_workday_calendar(window) -> None:
    calendar_window = window._workday_calendar_window
    if calendar_window is None:
        return
    try:
        if calendar_window.winfo_exists():
            calendar_window.destroy()
    except tk.TclError:
        pass
    window._workday_calendar_window = None


def _prepare_workday_calendar_window(window, title: str) -> tk.Toplevel:
    calendar_window = window._workday_calendar_window
    if calendar_window is None or not calendar_window.winfo_exists():
        calendar_window = tk.Toplevel(window.root)
        calendar_window.transient(window.root)
        window._workday_calendar_window = calendar_window
    else:
        calendar_window.deiconify()
        calendar_window.lift()

    calendar_window.title(title)
    for child in calendar_window.winfo_children():
        child.destroy()

    def handle_close() -> None:
        window._workday_calendar_window = None
        calendar_window.destroy()

    calendar_window.protocol("WM_DELETE_WINDOW", handle_close)
    return calendar_window



def set_scheduler_notification_enabled(window, enabled: bool) -> None:
    window.scheduler_notification_var.set(enabled)


def set_autostart_enabled(window, enabled: bool) -> None:
    window.autostart_var.set(enabled)


def set_update_checking(window, checking: bool, text: str = "Проверяю...") -> None:
    window.update_check_button_var.set(text if checking else "Проверить обновления")
    if hasattr(window, "update_check_button"):
        window.update_check_button.configure(state="disabled" if checking else "normal")


def set_client_calls_notification_enabled(window, enabled: bool) -> None:
    window.client_calls_notification_var.set(enabled)


def set_client_calls_repeat_notification_enabled(window, enabled: bool) -> None:
    window.client_calls_repeat_notification_var.set(enabled)


def is_scheduler_notification_enabled(window) -> bool:
    return window.scheduler_notification_var.get()


def is_client_calls_notification_enabled(window) -> bool:
    return window.client_calls_notification_var.get()


def is_client_calls_repeat_enabled(window) -> bool:
    return window.client_calls_repeat_var.get()


def is_client_calls_repeat_notification_enabled(window) -> bool:
    return window.client_calls_repeat_notification_var.get()


def is_number_trim_silence_enabled(window) -> bool:
    return window.number_trim_silence_var.get()


def is_autostart_enabled(window) -> bool:
    return window.autostart_var.get()


def show_error(window, text: str) -> None:
    messagebox.showerror("Ошибка", text)


def show_info(window, title: str, text: str) -> None:
    messagebox.showinfo(title, text)


def ask_yes_no(window, title: str, text: str) -> bool:
    return bool(messagebox.askyesno(title, text))


def set_last_error_status(window, text: str) -> None:
    message = text.strip() or "Готово"
    window.last_error_status_var.set(message)
    is_error = message != "Готово"
    window.last_error_status_label.configure(fg="#b42318" if is_error else "#2f855a")


def set_main_window_geometry(window, geometry: str) -> None:
    window._fit_window_to_content(window.root)
    position = window._extract_window_position(geometry)
    if position:
        window.root.geometry(position)


def get_main_window_geometry(window) -> str:
    return window._extract_window_position(window.root.geometry())


def _set_option_menu_values(
    window,
    option_menu: tk.OptionMenu,
    variable: tk.StringVar,
    options: List[str],
    selected: str = "",
) -> None:
    menu = option_menu["menu"]
    menu.delete(0, "end")

    for name in options:
        menu.add_command(label=name, command=lambda value=name: variable.set(value))

    if window._is_windows:
        longest_option = max((len(name) for name in options), default=24)
        option_menu.config(width=min(max(longest_option, 24), 48))

    if options:
        variable.set(selected if selected in options else options[0])
    else:
        variable.set("")


def _handle_volume_change(
    window,
    value: str,
    display_var: tk.StringVar,
    callback: Optional[Callable[[float], None]],
) -> None:
    volume = float(value)
    display_var.set(f"{volume:.1f}")
    if callback:
        callback(volume)


def _handle_speed_change(
    window,
    value: str,
    display_var: tk.StringVar,
    callback: Optional[Callable[[float], None]],
) -> None:
    speed = float(value)
    display_var.set(str(int(round(speed))))
    if callback:
        callback(speed)


def _create_settings_scale(
    window,
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
        length=180 if window._is_windows else 210,
        width=10,
        sliderlength=16,
        highlightthickness=0,
        bd=0,
    )


def _set_file_value(window, path_var: tk.StringVar, display_var: tk.StringVar, file_path: str) -> None:
    path_var.set(file_path)
    display_var.set(os.path.basename(file_path) if file_path else "")


def _filter_combobox_values(window, combobox: ttk.Combobox, all_values: List[str], query: str) -> None:
    normalized_query = query.strip().lower()
    if not normalized_query:
        combobox["values"] = tuple(all_values)
        return

    filtered = [value for value in all_values if normalized_query in value.lower()]
    combobox["values"] = tuple(filtered if filtered else all_values)


def _employee_entry_focused(window, event: tk.Event) -> None:
    if not window._employee_placeholder_visible or window._employee_entry is None:
        return
    window.employee_input_var.set("")
    window._employee_entry.config(fg="#111111", font=window._employee_entry_font)
    window._employee_placeholder_visible = False


def _employee_entry_unfocused(window, event: tk.Event) -> None:
    if window.employee_input_var.get().strip():
        return
    window._show_employee_placeholder()


def _show_employee_placeholder(window) -> None:
    if window._employee_entry is None:
        return
    window.employee_input_var.set(window._employee_placeholder_text)
    window._employee_entry.config(fg="#8a8a8a", font=window._employee_entry_placeholder_font)
    window._employee_entry.icursor(0)
    window._employee_placeholder_visible = True
