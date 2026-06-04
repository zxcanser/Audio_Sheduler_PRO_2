import tkinter as tk


def _browse_clicked(window) -> None:
    if window.on_browse:
        window.on_browse()


def _add_clicked(window) -> None:
    if window.on_add:
        window.on_add()


def _delete_clicked(window) -> None:
    if window.on_delete:
        window.on_delete()


def _play_clicked(window) -> None:
    if window.on_play:
        window.on_play()


def _browse_client_calls_file_clicked(window) -> None:
    if window.on_browse_client_calls_file:
        window.on_browse_client_calls_file()


def _browse_client_calls_voice_message_file_clicked(window) -> None:
    if window.on_browse_client_calls_voice_message_file:
        window.on_browse_client_calls_voice_message_file()


def _browse_employees_file_clicked(window) -> None:
    if window.on_browse_employees_file:
        window.on_browse_employees_file()


def _refresh_devices_clicked(window) -> None:
    if window.on_refresh_devices:
        window.on_refresh_devices()


def _browse_notification_sound_file_clicked(window) -> None:
    if window.on_browse_notification_sound_file:
        window.on_browse_notification_sound_file()


def _play_notification_sound_clicked(window) -> None:
    if window.on_play_notification_sound:
        window.on_play_notification_sound()


def _export_schedule_clicked(window) -> None:
    if window.on_export_schedule:
        window.on_export_schedule()


def _import_schedule_clicked(window) -> None:
    if window.on_import_schedule:
        window.on_import_schedule()


def _generator_api_key_focused(window, event: tk.Event) -> None:
    if not window._generator_api_key_editable:
        return
    window._generator_api_key_masked = False
    window.generator_api_key_button_var.set(window._generator_api_key_value)
    if hasattr(event.widget, "icursor"):
        event.widget.icursor(tk.END)


def _generator_api_key_changed(window, event: tk.Event | None = None) -> None:
    if not window._generator_api_key_editable:
        return
    raw_value = window.generator_api_key_button_var.get()
    window._generator_api_key_value = raw_value.strip()
    if window.on_generator_api_key_change:
        window.on_generator_api_key_change(window._generator_api_key_value)


def _generator_api_key_unfocused(window, event: tk.Event) -> None:
    if not window._generator_api_key_editable:
        return
    window._generator_api_key_changed()


def _show_generator_clicked(window) -> None:
    if window.on_show_generator:
        window.on_show_generator()


def _show_employees_clicked(window) -> None:
    if window.on_show_employees:
        window.on_show_employees()


def _hide_to_tray_clicked(window) -> None:
    if window.on_hide_to_tray:
        window.on_hide_to_tray()


def _quit_application_clicked(window) -> None:
    if window.on_quit_application:
        window.on_quit_application()


def _client_calls_device_changed(window, *args) -> None:
    if window.on_client_calls_device_change:
        window.on_client_calls_device_change(window.client_calls_device_var.get())


def _client_calls_voice_message_device_changed(window, *args) -> None:
    if window.on_client_calls_voice_message_device_change:
        window.on_client_calls_voice_message_device_change(window.client_calls_voice_message_device_var.get())


def _generator_device_changed(window, *args) -> None:
    if window.on_generator_device_change:
        window.on_generator_device_change(window.generator_device_var.get())


def _generator_voice_changed(window) -> None:
    if window.on_generator_voice_change:
        window.on_generator_voice_change(window.generator_voice_var.get())


def _generator_language_selected(window, event: tk.Event) -> None:
    if window.on_generator_language_change:
        window.on_generator_language_change(window.generator_language_var.get())


def _generator_accent_selected(window, event: tk.Event) -> None:
    if window.on_generator_accent_change:
        window.on_generator_accent_change(window.generator_accent_var.get())


def _generator_voice_selected(window, event: tk.Event) -> None:
    window._generator_voice_changed()


def _client_calls_text_voice_selected(window, event: tk.Event) -> None:
    if window.on_client_calls_text_voice_change:
        window.on_client_calls_text_voice_change(window.client_calls_text_voice_var.get())


def _client_calls_text_language_selected(window, event: tk.Event) -> None:
    if window.on_client_calls_text_language_change:
        window.on_client_calls_text_language_change(window.client_calls_text_language_var.get())


def _preview_client_calls_text_voice_clicked(window) -> None:
    if window.on_preview_client_calls_text_voice:
        window.on_preview_client_calls_text_voice()


def _generator_voice_dropdown_clicked(window, event: tk.Event) -> None:
    if window.on_request_generator_voices:
        window.on_request_generator_voices()


def _client_calls_text_voice_dropdown_clicked(window, event: tk.Event) -> None:
    if window.on_request_client_calls_text_voices:
        window.on_request_client_calls_text_voices()


def _client_calls_interval_changed(window) -> None:
    if window.on_client_calls_interval_change:
        window.on_client_calls_interval_change()


def _client_calls_interval_submitted(window, event: tk.Event) -> str:
    window._client_calls_interval_changed()
    return "break"


def _client_calls_api_enabled_toggled(window) -> None:
    if window.on_client_calls_api_enabled_toggle:
        window.on_client_calls_api_enabled_toggle()


def _client_calls_api_host_changed(window) -> None:
    if window.on_client_calls_api_host_change:
        window.on_client_calls_api_host_change()


def _client_calls_api_host_submitted(window, event: tk.Event) -> str:
    window._client_calls_api_host_changed()
    return "break"


def _client_calls_api_port_changed(window) -> None:
    if window.on_client_calls_api_port_change:
        window.on_client_calls_api_port_change()


def _client_calls_api_port_submitted(window, event: tk.Event) -> str:
    window._client_calls_api_port_changed()
    return "break"


def _workday_indicator_clicked(window, event: tk.Event | None = None) -> None:
    if window.on_workday_indicator_click:
        window.on_workday_indicator_click()


def _scheduler_notification_toggled(window) -> None:
    if window.on_scheduler_notification_toggle:
        window.on_scheduler_notification_toggle()


def _client_calls_notification_toggled(window) -> None:
    if window.on_client_calls_notification_toggle:
        window.on_client_calls_notification_toggle()


def _client_calls_repeat_toggled(window) -> None:
    if window.on_client_calls_repeat_toggle:
        window.on_client_calls_repeat_toggle()


def _client_calls_repeat_notification_toggled(window) -> None:
    if window.on_client_calls_repeat_notification_toggle:
        window.on_client_calls_repeat_notification_toggle()


def _autostart_toggled(window) -> None:
    if window.on_autostart_toggle:
        window.on_autostart_toggle()


def _close_requested(window) -> None:
    if window.on_close:
        window.on_close()


def _window_unmapped(window, event: tk.Event) -> None:
    if event.widget is window.root and window.on_window_unmap:
        window.on_window_unmap()


def _window_configured(window, event: tk.Event) -> None:
    if event.widget is window.root and window.on_window_configure:
        window.on_window_configure()


def _last_error_status_clicked(window, event: tk.Event) -> None:
    if window.on_open_error_log:
        window.on_open_error_log()


def _device_changed(window, *args) -> None:
    if window.on_device_change:
        window.on_device_change(window.device_var.get())


def _select_entry(window) -> None:
    if window.on_select_entry:
        window.on_select_entry()


def _generate_ai_speech_clicked(window) -> None:
    if window.on_generate_ai_speech:
        window.on_generate_ai_speech()


def _save_generated_ai_speech_clicked(window) -> None:
    if window.on_save_generated_ai_speech:
        window.on_save_generated_ai_speech()


def _add_employee_clicked(window) -> None:
    if window.on_add_employee:
        window.on_add_employee()


def _delete_employee_clicked(window) -> None:
    if window.on_delete_employee:
        window.on_delete_employee()


def _employee_enter_pressed(window, event: tk.Event) -> str:
    window._add_employee_clicked()
    return "break"


def _generator_enter_pressed(window, event: tk.Event) -> str:
    window._generate_ai_speech_clicked()
    return "break"
