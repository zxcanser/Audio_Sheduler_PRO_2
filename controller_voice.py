import os
import tempfile
import unicodedata
from tkinter import filedialog

from services.playback_coordinator import PlaybackTask
from services.validation_service import ValidationError, ValidationService
from services.voicemaker_service import VoiceMakerVoice


def show_generator_window(controller) -> None:
    controller.window.show_generator_window()
    controller._refresh_generator_voices(show_errors=True)


def show_employees_window(controller) -> None:
    controller._refresh_employees_list()
    controller.window.show_employees_window()


def request_generator_voices(controller) -> None:
    controller._refresh_generator_voices(show_errors=True)


def preview_client_calls_text_voice(controller) -> None:
    if controller._client_calls_text_voice_preview_playing:
        controller._stop_client_calls_text_voice_preview()
        return
    if controller._client_calls_text_voice_preview_busy:
        return

    try:
        if not controller.settings.generator_api_key.strip():
            raise RuntimeError("Сначала введите API ключ генератора")
    except RuntimeError as error:
        controller.window.show_error(str(error))
        return

    voice_id = controller.settings.client_calls_text_voice_id or controller.settings.generator_voice_id
    if not voice_id:
        controller.window.show_error("Сначала выберите голос для произвольного текста")
        return

    signature = controller._build_client_calls_text_voice_preview_signature()
    if controller._client_calls_text_voice_preview_bytes and signature == controller._client_calls_text_voice_preview_signature:
        controller._play_client_calls_text_voice_preview(controller._client_calls_text_voice_preview_bytes)
        return

    controller._client_calls_text_voice_preview_busy = True
    controller._start_worker(controller._preview_client_calls_text_voice_worker)


def _preview_client_calls_text_voice_worker(controller) -> None:
    try:
        generated_audio = controller._generate_voice_maker_audio(
            text=controller.CLIENT_CALLS_TEXT_VOICE_PREVIEW_TEXT,
            voice_id=controller.settings.client_calls_text_voice_id or controller.settings.generator_voice_id,
            language_code=(controller.settings.client_calls_text_language_code or "ru-RU"),
        )
    except Exception as error:
        controller._post_to_ui(controller._finish_client_calls_text_voice_preview_error, str(error))
        return

    controller._post_to_ui(controller._finish_client_calls_text_voice_preview_success, generated_audio)


def _finish_client_calls_text_voice_preview_success(controller, generated_audio: bytes) -> None:
    controller._client_calls_text_voice_preview_busy = False
    controller._client_calls_text_voice_preview_bytes = generated_audio
    controller._client_calls_text_voice_preview_signature = controller._build_client_calls_text_voice_preview_signature()
    controller._play_client_calls_text_voice_preview(generated_audio)


def _finish_client_calls_text_voice_preview_error(controller, message: str) -> None:
    controller._client_calls_text_voice_preview_busy = False
    controller._client_calls_text_voice_preview_playing = False
    controller.window.set_client_calls_text_voice_preview_playing(False)
    controller.window.show_error(f"Не удалось воспроизвести тест голоса: {message}")


def _play_client_calls_text_voice_preview(controller, audio_bytes: bytes) -> None:
    controller._cleanup_client_calls_text_voice_preview_file()
    temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    with os.fdopen(temp_fd, "wb") as temp_file:
        temp_file.write(audio_bytes)

    controller._client_calls_text_voice_preview_temp_path = temp_path
    controller._client_calls_text_voice_preview_playing = True
    controller.window.set_client_calls_text_voice_preview_playing(True)
    controller.generator_preview_player.play_async(
        file_path=temp_path,
        volume=min(controller.settings.generator_volume * 2.0, 1.0),
        device_name=controller.settings.generator_selected_device,
        on_error=lambda message: controller.root.after(
            0, lambda msg=message: controller._handle_client_calls_text_voice_preview_finished(error_message=msg)
        ),
        on_finished=lambda: controller.root.after(0, controller._handle_client_calls_text_voice_preview_finished),
    )


def _stop_client_calls_text_voice_preview(controller) -> None:
    controller.generator_preview_player.stop()
    controller._handle_client_calls_text_voice_preview_finished()


def _handle_client_calls_text_voice_preview_finished(controller, error_message: str = "") -> None:
    controller._client_calls_text_voice_preview_playing = False
    controller.window.set_client_calls_text_voice_preview_playing(False)
    controller._cleanup_client_calls_text_voice_preview_file()
    if error_message:
        controller.window.show_error(f"Не удалось воспроизвести тест голоса: {error_message}")


def generate_ai_speech(controller) -> None:
    if controller._generator_busy:
        return

    try:
        if not controller.settings.generator_api_key.strip():
            raise RuntimeError("Сначала введите API ключ генератора")
    except RuntimeError as error:
        controller.window.show_error(str(error))
        return

    text = controller.window.get_generator_text()
    if not text.strip():
        controller.window.show_error("Введите текст для генерации")
        return
    request_signature = controller._build_generator_request_signature(text)
    if controller._generated_voice_bytes and request_signature == controller._generated_voice_signature:
        controller._play_generated_audio(controller._generated_voice_bytes)
        return

    controller._generator_busy = True
    controller._start_worker(controller._generate_ai_speech_worker, text)


def _generate_ai_speech_worker(controller, text: str) -> None:
    try:
        generated_audio = controller._generate_voice_maker_audio(
            text=text,
            voice_id=controller.settings.generator_voice_id,
            language_code=controller.settings.generator_language_code,
        )
    except Exception as error:
        controller._post_to_ui(controller._finish_generator_error, str(error))
        return

    controller._post_to_ui(controller._finish_generator_success, generated_audio)


def _finish_generator_success(controller, generated_audio: bytes) -> None:
    controller._generator_busy = False
    controller._generated_voice_bytes = generated_audio
    controller._generated_voice_signature = controller._build_generator_request_signature(controller.window.get_generator_text())
    controller._play_generated_audio(generated_audio)


def _finish_generator_error(controller, message: str) -> None:
    controller._generator_busy = False
    controller.window.show_error(f"Не удалось сгенерировать речь: {message}")


def _play_generated_audio(controller, audio_bytes: bytes) -> None:
    device_name = controller.settings.generator_selected_device

    temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    with os.fdopen(temp_fd, "wb") as temp_file:
        temp_file.write(audio_bytes)

    controller.playback_coordinator.enqueue(
        PlaybackTask(
            file_path=temp_path,
            volume=min(controller.settings.generator_volume * 2.0, 1.0),
            device_name=device_name,
            cleanup_file=True,
            on_error=lambda msg: controller.window.show_error(msg),
        )
    )


def save_generated_ai_speech(controller) -> None:
    if not controller._generated_voice_bytes:
        controller.window.show_error("Сначала сгенерируйте речь")
        return

    suggested_name = controller.window.get_generator_file_name().strip().replace(" ", "_") or "generated_voice"
    file_path = filedialog.asksaveasfilename(
        defaultextension=".mp3",
        initialfile=f"{suggested_name}.mp3",
        filetypes=[("MP3 Files", "*.mp3")],
    )
    if not file_path:
        return

    try:
        with open(file_path, "wb") as output_file:
            output_file.write(controller._generated_voice_bytes)
    except OSError as error:
        controller.window.show_error(f"Не удалось сохранить файл: {error}")


def add_employee(controller) -> None:
    try:
        ValidationService.validate_optional_file(
            controller.settings.employees_file_path,
            "Сначала выберите файл списка сотрудников",
        )
        if not controller.settings.generator_api_key.strip():
            raise RuntimeError("Сначала введите API ключ генератора")
    except (ValidationError, RuntimeError) as error:
        controller.window.show_error(str(error))
        return

    employee_name = controller._normalize_employee_name(controller.window.get_employee_input())
    if not employee_name:
        controller.window.show_error("Введите Имя Фамилию сотрудника")
        return
    if not controller.settings.generator_voice_id:
        controller.window.show_error("Сначала выберите голос генератора")
        return

    existing_employees = controller._read_employees_file()
    if employee_name in existing_employees:
        controller.window.show_error("Такой сотрудник уже есть в списке")
        return

    controller._append_employee_to_file(employee_name)
    controller.window.clear_employee_input()
    controller._refresh_employees_list()
    controller.window.focus_employees_list()
    controller._employee_generation_in_progress.add(employee_name)
    controller._start_worker(controller._add_employee_worker, employee_name)


def _add_employee_worker(controller, employee_name: str) -> None:
    try:
        generated_audio = controller._generate_voice_maker_audio(
            text=employee_name,
            voice_id=controller.settings.generator_voice_id,
            language_code=controller.settings.generator_language_code,
        )
        controller._write_worker_audio(employee_name, generated_audio)
    except Exception as error:
        controller._post_to_ui(controller._finish_add_employee_error, employee_name, str(error))
        return

    controller._post_to_ui(controller._finish_add_employee_success, employee_name)


def _finish_add_employee_success(controller, employee_name: str) -> None:
    controller._employee_generation_in_progress.discard(employee_name)


def _finish_add_employee_error(controller, employee_name: str, message: str) -> None:
    controller._employee_generation_in_progress.discard(employee_name)
    controller.window.show_error(
        f"Сотрудник добавлен в список, но не удалось создать его аудио: {message}"
    )


def delete_employee(controller) -> None:
    try:
        ValidationService.validate_optional_file(
            controller.settings.employees_file_path,
            "Сначала выберите файл списка сотрудников",
        )
    except ValidationError as error:
        controller.window.show_error(str(error))
        return

    employee_name = controller._normalize_employee_name(controller.window.get_selected_employee())
    if not employee_name:
        controller.window.show_error("Выберите сотрудника для удаления")
        return

    employees = controller._read_employees_file()
    filtered = [item for item in employees if item != employee_name]
    controller._write_employees_file(filtered)
    controller._delete_worker_audio(employee_name)
    controller._refresh_employees_list()


def preview_employee(controller) -> None:
    employee_name = controller._normalize_employee_name(controller.window.get_selected_employee())
    if not employee_name:
        controller.window.show_error("Выберите сотрудника для воспроизведения")
        return

    worker_audio_path = controller.recorded_call_builder.get_worker_audio_path(employee_name)
    if not worker_audio_path or not os.path.exists(worker_audio_path):
        controller.window.show_error("Для этого сотрудника не найден аудиофайл")
        return

    if not controller.settings.generator_selected_device:
        controller.window.show_error("Выберите аудиоустройство для генератора")
        return

    controller.generator_preview_player.play_async(
        file_path=worker_audio_path,
        volume=min(controller.settings.generator_volume * 2.0, 1.0),
        device_name=controller.settings.generator_selected_device,
        on_error=lambda message: controller.root.after(
            0, lambda msg=message: controller.window.show_error(f"Не удалось воспроизвести сотрудника: {msg}")
        ),
    )


def _refresh_employees_list(controller) -> None:
    employees = controller._read_employees_file() if controller.settings.employees_file_path else []
    controller.window.fill_employees_list(employees)


def _read_generator_api_key(controller) -> str:
    key = controller.settings.generator_api_key.strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if not key:
        raise RuntimeError("Не указан API ключ генератора")
    return key


def _build_generator_request_signature(controller, text: str) -> str:
    return controller._build_voice_request_signature(
        language_code=controller.settings.generator_language_code,
        voice_id=controller.settings.generator_voice_id,
        text=text,
    )


def _build_client_calls_text_voice_preview_signature(controller) -> str:
    return controller._build_voice_request_signature(
        language_code=controller.settings.client_calls_text_language_code or "ru-RU",
        voice_id=controller.settings.client_calls_text_voice_id or controller.settings.generator_voice_id,
        text=controller.CLIENT_CALLS_TEXT_VOICE_PREVIEW_TEXT,
    )


def _build_client_call_text_request_signature(controller, text: str) -> str:
    return controller._build_voice_request_signature(
        language_code=controller.settings.client_calls_text_language_code or "ru-RU",
        voice_id=controller.settings.client_calls_text_voice_id or controller.settings.generator_voice_id,
        text=text,
    )


def _build_voice_request_signature(controller, language_code: str, voice_id: str, text: str) -> str:
    return "|".join(
        [
            language_code.strip(),
            controller.settings.generator_accent_code.strip(),
            str(controller._generator_master_volume_for_request()),
            str(controller.settings.generator_speed),
            voice_id.strip(),
            text.strip(),
        ]
    )


def _cleanup_client_calls_text_voice_preview_file(controller) -> None:
    if not controller._client_calls_text_voice_preview_temp_path:
        return
    if os.path.exists(controller._client_calls_text_voice_preview_temp_path):
        try:
            os.remove(controller._client_calls_text_voice_preview_temp_path)
        except OSError:
            pass
    controller._client_calls_text_voice_preview_temp_path = None


def _refresh_generator_voices(controller, show_errors: bool) -> None:
    if controller._generator_voices_loading:
        return
    if not controller.settings.generator_api_key.strip():
        controller._set_generator_voice_options([], "")
        return

    controller._generator_voices_loading = True
    controller._start_worker(controller._refresh_generator_voices_worker, show_errors)


def _refresh_generator_voices_worker(controller, show_errors: bool) -> None:
    try:
        voices = controller._list_voice_maker_voices(controller.settings.generator_language_code)
    except Exception as error:
        controller._post_to_ui(controller._finish_refresh_generator_voices, [], show_errors, str(error))
        return

    controller._post_to_ui(controller._finish_refresh_generator_voices, voices, show_errors, "")


def _refresh_client_calls_text_voices(controller, show_errors: bool) -> None:
    if controller._client_calls_text_voices_loading:
        return
    if not controller.settings.generator_api_key.strip():
        controller.window.set_client_calls_text_voice_options([], "")
        return

    controller._client_calls_text_voices_loading = True
    controller._start_worker(controller._refresh_client_calls_text_voices_worker, show_errors)


def _refresh_client_calls_text_voices_worker(controller, show_errors: bool) -> None:
    try:
        voices = controller._list_voice_maker_voices(
            controller.settings.client_calls_text_language_code or "ru-RU",
        )
    except Exception as error:
        controller._post_to_ui(controller._finish_refresh_client_calls_text_voices, [], show_errors, str(error))
        return

    controller._post_to_ui(controller._finish_refresh_client_calls_text_voices, voices, show_errors, "")


def _finish_refresh_client_calls_text_voices(
    controller,
    voices: list[VoiceMakerVoice],
    show_errors: bool,
    error_message: str,
) -> None:
    controller._client_calls_text_voices_loading = False
    if error_message:
        controller._handle_voice_refresh_failure(
            show_errors=show_errors,
            error_message=error_message,
            clear_options=controller._clear_client_calls_text_voice_options,
            prefix_message=True,
        )
        return

    if not voices:
        controller._handle_voice_refresh_failure(
            show_errors=show_errors,
            error_message="VoiceMaker не вернул ни одного голоса для выбранного языка",
            clear_options=controller._clear_client_calls_text_voice_options,
            prefix_message=False,
        )
        return

    controller._client_calls_text_voices_by_label = {voice.label: voice for voice in voices}
    labels = [voice.label for voice in voices]
    selected_label = controller._resolve_selected_voice_label(
        controller.settings.client_calls_text_voice,
        controller._client_calls_text_voices_by_label,
        labels,
    )
    if selected_label and selected_label != controller.settings.client_calls_text_voice:
        controller._apply_default_client_calls_text_voice(selected_label)

    controller.window.set_client_calls_text_voice_options(labels, selected_label)


def _finish_refresh_generator_voices(
    controller,
    voices: list[VoiceMakerVoice],
    show_errors: bool,
    error_message: str,
) -> None:
    controller._generator_voices_loading = False
    if error_message:
        controller._handle_voice_refresh_failure(
            show_errors=show_errors,
            error_message=error_message,
            clear_options=controller._clear_generator_voice_options,
            prefix_message=True,
        )
        return

    if not voices:
        controller._handle_voice_refresh_failure(
            show_errors=show_errors,
            error_message="VoiceMaker не вернул ни одного голоса для выбранного языка",
            clear_options=controller._clear_generator_voice_options,
            prefix_message=False,
        )
        return

    controller._generator_voices_by_label = {voice.label: voice for voice in voices}
    labels = [voice.label for voice in voices]
    selected_label = controller._resolve_selected_voice_label(
        controller.settings.generator_voice,
        controller._generator_voices_by_label,
        labels,
    )
    if selected_label and selected_label != controller.settings.generator_voice:
        controller._apply_default_generator_voice(selected_label)

    controller._set_generator_voice_options(labels, selected_label)
    controller._sync_generator_accent_availability()


def _set_generator_voice_options(controller, labels: list[str], selected_label: str) -> None:
    controller.window.set_generator_voice_options(labels, selected_label)


def _clear_generator_voice_options(controller) -> None:
    controller._generator_voices_by_label = {}
    controller._set_generator_voice_options([], "")
    controller.window.set_generator_accent_enabled(False, "Сначала выберите совместимый голос.")


def _clear_client_calls_text_voice_options(controller) -> None:
    controller._client_calls_text_voices_by_label = {}
    controller.window.set_client_calls_text_voice_options([], "")


def _handle_voice_refresh_failure(controller, show_errors: bool, error_message: str, clear_options, prefix_message: bool) -> None:
    if show_errors:
        message = (
            f"Не удалось загрузить голоса VoiceMaker: {error_message}"
            if prefix_message
            else error_message
        )
        controller.window.show_error(message)
    clear_options()


def _resolve_selected_voice_label(controller, preferred_label: str, voices_by_label: dict[str, VoiceMakerVoice], labels: list[str]) -> str:
    if preferred_label in voices_by_label:
        return preferred_label
    return labels[0] if labels else ""


def _apply_default_client_calls_text_voice(controller, selected_label: str) -> None:
    selected_voice = controller._client_calls_text_voices_by_label[selected_label]
    controller.settings.client_calls_text_voice = selected_label
    controller.settings.client_calls_text_voice_id = selected_voice.voice_id
    controller.settings.client_calls_text_language_code = selected_voice.language_code or "ru-RU"
    controller.repository.save_settings(controller.settings)


def _apply_default_generator_voice(controller, selected_label: str) -> None:
    selected_voice = controller._generator_voices_by_label[selected_label]
    controller.settings.generator_voice = selected_label
    controller.settings.generator_voice_id = selected_voice.voice_id
    controller.repository.save_settings(controller.settings)


def _sync_generator_accent_availability(controller) -> None:
    voice = controller._generator_voices_by_label.get(controller.settings.generator_voice)
    if voice is None:
        controller.window.set_generator_accent_enabled(False, "Сначала выберите совместимый голос.")
        return

    if voice.supports_accent_code:
        controller.window.set_generator_accent_enabled(True, "")
        return

    if controller.settings.generator_accent_code:
        controller.settings.generator_accent_code = ""
        controller.repository.save_settings(controller.settings)
        controller.window.set_generator_accent_options(
            [accent.label for accent in controller.voice_maker_service.get_accents()],
            controller._accent_label_by_code(""),
        )
    controller.window.set_generator_accent_enabled(
        False,
        "Этот голос не поддерживает AccentCode.",
    )


def _language_code_by_label(controller, label: str) -> str:
    for language in controller.voice_maker_service.get_languages():
        if language.label == label:
            return language.code
    return "ru-RU"


def _language_label_by_code(controller, code: str) -> str:
    for language in controller.voice_maker_service.get_languages():
        if language.code == code:
            return language.label
    return "Русский"


def _accent_code_by_label(controller, label: str) -> str:
    for accent in controller.voice_maker_service.get_accents():
        if accent.label == label:
            return accent.code
    return label.strip()


def _accent_label_by_code(controller, code: str) -> str:
    for accent in controller.voice_maker_service.get_accents():
        if accent.code == code:
            return accent.label
    return code


def _read_employees_file(controller) -> list[str]:
    if not controller.settings.employees_file_path or not os.path.exists(controller.settings.employees_file_path):
        return []
    with open(controller.settings.employees_file_path, "r", encoding="utf-8") as file:
        employees: list[str] = []
        for line in file:
            employee_name = controller._normalize_employee_name(line)
            if employee_name:
                employees.append(employee_name)
        return employees


def _append_employee_to_file(controller, employee_name: str) -> None:
    with open(controller.settings.employees_file_path, "a", encoding="utf-8") as file:
        file.write(f"{employee_name}\n")


def _write_employees_file(controller, employees: list[str]) -> None:
    with open(controller.settings.employees_file_path, "w", encoding="utf-8") as file:
        for employee_name in employees:
            file.write(f"{employee_name}\n")


def _write_worker_audio(controller, employee_name: str, audio_bytes: bytes) -> None:
    workers_dir = os.path.join(controller.recorded_call_builder.audio_root, "workers")
    os.makedirs(workers_dir, exist_ok=True)
    worker_path = os.path.join(workers_dir, f"{controller._employee_audio_stem(employee_name)}.mp3")
    with open(worker_path, "wb") as audio_file:
        audio_file.write(audio_bytes)


def _delete_worker_audio(controller, employee_name: str) -> None:
    workers_dir = os.path.join(controller.recorded_call_builder.audio_root, "workers")
    if not os.path.isdir(workers_dir):
        return

    normalized_stem = controller._normalized_employee_audio_stem(employee_name)
    for extension in (".mp3", ".wav"):
        worker_path = os.path.join(workers_dir, f"{controller._employee_audio_stem(employee_name)}{extension}")
        if os.path.exists(worker_path):
            os.remove(worker_path)
            return

    for file_name in os.listdir(workers_dir):
        file_path = os.path.join(workers_dir, file_name)
        if not os.path.isfile(file_path):
            continue
        stem, extension = os.path.splitext(file_name)
        if extension.lower() not in {".mp3", ".wav"}:
            continue
        if controller._normalized_employee_audio_stem(stem) == normalized_stem:
            os.remove(file_path)
            return


def _employee_audio_stem(controller, employee_name: str) -> str:
    normalized = controller._normalize_employee_name(employee_name)
    parts = normalized.split()
    if len(parts) >= 2:
        normalized = f"{parts[0]}_{parts[1]}"
    else:
        normalized = normalized.replace(" ", "_")
    return normalized.replace(" ", "_")


def _normalized_employee_audio_stem(controller, employee_name: str) -> str:
    return unicodedata.normalize("NFKC", controller._employee_audio_stem(employee_name)).casefold()


def _normalize_employee_name(controller, employee_name: str) -> str:
    normalized = unicodedata.normalize("NFKC", employee_name or "")
    return " ".join(normalized.split())


def _build_client_call_text_audio_file(controller, text: str) -> str:
    if not controller.settings.generator_api_key.strip():
        raise RuntimeError("Сначала введите API ключ генератора")

    voice_id = controller.settings.client_calls_text_voice_id or controller.settings.generator_voice_id
    if not voice_id:
        raise RuntimeError("Сначала выберите голос для текстовых сообщений")

    language_code = controller.settings.client_calls_text_language_code or "ru-RU"
    request_signature = controller._build_client_call_text_request_signature(text)
    if (
        controller._client_calls_text_audio_bytes is not None
        and request_signature == controller._client_calls_text_audio_signature
    ):
        generated_audio = controller._client_calls_text_audio_bytes
    else:
        generated_audio = controller._generate_voice_maker_audio(
            text=text,
            voice_id=voice_id,
            language_code=language_code,
        )
        controller._client_calls_text_audio_bytes = generated_audio
        controller._client_calls_text_audio_signature = request_signature

    temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    with os.fdopen(temp_fd, "wb") as temp_file:
        temp_file.write(generated_audio)
    return temp_path


def _generate_voice_maker_audio(controller, text: str, voice_id: str, language_code: str) -> bytes:
    return controller.voice_maker_service.generate_mp3(
        api_key=controller._read_generator_api_key(),
        text=text,
        voice_id=voice_id,
        language_code=language_code,
        master_volume=controller._generator_master_volume_for_request(),
        master_speed=controller.settings.generator_speed,
        accent_code=controller.settings.generator_accent_code,
    )


def _list_voice_maker_voices(controller, language_code: str) -> list[VoiceMakerVoice]:
    return controller.voice_maker_service.list_voices(
        controller._read_generator_api_key(),
        language_code,
    )
