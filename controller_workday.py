from datetime import date, datetime, time, timedelta


WORKDAY_ERROR_RETRY_MS = 30 * 60_000


def _is_today_workday(controller) -> bool:
    today = date.today()
    if controller._today_workday_date != today:
        return False
    return controller.workday_calendar_service.is_workday_status(controller._today_workday_status)


def _refresh_workday_status_loop(controller) -> None:
    today = date.today()
    if controller._workday_status_loading:
        return

    controller._workday_status_loading = True
    controller.window.set_workday_status(None)
    controller._start_worker(controller._refresh_workday_status_worker, today)


def _refresh_workday_status_worker(controller, target_date: date) -> None:
    try:
        status = controller.workday_calendar_service.get_day_status(target_date)
    except Exception as error:
        cached_status = controller.workday_calendar_service.get_cached_day_status(target_date)
        if cached_status is None:
            controller._post_to_ui(controller._finish_workday_status, target_date, None, str(error))
            return
        controller._post_to_ui(controller._finish_workday_status, target_date, cached_status, "")
        return

    controller._post_to_ui(controller._finish_workday_status, target_date, status, "")


def _finish_workday_status(controller, target_date: date, status: int | None, error_message: str) -> None:
    controller._workday_status_loading = False
    if target_date != date.today():
        controller._schedule_root_after(0, controller._refresh_workday_status_loop)
        return

    previous_error = controller._today_workday_error
    controller._today_workday_date = target_date
    controller._today_workday_status = status
    controller._today_workday_error = error_message
    controller.window.set_workday_status(status)

    if error_message:
        if error_message != previous_error:
            controller._report_runtime_error(f"Не удалось проверить рабочий день: {error_message}")
        controller._schedule_root_after(WORKDAY_ERROR_RETRY_MS, controller._refresh_workday_status_loop)
        return

    controller._schedule_root_after(_milliseconds_until_next_day(), controller._refresh_workday_status_loop)


def _milliseconds_until_next_day() -> int:
    now = datetime.now()
    next_day = datetime.combine(now.date() + timedelta(days=1), time.min)
    return max(1_000, int((next_day - now).total_seconds() * 1000) + 5_000)


def show_workday_calendar(controller) -> None:
    year = date.today().year
    controller.window.show_workday_calendar_loading(year)
    controller._start_worker(controller._load_workday_calendar_worker, year)


def _load_workday_calendar_worker(controller, year: int) -> None:
    try:
        statuses = controller.workday_calendar_service.get_year_statuses(year)
    except Exception as error:
        controller._post_to_ui(controller._finish_workday_calendar, year, {}, str(error))
        return

    controller._post_to_ui(controller._finish_workday_calendar, year, statuses, "")


def _finish_workday_calendar(controller, year: int, statuses: dict[date, int], error_message: str) -> None:
    if error_message:
        controller.window.close_workday_calendar()
        controller.window.show_error(f"Не удалось загрузить календарь: {error_message}")
        return
    controller.window.show_workday_calendar(year, statuses)
