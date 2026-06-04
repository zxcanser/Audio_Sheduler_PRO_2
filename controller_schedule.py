import json
import os
import time
from tkinter import filedialog

from models import ScheduleEntry
from services.validation_service import ValidationError, ValidationService


def _refresh_schedule_list(controller) -> None:
    entries = controller.schedule_manager.get_all()
    controller._missing_schedule_entry_ids = controller._get_missing_schedule_entry_ids(entries)
    controller.window.fill_schedule_list(entries, controller._missing_schedule_entry_ids)
    controller.repository.save_schedule(entries)


def browse_file(controller) -> None:
    file_path = filedialog.askopenfilename(
        filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg")]
    )
    if file_path:
        controller.window.set_selected_file(file_path)


def browse_client_calls_file(controller) -> None:
    file_path = filedialog.askopenfilename(
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if file_path:
        controller.window.set_client_calls_file(file_path)
        controller.settings.client_calls_file_path = file_path
        controller.repository.save_settings(controller.settings)


def browse_client_calls_voice_message_file(controller) -> None:
    file_path = filedialog.askopenfilename(
        filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg"), ("All Files", "*.*")]
    )
    if file_path:
        controller.window.set_client_calls_voice_message_file(file_path)
        controller._update_setting("client_calls_voice_message_file_path", file_path)


def browse_employees_file(controller) -> None:
    file_path = filedialog.askopenfilename(
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if file_path:
        controller.window.set_employees_file(file_path)
        controller._update_setting("employees_file_path", file_path)
        controller._refresh_employees_list()


def browse_notification_sound_file(controller) -> None:
    file_path = filedialog.askopenfilename(
        filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg"), ("All Files", "*.*")]
    )
    if file_path:
        controller.window.set_notification_sound_file(file_path)
        controller._update_setting("notification_sound_file_path", file_path)
    controller._set_ready_status()


def add_schedule(controller) -> None:
    try:
        file_path = controller.window.get_selected_file()
        ValidationService.validate_file(file_path)

        hours, minutes = controller.window.get_time_input()
        time_str = ValidationService.validate_time(hours, minutes)

        entry_id = controller.window.get_selected_entry_id()
        if entry_id and controller.schedule_manager.get_by_id(entry_id):
            old_file_path = controller.schedule_manager.get_by_id(entry_id).file_path
            controller.schedule_manager.update_entry(entry_id, time_str, file_path)
            if old_file_path != file_path:
                controller.schedule_manager.replace_file_path(old_file_path, file_path)
        else:
            controller.schedule_manager.add_entry(time_str, file_path)
        controller._refresh_schedule_list()

    except ValidationError as error:
        controller.window.show_error(str(error))


def delete_schedule(controller) -> None:
    try:
        entry_id = controller.window.get_selected_entry_id()
        if not entry_id:
            raise ValidationError("Выберите запись для удаления")

        controller.schedule_manager.delete_entry(entry_id)
        controller._refresh_schedule_list()

    except ValidationError as error:
        controller.window.show_error(str(error))


def load_selected_entry_into_form(controller) -> None:
    entry_id = controller.window.get_selected_entry_id()
    if not entry_id:
        controller.window.set_schedule_action_button_label("Добавить")
        return

    entry = controller.schedule_manager.get_by_id(entry_id)
    if not entry:
        controller.window.set_schedule_action_button_label("Добавить")
        return

    controller.window.set_time_input(entry.time_str)
    controller.window.set_selected_file(entry.file_path)
    if entry.entry_id in controller._missing_schedule_entry_ids:
        controller.window.set_schedule_action_button_label("Заменить путь")
    else:
        controller.window.set_schedule_action_button_label("Обновить")


def play_selected_or_current(controller) -> None:
    if (
        controller.playback_coordinator.is_actively_playing
        or controller._client_call_queue_current is not None
        or controller._planner_queue_current is not None
    ):
        controller.stop_audio()
        return

    file_path = controller.window.get_selected_file()
    if not file_path:
        controller.window.show_error("Сначала выберите файл")
        return

    entry_id = controller.window.get_selected_entry_id()
    if entry_id:
        entry = controller.schedule_manager.get_by_id(entry_id)
        if entry is not None:
            planner_log_message = f"Добавлено в очередь - {entry.file_name}"
        else:
            planner_log_message = f"Добавлено в очередь - {os.path.basename(file_path)}"
    else:
        planner_log_message = f"Добавлено в очередь - {os.path.basename(file_path)}"

    controller._play_file(file_path, log_message=planner_log_message)


def queue_selected_schedule_entry(controller, entry_id: str) -> None:
    if not entry_id:
        return

    entry = controller.schedule_manager.get_by_id(entry_id)
    if entry is None:
        controller.window.show_error("Запись не найдена")
        return

    signature = f"{entry.entry_id}:{entry.file_path}"
    now = time.monotonic()
    if signature == controller._last_manual_queue_signature and (now - controller._last_manual_queue_at) < 0.35:
        return

    controller._last_manual_queue_signature = signature
    controller._last_manual_queue_at = now

    controller._play_file(
        entry.file_path,
        log_message=f"Добавлено в очередь - {entry.file_name}",
    )


def export_schedule(controller) -> None:
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        initialfile="schedule.json",
        filetypes=[("JSON Files", "*.json")],
    )
    if not file_path:
        return

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(
                [
                    {
                        "time_str": entry.time_str,
                        "file_path": entry.file_path,
                        "enabled": entry.enabled,
                        "entry_id": entry.entry_id,
                    }
                    for entry in controller.schedule_manager.get_all()
                ],
                file,
                ensure_ascii=False,
                indent=2,
            )
    except OSError as error:
        controller.window.show_error(f"Не удалось экспортировать расписание: {error}")


def import_schedule(controller) -> None:
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
    )
    if not file_path:
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        controller.window.show_error(f"Не удалось импортировать расписание: {error}")
        return

    try:
        entries = controller._parse_imported_schedule_entries(raw_data)
    except (TypeError, KeyError, ValueError) as error:
        controller.window.show_error(f"Некорректный файл расписания: {error}")
        return

    controller.schedule_manager.replace_entries(entries)
    controller._refresh_schedule_list()


def _parse_imported_schedule_entries(controller, raw_data) -> list[ScheduleEntry]:
    if not isinstance(raw_data, list):
        raise ValueError("Файл расписания должен содержать список записей")

    return [
        ScheduleEntry(
            time_str=item["time_str"],
            file_path=item["file_path"],
            enabled=item.get("enabled", True),
            entry_id=item.get("entry_id"),
        )
        for item in raw_data
    ]
