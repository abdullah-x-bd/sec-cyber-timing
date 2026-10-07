from __future__ import annotations

import json
import os
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import requests


@dataclass
class SecClient:
    user_agent: str
    max_requests_per_second: float = 4.0

    def __post_init__(self) -> None:
        if not self.user_agent or "@" not in self.user_agent:
            raise ValueError(
                "SEC_USER_AGENT must be descriptive and include a contact email address."
            )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov",
            }
        )
        self._last_request = 0.0

    @classmethod
    def from_env(cls, max_requests_per_second: float = 4.0) -> "SecClient":
        return cls(
            user_agent=os.environ.get("SEC_USER_AGENT", ""),
            max_requests_per_second=max_requests_per_second,
        )

    def _throttle(self) -> None:
        interval = 1.0 / self.max_requests_per_second
        elapsed = time.monotonic() - self._last_request
        if elapsed < interval:
            time.sleep(interval - elapsed)

    def get(self, url: str, **kwargs) -> requests.Response:
        self._throttle()
        response = self.session.get(url, timeout=60, **kwargs)
        self._last_request = time.monotonic()
        response.raise_for_status()
        return response

    def download(self, url: str, destination: Path, overwrite: bool = False) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            return destination
        temp = destination.with_suffix(destination.suffix + ".part")
        with self.get(url, stream=True) as response:
            with temp.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        temp.replace(destination)
        return destination


def iter_submission_records(zip_path: Path) -> Iterator[dict]:
    """Yield normalized filing records from the SEC bulk submissions archive."""
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not name.startswith("CIK") or not name.endswith(".json"):
                continue
            with archive.open(name) as handle:
                payload = json.load(handle)
            recent = payload.get("filings", {}).get("recent", {})
            if not recent:
                continue

            columns = list(recent)
            count = len(recent.get("accessionNumber", []))
            for index in range(count):
                row = {
                    column: recent[column][index]
                    for column in columns
                    if index < len(recent.get(column, []))
                }
                row["cik"] = str(payload.get("cik", "")).zfill(10)
                row["company_name"] = payload.get("name")
                row["tickers"] = payload.get("tickers", [])
                row["exchanges"] = payload.get("exchanges", [])
                yield row
