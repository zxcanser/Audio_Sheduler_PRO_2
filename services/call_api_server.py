import json
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlparse


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class CallApiServerService:
    def __init__(
        self,
        on_call_request: Callable[[dict], dict],
        on_error: Callable[[str], None],
    ) -> None:
        self._on_call_request = on_call_request
        self._on_error = on_error
        self._server: _ReusableThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._host = "127.0.0.1"
        self._port = 8765
        self._token = ""
        self._seen_request_ids: set[str] = set()
        self._recent_request_ids: deque[str] = deque()
        self._request_ids_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._server_thread is not None and self._server_thread.is_alive()

    def start(self, host: str, port: int, token: str = "") -> None:
        self.stop()
        self._host = host
        self._port = port
        self._token = token.strip()

        handler_class = self._build_handler_class()
        try:
            self._server = _ReusableThreadingHTTPServer((host, port), handler_class)
        except OSError as error:
            raise RuntimeError(f"Не удалось запустить API сервер на {host}:{port}: {error}") from error

        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except OSError:
                pass
        if self._server_thread is not None:
            self._server_thread.join(timeout=1.0)

        self._server = None
        self._server_thread = None

    def _build_handler_class(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "AudioSchedulerProAPI/1.0"

            def do_GET(self) -> None:
                path = urlparse(self.path).path.rstrip("/") or "/"
                if path != "/health":
                    self._write_json(404, {"success": False, "message": "Маршрут не найден"})
                    return

                self._write_json(
                    200,
                    {
                        "success": True,
                        "status": "ok",
                        "host": outer._host,
                        "port": outer._port,
                    },
                )

            def do_POST(self) -> None:
                path = urlparse(self.path).path.rstrip("/") or "/"
                if path != "/api/call":
                    self._write_json(404, {"success": False, "message": "Маршрут не найден"})
                    return

                if not self._is_authorized():
                    self._write_json(401, {"success": False, "message": "Неверный токен API"})
                    return

                try:
                    payload = self._read_payload()
                    request_id = str(payload.get("request_id") or "").strip()
                    if request_id and outer._is_duplicate_request_id(request_id):
                        self._write_json(
                            200,
                            {
                                "success": True,
                                "duplicate": True,
                                "message": "Запрос с таким request_id уже был обработан",
                            },
                        )
                        return

                    result = outer._on_call_request(payload) or {}
                    if request_id:
                        outer._remember_request_id(request_id)
                    response = {"success": True, **result}
                    self._write_json(200, response)
                except ValueError as error:
                    self._write_json(400, {"success": False, "message": str(error)})
                except RuntimeError as error:
                    self._write_json(400, {"success": False, "message": str(error)})
                except Exception as error:
                    outer._on_error(f"Ошибка API вызовов: {error}")
                    self._write_json(500, {"success": False, "message": "Внутренняя ошибка API"})

            def log_message(self, format: str, *args) -> None:
                return

            def _is_authorized(self) -> bool:
                if not outer._token:
                    return True

                authorization = self.headers.get("Authorization", "").strip()
                if authorization.lower().startswith("bearer "):
                    authorization = authorization[7:].strip()
                return authorization == outer._token

            def _read_payload(self) -> dict:
                content_length_header = self.headers.get("Content-Length", "0").strip()
                try:
                    content_length = int(content_length_header)
                except ValueError as error:
                    raise ValueError("Некорректный Content-Length") from error

                if content_length <= 0:
                    raise ValueError("Тело запроса пустое")
                if content_length > 1024 * 1024:
                    raise ValueError("Слишком большой JSON запрос")

                raw_body = self.rfile.read(content_length)
                try:
                    payload = json.loads(raw_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ValueError("Некорректный JSON") from error

                if not isinstance(payload, dict):
                    raise ValueError("JSON должен быть объектом")
                return payload

            def _write_json(self, status_code: int, payload: dict) -> None:
                body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                try:
                    self.send_response(status_code)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    return

        return Handler

    def _is_duplicate_request_id(self, request_id: str) -> bool:
        with self._request_ids_lock:
            return request_id in self._seen_request_ids

    def _remember_request_id(self, request_id: str) -> None:
        with self._request_ids_lock:
            if request_id in self._seen_request_ids:
                return

            self._seen_request_ids.add(request_id)
            self._recent_request_ids.append(request_id)
            while len(self._recent_request_ids) > 300:
                expired_request_id = self._recent_request_ids.popleft()
                self._seen_request_ids.discard(expired_request_id)
