import json
import re
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.estoque.domain.tipos import FamiliaProduto
from apps.estoque.models import Produto, Reserva
from apps.estoque.models.categoria import CategoriaProduto
from apps.estoque.permissions import grupo_requerido, pode_cadastrar_estoque, pode_movimentar_estoque
from apps.estoque.selectors.disponibilidade_selector import (
    get_disponibilidade_resumida,
    get_necessidades_reposicao,
    get_sinais_operacionais,
)
from apps.estoque.selectors.produto_selector import ProdutoSelector
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.estoque.services.produto_service import ProdutoService
from apps.estoque.services.reserva_service import ReservaService


@login_required
def lista_produtos(request):
    q = (request.GET.get("q") or "").strip()
    familia = (request.GET.get("familia") or "").strip()
    status = (request.GET.get("status") or "").strip()

    produtos = ProdutoSelector.get_all_produtos().select_related("categoria").prefetch_related("saldos_mdf")
    if q:
        produtos = produtos.filter(
            Q(nome__icontains=q)
            | Q(sku__icontains=q)
            | Q(categoria__nome__icontains=q)
        )
    if familia:
        produtos = produtos.filter(categoria__familia=familia)

    produto_rows = []
    for produto in produtos:
        disponibilidade = get_disponibilidade_resumida(produto)
        if produto.categoria.familia == FamiliaProduto.MDF:
            critico = any(
                item["saldo_reservado"] > 0 and item["saldo_disponivel"] <= produto.estoque_minimo
                for item in disponibilidade["por_espessura"]
            )
        else:
            critico = disponibilidade["saldo_disponivel"] <= produto.estoque_minimo
        produto_rows.append(
            {
                "produto": produto,
                "disponibilidade": disponibilidade,
                "critico": critico,
            }
        )

    if status == "critico":
        produto_rows = [row for row in produto_rows if row["critico"]]
    elif status == "ok":
        produto_rows = [row for row in produto_rows if not row["critico"]]

    mdf_groups: dict[tuple, dict] = {}
    display_rows = []

    for row in produto_rows:
        produto = row["produto"]
        disponibilidade = row["disponibilidade"]
        critico = row["critico"]

        if produto.categoria.familia != FamiliaProduto.MDF:
            display_rows.append(
                {
                    "kind": "single",
                    "produto": produto,
                    "disponibilidade": disponibilidade,
                    "critico": critico,
                }
            )
            continue

        atributos = produto.atributos_especificos or {}
        marca = str(atributos.get("marca") or atributos.get("fabricante") or "").strip()
        acabamento = str(atributos.get("padrao") or atributos.get("acabamento") or "").strip()
        if acabamento:
            nome_grupo = f"MDF {acabamento}" + (f" ({marca})" if marca else "")
            # Agrupamento operacional por acabamento (marca + padrao/acabamento).
            # Nao separar por "linha" para evitar duplicidade visual.
            chave_grupo = (
                produto.categoria_id,
                marca.lower(),
                acabamento.lower(),
            )
        else:
            nome_base = re.sub(r"\b\d+\s*mm\b", "", produto.nome, flags=re.IGNORECASE).strip()
            nome_grupo = nome_base or produto.nome
            chave_grupo = (produto.categoria_id, nome_grupo.lower())

        if chave_grupo not in mdf_groups:
            mdf_groups[chave_grupo] = {
                "kind": "mdf_group",
                "nome_exibicao": nome_grupo,
                "sku_exibicao": marca or produto.sku,
                "familia": produto.categoria.familia,
                "chips_map": {},
                "critico": False,
                "minimo": produto.estoque_minimo,
            }

        grupo = mdf_groups[chave_grupo]
        grupo["critico"] = grupo["critico"] or critico
        grupo["minimo"] = max(grupo["minimo"], produto.estoque_minimo)

        for item in disponibilidade["por_espessura"]:
            esp = item["espessura"]
            if esp not in grupo["chips_map"]:
                grupo["chips_map"][esp] = {
                    "espessura": esp,
                    "saldo_disponivel": 0,
                    "saldo_fisico": 0,
                    "saldo_reservado": 0,
                    "produto_nomes": set(),
                }
            chip = grupo["chips_map"][esp]
            chip["saldo_disponivel"] += int(item["saldo_disponivel"] or 0)
            chip["saldo_fisico"] += int(item["saldo_fisico"] or 0)
            chip["saldo_reservado"] += int(item["saldo_reservado"] or 0)
            chip["produto_nomes"].add(produto.nome)

    for grupo in mdf_groups.values():
        chips = []
        for chip in grupo["chips_map"].values():
            chip["produto_nome"] = " | ".join(sorted(chip["produto_nomes"]))
            chip.pop("produto_nomes", None)
            chips.append(chip)
        chips.sort(key=lambda chip: chip["espessura"])
        grupo["chips"] = chips
        grupo.pop("chips_map", None)
        display_rows.append(grupo)

    display_rows.sort(key=lambda row: (row["nome_exibicao"] if row["kind"] == "mdf_group" else row["produto"].nome))
    produtos_criticos_count = sum(1 for row in display_rows if row["critico"])

    pode_movimentar = pode_movimentar_estoque(request.user)
    pode_cadastrar = pode_cadastrar_estoque(request.user)

    return render(
        request,
        "estoque/lista_produtos.html",
        {
            "produtos": produtos,
            "produto_rows": produto_rows,
            "display_rows": display_rows,
            "produtos_criticos_count": produtos_criticos_count,
            "pode_movimentar": pode_movimentar,
            "pode_cadastrar": pode_cadastrar,
            "FAMILIA_MDF": FamiliaProduto.MDF,
            "familias_disponiveis": [choice[0] for choice in FamiliaProduto.choices()],
            "query_q": q,
            "query_familia": familia,
            "query_status": status,
        },
    )


@grupo_requerido("estoque.movimentar")
def movimentacao_create(request):
    if request.method == "POST":
        try:
            data = {
                "produto_id": int(request.POST["produto_id"]),
                "tipo": request.POST["tipo"],
                "quantidade": int(request.POST["quantidade"]),
                "espessura": request.POST.get("espessura") or None,
                "observacao": request.POST.get("observacao") or None,
            }

            if data["espessura"]:
                data["espessura"] = int(data["espessura"])

            MovimentacaoService.processar_movimentacao(data, usuario=request.user)
            messages.success(request, "Movimentacao registrada com sucesso!")
            return redirect("estoque:lista_produtos")
        except Exception as exc:
            messages.error(request, str(exc))

    produtos = ProdutoSelector.get_all_produtos().select_related("categoria")
    return render(
        request,
        "estoque/movimentacao_form.html",
        {
            "produtos": produtos,
            "FAMILIA_MDF": FamiliaProduto.MDF,
        },
    )


@grupo_requerido("estoque.cadastrar")
def produto_create(request):
    if request.method == "POST":
        try:
            atributos_raw = request.POST.get("atributos_especificos", "{}")
            try:
                atributos = json.loads(atributos_raw)
            except Exception:
                atributos = {}

            data = {
                "nome": request.POST.get("nome", "").strip(),
                "sku": request.POST.get("sku", "").strip().upper(),
                "categoria_id": int(request.POST.get("categoria_id")),
                "unidade_medida": request.POST.get("unidade_medida"),
                "estoque_minimo": int(request.POST.get("estoque_minimo", 0)),
                "preco_custo": float(request.POST.get("preco_custo")) if request.POST.get("preco_custo") else None,
                "lote": request.POST.get("lote", "").strip() or None,
                "localizacao": request.POST.get("localizacao", "").strip() or None,
                "atributos_especificos": atributos,
            }

            produto = ProdutoService.criar_produto(data)
            messages.success(request, f'Produto "{produto.nome}" ({produto.sku}) cadastrado com sucesso!')
            return redirect("estoque:lista_produtos")

        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Erro inesperado ao cadastrar produto: {exc}")

    categorias = CategoriaProduto.objects.all().order_by("ordem", "nome")
    return render(request, "estoque/produto_form.html", {"categorias": categorias})


@login_required
def lista_reservas(request):
    reservas = Reserva.objects.select_related("produto", "produto__categoria").all()
    return render(
        request,
        "estoque/lista_reservas.html",
        {
            "reservas": reservas,
            "FAMILIA_MDF": FamiliaProduto.MDF,
        },
    )


@grupo_requerido("estoque.movimentar")
def reserva_create(request):
    if request.method == "POST":
        try:
            data = {
                "produto_id": int(request.POST.get("produto_id")),
                "quantidade": int(request.POST.get("quantidade")),
                "espessura": int(request.POST.get("espessura")) if request.POST.get("espessura") else None,
                "referencia_externa": request.POST.get("referencia_externa") or None,
                "lote_pcp_id": request.POST.get("lote_pcp_id") or None,
                "modulo_id": request.POST.get("modulo_id") or None,
                "ambiente": request.POST.get("ambiente") or None,
                "origem_externa": request.POST.get("origem_externa") or "pcp",
                "observacao": request.POST.get("observacao"),
            }
            ReservaService.criar_reserva(data, usuario=request.user)
            messages.success(request, "Reserva criada com sucesso!")
            return redirect("estoque:lista_reservas")
        except ValidationError as exc:
            messages.error(request, f"Erro de validacao: {exc}")
        except Exception as exc:
            messages.error(request, f"Erro inesperado ao criar reserva: {exc}")

    produtos = Produto.objects.select_related("categoria").prefetch_related("saldos_mdf").all()
    return render(
        request,
        "estoque/reserva_form.html",
        {
            "produtos": produtos,
            "FAMILIA_MDF": FamiliaProduto.MDF,
        },
    )


@grupo_requerido("estoque.movimentar")
def reserva_consumir(request, reserva_id):
    if request.method == "POST":
        try:
            ReservaService.consumir_reserva(reserva_id, usuario=request.user)
            messages.success(request, "Reserva consumida com sucesso.")
        except Exception as exc:
            messages.error(request, f"Erro ao consumir reserva: {exc}")
    return redirect("estoque:lista_reservas")


@grupo_requerido("estoque.movimentar")
def reserva_cancelar(request, reserva_id):
    if request.method == "POST":
        try:
            ReservaService.cancelar_reserva(reserva_id, usuario=request.user)
            messages.success(request, "Reserva cancelada com sucesso.")
        except Exception as exc:
            messages.error(request, f"Erro ao cancelar reserva: {exc}")
    return redirect("estoque:lista_reservas")


@grupo_requerido("estoque.cadastrar")
def produto_config_update(request, produto_id):
    if request.method == "POST":
        try:
            espessura = int(request.POST.get("espessura"))
            estoque_minimo = int(request.POST.get("estoque_minimo"))
            preco_custo = Decimal(request.POST.get("preco_custo")) if request.POST.get("preco_custo") else None

            ProdutoService.atualizar_configuracoes_mdf(
                produto_id=produto_id,
                espessura=espessura,
                estoque_minimo=estoque_minimo,
                preco_custo=preco_custo,
            )
            messages.success(request, "Configuracoes atualizadas com sucesso!")
        except Exception as exc:
            messages.error(request, f"Erro ao atualizar: {exc}")

    return redirect("estoque:lista_produtos")


@login_required
def dashboard_operacional(request):
    dias = int(request.GET.get("dias", 30) or 30)
    dias = max(7, min(120, dias))
    familia = (request.GET.get("familia") or "").strip()
    apenas_risco = (request.GET.get("apenas_risco") or "").strip() in {"1", "true", "on", "sim"}

    sinais = get_sinais_operacionais(dias=dias)
    necessidades = get_necessidades_reposicao(dias=dias)

    if familia:
        sinais = [item for item in sinais if item.get("familia") == familia]
        necessidades = [item for item in necessidades if item.get("familia") == familia]

    if apenas_risco:
        sinais = [item for item in sinais if item.get("risco_ruptura")]

    riscos_altos = [item for item in sinais if item["risco_ruptura"]]

    return render(
        request,
        "estoque/dashboard_operacional.html",
        {
            "dias": dias,
            "familia": familia,
            "apenas_risco": apenas_risco,
            "sinais": sinais[:120],
            "necessidades": necessidades[:60],
            "riscos_altos": riscos_altos[:60],
            "pode_movimentar": pode_movimentar_estoque(request.user),
            "pode_cadastrar": pode_cadastrar_estoque(request.user),
            "total_itens_monitorados": len(sinais),
            "total_riscos_altos": len(riscos_altos),
            "total_necessidades": len(necessidades),
            "familias_disponiveis": [choice[0] for choice in FamiliaProduto.choices()],
        },
    )
