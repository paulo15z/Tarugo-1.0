from __future__ import annotations

from django.db import transaction

from apps.integracoes.models import DinaboxClienteIndex
from apps.integracoes.dinabox.client import DinaboxAPIClient, DinaboxRequestError
from apps.integracoes.dinabox.parsers.customer_detail import parse_customer_detail
from apps.integracoes.dinabox.schemas.api import (
    DinaboxCustomerDetail,
    DinaboxCustomerListResponse,
    DinaboxGroupDetail,
    DinaboxGroupListResponse,
    DinaboxLabelListResponse,
    DinaboxMaterialListResponse,
    DinaboxProjectDetail,
    DinaboxProjectListResponse,
)


DINABOX_CAPABILITIES = [
    {"nome": "Usuario autenticado", "endpoint": "/api/v1/user", "descricao": "Dados da conta conectada na API.", "sample_params": {}},
    {"nome": "Projetos (lista)", "endpoint": "/api/v1/projects", "descricao": "Lista de projetos com filtros.", "sample_params": {"p": 1}},
    {"nome": "Projeto (detalhe)", "endpoint": "/api/v1/project", "descricao": "Detalhe por project_id.", "sample_params": {}},
    {"nome": "Lotes (lista)", "endpoint": "/api/v1/project-groups", "descricao": "Lista de lotes de projetos.", "sample_params": {"p": 1}},
    {"nome": "Lote (detalhe/acoes)", "endpoint": "/api/v1/project-group", "descricao": "Detalhe de lote e acoes POST/DELETE.", "sample_params": {}},
    {"nome": "Clientes (lista)", "endpoint": "/api/v1/customers", "descricao": "Lista paginada de clientes.", "sample_params": {"p": 1}},
    {"nome": "Cliente (detalhe/edicao)", "endpoint": "/api/v1/customer", "descricao": "GET/PUT/PATCH/DELETE por customer_id.", "sample_params": {}},
    {"nome": "Projetistas (lista)", "endpoint": "/api/v1/designers", "descricao": "Lista paginada de projetistas.", "sample_params": {"p": 1}},
    {"nome": "Projetista (detalhe/edicao)", "endpoint": "/api/v1/designer", "descricao": "GET/PUT/PATCH por designer_id.", "sample_params": {}},
    {"nome": "Fornecedores (lista)", "endpoint": "/api/v1/providers", "descricao": "Lista de fornecedores (pode retornar 404 quando vazio).", "sample_params": {"p": 1}},
    {"nome": "Fornecedor (detalhe/edicao)", "endpoint": "/api/v1/provider", "descricao": "GET/PUT/PATCH/DELETE por provider_id.", "sample_params": {}},
    {"nome": "Funcionarios (lista)", "endpoint": "/api/v1/employees", "descricao": "Lista de funcionarios (pode retornar 404 quando vazio).", "sample_params": {"p": 1}},
    {"nome": "Funcionario (detalhe/edicao)", "endpoint": "/api/v1/employee", "descricao": "GET/PUT/PATCH/DELETE por employee_id.", "sample_params": {}},
    {"nome": "Materiais", "endpoint": "/api/v1/materials", "descricao": "Catalogo de materiais (type=dinabox|user).", "sample_params": {"p": 1, "type": "dinabox"}},
    {"nome": "Componentes", "endpoint": "/api/v1/components", "descricao": "Catalogo de componentes (type=dinabox|user).", "sample_params": {"p": 1, "type": "user"}},
    {"nome": "Portas", "endpoint": "/api/v1/doors", "descricao": "Catalogo de portas (type=dinabox|user).", "sample_params": {"p": 1, "type": "dinabox"}},
    {"nome": "Etiquetas (lista)", "endpoint": "/api/v1/labels", "descricao": "Lista de etiquetas cadastradas.", "sample_params": {"p": 1}},
    {"nome": "Etiqueta (detalhe/acoes)", "endpoint": "/api/v1/label", "descricao": "GET/POST/DELETE por label_id.", "sample_params": {}},
]


class DinaboxApiService:
    """Camada de servico da API Dinabox."""

    def __init__(self, token: str | None = None):
        self.client = DinaboxAPIClient(token=token)

    def list_projects(self, page: int = 1, search: str | None = None, status: str | None = None) -> DinaboxProjectListResponse:
        payload = self.client.get_projects(page=page, search=search, status=status)
        return DinaboxProjectListResponse(**payload)

    def get_project_detail(self, project_id: str) -> DinaboxProjectDetail:
        payload = self.client.get_project(project_id=project_id)
        return DinaboxProjectDetail(**payload)

    def list_groups(self, page: int = 1, search: str | None = None) -> DinaboxGroupListResponse:
        payload = self.client.get_project_groups(page=page, search=search)
        return DinaboxGroupListResponse(**payload)

    def get_group_detail(self, group_id: str) -> DinaboxGroupDetail:
        payload = self.client.get_project_group(group_id=group_id)
        return DinaboxGroupDetail(**payload)

    def list_customers(self, page: int = 1, search: str | None = None) -> DinaboxCustomerListResponse:
        payload = self.client.get_customers(page=page, search=search)
        return DinaboxCustomerListResponse(**payload)

    def get_customer_detail(self, customer_id: str) -> DinaboxCustomerDetail:
        """
        Busca detalhe de um cliente na API Dinabox e retorna estrutura tipada.
        
        A API Dinabox pode retornar de diferentes formas:
        1. Cliente isolado com paginação em nível raiz: {'page': 1, 'total': 1, 'customer_id': '...', ...}
        2. Cliente em 'customer': {'page': 1, 'total': 1, 'customer': {...}}
        3. Cliente em 'customers' lista: {'customers': [{...}], 'page': 1, 'total': 1}
        
        Este método normaliza todas essas formas.
        
        Args:
            customer_id: ID do cliente no Dinabox
            
        Returns:
            DinaboxCustomerDetail com dados validados e normalizados
            
        Raises:
            DinaboxRequestError: Se a requisição falhar
            ValueError: Se o cliente não for encontrado ou formato inválido
        """
        payload = self.client.get_customer(customer_id=customer_id)
        
        if not isinstance(payload, dict):
            raise ValueError(f"Resposta inválida da API Dinabox: esperado dict, recebido {type(payload)}")
        
        # Extrai o cliente da resposta
        customer_data = None
        
        # Caso 1: Cliente está em 'customer' (chave singular)
        if "customer" in payload and isinstance(payload["customer"], dict):
            customer_data = payload["customer"]
        
        # Caso 2: Cliente está em 'customers' (lista)
        elif "customers" in payload and isinstance(payload["customers"], list):
            if payload["customers"]:
                customer_data = payload["customers"][0]
        
        # Caso 3: Os dados do cliente estão no nível raiz com paginação
        # Exemplo: {'page': 1, 'total': 1, 'customer_id': '...', 'customer_name': '...', ...}
        elif "customer_id" in payload or "customer_name" in payload:
            # Remove campos de paginação e metadados da resposta
            pagination_keys = {"page", "total", "quantity", "offset"}
            customer_data = {k: v for k, v in payload.items() if k not in pagination_keys}
        
        if not customer_data:
            # Log da estrutura para debug
            keys_preview = list(payload.keys())[:20]
            raise ValueError(
                f"Cliente {customer_id} não encontrado ou resposta em formato desconhecido. "
                f"Chaves na resposta: {keys_preview}"
            )
        
        # Garante que temos customer_id e customer_name
        if "customer_id" not in customer_data:
            customer_data["customer_id"] = customer_id
        
        if "customer_name" not in customer_data or not customer_data.get("customer_name"):
            raise ValueError(f"Resposta sem 'customer_name' válido para cliente {customer_id}")
        
        # Cria schema e valida
        try:
            schema = DinaboxCustomerDetail(**customer_data)
        except Exception as e:
            raise ValueError(f"Erro ao validar dados do cliente {customer_id}: {str(e)}")
        
        # Validação final: customer_id e customer_name devem estar preenchidos
        if not schema.customer_id or not schema.customer_name:
            raise ValueError(f"Cliente {customer_id} sem customer_id ou customer_name válidos após validação")
        
        return schema

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
        created = self.client.create_customer(
            customer_name=customer_name,
            customer_type=customer_type,
            customer_status=customer_status,
            customer_emails=customer_emails,
            customer_phones=customer_phones,
            customer_pf_data=customer_pf_data,
            customer_pj_data=customer_pj_data,
            customer_addresses=customer_addresses,
            customer_note=customer_note,
            custom_fields=custom_fields,
        )
        self.sync_customers_index(full_sync=False)
        return created

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
        updated = self.client.update_customer(
            customer_id=customer_id,
            customer_name=customer_name,
            customer_type=customer_type,
            customer_status=customer_status,
            customer_emails=customer_emails,
            customer_phones=customer_phones,
            customer_pf_data=customer_pf_data,
            customer_pj_data=customer_pj_data,
            customer_addresses=customer_addresses,
            customer_note=customer_note,
            custom_fields=custom_fields,
        )
        self.sync_customers_index(full_sync=False)
        return updated

    def delete_customer(self, customer_id: str) -> dict:
        deleted = self.client.delete_customer(customer_id=customer_id)
        DinaboxClienteIndex.objects.filter(customer_id=str(customer_id)).delete()
        return deleted

    def list_materials(self, page: int = 1, search: str | None = None, type_source: str = "dinabox") -> DinaboxMaterialListResponse:
        payload = self.client.get_materials(page=page, search=search, type_source=type_source)
        return DinaboxMaterialListResponse(**payload)

    def list_labels(self, page: int = 1, search: str | None = None) -> DinaboxLabelListResponse:
        payload = self.client.get_labels(page=page, search=search)
        return DinaboxLabelListResponse(**payload)

    def create_label(self, label_name: str, label_type: str, label_content: str = "") -> dict:
        return self.client.create_label(label_name=label_name, label_type=label_type, label_content=label_content)

    def delete_label(self, label_id: str) -> dict:
        return self.client.delete_label(label_id=label_id)

    def get_service_account_profile(self) -> tuple[dict, dict]:
        token_result = self.client.obter_token()
        profile = self.client.get_user_info()
        return profile, {
            "user_login": token_result.user_login,
            "user_display_name": token_result.user_display_name,
            "user_email": token_result.user_email,
            "expires_in": token_result.expires_in,
            "token_type": token_result.token_type,
            "token_preview": (token_result.token[:6] + "..." + token_result.token[-4:]) if len(token_result.token) >= 12 else "***",
        }

    @transaction.atomic
    def sync_customers_index(self, full_sync: bool = True, limit_pages: int | None = None) -> int:
        synced = 0
        page = 1
        total_pages: int | None = None

        while True:
            try:
                payload = self.client.get_customers(page=page)
            except DinaboxRequestError as exc:
                # A API retorna 404 quando nao ha clientes/pagina nao existe; nao eh erro de negocio.
                if "Erro na API Dinabox (404)" in str(exc):
                    break
                raise
            customers = payload.get("customers") or []
            total = int(payload.get("total") or 0)
            per_page = len(customers) if customers else 1
            total_pages = max(1, (total + per_page - 1) // per_page)

            for customer in customers:
                customer_id = str(customer.get("customer_id") or "").strip()
                if not customer_id:
                    continue
                DinaboxClienteIndex.objects.update_or_create(
                    customer_id=customer_id,
                    defaults={
                        "customer_name": str(customer.get("customer_name") or ""),
                        "customer_type": str(customer.get("customer_type") or ""),
                        "customer_status": str(customer.get("customer_status") or ""),
                        "customer_emails_text": str(customer.get("customer_emails") or ""),
                        "customer_phones_text": str(customer.get("customer_phones") or ""),
                        "raw_payload": customer,
                    },
                )
                synced += 1

            if not full_sync:
                break
            if limit_pages is not None and page >= limit_pages:
                break
            if total_pages is not None and page >= total_pages:
                break
            page += 1

        return synced

    def discover_capabilities(self) -> list[dict]:
        rows: list[dict] = []

        for item in DINABOX_CAPABILITIES:
            endpoint = item["endpoint"]
            options_meta = self.client.request_meta("OPTIONS", endpoint)
            get_meta = self.client.request_meta("GET", endpoint, params=item.get("sample_params") or {})

            methods = []
            args = []
            options_json = options_meta.get("json")
            if isinstance(options_json, dict):
                methods = options_json.get("methods") or []
                endpoints = options_json.get("endpoints") or []
                if endpoints and isinstance(endpoints, list):
                    first = endpoints[0]
                    if isinstance(first, dict):
                        args = list((first.get("args") or {}).keys())

            get_message = ""
            get_json = get_meta.get("json")
            if isinstance(get_json, dict):
                get_message = str(get_json.get("message") or get_json.get("code") or "")
            if not get_message:
                get_message = (get_meta.get("text") or "")[:120]

            rows.append(
                {
                    "nome": item["nome"],
                    "descricao": item["descricao"],
                    "endpoint": endpoint,
                    "methods": methods,
                    "args": args,
                    "options_status": options_meta.get("status"),
                    "get_status": get_meta.get("status"),
                    "get_message": get_message,
                }
            )

        return rows
