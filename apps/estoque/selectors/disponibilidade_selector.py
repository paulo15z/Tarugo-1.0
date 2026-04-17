from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.estoque.domain.tipos import FamiliaProduto
from apps.estoque.models import Movimentacao, Produto, Reserva, SaldoMDF


def get_espessuras_operacionais(produto: Produto) -> list[int]:
    """Define quais espessuras devem ser consideradas para o produto MDF."""
    if produto.categoria.familia != FamiliaProduto.MDF:
        return []

    atributos = produto.atributos_especificos or {}
    esp_atributo = atributos.get("espessura")
    try:
        esp_unica = int(esp_atributo) if esp_atributo is not None else None
    except (TypeError, ValueError):
        esp_unica = None

    if esp_unica:
        return [esp_unica]

    return sorted(set(produto.saldos_mdf.values_list("espessura", flat=True)))


def get_saldo_fisico(produto: Produto, espessura: int | None = None) -> int:
    familia = produto.categoria.familia
    if familia == FamiliaProduto.MDF:
        if espessura is None:
            return (
                SaldoMDF.objects.filter(produto=produto).aggregate(total=Sum("quantidade")).get("total")
                or 0
            )
        saldo = SaldoMDF.objects.filter(produto=produto, espessura=espessura).first()
        return saldo.quantidade if saldo else 0
    return int(produto.quantidade or 0)


def get_saldo_reservado(produto: Produto, espessura: int | None = None) -> int:
    reservas = Reserva.objects.filter(produto=produto, status="ativa")
    if espessura is not None:
        reservas = reservas.filter(espessura=espessura)
    return reservas.aggregate(total=Sum("quantidade")).get("total") or 0


def get_saldo_disponivel(produto: Produto, espessura: int | None = None) -> int:
    saldo_fisico = get_saldo_fisico(produto, espessura=espessura)
    saldo_reservado = get_saldo_reservado(produto, espessura=espessura)
    return max(0, saldo_fisico - saldo_reservado)


def get_disponibilidade_por_produto(produto: Produto, espessura: int | None = None) -> dict:
    saldo_fisico = get_saldo_fisico(produto, espessura=espessura)
    saldo_reservado = get_saldo_reservado(produto, espessura=espessura)
    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "sku": produto.sku,
        "familia": produto.categoria.familia,
        "espessura": espessura,
        "saldo_fisico": saldo_fisico,
        "saldo_reservado": saldo_reservado,
        "saldo_disponivel": max(0, saldo_fisico - saldo_reservado),
    }


def get_disponibilidade_resumida(produto: Produto) -> dict:
    if produto.categoria.familia == FamiliaProduto.MDF:
        por_espessura = []
        for esp in get_espessuras_operacionais(produto):
            por_espessura.append(get_disponibilidade_por_produto(produto, espessura=esp))
        return {
            "produto_id": produto.id,
            "familia": produto.categoria.familia,
            "saldo_fisico": sum(item["saldo_fisico"] for item in por_espessura),
            "saldo_reservado": sum(item["saldo_reservado"] for item in por_espessura),
            "saldo_disponivel": sum(item["saldo_disponivel"] for item in por_espessura),
            "por_espessura": por_espessura,
        }

    base = get_disponibilidade_por_produto(produto)
    return {
        "produto_id": produto.id,
        "familia": produto.categoria.familia,
        "saldo_fisico": base["saldo_fisico"],
        "saldo_reservado": base["saldo_reservado"],
        "saldo_disponivel": base["saldo_disponivel"],
        "por_espessura": [],
    }


def listar_reservas_por_lote(lote_pcp_id: str):
    """Retorna reservas ordenadas do lote solicitado (importante para PCP)."""
    return Reserva.objects.select_related("produto").filter(lote_pcp_id=lote_pcp_id).order_by("-criado_em")


def get_comprometimento_por_lote(lote_pcp_id: str, status: str = "ativa") -> list[dict]:
    """Agrupa o que está comprometido por produto/espessura dentro de um lote PCP."""
    qs = Reserva.objects.filter(lote_pcp_id=lote_pcp_id, status=status)
    agregados = (
        qs.values("produto_id", "produto__nome", "espessura")
        .annotate(quantidade=Sum("quantidade"))
        .order_by("produto_id", "espessura")
    )
    return [
        {
            "produto_id": item["produto_id"],
            "produto_nome": item["produto__nome"],
            "espessura": item["espessura"],
            "quantidade": item["quantidade"],
        }
        for item in agregados
    ]


def get_sinais_operacionais(dias: int = 30) -> list[dict]:
    """
    Consolida sinais de risco por item operacional (produto/espessura).
    Regras simples e transparentes para apoiar decisao de reposicao.
    """
    dias_validos = max(7, min(120, int(dias or 30)))
    janela_inicio = timezone.now() - timedelta(days=dias_validos)

    consumo_qs = (
        Movimentacao.objects
        .filter(tipo="saida", criado_em__gte=janela_inicio)
        .values("produto_id", "espessura")
        .annotate(total_consumo=Sum("quantidade"))
    )
    consumo_map = {
        (item["produto_id"], item["espessura"]): int(item["total_consumo"] or 0)
        for item in consumo_qs
    }

    sinais: list[dict] = []
    produtos = Produto.objects.select_related("categoria").filter(ativo=True).order_by("nome")

    for produto in produtos:
        if produto.categoria.familia == FamiliaProduto.MDF:
            espessuras = get_espessuras_operacionais(produto)
            if not espessuras:
                continue
            for esp in espessuras:
                sinais.append(_construir_sinal(produto, esp, consumo_map, dias_validos))
        else:
            sinais.append(_construir_sinal(produto, None, consumo_map, dias_validos))

    sinais.sort(key=lambda item: item["prioridade"], reverse=True)
    return sinais


def get_necessidades_reposicao(dias: int = 30) -> list[dict]:
    """
    Lista de reposicao manual baseada em minimo + comprometimento + saldo fisico.
    """
    necessidades: list[dict] = []

    for sinal in get_sinais_operacionais(dias=dias):
        minimo = int(sinal["estoque_minimo"] or 0)
        reservado = int(sinal["saldo_reservado"] or 0)
        fisico = int(sinal["saldo_fisico"] or 0)

        alvo = max(minimo, reservado)
        sugerido = max(0, alvo - fisico)
        if sugerido <= 0 and not sinal["risco_ruptura"]:
            continue

        necessidades.append(
            {
                **sinal,
                "quantidade_sugerida": sugerido,
                "alvo_recomendado": alvo,
            }
        )

    necessidades.sort(
        key=lambda item: (
            item["quantidade_sugerida"],
            item["prioridade"],
        ),
        reverse=True,
    )
    return necessidades


def get_risco_ruptura_por_lote(lote_pcp_id: str, dias: int = 30) -> dict:
    """
    Avalia o comprometimento do lote contra disponibilidade atual e cobertura.
    """
    comprometimentos = get_comprometimento_por_lote(lote_pcp_id=lote_pcp_id, status="ativa")
    if not comprometimentos:
        return {
            "lote_pcp_id": lote_pcp_id,
            "risco_ruptura": False,
            "itens_criticos": [],
            "itens": [],
        }

    produto_ids = {item["produto_id"] for item in comprometimentos}
    produtos_map = Produto.objects.select_related("categoria").in_bulk(produto_ids)

    sinais = get_sinais_operacionais(dias=dias)
    sinais_map = {(item["produto_id"], item["espessura"]): item for item in sinais}

    itens = []
    for compromisso in comprometimentos:
        produto_id = compromisso["produto_id"]
        espessura = compromisso["espessura"]
        quantidade_comprometida = int(compromisso["quantidade"] or 0)
        produto = produtos_map.get(produto_id)
        if not produto:
            continue

        sinal = sinais_map.get((produto_id, espessura))
        if not sinal:
            sinal = _construir_sinal(
                produto=produto,
                espessura=espessura,
                consumo_map={},
                dias=max(7, min(120, int(dias or 30))),
            )

        ruptura_imediata = int(sinal["saldo_disponivel"] or 0) < quantidade_comprometida
        risco_item = bool(ruptura_imediata or sinal["risco_ruptura"])

        itens.append(
            {
                "produto_id": produto_id,
                "produto_nome": compromisso["produto_nome"],
                "espessura": espessura,
                "quantidade_comprometida": quantidade_comprometida,
                "saldo_disponivel": sinal["saldo_disponivel"],
                "saldo_reservado": sinal["saldo_reservado"],
                "cobertura_dias": sinal["cobertura_dias"],
                "risco_item": risco_item,
                "ruptura_imediata": ruptura_imediata,
            }
        )

    itens_criticos = [item for item in itens if item["risco_item"]]

    return {
        "lote_pcp_id": lote_pcp_id,
        "risco_ruptura": len(itens_criticos) > 0,
        "itens_criticos": itens_criticos,
        "itens": itens,
    }


def _construir_sinal(produto: Produto, espessura: int | None, consumo_map: dict, dias: int) -> dict:
    disponibilidade = get_disponibilidade_por_produto(produto, espessura=espessura)

    chave_consumo = (produto.id, espessura)
    consumo_total = int(consumo_map.get(chave_consumo, 0))
    consumo_medio_dia = round(consumo_total / dias, 2) if dias > 0 else 0.0

    saldo_disponivel = int(disponibilidade["saldo_disponivel"] or 0)
    saldo_fisico = int(disponibilidade["saldo_fisico"] or 0)
    saldo_reservado = int(disponibilidade["saldo_reservado"] or 0)
    minimo = int(produto.estoque_minimo or 0)

    if consumo_medio_dia > 0:
        cobertura_dias = round(saldo_disponivel / consumo_medio_dia, 1)
    else:
        cobertura_dias = None

    risco_ruptura = saldo_disponivel <= minimo or saldo_disponivel <= 0
    if cobertura_dias is not None and cobertura_dias <= 7:
        risco_ruptura = True

    prioridade = 0
    if risco_ruptura:
        prioridade += 100
    if saldo_disponivel <= 0:
        prioridade += 80
    prioridade += min(50, saldo_reservado)
    prioridade += min(40, int(consumo_medio_dia * 10))

    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "sku": produto.sku,
        "familia": produto.categoria.familia,
        "espessura": espessura,
        "estoque_minimo": minimo,
        "saldo_fisico": saldo_fisico,
        "saldo_reservado": saldo_reservado,
        "saldo_disponivel": saldo_disponivel,
        "consumo_total_periodo": consumo_total,
        "consumo_medio_dia": consumo_medio_dia,
        "cobertura_dias": cobertura_dias,
        "risco_ruptura": risco_ruptura,
        "prioridade": prioridade,
    }
