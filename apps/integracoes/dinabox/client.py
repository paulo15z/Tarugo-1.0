from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from urllib.parse import urljoin

import requests
from django.conf import settings


class DinaboxAuthError(RuntimeError):
    """Erro de autenticacao na API Dinabox."""


class DinaboxRequestError(RuntimeError):
    """Erro de requisicao na API Dinabox."""


@dataclass
class DinaboxTokenResult:
    token: str
    expires_in: int | None = None
    token_type: str | None = None
    user_login: str | None = None
    user_display_name: str | None = None
    user_email: str | None = None
    company_id: int | None = None


class DinaboxAPIClient:
    """
    Cliente HTTP para autenticar e consumir API Dinabox.
    Suporta conta tecnica global (service account) e token explicito.
    """

    _GLOBAL_TOKEN_CACHE: dict[str, dict] = {}

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        timeout: int | None = None,
        verify_ssl: bool | None = None,
    ) -> None:
        self.base_url = (base_url or settings.DINABOX_BASE_URL).rstrip("/") + "/"
        self.username = (username if username is not None else getattr(settings, "DINABOX_SERVICE_USERNAME", "")).strip()
        self.password = (password if password is not None else getattr(settings, "DINABOX_SERVICE_PASSWORD", "")).strip()
        self.timeout = timeout if timeout is not None else int(settings.DINABOX_TIMEOUT_SECONDS)
        self.verify_ssl = settings.DINABOX_VERIFY_SSL if verify_ssl is None else bool(verify_ssl)

        self._session = requests.Session()
        self._token_cache: str | None = None
        self._token_expira_em: datetime | None = None

        if token:
            self.definir_token(token)
        else:
            self._carregar_token_global()

    @classmethod
    def invalidar_cache_global(cls) -> None:
        cls._GLOBAL_TOKEN_CACHE.clear()

    def _token_url(self) -> str:
        return urljoin(self.base_url, "api/v1/token")

    def _cache_key(self) -> str:
        return f"{self.base_url}|{self.username}"

    def _carregar_token_global(self) -> None:
        if not self.username:
            return

        payload = self._GLOBAL_TOKEN_CACHE.get(self._cache_key())
        if not payload:
            return

        expira_em = payload.get("expira_em")
        token = payload.get("token")
        if not token or not isinstance(expira_em, datetime):
            return

        self._token_cache = token
        self._token_expira_em = expira_em
        if self._token_ainda_valido():
            self._session.headers.update({"Authorization": f"Bearer {self._token_cache}"})

    def _salvar_token_global(self) -> None:
        if not self.username or not self._token_cache or not self._token_expira_em:
            return

        self._GLOBAL_TOKEN_CACHE[self._cache_key()] = {
            "token": self._token_cache,
            "expira_em": self._token_expira_em,
        }

    def definir_token(self, token: str) -> None:
        self._token_cache = token.strip()
        self._session.headers.update({"Authorization": f"Bearer {self._token_cache}"})

    def _token_ainda_valido(self) -> bool:
        if not self._token_cache or not self._token_expira_em:
            return False
        margem = timedelta(seconds=30)
        return datetime.now(timezone.utc) + margem < self._token_expira_em

    def obter_token(self, force_refresh: bool = False) -> DinaboxTokenResult:
        if not self.username or not self.password:
            raise DinaboxAuthError(
                "Credenciais Dinabox ausentes. Configure DINABOX_SERVICE_USERNAME e DINABOX_SERVICE_PASSWORD."
            )

        if not force_refresh and self._token_ainda_valido():
            return DinaboxTokenResult(token=self._token_cache or "")

        self._carregar_token_global()
        if not force_refresh and self._token_ainda_valido():
            return DinaboxTokenResult(token=self._token_cache or "")

        try:
            response = self._session.post(
                self._token_url(),
                params={"username": self.username, "password": self.password},
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            raise DinaboxAuthError(f"Falha de comunicacao com Dinabox: {exc}") from exc

        if response.status_code >= 400:
            detalhe = response.text[:300] if response.text else f"HTTP {response.status_code}"
            raise DinaboxAuthError(f"Autenticacao Dinabox falhou: {detalhe}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise DinaboxAuthError("Resposta de token da Dinabox nao esta em JSON.") from exc

        token = payload.get("token") or payload.get("access_token") or payload.get("access") or payload.get("jwt")
        if not token:
            raise DinaboxAuthError("Resposta de autenticacao sem campo de token reconhecido.")

        expires_in_raw = payload.get("expires_in") or payload.get("expires")
        expiration_time_raw = payload.get("expiration_time")
        expires_in = None

        if isinstance(expiration_time_raw, (int, float, str)) and str(expiration_time_raw).strip().isdigit():
            expiration_ts = int(str(expiration_time_raw).strip())
            self._token_expira_em = datetime.fromtimestamp(expiration_ts, tz=timezone.utc)
            restante = int((self._token_expira_em - datetime.now(timezone.utc)).total_seconds())
            expires_in = max(0, restante)
        elif isinstance(expires_in_raw, (int, float, str)) and str(expires_in_raw).strip().isdigit():
            expires_in = int(str(expires_in_raw).strip())
            self._token_expira_em = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        else:
            self._token_expira_em = datetime.now(timezone.utc) + timedelta(minutes=5)

        self.definir_token(str(token))
        self._salvar_token_global()

        return DinaboxTokenResult(
            token=self._token_cache,
            expires_in=expires_in,
            token_type=payload.get("token_type"),
            user_login=payload.get("user_login"),
            user_display_name=payload.get("user_display_name"),
            user_email=payload.get("user_email"),
            company_id=payload.get("company_id"),
        )

    def _ensure_auth(self) -> None:
        if "Authorization" in self._session.headers and self._token_ainda_valido():
            return
        if self._token_cache and "Authorization" in self._session.headers:
            return
        self.obter_token()

    def request_meta(self, method: str, endpoint: str, **kwargs) -> dict:
        self._ensure_auth()
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        try:
            response = self._session.request(
                method=method.upper(),
                url=url,
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs,
            )
        except requests.RequestException as exc:
            return {
                "status": 0,
                "ok": False,
                "json": None,
                "text": str(exc),
                "error": str(exc),
            }

        payload = None
        try:
            payload = response.json()
        except ValueError:
            payload = None

        return {
            "status": response.status_code,
            "ok": response.status_code < 400,
            "json": payload,
            "text": response.text,
        }

    @staticmethod
    def _encode_params(params: dict | None) -> dict | None:
        if not params:
            return params
        encoded = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                encoded[key] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            else:
                encoded[key] = value
        return encoded

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        if "params" in kwargs:
            kwargs["params"] = self._encode_params(kwargs.get("params"))
        meta = self.request_meta(method, endpoint, **kwargs)

        if meta["status"] in (401, 403):
            detalhe = (meta.get("text") or "")[:300] or f"HTTP {meta['status']}"
            raise DinaboxAuthError(f"Token Dinabox invalido ou expirado: {detalhe}")

        if not meta["ok"]:
            detalhe = (meta.get("text") or "")[:300] or f"HTTP {meta['status']}"
            raise DinaboxRequestError(f"Erro na API Dinabox ({meta['status']}): {detalhe}")

        if meta.get("json") is None:
            raise DinaboxRequestError("Resposta da API Dinabox nao esta em JSON.")

        return meta["json"]

    def get_user_info(self) -> dict:
        return self._request("GET", "/api/v1/user")

    def get_projects(self, page: int = 1, search: str | None = None, status: str | None = None) -> dict:
        params = {"p": page}
        if search:
            params["s"] = search
        if status:
            params["filter_by_project_status"] = status
        return self._request("GET", "/api/v1/projects", params=params)

    def get_project(self, project_id: str) -> dict:
        return self._request("GET", "/api/v1/project", params={"project_id": project_id})

    def get_project_groups(self, page: int = 1, search: str | None = None) -> dict:
        params = {"p": page}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/project-groups", params=params)

    def get_project_group(self, group_id: str) -> dict:
        return self._request("GET", "/api/v1/project-group", params={"group_id": group_id})

    def get_customers(self, page: int = 1, search: str | None = None) -> dict:
        params = {"p": page}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/customers", params=params)

    def create_customer(
        self,
        customer_name: str,
        customer_type: str = "pf",
        customer_status: str = "on",
        customer_emails: str | None = None,
        customer_phones: str | None = None,
        customer_pf_data: dict | None = None,
        customer_pj_data: dict | None = None,
        customer_addresses: list[dict] | None = None,
        customer_note: str | None = None,
        custom_fields: dict | None = None,
    ) -> dict:
        params = {
            "customer_name": customer_name,
            "customer_type": customer_type,
            "customer_status": customer_status,
        }
        if customer_emails:
            params["customer_emails"] = customer_emails
        if customer_phones:
            params["customer_phones"] = customer_phones
        if customer_pf_data:
            params["customer_pf_data"] = customer_pf_data
        if customer_pj_data:
            params["customer_pj_data"] = customer_pj_data
        if customer_addresses:
            params["customer_addresses"] = customer_addresses
        if customer_note:
            params["customer_note"] = customer_note
        if custom_fields:
            params["custom_fields"] = custom_fields
        return self._request("PUT", "/api/v1/customer", params=params)

    def update_customer(
        self,
        customer_id: str,
        customer_name: str,
        customer_type: str = "pf",
        customer_status: str = "on",
        customer_emails: str | None = None,
        customer_phones: str | None = None,
        customer_pf_data: dict | None = None,
        customer_pj_data: dict | None = None,
        customer_addresses: list[dict] | None = None,
        customer_note: str | None = None,
        custom_fields: dict | None = None,
    ) -> dict:
        params = {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_type": customer_type,
            "customer_status": customer_status,
        }
        if customer_emails:
            params["customer_emails"] = customer_emails
        if customer_phones:
            params["customer_phones"] = customer_phones
        if customer_pf_data:
            params["customer_pf_data"] = customer_pf_data
        if customer_pj_data:
            params["customer_pj_data"] = customer_pj_data
        if customer_addresses:
            params["customer_addresses"] = customer_addresses
        if customer_note:
            params["customer_note"] = customer_note
        if custom_fields:
            params["custom_fields"] = custom_fields
        return self._request("PATCH", "/api/v1/customer", params=params)

    def get_customer(self, customer_id: str) -> dict:
        return self._request("GET", "/api/v1/customer", params={"customer_id": customer_id})

    def delete_customer(self, customer_id: str) -> dict:
        return self._request("DELETE", "/api/v1/customer", params={"customer_id": customer_id})

    def get_designers(self, page: int = 1, search: str | None = None) -> dict:
        params = {"p": page}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/designers", params=params)

    def get_providers(self, page: int = 1, search: str | None = None) -> dict:
        params = {"p": page}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/providers", params=params)

    def get_employees(self, page: int = 1, search: str | None = None) -> dict:
        params = {"p": page}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/employees", params=params)

    def get_materials(self, page: int = 1, type_source: str = "dinabox", search: str | None = None) -> dict:
        params = {"p": page, "type": type_source}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/materials", params=params)

    def get_components(self, page: int = 1, type_source: str = "user", search: str | None = None) -> dict:
        params = {"p": page, "type": type_source}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/components", params=params)

    def get_doors(self, page: int = 1, type_source: str = "dinabox", search: str | None = None) -> dict:
        params = {"p": page, "type": type_source}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/doors", params=params)

    def get_labels(self, page: int = 1, search: str | None = None) -> dict:
        params = {"p": page}
        if search:
            params["s"] = search
        return self._request("GET", "/api/v1/labels", params=params)

    def create_label(self, label_name: str, label_type: str, label_content: str = "") -> dict:
        params = {
            "label_name": label_name,
            "label_type": label_type,
            "label_content": label_content,
        }
        return self._request("POST", "/api/v1/label", params=params)

    def delete_label(self, label_id: str) -> dict:
        return self._request("DELETE", "/api/v1/label", params={"label_id": label_id})
