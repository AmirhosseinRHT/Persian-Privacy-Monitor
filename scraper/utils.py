import time
from pathlib import Path
from urllib.parse import urlparse


class FileUtils:
    """Utility methods for filenames and paths."""

    @staticmethod
    def sanitize_filename(url: str) -> str:
        url = url.replace("http://", "").replace("https://", "")
        safe = url.replace(".", "-").replace(":", "").replace("/", "-")
        safe = "".join(c if c.isalnum() or c in "-_" else "" for c in safe)
        return safe

    @staticmethod
    def get_output_paths(url: str, out_dir: str):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        domain = urlparse(url).netloc or "output"
        safe_name = FileUtils.sanitize_filename(domain)
        return (
            Path(out_dir) / f"{safe_name}_{ts}.html",
            Path(out_dir) / f"{safe_name}_{ts}.txt",
        )
