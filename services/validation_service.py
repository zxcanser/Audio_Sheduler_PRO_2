import os


class ValidationError(Exception):
    pass


class ValidationService:
    @staticmethod
    def validate_time(hours: str, minutes: str) -> str:
        hours = hours.strip()
        minutes = minutes.strip()

        if not hours or not minutes:
            raise ValidationError("Введите время")

        if not hours.isdigit() or not minutes.isdigit():
            raise ValidationError("Время должно быть в формате HH:MM")

        hour = int(hours)
        minute = int(minutes)

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValidationError("Некорректное время")

        return f"{hour:02d}:{minute:02d}"

    @staticmethod
    def validate_file(file_path: str) -> None:
        if not file_path:
            raise ValidationError("Сначала выберите аудиофайл")

        if not os.path.exists(file_path):
            raise ValidationError("Выбранный файл не существует")

    @staticmethod
    def validate_optional_file(file_path: str, empty_message: str) -> None:
        if not file_path:
            raise ValidationError(empty_message)

        if not os.path.exists(file_path):
            raise ValidationError("Выбранный файл не существует")

    @staticmethod
    def validate_interval(value: str) -> float:
        raw = value.strip().replace(",", ".")
        if not raw:
            return 5.0

        try:
            interval = float(raw)
        except ValueError as exc:
            raise ValidationError("Интервал должен быть числом") from exc

        if interval < 0:
            raise ValidationError("Интервал не может быть отрицательным")

        return interval

    @staticmethod
    def validate_host(value: str) -> str:
        host = value.strip()
        if not host:
            raise ValidationError("Укажите адрес API сервера")
        return host

    @staticmethod
    def validate_port(value: str) -> int:
        raw = value.strip()
        if not raw:
            return 8765

        if not raw.isdigit():
            raise ValidationError("Порт API должен быть целым числом")

        port = int(raw)
        if not (1 <= port <= 65535):
            raise ValidationError("Порт API должен быть в диапазоне 1-65535")

        return port
