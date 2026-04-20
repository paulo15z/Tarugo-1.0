from __future__ import annotations

import json
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from pydantic import ValidationError

from apps.integracoes.dinabox.api_service import DinaboxApiService
from apps.integracoes.dinabox.client import DinaboxAPIClient, DinaboxAuthError, DinaboxRequestError
from apps.integracoes.models import DinaboxClienteIndex, DinaboxImportacaoProjeto, StatusImportacaoProjeto
from apps.integracoes.services_importacao import DinaboxImportacaoProjetoService
from collections import defaultdict
from datetime import datetime
from apps.integracoes.dinabox.parsers.project_detail import parse_project_detail


def _user_pode_testar_integracoes(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=["PCP", "TI", "Gestao", "GESTAO"]).exists()


def _user_pode_disparar_importacao_projetos(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=["PROJETOS", "Projetos", "TI", "Gestao", "GESTAO"]).exists()


def _token_disparo_projetos_valido(request: HttpRequest) -> bool:
    configured = str(getattr(settings, "DINABOX_PROJETOS_TRIGGER_TOKEN", "") or "").strip()
    if not configured:
        return False
    received = str(request.META.get("HTTP_X_TARUGO_TRIGGER_TOKEN", "") or "").strip()
    return bool(received) and received == configured


def _obter_servico_dinabox() -> DinaboxApiService:
    return DinaboxApiService()


def _coerce_page(raw_value) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return 1
    return value if value > 0 else 1


def _only_digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _normalize_json_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _normalize_json_list(value) -> list:
    return value if isinstance(value, list) else []


def _extract_payload_dict(request: HttpRequest) -> dict:
    content_type = str(request.content_type or "").lower()
    if "application/json" in content_type:
        raw = (request.body or b"").decode("utf-8").strip()
        if not raw:
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Payload JSON deve ser um objeto.")
        return parsed
    return {k: v for k, v in request.POST.items()}


def _build_customer_payload_from_request(request: HttpRequest) -> dict:
    nome = str(request.POST.get("customer_name", "")).strip()
    tipo = str(request.POST.get("customer_type", "pf")).strip().lower() or "pf"
    status = str(request.POST.get("customer_status", "on")).strip().lower() or "on"
    emails = str(request.POST.get("customer_emails", "")).strip() or None
    phones = str(request.POST.get("customer_phones", "")).strip() or None
    customer_note = str(request.POST.get("customer_note", "")).strip() or None

    cpf = _only_digits(str(request.POST.get("customer_cpf", "")).strip())
    cnpj = _only_digits(str(request.POST.get("customer_cnpj", "")).strip())

    endereco_cep = str(request.POST.get("address_zipcode", "")).strip()
    endereco_logradouro = str(request.POST.get("address_street", "")).strip()
    endereco_numero = str(request.POST.get("address_number", "")).strip()
    endereco_complemento = str(request.POST.get("address_complement", "")).strip()
    endereco_bairro = str(request.POST.get("address_district", "")).strip()
    endereco_cidade = str(request.POST.get("address_city", "")).strip()
    endereco_estado = str(request.POST.get("address_state", "")).strip()

    origem = str(request.POST.get("custom_origem", "comercial_tarugo")).strip()

    customer_pf_data = {"customer_cpf": cpf} if cpf else None
    customer_pj_data = {"customer_cnpj": cnpj} if cnpj else None

    address = {}
    if endereco_cep:
        address["zipcode"] = endereco_cep
    if endereco_logradouro:
        address["address"] = endereco_logradouro
    if endereco_numero:
        address["number"] = endereco_numero
    if endereco_complemento:
        address["complement"] = endereco_complemento
    if endereco_bairro:
        address["district"] = endereco_bairro
    if endereco_cidade:
        address["city"] = endereco_cidade
    if endereco_estado:
        address["state"] = endereco_estado

    customer_addresses = [address] if address else None
    custom_fields = {"origem": origem} if origem else None

    return {
        "customer_name": nome,
        "customer_type": tipo,
        "customer_status": status,
        "customer_emails": emails,
        "customer_phones": phones,
        "customer_pf_data": customer_pf_data,
        "customer_pj_data": customer_pj_data,
        "customer_addresses": customer_addresses,
        "customer_note": customer_note,
        "custom_fields": custom_fields,
    }


def _extract_customer_form_initial(customer: dict) -> dict:
    customer = customer or {}
    pf_data = _normalize_json_dict(customer.get("customer_pf_data"))
    pj_data = _normalize_json_dict(customer.get("customer_pj_data"))
    addresses = _normalize_json_list(customer.get("customer_addresses"))
    first_address = addresses[0] if addresses and isinstance(addresses[0], dict) else {}
    custom_fields = _normalize_json_dict(customer.get("custom_fields"))

    return {
        "customer_cpf": str(pf_data.get("customer_cpf") or ""),
        "customer_cnpj": str(pj_data.get("customer_cnpj") or ""),
        "address_zipcode": str(first_address.get("zipcode") or ""),
        "address_street": str(first_address.get("address") or ""),
        "address_number": str(first_address.get("number") or ""),
        "address_complement": str(first_address.get("complement") or ""),
        "address_district": str(first_address.get("district") or ""),
        "address_city": str(first_address.get("city") or ""),
        "address_state": str(first_address.get("state") or ""),
        "custom_origem": str(custom_fields.get("origem") or "comercial_tarugo"),
    }


@login_required
def dinabox_conectar(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    force_refresh = request.method == "POST"
    service = _obter_servico_dinabox()

    profile = {}
    auth = {}
    conectado = False
    erro = ""

    try:
        service.client.obter_token(force_refresh=force_refresh)
        profile, auth = service.get_service_account_profile()
        conectado = True
        if force_refresh:
            messages.success(request, "Token da conta tecnica Dinabox renovado com sucesso.")
    except DinaboxAuthError as exc:
        erro = str(exc)
        messages.error(request, f"Falha de autenticacao da conta tecnica Dinabox: {exc}")
    except DinaboxRequestError as exc:
        erro = str(exc)
        messages.error(request, f"Falha ao consultar perfil da conta tecnica Dinabox: {exc}")

    return render(
        request,
        "integracoes/dinabox/conectar.html",
        {
            "dinabox_conectado": conectado,
            "dinabox_profile": profile,
            "dinabox_auth": auth,
            "dinabox_error": erro,
        },
    )


@login_required
@require_POST
def dinabox_desconectar(request: HttpRequest):
    DinaboxAPIClient.invalidar_cache_global()
    messages.success(request, "Cache de token Dinabox limpo. A proxima chamada ira reautenticar.")
    return redirect("integracoes:dinabox-conectar")


@login_required
@require_POST
def dinabox_test_auth(request):
    if not _user_pode_testar_integracoes(request.user):
        return JsonResponse({"erro": "Somente PCP, TI, Gestao ou admin podem testar integracoes."}, status=403)

    force_refresh = str(request.POST.get("force_refresh", "")).strip().lower() in {"1", "true", "on", "sim"}

    try:
        service = _obter_servico_dinabox()
        token_result = service.client.obter_token(force_refresh=force_refresh)
        profile = service.client.get_user_info()
        token_preview = (token_result.token[:6] + "..." + token_result.token[-4:]) if len(token_result.token) >= 12 else "***"

        return JsonResponse(
            {
                "sucesso": True,
                "mensagem": "Autenticacao Dinabox (conta tecnica) realizada com sucesso.",
                "token_preview": token_preview,
                "expires_in": token_result.expires_in,
                "token_type": token_result.token_type,
                "user_login": token_result.user_login or profile.get("user_login"),
                "user_display_name": token_result.user_display_name or profile.get("user_display_name"),
                "user_email": token_result.user_email or profile.get("user_email"),
            }
        )
    except DinaboxAuthError as exc:
        return JsonResponse({"sucesso": False, "erro": str(exc)}, status=400)
    except DinaboxRequestError as exc:
        return JsonResponse({"sucesso": False, "erro": str(exc)}, status=502)


@login_required
def dinabox_capacidades(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()
    capabilities: list[dict] = []

    try:
        capabilities = service.discover_capabilities()
    except DinaboxAuthError as exc:
        messages.error(request, f"Falha de autenticacao da conta tecnica Dinabox: {exc}")
    except DinaboxRequestError as exc:
        messages.error(request, f"Falha ao extrair capacidades da API Dinabox: {exc}")

    return render(
        request,
        "integracoes/dinabox/capacidades.html",
        {
            "capabilities": capabilities,
        },
    )


@login_required
def dinabox_projetos_list(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()

    page = _coerce_page(request.GET.get("p", "1"))
    search = str(request.GET.get("s", "")).strip() or None
    status = str(request.GET.get("status", "")).strip() or None

    try:
        response = service.list_projects(page=page, search=search, status=status)
    except DinaboxAuthError as exc:
        messages.error(request, f"Falha de autenticacao da conta tecnica Dinabox: {exc}")
        return redirect("integracoes:dinabox-conectar")
    except DinaboxRequestError as exc:
        messages.error(request, f"Falha ao consultar projetos na Dinabox: {exc}")
        response = SimpleNamespace(projects=[], total=0, quantity=10, page=page)

    return render(
        request,
        "integracoes/dinabox/projetos_list.html",
        {
            "response": response,
            "search": search or "",
            "status": status or "",
        },
    )


@login_required
def dinabox_projeto_detail(request: HttpRequest, project_id: str):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()

    try:
        projeto = service.get_project_detail(project_id)
    except DinaboxAuthError as exc:
        messages.error(request, f"Falha de autenticacao da conta tecnica Dinabox: {exc}")
        return redirect("integracoes:dinabox-conectar")
    except DinaboxRequestError as exc:
        messages.error(request, f"Falha ao consultar projeto na Dinabox: {exc}")
        return redirect("integracoes:dinabox-projetos-list")

    return render(request, "integracoes/dinabox/projeto_detail.html", {"projeto": projeto})


@login_required
def dinabox_lotes_list(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()

    page = _coerce_page(request.GET.get("p", "1"))
    search = str(request.GET.get("s", "")).strip() or None

    try:
        response = service.list_groups(page=page, search=search)
    except DinaboxAuthError as exc:
        messages.error(request, f"Falha de autenticacao da conta tecnica Dinabox: {exc}")
        return redirect("integracoes:dinabox-conectar")
    except DinaboxRequestError as exc:
        messages.error(request, f"Falha ao consultar lotes na Dinabox: {exc}")
        response = SimpleNamespace(project_groups=[], total=0, page=page)

    return render(
        request,
        "integracoes/dinabox/lotes_list.html",
        {
            "response": response,
            "search": search or "",
        },
    )


@login_required
def dinabox_lote_detail(request: HttpRequest, group_id: str):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()

    try:
        lote = service.get_group_detail(group_id)
    except DinaboxAuthError as exc:
        messages.error(request, f"Falha de autenticacao da conta tecnica Dinabox: {exc}")
        return redirect("integracoes:dinabox-conectar")
    except DinaboxRequestError as exc:
        messages.error(request, f"Falha ao consultar lote na Dinabox: {exc}")
        return redirect("integracoes:dinabox-lotes-list")

    return render(request, "integracoes/dinabox/lote_detail.html", {"lote": lote})


@login_required
def dinabox_clientes_list(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()
    page = _coerce_page(request.GET.get("p", "1"))
    refresh = str(request.GET.get("refresh", "")).strip().lower() in {"1", "true", "on", "sim"}
    search = str(request.GET.get("s", "")).strip() or None

    try:
        if refresh or not DinaboxClienteIndex.objects.exists():
            synced = service.sync_customers_index(full_sync=True)
            if synced:
                messages.success(request, f"Indice local de clientes atualizado ({synced} registros sincronizados).")
            else:
                messages.info(request, "Indice de clientes atualizado. Nenhum cliente retornado pela API neste momento.")
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao sincronizar indice de clientes com Dinabox: {exc}")

    queryset = DinaboxClienteIndex.objects.all().order_by("customer_name_normalized")
    if search:
        search_norm = " ".join(search.lower().split())
        queryset = queryset.filter(
            Q(customer_name_normalized__icontains=search_norm)
            | Q(customer_emails_text__icontains=search)
            | Q(customer_phones_text__icontains=search)
            | Q(customer_id__icontains=search)
        )

    total = queryset.count()
    page_size = 50
    start = (page - 1) * page_size
    end = start + page_size
    rows = list(queryset[start:end])

    return render(
        request,
        "integracoes/dinabox/clientes_list.html",
        {
            "response": SimpleNamespace(customers=rows, total=total, page=page, page_size=page_size),
            "search": search or "",
        },
    )


@login_required
@require_POST
def dinabox_cliente_criar(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Sem permissao para criar clientes no Dinabox.")
        return redirect("integracoes:dinabox-clientes-list")

    payload = _build_customer_payload_from_request(request)
    nome = payload["customer_name"]

    if not nome:
        messages.error(request, "Nome do cliente e obrigatorio.")
        return redirect("integracoes:dinabox-clientes-list")

    try:
        service = _obter_servico_dinabox()
        result = service.create_customer(**payload)
        novo_id = result.get("new_id")
        if novo_id:
            messages.success(request, f"Cliente criado no Dinabox com ID {novo_id}.")
        else:
            messages.success(request, "Cliente enviado para criacao no Dinabox.")
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao criar cliente no Dinabox: {exc}")

    return redirect("integracoes:dinabox-clientes-list")


@login_required
def dinabox_cliente_detail(request: HttpRequest, customer_id: str):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Sem permissao para acessar detalhes de clientes no Dinabox.")
        return redirect("integracoes:dinabox-clientes-list")

    try:
        service = _obter_servico_dinabox()
        customer = service.get_customer_detail(customer_id=customer_id)
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao carregar cliente {customer_id}: {exc}")
        return redirect("integracoes:dinabox-clientes-list")

    return render(
        request,
        "integracoes/dinabox/cliente_detail.html",
        {
            "customer": customer,
            "customer_id": customer_id,
            "form_initial": _extract_customer_form_initial(customer),
        },
    )


@login_required
@require_POST
def dinabox_cliente_atualizar(request: HttpRequest, customer_id: str):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Sem permissao para atualizar clientes no Dinabox.")
        return redirect("integracoes:dinabox-clientes-list")

    payload = _build_customer_payload_from_request(request)
    nome = payload["customer_name"]

    if not nome:
        messages.error(request, "Nome do cliente e obrigatorio para atualizar.")
        return redirect("integracoes:dinabox-cliente-detail", customer_id=customer_id)

    try:
        service = _obter_servico_dinabox()
        service.update_customer(
            customer_id=customer_id,
            **payload,
        )
        messages.success(request, f"Cliente {customer_id} atualizado no Dinabox.")
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao atualizar cliente {customer_id}: {exc}")

    return redirect("integracoes:dinabox-cliente-detail", customer_id=customer_id)


@login_required
@require_POST
def dinabox_cliente_excluir(request: HttpRequest, customer_id: str):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Sem permissao para excluir clientes no Dinabox.")
        return redirect("integracoes:dinabox-clientes-list")

    try:
        service = _obter_servico_dinabox()
        service.delete_customer(customer_id=customer_id)
        messages.success(request, f"Cliente {customer_id} excluido no Dinabox.")
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao excluir cliente {customer_id}: {exc}")

    return redirect("integracoes:dinabox-clientes-list")


@login_required
def dinabox_materiais_list(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()
    page = _coerce_page(request.GET.get("p", "1"))
    search = str(request.GET.get("s", "")).strip() or None
    tipo = str(request.GET.get("type", "dinabox")).strip().lower()
    if tipo not in {"dinabox", "user"}:
        tipo = "dinabox"

    try:
        response = service.list_materials(page=page, search=search, type_source=tipo)
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao consultar materiais na Dinabox: {exc}")
        response = SimpleNamespace(materials=[], total=0, page=page)

    return render(
        request,
        "integracoes/dinabox/materiais_list.html",
        {
            "response": response,
            "search": search or "",
            "type_source": tipo,
        },
    )


@login_required
def dinabox_etiquetas_list(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()
    page = _coerce_page(request.GET.get("p", "1"))
    search = str(request.GET.get("s", "")).strip() or None

    try:
        response = service.list_labels(page=page, search=search)
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao consultar etiquetas na Dinabox: {exc}")
        response = SimpleNamespace(labels=[], total=0, page=page)

    return render(
        request,
        "integracoes/dinabox/etiquetas_list.html",
        {
            "response": response,
            "search": search or "",
        },
    )


@login_required
@require_POST
def dinabox_etiqueta_criar(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Sem permissao para criar etiquetas no Dinabox.")
        return redirect("integracoes:dinabox-etiquetas-list")

    label_name = str(request.POST.get("label_name", "")).strip()
    label_type = str(request.POST.get("label_type", "part")).strip().lower()
    label_content = str(request.POST.get("label_content", "")).strip()

    if label_type not in {"part", "scrap", "thickened", "input", "volume"}:
        messages.error(request, "Tipo de etiqueta invalido.")
        return redirect("integracoes:dinabox-etiquetas-list")

    if not label_name:
        messages.error(request, "Nome da etiqueta e obrigatorio.")
        return redirect("integracoes:dinabox-etiquetas-list")

    try:
        service = _obter_servico_dinabox()
        result = service.create_label(label_name=label_name, label_type=label_type, label_content=label_content)
        novo_id = result.get("new_id")
        if novo_id:
            messages.success(request, f"Etiqueta criada no Dinabox com ID {novo_id}.")
        else:
            messages.success(request, "Etiqueta criada no Dinabox.")
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao criar etiqueta no Dinabox: {exc}")

    return redirect("integracoes:dinabox-etiquetas-list")


@login_required
@require_POST
def dinabox_etiqueta_excluir(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Sem permissao para excluir etiquetas no Dinabox.")
        return redirect("integracoes:dinabox-etiquetas-list")

    label_id = str(request.POST.get("label_id", "")).strip()
    if not label_id:
        messages.error(request, "ID da etiqueta e obrigatorio.")
        return redirect("integracoes:dinabox-etiquetas-list")

    try:
        service = _obter_servico_dinabox()
        service.delete_label(label_id=label_id)
        messages.success(request, f"Etiqueta {label_id} excluida no Dinabox.")
    except (DinaboxAuthError, DinaboxRequestError) as exc:
        messages.error(request, f"Falha ao excluir etiqueta no Dinabox: {exc}")

    return redirect("integracoes:dinabox-etiquetas-list")


@login_required
def dinabox_projeto_modulos_pecas(request: HttpRequest, project_id: str):
    """
    Visualiza módulos e peças de um projeto Dinabox.
    Busca detalhes via `DinaboxApiService` e tenta extrair todas as peças
    buscando dentro de `woodwork` (fallback para estrutura vazia).
    """
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a integracao Dinabox.")
        return redirect("estoque:lista_produtos")

    service = _obter_servico_dinabox()

    try:
        detail = service.get_project_detail(project_id)
    except DinaboxAuthError as exc:
        messages.error(request, f"Falha de autenticacao da conta tecnica Dinabox: {exc}")
        return redirect("integracoes:dinabox-conectar")
    except DinaboxRequestError as exc:
        messages.error(request, f"Falha ao consultar projeto na Dinabox: {exc}")
        return redirect("integracoes:dinabox-projetos-list")

    # Usar parser dedicado para normalizar o detail em pecas/modulos
    parsed = parse_project_detail(detail)

    projeto = {
        "projeto": {"id": getattr(detail, "project_id", project_id), "nome": getattr(detail, "project_description", None) or ""},
        "cliente": {"nome": parsed.get("cliente", {}).get("nome", getattr(detail, "project_customer_name", "") or "")},
        "pecas": parsed.get("pecas", []),
        "modulos": parsed.get("modulos", []),
        "insumos": [],
        "chapas": [],
        "metadata": parsed.get("metadata", {}),
    }

    if not projeto["pecas"]:
        messages.info(request, "Nenhuma peça encontrada no projeto Dinabox (payload não continha peças reconhecíveis).")

    materiais_unicos = sorted({p["material"] for p in projeto["pecas"] if p.get("material")})

    return render(
        request,
        "integracoes/dinabox/projeto_modulos_pecas.html",
        {
            "projeto": projeto,
            "materiais_unicos": list(materiais_unicos),
        },
    )


@login_required
def dinabox_importacoes_list(request: HttpRequest):
    if not _user_pode_testar_integracoes(request.user):
        messages.error(request, "Somente PCP, TI, Gestao ou admin podem acessar a fila Dinabox.")
        return redirect("estoque:lista_produtos")

    status = str(request.GET.get("status", "")).strip().upper()
    search = str(request.GET.get("q", "")).strip()

    queryset = DinaboxImportacaoProjeto.objects.all().order_by("status", "prioridade", "-criado_em")
    if status in StatusImportacaoProjeto.values:
        queryset = queryset.filter(status=status)
    else:
        status = ""

    if search:
        queryset = queryset.filter(
            Q(project_id__icontains=search)
            | Q(project_customer_id__icontains=search)
            | Q(project_description__icontains=search)
            | Q(origem__icontains=search)
        )

    summary_counts = {
        item["status"]: item["total"]
        for item in DinaboxImportacaoProjeto.objects.values("status").annotate(total=Count("id"))
    }
    status_summary = [
        {"value": value, "label": label, "total": summary_counts.get(value, 0)}
        for value, label in StatusImportacaoProjeto.choices
    ]

    return render(
        request,
        "integracoes/dinabox/importacoes_list.html",
        {
            "rows": list(queryset[:100]),
            "search": search,
            "status": status,
            "status_choices": StatusImportacaoProjeto.choices,
            "status_summary": status_summary,
            "total_rows": queryset.count(),
        },
    )


@csrf_exempt
@require_POST
def dinabox_enfileirar_projeto_concluido(request: HttpRequest):
    permitido_por_token = _token_disparo_projetos_valido(request)
    permitido_por_usuario = _user_pode_disparar_importacao_projetos(getattr(request, "user", None))
    if not (permitido_por_token or permitido_por_usuario):
        return JsonResponse(
            {
                "sucesso": False,
                "erro": "Nao autorizado para enfileirar importacao de projeto concluido.",
            },
            status=403,
        )

    try:
        payload = _extract_payload_dict(request)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        return JsonResponse({"sucesso": False, "erro": str(exc)}, status=400)

    try:
        item = DinaboxImportacaoProjetoService.enfileirar_importacao_por_evento(payload)
    except ValidationError as exc:
        return JsonResponse(
            {"sucesso": False, "erro": "Payload invalido.", "detalhes": exc.errors()},
            status=400,
        )
    except ValueError as exc:
        return JsonResponse({"sucesso": False, "erro": str(exc)}, status=400)

    return JsonResponse(
        {
            "sucesso": True,
            "importacao": {
                "id": item.pk,
                "project_id": item.project_id,
                "project_customer_id": item.project_customer_id,
                "project_description": item.project_description,
                "status": item.status,
                "origem": item.origem,
                "prioridade": item.prioridade,
            },
        },
        status=202,
    )
