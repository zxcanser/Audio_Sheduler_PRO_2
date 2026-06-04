import os
import time
import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from PIL import Image, ImageTk

from config import APP_ICON_FILE
from models import ClientCall


def _time_entry_focused(window, event: tk.Event) -> str:
    window._normalize_time_value()
    window._set_time_cursor(0)
    return None


def _time_entry_clicked(window, event: tk.Event) -> str:
    if window._time_entry is None:
        return "break"
    entry = window._time_entry
    entry.focus_set()
    index = entry.index(f"@{event.x}")
    window._set_time_cursor(index)
    return "break"


def _time_entry_move_left(window, event: tk.Event) -> str:
    if window._time_entry is None:
        return "break"
    target_index = window._previous_time_digit_index(window._time_entry.index(tk.INSERT) - 1)
    window._set_time_cursor(0 if target_index is None else target_index)
    return "break"


def _time_entry_move_right(window, event: tk.Event) -> str:
    if window._time_entry is None:
        return "break"
    target_index = window._next_time_digit_index(window._time_entry.index(tk.INSERT) + 1)
    window._set_time_cursor(5 if target_index is None else target_index)
    return "break"


def _time_entry_home(window, event: tk.Event) -> str:
    window._set_time_cursor(0)
    return "break"


def _time_entry_end(window, event: tk.Event) -> str:
    window._set_time_cursor(5)
    return "break"


def _time_entry_backspace(window, event: tk.Event) -> str:
    if window._time_entry is None:
        return "break"
    cursor_index = window._time_entry.index(tk.INSERT)
    target_index = window._previous_time_digit_index(cursor_index - 1)
    if target_index is not None:
        window._replace_time_digit(target_index, "0")
        window._set_time_cursor(target_index)
    return "break"


def _time_entry_delete(window, event: tk.Event) -> str:
    if window._time_entry is None:
        return "break"
    cursor_index = window._time_entry.index(tk.INSERT)
    target_index = window._next_time_digit_index(cursor_index)
    if target_index is not None:
        window._replace_time_digit(target_index, "0")
        window._set_time_cursor(target_index)
    return "break"


def _time_entry_keypress(window, event: tk.Event) -> str | None:
    key = getattr(event, "keysym", "")
    char = getattr(event, "char", "")
    if window._has_edit_shortcut_modifier(event):
        return None
    if key in {"Tab", "Return", "KP_Enter", "Escape"}:
        return None
    if key in {"Left", "Right", "Home", "End", "BackSpace", "Delete"}:
        return "break"
    if key.startswith(("Shift_", "Control_", "Alt_", "Meta_", "Command_")):
        return None
    if not char:
        return "break"
    if not char.isdigit():
        return "break"

    if window._time_entry is None:
        return "break"
    cursor_index = window._time_entry.index(tk.INSERT)
    target_index = window._next_time_digit_index(cursor_index)
    if target_index is None:
        target_index = window._previous_time_digit_index(4)
    if target_index is None:
        return "break"

    window._replace_time_digit(target_index, char)
    next_index = window._next_time_digit_index(target_index + 1)
    window._set_time_cursor(5 if next_index is None else next_index)
    return "break"


def _normalize_time_value(window) -> None:
    raw_value = window.time_var.get() or ""
    digits = [char for char in raw_value if char.isdigit()]
    digits.extend(["0"] * (4 - len(digits)))
    normalized = f"{digits[0]}{digits[1]}:{digits[2]}{digits[3]}"
    window.time_var.set(normalized[:5])


def _set_time_cursor(window, index: int) -> None:
    if window._time_entry is None:
        return
    normalized_index = max(0, min(index, 5))
    if normalized_index == 2:
        normalized_index = 3 if index >= 2 else 1
    window._time_entry.icursor(normalized_index)
    window._time_entry.selection_clear()


def _replace_time_digit(window, index: int, digit: str) -> None:
    window._normalize_time_value()
    value = list(window.time_var.get())
    if index not in (0, 1, 3, 4):
        return
    value[index] = digit
    window.time_var.set("".join(value))


def _next_time_digit_index(window, index: int) -> int | None:
    for candidate in (0, 1, 3, 4):
        if candidate >= index:
            return candidate
    return None


def _previous_time_digit_index(window, index: int) -> int | None:
    for candidate in (4, 3, 1, 0):
        if candidate <= index:
            return candidate
    return None


def _global_left_click(window, event: tk.Event) -> None:
    widget = window._resolve_widget(event.widget)
    if widget is None:
        return
    try:
        if widget.winfo_toplevel() is not window.root:
            return
    except tk.TclError:
        return
    if window._is_widget_inside_listbox(widget):
        return
    if window._is_interactive_widget(widget):
        return

    window.listbox.selection_clear(0, tk.END)
    window.set_schedule_action_button_label("Добавить")
    window.employees_listbox.selection_clear(0, tk.END)
    window._clear_text_selection(widget)
    window.root.focus_set()


def _space_pressed(window, event: tk.Event) -> str:
    focused_widget = window.root.focus_get()
    if focused_widget is window._generator_text_widget:
        return "break"
    if focused_widget is window.employees_listbox:
        if window.on_preview_employee:
            window.on_preview_employee()
        return "break"
    if isinstance(focused_widget, (tk.Entry, ttk.Entry, ttk.Combobox, tk.Text)):
        return "break"
    if window._main_playback_active:
        if window.on_stop:
            window.on_stop()
    elif window.on_play:
        window.on_play()
    return "break"


def _schedule_listbox_double_clicked(window, event: tk.Event) -> str:
    clicked_index = window.listbox.nearest(event.y)
    if clicked_index < 0:
        return "break"

    bbox = window.listbox.bbox(clicked_index)
    if bbox is None:
        return "break"

    _x, y, _width, height = bbox
    if not (y <= event.y <= y + height):
        return "break"

    selected_index = int(clicked_index)
    now = time.monotonic()
    if (
        window._last_schedule_double_click_index == selected_index
        and (now - window._last_schedule_double_click_at) < 1.0
    ):
        return "break"

    window._last_schedule_double_click_index = selected_index
    window._last_schedule_double_click_at = now
    window.listbox.selection_clear(0, tk.END)
    window.listbox.selection_set(selected_index)
    window.listbox.activate(selected_index)
    entry_id = window.get_entry_id_by_index(selected_index)
    if not entry_id:
        return "break"
    if window.on_queue_selected_schedule:
        window.on_queue_selected_schedule(entry_id)
    return "break"


def _delete_key_pressed(window, event: tk.Event) -> str:
    if window._is_editable_text_widget(event.widget):
        return "break"
    if window._should_handle_employee_shortcut(event):
        window._delete_employee_clicked()
        return "break"
    window._delete_clicked()
    return "break"


def _delete_shortcut_pressed(window, event: tk.Event) -> str:
    if window._is_editable_text_widget(event.widget):
        return "break"
    if window._should_handle_employee_shortcut(event):
        window._delete_employee_clicked()
        return "break"
    window._delete_clicked()
    return "break"


def _employee_listbox_double_clicked(window, event: tk.Event) -> str:
    if window.on_preview_employee:
        window.on_preview_employee()
    return "break"


def _employee_listbox_space_pressed(window, event: tk.Event) -> str:
    if window.on_preview_employee:
        window.on_preview_employee()
    return "break"


def _show_employees_help_tooltip(window, event: tk.Event) -> None:
    window._hide_employees_help_tooltip()
    tooltip = tk.Toplevel(window.root)
    tooltip.wm_overrideredirect(True)
    tooltip.transient(window._employees_window)
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
    window._employees_help_tooltip = tooltip


def _hide_employees_help_tooltip(window, event: Optional[tk.Event] = None) -> None:
    if window._employees_help_tooltip is None:
        return
    window._safe_destroy_widget(window._employees_help_tooltip)
    window._employees_help_tooltip = None


def _resize_client_call_rows(window) -> None:
    if not window.client_calls_rows_frame.winfo_exists():
        return

    window.render_client_calls(
        window._current_client_call,
        window._queued_client_calls,
        window._current_client_call_progress,
    )


def show_client_calls_settings_window(window) -> None:
    if window._client_calls_settings_window is None:
        return

    window._settings_window_requested_visible = True
    window._fit_window_to_content(window._client_calls_settings_window)
    window._show_side_window(window._client_calls_settings_window)


def show_generator_window(window) -> None:
    if window._generator_window is None:
        return

    window._generator_window_requested_visible = True
    window._fit_window_to_content(window._generator_window)
    window._show_side_window(window._generator_window)


def show_employees_window(window) -> None:
    if window._employees_window is None:
        return

    window._employees_window_requested_visible = True
    window._fit_window_to_content(window._employees_window)
    window._show_side_window(window._employees_window)


def render_client_calls(
    window,
    current_call: Optional[ClientCall],
    queued_calls: List[ClientCall],
    progress: float,
) -> None:
    window._current_client_call = current_call
    window._queued_client_calls = queued_calls[:]
    window._current_client_call_progress = progress
    current_call_id = current_call.call_id if current_call is not None else None
    visible_queued_calls = [
        call for call in queued_calls
        if call.call_id != current_call_id
    ]
    target_visible_row_count = min(
        window.VISIBLE_QUEUE_ROWS,
        max(1, (1 if current_call is not None else 0) + len(visible_queued_calls)),
    )
    window._set_visible_queue_row_count(target_visible_row_count)
    rows: list[tuple[Optional[ClientCall], str, float, bool]] = []
    if current_call is not None:
        rows.append((current_call, current_call.display_text, max(0.0, min(progress, 1.0)), False))

    for call in visible_queued_calls[: max(0, window.VISIBLE_QUEUE_ROWS - len(rows))]:
        rows.append((call, call.display_text, 0.0, True))

    while len(rows) < window.VISIBLE_QUEUE_ROWS:
        rows.append((None, "", 0.0, False))

    window._visible_queue_rows = [
        (call.call_id if call is not None else None, removable)
        for call, _text, _fill_ratio, removable in rows
    ]

    for index, (_call, text, fill_ratio, removable) in enumerate(rows):
        canvas = window.client_call_row_canvases[index]
        if not canvas.winfo_exists():
            continue

        fill_id = window.client_call_row_fill_ids[index]
        text_id = window.client_call_row_text_ids[index]
        remove_id = window.client_call_row_remove_ids[index]
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 24)

        canvas.config(bg="#ffffff")
        canvas.coords(fill_id, 0, 0, width * fill_ratio, height)
        canvas.itemconfigure(fill_id, state="normal" if text and fill_ratio > 0 else "hidden")
        canvas.coords(text_id, 6, height / 2)
        canvas.itemconfigure(text_id, text=text, fill="#ffffff" if fill_ratio > 0.6 else "#1f2933")
        canvas.coords(remove_id, width - 8, height / 2)
        canvas.itemconfigure(remove_id, text="×" if removable and text else "", fill="#8a8a8a")

        if not text:
            canvas.itemconfigure(fill_id, state="hidden")


def _queue_row_clicked(window, event: tk.Event) -> None:
    canvas = event.widget
    try:
        row_index = window.client_call_row_canvases.index(canvas)
    except ValueError:
        return

    if row_index >= len(window._visible_queue_rows):
        return

    call_id, removable = window._visible_queue_rows[row_index]
    if not removable or not call_id:
        return

    remove_id = window.client_call_row_remove_ids[row_index]
    bbox = canvas.bbox(remove_id)
    if bbox is None:
        return

    x1, y1, x2, y2 = bbox
    if x1 <= event.x <= x2 and y1 <= event.y <= y2:
        if window.on_remove_queued_call:
            window.on_remove_queued_call(call_id)


def _set_visible_queue_row_count(window, count: int) -> None:
    normalized_count = max(1, min(count, window.VISIBLE_QUEUE_ROWS))
    if normalized_count == window._visible_queue_row_count:
        return

    window._visible_queue_row_count = normalized_count
    for index, canvas in enumerate(window.client_call_row_canvases):
        if index < normalized_count:
            if not canvas.winfo_manager():
                canvas.pack(fill="x")
        elif canvas.winfo_manager():
            canvas.pack_forget()

    window.root.after_idle(window._fit_main_window_to_content)


def _mask_api_token(window, token: str) -> str:
    clean_token = token.strip()
    if not clean_token:
        return "Не сгенерирован"

    suffix = clean_token[-5:]
    return f"••••••••••{suffix}"


def _fit_window_to_content(window, target_window: tk.Misc) -> None:
    target_window.update_idletasks()
    width = target_window.winfo_reqwidth()
    height = target_window.winfo_reqheight()
    if target_window is window._client_calls_settings_window:
        width = min(width, window.root.winfo_width())
    target_window.geometry(f"{width}x{height}")


def _show_side_window(window, target_window: tk.Toplevel) -> None:
    target_window.deiconify()
    target_window.lift()
    target_window.focus_set()


def _register_window_group_behavior(window) -> None:
    for app_window in window._get_app_windows():
        app_window.bind("<Button-1>", window._app_window_activated, add="+")
        app_window.bind("<FocusIn>", window._app_window_activated, add="+")


def _get_app_windows(window) -> list[tk.Misc]:
    windows: list[tk.Misc] = [window.root]
    for app_window in (
        window._client_calls_settings_window,
        window._generator_window,
        window._employees_window,
    ):
        if app_window is not None:
            windows.append(app_window)
    return windows


def _app_window_activated(window, event: tk.Event) -> None:
    active_window = window._resolve_widget(getattr(event, "widget", None))
    if active_window is None:
        return

    try:
        active_toplevel = active_window.winfo_toplevel()
    except tk.TclError:
        return

    app_windows = window._get_app_windows()
    for app_window in app_windows:
        if app_window is active_toplevel:
            continue
        if app_window is window.root and active_toplevel is not window.root:
            continue
        try:
            if app_window.winfo_viewable():
                app_window.lift()
        except tk.TclError:
            continue

    try:
        if active_toplevel.winfo_viewable():
            active_toplevel.lift()
    except tk.TclError:
        return


def _extract_window_position(window, geometry: str) -> str:
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


def _apply_window_icon(window, target_window: tk.Misc) -> None:
    if not os.path.exists(APP_ICON_FILE):
        return

    if window._is_windows:
        try:
            target_window.iconbitmap(APP_ICON_FILE)
        except tk.TclError:
            pass

    try:
        with Image.open(APP_ICON_FILE) as icon_image:
            window._window_icon_image = ImageTk.PhotoImage(icon_image.copy())
        target_window.iconphoto(True, window._window_icon_image)
    except (OSError, tk.TclError):
        pass


def _fit_main_window_to_content(window) -> None:
    window._fit_window_to_content(window.root)


def _resolve_widget(window, widget) -> tk.Misc | None:
    if isinstance(widget, str):
        try:
            return window.root.nametowidget(widget)
        except KeyError:
            return None
    return widget


def _is_editable_text_widget(window, widget) -> bool:
    resolved_widget = window._resolve_widget(widget)
    return isinstance(resolved_widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox))


def _should_handle_employee_shortcut(window, event: tk.Event) -> bool:
    if window._employees_window is None or not window._employees_window.winfo_viewable():
        return False
    if window.employees_listbox.curselection():
        return True

    widget = window._resolve_widget(getattr(event, "widget", None))
    if widget is None:
        widget = window.root.focus_get()
    if widget is None:
        return False

    try:
        return widget.winfo_toplevel() is window._employees_window
    except tk.TclError:
        return False


def _is_widget_inside_listbox(window, widget: tk.Misc) -> bool:
    current_widget: tk.Misc | None = widget
    while current_widget is not None:
        if current_widget is window.listbox or current_widget is window.employees_listbox:
            return True
        parent_name = current_widget.winfo_parent()
        if not parent_name:
            break
        try:
            current_widget = current_widget.nametowidget(parent_name)
        except KeyError:
            break
    return False


def _clear_text_selection(window, widget: tk.Misc) -> None:
    focus_widget = window.root.focus_get()
    for current_widget in {widget, focus_widget}:
        if current_widget is None:
            continue
        if isinstance(current_widget, (tk.Entry, ttk.Entry, ttk.Combobox)):
            window._safe_clear_selection(current_widget)
        elif isinstance(current_widget, tk.Text):
            current_widget.tag_remove("sel", "1.0", "end")


def _safe_clear_selection(window, widget: tk.Misc) -> None:
    try:
        widget.selection_clear()
    except tk.TclError:
        pass


def _safe_destroy_widget(window, widget: tk.Misc | None) -> None:
    if widget is None:
        return
    try:
        widget.destroy()
    except tk.TclError:
        pass


def _is_interactive_widget(window, widget: tk.Misc) -> bool:
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
