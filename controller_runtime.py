import os
import subprocess
import sys
import time
from datetime import datetime

import soundfile as sf

from config import ERROR_LOG_FILE
from models import ClientCall
from services.playback_coordinator import PlaybackTask
from services.validation_service import ValidationError, ValidationService


def _play_file(
    controller,
    file_path: str,
    display_text: str = "",
    log_message: str = "",
    insert_as_next: bool = False,
) -> None:
    target_path = file_path.strip()
    if not target_path or not os.path.exists(target_path):
        file_name = os.path.basename(target_path) if target_path else "аудиофайл"
        controller._report_runtime_error(f"Не найден файл планировщика: {file_name}")
        return

    display_call = ClientCall(
        start_choice="",
        car_number="",
        end_choice="",
        display_message=display_text or os.path.basename(target_path),
    )
    should_defer = (
        controller._client_call_queue_current is not None
        or (not insert_as_next and controller._has_pending_client_calls())
    )
    controller._append_planner_queue_call(display_call, insert_as_next, should_defer)
    if log_message:
        controller._append_event_log(log_message)
    controller._render_combined_call_queue()

    main_duration = controller._get_audio_duration(target_path)
    notification_duration = controller._get_audio_duration(controller.settings.notification_sound_file_path)
    has_notification = controller._has_valid_notification_sound()
    total_duration = main_duration + (notification_duration if has_notification else 0.0)

    controller._enqueue_with_optional_notification(
        main_task=controller._build_planner_playback_task(target_path, display_call, total_duration, has_notification),
        notification_enabled=controller.settings.scheduler_notification_enabled,
        notification_device_name=controller.settings.selected_device,
        notification_volume=controller.settings.notification_volume,
        notification_started=(
            lambda call=display_call: controller._post_to_ui(controller._handle_planner_playback_started, call, total_duration)
        ) if has_notification else None,
        insert_as_next=insert_as_next,
        defer=should_defer,
        queue_group_id=display_call.call_id,
    )


def stop_audio(controller) -> None:
    controller.playback_coordinator.stop_current_group()
    controller.client_call_service.stop_current_playback()
    controller._clear_current_planner_playback()
    controller._append_event_log("Воспроизведение остановлено")
    controller._render_combined_call_queue()
    controller.window.clear_schedule_selection()
    controller._dispatch_deferred_planner_if_possible()
    controller._set_ready_status()


def _run_scheduled_entry(controller, entry) -> None:
    controller._play_file(
        entry.file_path,
        display_text=f"{entry.time_str} | {entry.file_name}",
        log_message=f"По расписанию - {entry.time_str} | {entry.file_name}",
        insert_as_next=controller._has_pending_playback(),
    )


def _refresh_client_calls_queue(
    controller,
    current_call: ClientCall | None,
    calls: list[ClientCall],
    progress: float,
) -> None:
    controller._client_call_queue_current = current_call
    controller._client_call_queue_items = calls[:]
    controller._client_call_queue_progress = progress
    controller._render_combined_call_queue()


def _report_runtime_error(controller, message: str) -> None:
    normalized_message = message.strip()
    if not normalized_message:
        return

    if normalized_message == controller._last_runtime_error:
        controller.window.set_last_error_status(normalized_message)
        return

    controller._last_runtime_error = normalized_message
    controller.window.set_last_error_status(normalized_message)
    controller._append_event_log(normalized_message)


def _handle_runtime_event(controller, message: str) -> None:
    controller._append_event_log(message)


def _handle_client_call_playback_finished(controller) -> None:
    controller._dispatch_deferred_planner_if_possible()
    controller._set_ready_status()


def _set_ready_status(controller) -> None:
    persistent_error = controller._get_persistent_status_error()
    if persistent_error:
        controller._last_runtime_error = persistent_error
        controller.window.set_last_error_status(persistent_error)
        return

    controller._last_runtime_error = ""
    controller.window.set_last_error_status("Готово")


def _get_persistent_status_error(controller) -> str:
    notification_enabled = (
        controller.settings.scheduler_notification_enabled
        or controller.settings.client_calls_notification_enabled
    )
    notification_path = controller.settings.notification_sound_file_path.strip()
    if notification_enabled and (not notification_path or not os.path.exists(notification_path)):
        return "Не найден файл звука уведомления"
    if controller._missing_schedule_entry_ids:
        return "Не найдены файлы из расписания"
    return ""


def _get_missing_schedule_entry_ids(controller, entries: list | None = None) -> set[str]:
    target_entries = entries if entries is not None else controller.schedule_manager.get_all()
    return {
        entry.entry_id
        for entry in target_entries
        if not os.path.exists(entry.file_path)
    }


def _refresh_runtime_status_loop(controller) -> None:
    try:
        current_missing_schedule_entry_ids = controller._get_missing_schedule_entry_ids()
        if current_missing_schedule_entry_ids != controller._missing_schedule_entry_ids:
            controller._missing_schedule_entry_ids = current_missing_schedule_entry_ids
            controller.window.fill_schedule_list(controller.schedule_manager.get_all(), controller._missing_schedule_entry_ids)
        persistent_error = controller._get_persistent_status_error()
        if persistent_error:
            if persistent_error != controller._last_runtime_error:
                controller._last_runtime_error = persistent_error
                controller.window.set_last_error_status(persistent_error)
        elif controller._last_runtime_error in {"Не найден файл звука уведомления", "Не найдены файлы из расписания"}:
            controller._set_ready_status()
    finally:
        controller._schedule_root_after(500, controller._refresh_runtime_status_loop)


def _append_event_log(controller, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        log_dir = os.path.dirname(ERROR_LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except OSError:
        return


def open_error_log(controller) -> None:
    try:
        log_dir = os.path.dirname(ERROR_LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        if not os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, "a", encoding="utf-8"):
                pass

        if os.name == "nt":
            os.startfile(ERROR_LOG_FILE)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ERROR_LOG_FILE])
        else:
            subprocess.Popen(["xdg-open", ERROR_LOG_FILE])
    except (OSError, subprocess.SubprocessError) as error:
        controller.window.show_error(f"Не удалось открыть лог ошибок: {error}")


def _render_combined_call_queue(controller) -> None:
    current_call = controller._client_call_queue_current or controller._planner_queue_current
    progress = (
        controller._client_call_queue_progress
        if controller._client_call_queue_current is not None
        else controller._planner_queue_progress
    )
    queued_calls = controller._get_combined_queued_calls()
    controller.window.render_client_calls(current_call, queued_calls, progress)
    controller.window.set_main_playback_active(
        controller.playback_coordinator.is_actively_playing or current_call is not None
    )


def _handle_planner_playback_started(controller, call: ClientCall, duration: float) -> None:
    if controller._planner_queue_current is not None and controller._planner_queue_current.call_id == call.call_id:
        return

    controller._remove_planner_queue_call(call.call_id)
    controller._planner_queue_current = call
    controller._planner_queue_duration = duration
    controller._planner_queue_started_at = time.monotonic() if duration > 0 else None
    controller._planner_queue_progress = 0.0
    controller._render_combined_call_queue()
    controller._schedule_planner_progress_update()


def _handle_planner_playback_finished(controller, call: ClientCall) -> None:
    if controller._planner_queue_current is not None and controller._planner_queue_current.call_id == call.call_id:
        controller._planner_queue_current = None
    controller._clear_current_planner_playback()
    controller._render_combined_call_queue()
    controller._dispatch_deferred_planner_if_possible()
    controller.client_call_service.resume_if_idle()
    controller._set_ready_status()


def _handle_planner_playback_error(controller, call: ClientCall, message: str) -> None:
    controller._remove_planner_queue_call(call.call_id)
    if controller._planner_queue_current is not None and controller._planner_queue_current.call_id == call.call_id:
        controller._planner_queue_current = None
    controller._clear_current_planner_playback()
    controller._render_combined_call_queue()
    controller._dispatch_deferred_planner_if_possible()
    controller.client_call_service.resume_if_idle()
    controller._report_runtime_error(message)


def _schedule_planner_progress_update(controller) -> None:
    if controller._planner_queue_current is None:
        return

    if controller._planner_queue_started_at is None or controller._planner_queue_duration <= 0:
        controller._planner_queue_progress = 1.0
        controller._render_combined_call_queue()
        return

    elapsed = time.monotonic() - controller._planner_queue_started_at
    controller._planner_queue_progress = max(0.0, min(elapsed / controller._planner_queue_duration, 1.0))
    controller._render_combined_call_queue()
    if controller._planner_queue_current is not None:
        controller.root.after(100, controller._schedule_planner_progress_update)


def _has_valid_notification_sound(controller) -> bool:
    notification_path = controller.settings.notification_sound_file_path.strip()
    return bool(notification_path and os.path.exists(notification_path))


def _get_audio_duration(controller, file_path: str) -> float:
    target_path = file_path.strip()
    if not target_path or not os.path.exists(target_path):
        return 0.0

    try:
        return float(sf.info(target_path).duration)
    except (OSError, RuntimeError, TypeError, ValueError):
        return 0.0


def _enqueue_with_optional_notification(
    controller,
    main_task: PlaybackTask,
    notification_enabled: bool,
    notification_device_name: str,
    notification_volume: float,
    notification_started=None,
    insert_as_next: bool = False,
    defer: bool = False,
    queue_group_id: str = "",
) -> None:
    tasks: list[PlaybackTask] = []
    if notification_enabled:
        try:
            ValidationService.validate_optional_file(
                controller.settings.notification_sound_file_path,
                "Сначала выберите файл звука уведомления",
            )
        except ValidationError:
            message = "Не найден файл звука уведомления"
            controller._report_runtime_error(message)
            controller.playback_coordinator.enqueue_batch([main_task], front=insert_as_next)
            return

        tasks.append(
            PlaybackTask(
                file_path=controller.settings.notification_sound_file_path,
                volume=notification_volume,
                device_name=notification_device_name,
                group_id=queue_group_id,
                on_started=(lambda _duration: notification_started()) if notification_started else None,
                on_error=main_task.on_error,
            )
        )

    tasks.append(main_task)
    if defer:
        controller._deferred_planner_task_groups.append((queue_group_id, tasks))
        return
    controller.playback_coordinator.enqueue_batch(tasks, front=insert_as_next)


def _append_planner_queue_call(controller, call: ClientCall, insert_as_next: bool, defer: bool) -> None:
    controller._planner_queue_items.append(call)
    controller._priority_planner_queue_ids.discard(call.call_id)
    controller._deferred_planner_queue_ids.discard(call.call_id)

    if insert_as_next:
        controller._planner_queue_items.remove(call)
        controller._planner_queue_items.insert(0, call)
        controller._priority_planner_queue_ids.add(call.call_id)
        return

    if defer:
        controller._deferred_planner_queue_ids.add(call.call_id)


def _build_planner_playback_task(
    controller,
    file_path: str,
    display_call: ClientCall,
    total_duration: float,
    has_notification: bool,
) -> PlaybackTask:
    return PlaybackTask(
        file_path=file_path,
        volume=controller.settings.volume,
        device_name=controller.settings.selected_device,
        group_id=display_call.call_id,
        on_started=lambda duration, call=display_call: controller._post_to_ui(
            controller._handle_planner_playback_started,
            call,
            total_duration if has_notification and total_duration > 0 else duration,
        ),
        on_finished=lambda call=display_call: controller._post_to_ui(
            controller._handle_planner_playback_finished,
            call,
        ),
        on_error=lambda message, call=display_call: controller._post_to_ui(
            controller._handle_planner_playback_error,
            call,
            message,
        ),
    )


def _clear_current_planner_playback(controller) -> None:
    controller._planner_queue_current = None
    controller._planner_queue_started_at = None
    controller._planner_queue_duration = 0.0
    controller._planner_queue_progress = 0.0


def _remove_planner_queue_call(controller, call_id: str) -> None:
    controller._planner_queue_items = [item for item in controller._planner_queue_items if item.call_id != call_id]
    controller._priority_planner_queue_ids.discard(call_id)
    controller._deferred_planner_queue_ids.discard(call_id)


def _get_combined_queued_calls(controller) -> list[ClientCall]:
    waiting_client_calls = controller._get_waiting_client_calls()
    priority_planner_calls = [
        call for call in controller._planner_queue_items
        if call.call_id in controller._priority_planner_queue_ids
    ]
    regular_planner_calls = [
        call for call in controller._planner_queue_items
        if call.call_id not in controller._priority_planner_queue_ids
        and call.call_id not in controller._deferred_planner_queue_ids
    ]
    deferred_planner_calls = [
        call for call in controller._planner_queue_items
        if call.call_id in controller._deferred_planner_queue_ids
    ]
    return priority_planner_calls + regular_planner_calls + waiting_client_calls + deferred_planner_calls


def _get_waiting_client_calls(controller) -> list[ClientCall]:
    current_call_id = (
        controller._client_call_queue_current.call_id
        if controller._client_call_queue_current is not None
        else None
    )
    return [
        call for call in controller._client_call_queue_items
        if call.call_id != current_call_id
    ]


def _has_pending_playback(controller) -> bool:
    return (
        controller.playback_coordinator.is_actively_playing
        or controller._planner_queue_current is not None
        or bool(controller._planner_queue_items)
        or controller._client_call_queue_current is not None
        or bool(controller._get_waiting_client_calls())
    )


def _has_pending_client_calls(controller) -> bool:
    return controller._client_call_queue_current is not None or bool(controller._get_waiting_client_calls())


def _dispatch_deferred_planner_if_possible(controller) -> None:
    if (
        controller.playback_coordinator.is_actively_playing
        or controller._planner_queue_current is not None
        or not controller._deferred_planner_task_groups
    ):
        if controller._has_priority_deferred_planner():
            controller._schedule_root_after(50, controller._dispatch_deferred_planner_if_possible)
        return

    deferred_index = controller._get_next_deferred_planner_group_index()
    if deferred_index is None:
        return

    group_id, tasks = controller._deferred_planner_task_groups.pop(deferred_index)
    controller.playback_coordinator.enqueue_batch(tasks, front=False)


def _get_next_deferred_planner_group_index(controller) -> int | None:
    for index, (group_id, _tasks) in enumerate(controller._deferred_planner_task_groups):
        if group_id in controller._priority_planner_queue_ids:
            return index

    if controller._has_pending_client_calls():
        return None

    return 0


def _has_priority_deferred_planner(controller) -> bool:
    return any(
        group_id in controller._priority_planner_queue_ids
        for group_id, _tasks in controller._deferred_planner_task_groups
    )


def remove_queued_call(controller, call_id: str) -> None:
    if not call_id:
        return

    controller.client_call_service.remove_queued_call(call_id)
    controller.playback_coordinator.remove_group(call_id)
    controller._planner_queue_items = [item for item in controller._planner_queue_items if item.call_id != call_id]
    controller._priority_planner_queue_ids.discard(call_id)
    controller._deferred_planner_queue_ids.discard(call_id)
    controller._deferred_planner_task_groups = [
        (group_id, tasks)
        for group_id, tasks in controller._deferred_planner_task_groups
        if group_id != call_id
    ]
    controller._render_combined_call_queue()
