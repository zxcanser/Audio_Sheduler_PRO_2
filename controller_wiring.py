def connect_window_events(controller) -> None:
    bindings = {
        "on_browse": controller.browse_file,
        "on_add": controller.add_schedule,
        "on_delete": controller.delete_schedule,
        "on_play": controller.play_selected_or_current,
        "on_stop": controller.stop_audio,
        "on_queue_selected_schedule": controller.queue_selected_schedule_entry,
        "on_remove_queued_call": controller.remove_queued_call,
        "on_refresh_devices": controller.refresh_devices,
        "on_device_change": controller.change_device,
        "on_volume_change": controller.change_volume,
        "on_notification_volume_change": controller.change_notification_volume,
        "on_select_entry": controller.load_selected_entry_into_form,
        "on_browse_client_calls_file": controller.browse_client_calls_file,
        "on_browse_client_calls_voice_message_file": controller.browse_client_calls_voice_message_file,
        "on_browse_employees_file": controller.browse_employees_file,
        "on_client_calls_api_enabled_toggle": controller.change_client_calls_api_enabled,
        "on_client_calls_api_host_change": controller.change_client_calls_api_host,
        "on_client_calls_api_port_change": controller.change_client_calls_api_port,
        "on_generate_client_calls_api_token": controller.generate_client_calls_api_token,
        "on_client_calls_volume_change": controller.change_client_calls_volume,
        "on_client_calls_voice_message_volume_change": controller.change_client_calls_voice_message_volume,
        "on_client_calls_speech_rate_change": controller.change_client_calls_speech_rate,
        "on_number_trim_silence_toggle": controller.change_number_trim_silence_enabled,
        "on_number_silence_threshold_change": controller.change_number_silence_threshold,
        "on_number_trim_leading_padding_change": controller.change_number_trim_leading_padding,
        "on_number_trim_trailing_padding_change": controller.change_number_trim_trailing_padding,
        "on_number_symbol_pause_change": controller.change_number_symbol_pause,
        "on_preview_number_assembly": controller.preview_number_assembly,
        "on_client_calls_device_change": controller.change_client_calls_device,
        "on_client_calls_voice_message_device_change": controller.change_client_calls_voice_message_device,
        "on_client_calls_interval_change": controller.change_client_calls_interval,
        "on_client_calls_repeat_toggle": controller.change_client_calls_repeat_enabled,
        "on_client_calls_repeat_interval_change": controller.change_client_calls_repeat_interval,
        "on_client_calls_repeat_notification_toggle": controller.change_client_calls_repeat_notification_enabled,
        "on_client_calls_text_language_change": controller.change_client_calls_text_language,
        "on_client_calls_text_voice_change": controller.change_client_calls_text_voice,
        "on_preview_client_calls_text_voice": controller.preview_client_calls_text_voice,
        "on_request_client_calls_text_voices": controller.request_client_calls_text_voices,
        "on_workday_indicator_click": controller.show_workday_calendar,
        "on_browse_notification_sound_file": controller.browse_notification_sound_file,
        "on_play_notification_sound": controller.play_notification_sound,
        "on_export_schedule": controller.export_schedule,
        "on_import_schedule": controller.import_schedule,
        "on_show_generator": controller.show_generator_window,
        "on_show_employees": controller.show_employees_window,
        "on_generator_api_key_change": controller.change_generator_api_key,
        "on_generator_device_change": controller.change_generator_device,
        "on_generator_volume_change": controller.change_generator_volume,
        "on_generator_master_volume_change": controller.change_generator_master_volume,
        "on_generator_language_change": controller.change_generator_language,
        "on_generator_accent_change": controller.change_generator_accent,
        "on_generator_speed_change": controller.change_generator_speed,
        "on_generator_voice_change": controller.change_generator_voice,
        "on_request_generator_voices": controller.request_generator_voices,
        "on_generate_ai_speech": controller.generate_ai_speech,
        "on_save_generated_ai_speech": controller.save_generated_ai_speech,
        "on_add_employee": controller.add_employee,
        "on_delete_employee": controller.delete_employee,
        "on_preview_employee": controller.preview_employee,
        "on_autostart_toggle": controller.change_autostart_enabled,
        "on_check_updates": controller.check_for_updates,
        "on_scheduler_notification_toggle": controller.change_scheduler_notification_enabled,
        "on_client_calls_notification_toggle": controller.change_client_calls_notification_enabled,
        "on_hide_to_tray": controller.hide_to_tray,
        "on_quit_application": controller.save_and_close,
        "on_close": controller.handle_close_request,
        "on_window_unmap": controller.handle_window_unmap,
        "on_window_configure": controller.handle_window_configure,
        "on_open_error_log": controller.open_error_log,
    }
    for attr_name, handler in bindings.items():
        setattr(controller.window, attr_name, handler)


def load_initial_window_state(controller) -> None:
    settings = controller.settings
    window = controller.window

    scalar_setters = [
        (window.set_main_window_geometry, settings.main_window_geometry),
        (window.set_volume, settings.volume),
        (window.set_notification_volume, settings.notification_volume),
        (window.set_notification_sound_file, settings.notification_sound_file_path),
        (window.set_notification_sound_preview_playing, False),
        (window.set_autostart_enabled, settings.autostart_enabled),
        (window.set_scheduler_notification_enabled, settings.scheduler_notification_enabled),
        (window.set_client_calls_notification_enabled, settings.client_calls_notification_enabled),
        (window.set_client_calls_volume, settings.client_calls_volume),
        (window.set_client_calls_api_enabled, settings.client_calls_api_enabled),
        (window.set_client_calls_api_host, settings.client_calls_api_host),
        (window.set_client_calls_api_port, settings.client_calls_api_port),
        (window.set_client_calls_api_token, settings.client_calls_api_token),
        (window.set_client_calls_voice_message_volume, settings.client_calls_voice_message_volume),
        (window.set_client_calls_speech_rate, settings.client_calls_speech_rate),
        (window.set_number_trim_silence_enabled, settings.number_trim_silence_enabled),
        (window.set_number_silence_threshold, settings.number_silence_threshold_db),
        (window.set_number_trim_leading_padding, settings.number_trim_leading_padding_ms),
        (window.set_number_trim_trailing_padding, settings.number_trim_trailing_padding_ms),
        (window.set_number_symbol_pause, settings.number_symbol_pause_ms),
        (window.set_client_calls_file, settings.client_calls_file_path),
        (window.set_client_calls_voice_message_file, settings.client_calls_voice_message_file_path),
        (window.set_client_calls_interval, settings.client_calls_interval_seconds),
        (window.set_client_calls_repeat_enabled, settings.client_calls_repeat_enabled),
        (window.set_client_calls_repeat_interval, settings.client_calls_repeat_interval_seconds),
        (window.set_client_calls_repeat_notification_enabled, settings.client_calls_repeat_notification_enabled),
        (window.set_employees_file, settings.employees_file_path),
        (window.set_generator_api_key, settings.generator_api_key),
        (window.set_generator_volume, settings.generator_volume),
        (window.set_generator_master_volume, settings.generator_master_volume),
        (window.set_generator_speed, settings.generator_speed),
        (window.set_client_calls_text_voice_preview_playing, False),
        (window.set_workday_status, None),
        (window.set_update_checking, False),
    ]
    for setter, value in scalar_setters:
        setter(value)

    controller._sync_autostart_state()
    window.set_generator_accent_options(
        [accent.label for accent in controller.voice_maker_service.get_accents()],
        controller._accent_label_by_code(settings.generator_accent_code),
    )
    controller._set_ready_status()

    language_labels = [language.label for language in controller.voice_maker_service.get_languages()]
    window.set_client_calls_text_language_options(
        language_labels,
        controller._language_label_by_code(settings.client_calls_text_language_code or "ru-RU"),
    )
    window.set_generator_language_options(
        language_labels,
        controller._language_label_by_code(settings.generator_language_code),
    )

    controller._refresh_devices()
    controller._refresh_generator_voices(show_errors=False)
    controller._refresh_client_calls_text_voices(show_errors=False)
    controller._refresh_schedule_list()
    controller._refresh_employees_list()
    controller._refresh_client_calls_queue(None, [], 0.0)
    controller.platform_integration.start()
    controller._refresh_workday_status_loop()
    controller.scheduler.start()
    controller.client_call_service.start()
    controller._sync_client_calls_api_server(show_errors=False)
    controller.root.after(500, controller._refresh_runtime_status_loop)
