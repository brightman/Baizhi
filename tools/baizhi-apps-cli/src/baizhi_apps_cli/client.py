from __future__ import annotations

from typing import Any

import httpx


class ApiError(RuntimeError):
    def __init__(self, code: str, message: str, http_status: int | None = None) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        status = f" (HTTP {http_status})" if http_status is not None else ""
        super().__init__(f"{code}: {message}{status}")

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "http_status": self.http_status}


class ApiClient:
    def __init__(
        self,
        host: str,
        token: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30,
    ) -> None:
        self.host = host.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            base_url=self.host,
            follow_redirects=False,
            trust_env=False,
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        files: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = self.client.request(
                method, path, headers=headers, json=json, files=files, params=params,
            )
        except httpx.TimeoutException as exc:
            raise ApiError("REQUEST_TIMEOUT", "The platform request timed out; no automatic retry was made.") from exc
        except httpx.HTTPError as exc:
            raise ApiError("NETWORK_ERROR", f"The platform request failed ({exc.__class__.__name__}).") from exc
        try:
            body = response.json() if response.content else None
        except ValueError:
            body = None
        if response.status_code < 200 or response.status_code >= 300:
            detail = body.get("detail") if isinstance(body, dict) else None
            if isinstance(detail, dict):
                code = str(detail.get("code") or "HTTP_ERROR")
                message = str(detail.get("message") or "The platform rejected the request.")
            elif isinstance(detail, str):
                code, message = "HTTP_ERROR", detail
            else:
                code, message = "HTTP_ERROR", "The platform rejected the request."
            if response.status_code == 401 and code in {"HTTP_ERROR", "unauthorized"}:
                message = "Authentication failed or expired; run baizhi-apps login --env <name>."
            if code == "OIDC_ONLY":
                message = "This V1 CLI supports local email/password authentication only; this host requires OIDC."
            raise ApiError(code, message, response.status_code)
        return body
