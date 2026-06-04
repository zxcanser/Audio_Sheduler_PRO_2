import json
import os
import platform
import re
import subprocess
import tempfile
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    tag_name: str
    name: str
    installer_url: str
    installer_name: str
    html_url: str


class UpdateService:
    def __init__(self, releases_api_url: str, current_version: str) -> None:
        self.releases_api_url = releases_api_url
        self.current_version = current_version
        self.platform = platform.system()

    def get_available_update(self) -> UpdateInfo | None:
        release_data = self._fetch_latest_release()
        tag_name = str(release_data.get("tag_name") or "").strip()
        latest_version = self._normalize_version(tag_name)
        if not latest_version:
            raise RuntimeError("GitHub Release не содержит номер версии")

        if self._compare_versions(latest_version, self.current_version) <= 0:
            return None

        asset = self._select_installer_asset(release_data.get("assets") or [])
        if asset is None:
            raise RuntimeError("В последнем релизе не найден .exe установщик")

        return UpdateInfo(
            version=latest_version,
            tag_name=tag_name,
            name=str(release_data.get("name") or tag_name or latest_version),
            installer_url=str(asset.get("browser_download_url") or ""),
            installer_name=str(asset.get("name") or "AudioSchedulerPRO_Setup.exe"),
            html_url=str(release_data.get("html_url") or ""),
        )

    def download_installer(self, update_info: UpdateInfo) -> str:
        if self.platform != "Windows":
            raise RuntimeError("Автоустановка обновлений поддерживается только на Windows")

        updates_dir = Path(tempfile.gettempdir()) / "AudioSchedulerProUpdates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        installer_path = updates_dir / self._safe_file_name(update_info.installer_name)
        self._download_file(update_info.installer_url, installer_path)
        return str(installer_path)

    def launch_installer(self, installer_path: str) -> None:
        if self.platform != "Windows":
            raise RuntimeError("Запуск установщика поддерживается только на Windows")
        if not os.path.exists(installer_path):
            raise RuntimeError(f"Установщик не найден: {installer_path}")
        subprocess.Popen([installer_path], close_fds=True)

    def _fetch_latest_release(self) -> dict:
        request = urllib.request.Request(
            self.releases_api_url,
            headers={"User-Agent": "AudioSchedulerPro/1.0"},
        )
        try:
            with self._urlopen(request, timeout=20) as response:
                raw_data = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 403:
                return self._fetch_latest_release_from_public_page()
            if error.code == 404:
                raise RuntimeError("GitHub Release не найден") from error
            raise RuntimeError(f"GitHub вернул HTTP {error.code}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Не удалось подключиться к GitHub: {error.reason}") from error

        try:
            parsed = json.loads(raw_data)
        except json.JSONDecodeError as error:
            raise RuntimeError("GitHub вернул некорректный JSON") from error
        if not isinstance(parsed, dict):
            raise RuntimeError("GitHub вернул неожиданный ответ")
        return parsed

    def _fetch_latest_release_from_public_page(self) -> dict:
        repo_url = self._repository_web_url()
        latest_url = f"{repo_url}/releases/latest"
        request = urllib.request.Request(
            latest_url,
            headers={"User-Agent": "AudioSchedulerPro/1.0"},
        )

        try:
            with self._urlopen(request, timeout=20) as response:
                html = response.read().decode("utf-8", errors="replace")
                final_url = response.geturl()
        except urllib.error.URLError as error:
            raise RuntimeError(f"Не удалось открыть страницу релиза GitHub: {error.reason}") from error

        tag_name = self._tag_from_release_url(final_url)
        if not tag_name:
            tag_name = self._tag_from_release_html(html)
        if not tag_name:
            raise RuntimeError("GitHub Release не найден")

        assets = self._fetch_release_assets_from_public_page(repo_url, tag_name)
        html_url = f"{repo_url}/releases/tag/{urllib.parse.quote(tag_name, safe='')}"
        return {
            "tag_name": tag_name,
            "name": tag_name,
            "html_url": html_url,
            "assets": assets,
        }

    def _fetch_release_assets_from_public_page(self, repo_url: str, tag_name: str) -> list[dict]:
        assets_url = f"{repo_url}/releases/expanded_assets/{urllib.parse.quote(tag_name, safe='')}"
        request = urllib.request.Request(
            assets_url,
            headers={"User-Agent": "AudioSchedulerPro/1.0"},
        )

        try:
            with self._urlopen(request, timeout=20) as response:
                html = response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as error:
            raise RuntimeError(f"Не удалось получить список файлов релиза: {error.reason}") from error

        assets: list[dict] = []
        for href in re.findall(r'href="([^"]+/releases/download/[^"]+\.exe)"', html, flags=re.IGNORECASE):
            download_url = urllib.parse.urljoin(repo_url, href.replace("&amp;", "&"))
            name = urllib.parse.unquote(download_url.rsplit("/", 1)[-1])
            assets.append({"name": name, "browser_download_url": download_url})
        return assets

    def _repository_web_url(self) -> str:
        parsed = urllib.parse.urlparse(self.releases_api_url)
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.netloc != "api.github.com" or len(parts) < 2:
            raise RuntimeError("Неверно настроена ссылка GitHub Releases")
        return f"https://github.com/{parts[1]}/{parts[2]}"

    def _tag_from_release_url(self, release_url: str) -> str:
        marker = "/releases/tag/"
        if marker not in release_url:
            return ""
        tag = release_url.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0]
        return urllib.parse.unquote(tag).strip()

    def _tag_from_release_html(self, html: str) -> str:
        match = re.search(r"/releases/tag/([^\"?#<]+)", html)
        if not match:
            return ""
        return urllib.parse.unquote(match.group(1)).strip()

    def _select_installer_asset(self, assets: list) -> dict | None:
        exe_assets = [asset for asset in assets if str(asset.get("name") or "").lower().endswith(".exe")]
        if not exe_assets:
            return None

        preferred_assets = [
            asset
            for asset in exe_assets
            if any(marker in str(asset.get("name") or "").lower() for marker in ("setup", "installer", "install"))
        ]
        return (preferred_assets or exe_assets)[0]

    def _download_file(self, url: str, target_path: Path) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "AudioSchedulerPro/1.0"})
        try:
            with self._urlopen(request, timeout=60) as response:
                with target_path.open("wb") as target_file:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        target_file.write(chunk)
        except urllib.error.URLError as error:
            raise RuntimeError(f"Не удалось скачать установщик: {error.reason}") from error

    def _urlopen(self, request: urllib.request.Request, timeout: int):
        return urllib.request.urlopen(request, timeout=timeout, context=self._ssl_context())

    def _ssl_context(self):
        try:
            import certifi
        except Exception:
            return ssl.create_default_context()
        return ssl.create_default_context(cafile=certifi.where())

    def _safe_file_name(self, file_name: str) -> str:
        clean_name = "".join(char for char in file_name if char not in '<>:"/\\|?*').strip()
        return clean_name or "AudioSchedulerPRO_Setup.exe"

    def _normalize_version(self, version: str) -> str:
        return version.strip().lstrip("vV")

    def _compare_versions(self, left: str, right: str) -> int:
        left_parts = self._version_parts(left)
        right_parts = self._version_parts(right)
        max_length = max(len(left_parts), len(right_parts))
        left_parts.extend([0] * (max_length - len(left_parts)))
        right_parts.extend([0] * (max_length - len(right_parts)))
        if left_parts == right_parts:
            return 0
        return 1 if left_parts > right_parts else -1

    def _version_parts(self, version: str) -> list[int]:
        parts: list[int] = []
        for part in self._normalize_version(version).split("."):
            digits = "".join(char for char in part if char.isdigit())
            parts.append(int(digits) if digits else 0)
        return parts or [0]
