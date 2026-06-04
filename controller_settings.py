import os

from services.validation_service import ValidationError, ValidationService


def _invalidate_text_voice_preview_cache(controller) -> None:
    controller._client_calls_text_voice_preview_signature = ""
    controller._client_calls_text_voice_preview_bytes = None


def change_device(controller, device_name: str) -> None:
    controller._update_setting("selected_device", device_name)


def change_volume(controller, volume: float) -> None:
    controller._update_setting("volume", volume)


def change_notification_volume(controller, volume: float) -> None:
    controller._update_setting("notification_volume", volume)


def change_client_calls_device(controller, device_name: str) -> None:
    controller._update_setting("client_calls_selected_device", device_name)


def change_client_calls_voice_message_device(controller, device_name: str) -> None:
    controller._update_setting("client_calls_voice_message_selected_device", device_name)


def change_client_calls_volume(controller, volume: float) -> None:
    controller._update_setting("client_calls_volume", volume)


def change_client_calls_voice_message_volume(controller, volume: float) -> None:
    controller._update_setting("client_calls_voice_message_volume", volume)


def change_client_calls_speech_rate(controller, speech_rate: float) -> None:
    controller._update_setting("client_calls_speech_rate", speech_rate)


def change_number_trim_silence_enabled(controller) -> None:
    controller._update_setting("number_trim_silence_enabled", controller.window.is_number_trim_silence_enabled())


def change_number_silence_threshold(controller, value: float) -> None:
    controller._update_setting("number_silence_threshold_db", int(round(value)))


def change_number_trim_leading_padding(controller, value: float) -> None:
    controller._update_setting("number_trim_leading_padding_ms", int(round(value)))


def change_number_trim_trailing_padding(controller, value: float) -> None:
    controller._update_setting("number_trim_trailing_padding_ms", int(round(value)))


def change_number_symbol_pause(controller, value: float) -> None:
    controller._update_setting("number_symbol_pause_ms", int(round(value)))


def preview_number_assembly(controller) -> None:
    if controller._number_assembly_preview_busy:
        return

    car_number = controller.window.get_number_preview_text()
    if not car_number:
        controller.window.show_error("Введите тестовый номер")
        return

    controller._number_assembly_preview_busy = True
    controller._start_worker(controller._preview_number_assembly_worker, car_number)


def _preview_number_assembly_worker(controller, car_number: str) -> None:
    try:
        temp_path = controller.recorded_call_builder.build_audio_file(
            "1",
            car_number,
            "1",
            playback_rate=controller.settings.client_calls_speech_rate,
            trim_silence_enabled=controller.settings.number_trim_silence_enabled,
            silence_threshold_db=controller.settings.number_silence_threshold_db,
            trim_leading_padding_ms=controller.settings.number_trim_leading_padding_ms,
            trim_trailing_padding_ms=controller.settings.number_trim_trailing_padding_ms,
            symbol_pause_ms=controller.settings.number_symbol_pause_ms,
        )
    except Exception as error:
        controller._post_to_ui(controller._finish_number_assembly_preview_error, str(error))
        return

    controller._post_to_ui(controller._finish_number_assembly_preview_success, temp_path)


def _finish_number_assembly_preview_success(controller, temp_path: str) -> None:
    controller._number_assembly_preview_busy = False
    controller._cleanup_number_assembly_preview_file()
    controller._number_assembly_preview_temp_path = temp_path
    device_name = controller.settings.client_calls_selected_device or controller.settings.selected_device
    controller.generator_preview_player.play_async(
        file_path=temp_path,
        volume=controller.settings.client_calls_volume,
        device_name=device_name,
        on_error=lambda message: controller.root.after(
            0,
            lambda msg=message: controller._handle_number_assembly_preview_finished(error_message=msg),
        ),
        on_finished=lambda: controller.root.after(0, controller._handle_number_assembly_preview_finished),
    )


def _finish_number_assembly_preview_error(controller, error_message: str) -> None:
    controller._number_assembly_preview_busy = False
    controller.window.show_error(f"Не удалось собрать тестовый номер: {error_message}")


def _handle_number_assembly_preview_finished(controller, error_message: str = "") -> None:
    controller._cleanup_number_assembly_preview_file()
    if error_message:
        controller.window.show_error(f"Не удалось воспроизвести тестовый номер: {error_message}")


def _cleanup_number_assembly_preview_file(controller) -> None:
    temp_path = controller._number_assembly_preview_temp_path
    controller._number_assembly_preview_temp_path = None
    if not temp_path:
        return
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except OSError:
        pass


def change_client_calls_interval(controller) -> None:
    controller._sync_client_calls_interval(show_errors=True)


def change_client_calls_repeat_enabled(controller) -> None:
    controller._update_setting("client_calls_repeat_enabled", controller.window.is_client_calls_repeat_enabled())


def change_client_calls_repeat_interval(controller) -> None:
    controller._sync_client_calls_repeat_interval(show_errors=True)


def change_client_calls_text_language(controller, language_label: str) -> None:
    language_code = controller._language_code_by_label(language_label)
    controller._update_setting("client_calls_text_language_code", language_code)
    controller._update_setting("client_calls_text_voice", "")
    controller.settings.client_calls_text_voice_id = ""
    controller.repository.save_settings(controller.settings)
    _invalidate_text_voice_preview_cache(controller)
    controller._refresh_client_calls_text_voices(show_errors=True)


def change_client_calls_text_voice(controller, voice_label: str) -> None:
    voice = controller._client_calls_text_voices_by_label.get(voice_label)
    controller._update_setting("client_calls_text_voice", voice_label)
    _invalidate_text_voice_preview_cache(controller)
    if voice is not None:
        controller.settings.client_calls_text_voice_id = voice.voice_id
        controller.settings.client_calls_text_language_code = voice.language_code or controller.settings.client_calls_text_language_code
        controller.repository.save_settings(controller.settings)


def change_generator_device(controller, device_name: str) -> None:
    controller._update_setting("generator_selected_device", device_name)


def change_generator_api_key(controller, api_key: str) -> None:
    controller._update_setting("generator_api_key", api_key.strip())
    _invalidate_text_voice_preview_cache(controller)


def change_generator_volume(controller, volume: float) -> None:
    controller._update_setting("generator_volume", volume)


def change_generator_master_volume(controller, volume: float) -> None:
    controller._update_setting("generator_master_volume", max(50, min(150, int(round(volume)))))
    _invalidate_text_voice_preview_cache(controller)


def change_generator_language(controller, language_label: str) -> None:
    language_code = controller._language_code_by_label(language_label)
    controller._update_setting("generator_language_code", language_code)
    _invalidate_text_voice_preview_cache(controller)
    controller._refresh_generator_voices(show_errors=True)


def change_generator_accent(controller, accent_label: str) -> None:
    controller._update_setting("generator_accent_code", controller._accent_code_by_label(accent_label))
    _invalidate_text_voice_preview_cache(controller)


def change_generator_speed(controller, speed: float) -> None:
    controller._update_setting("generator_speed", int(round(speed)))
    _invalidate_text_voice_preview_cache(controller)


def _generator_master_volume_for_request(controller) -> int:
    percent_value = max(50, min(150, int(controller.settings.generator_master_volume)))
    return int(round((percent_value - 100) * 0.4))


def change_generator_voice(controller, voice_label: str) -> None:
    voice = controller._generator_voices_by_label.get(voice_label)
    if voice is not None:
        controller.settings.generator_voice_id = voice.voice_id
    controller._update_setting("generator_voice", voice_label)
    _invalidate_text_voice_preview_cache(controller)
    if voice is not None:
        controller.repository.save_settings(controller.settings)
    controller._sync_generator_accent_availability()


def request_client_calls_text_voices(controller) -> None:
    controller._refresh_client_calls_text_voices(show_errors=True)


def change_autostart_enabled(controller) -> None:
    enabled = controller.window.is_autostart_enabled()
    try:
        controller.autostart_service.set_enabled(enabled)
    except (OSError, RuntimeError) as error:
        controller.window.show_error(f"Не удалось изменить автозапуск: {error}")
        controller.window.set_autostart_enabled(controller.settings.autostart_enabled)
        return

    controller._update_setting("autostart_enabled", enabled)


def _sync_autostart_state(controller) -> None:
    try:
        enabled = controller.autostart_service.is_enabled()
    except (OSError, RuntimeError):
        return

    if enabled:
        try:
            controller.autostart_service.set_enabled(True)
        except (OSError, RuntimeError):
            pass

    controller.window.set_autostart_enabled(enabled)
    if enabled != controller.settings.autostart_enabled:
        controller.settings.autostart_enabled = enabled
        controller.repository.save_settings(controller.settings)


def change_scheduler_notification_enabled(controller) -> None:
    controller._sync_notification_settings(
        enabled=controller.window.is_scheduler_notification_enabled(),
        field_name="scheduler_notification_enabled",
        reset=lambda: controller.window.set_scheduler_notification_enabled(controller.settings.scheduler_notification_enabled),
    )


def change_client_calls_notification_enabled(controller) -> None:
    controller._sync_notification_settings(
        enabled=controller.window.is_client_calls_notification_enabled(),
        field_name="client_calls_notification_enabled",
        reset=lambda: controller.window.set_client_calls_notification_enabled(controller.settings.client_calls_notification_enabled),
    )


def change_client_calls_repeat_notification_enabled(controller) -> None:
    controller._sync_notification_settings(
        enabled=controller.window.is_client_calls_repeat_notification_enabled(),
        field_name="client_calls_repeat_notification_enabled",
        reset=lambda: controller.window.set_client_calls_repeat_notification_enabled(
            controller.settings.client_calls_repeat_notification_enabled
        ),
    )


def _sync_client_calls_interval(controller, show_errors: bool) -> bool:
    return controller._sync_interval_setting(
        raw_value=controller.window.get_client_calls_interval(),
        current_value=controller.settings.client_calls_interval_seconds,
        apply_value=lambda interval: setattr(controller.settings, "client_calls_interval_seconds", interval),
        reset_ui=lambda value: controller.window.set_client_calls_interval(value),
        show_errors=show_errors,
    )


def _sync_client_calls_repeat_interval(controller, show_errors: bool) -> bool:
    return controller._sync_interval_setting(
        raw_value=controller.window.get_client_calls_repeat_interval(),
        current_value=controller.settings.client_calls_repeat_interval_seconds,
        apply_value=lambda interval: setattr(controller.settings, "client_calls_repeat_interval_seconds", interval),
        reset_ui=lambda value: controller.window.set_client_calls_repeat_interval(value),
        show_errors=show_errors,
    )


def _sync_interval_setting(
    controller,
    raw_value: str,
    current_value: float,
    apply_value,
    reset_ui,
    show_errors: bool,
) -> bool:
    try:
        interval = ValidationService.validate_interval(raw_value)
    except ValidationError as error:
        if show_errors:
            controller.window.show_error(str(error))
            reset_ui(current_value)
        return False

    apply_value(interval)
    reset_ui(interval)
    controller.repository.save_settings(controller.settings)
    return True


def _sync_notification_settings(controller, enabled: bool, field_name: str, reset) -> bool:
    if enabled:
        try:
            ValidationService.validate_optional_file(
                controller.window.get_notification_sound_file(),
                "Сначала выберите файл звука уведомления",
            )
        except ValidationError as error:
            controller.window.show_error(str(error))
            reset()
            return False

    controller._update_setting(field_name, enabled)
    controller._set_ready_status()
    return True


def _update_setting(controller, field_name: str, value) -> None:
    setattr(controller.settings, field_name, value)
    controller.repository.save_settings(controller.settings)
