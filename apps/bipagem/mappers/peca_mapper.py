from apps.bipagem.schemas.bipagem_schema import PecaOutput
from apps.bipagem.domain.tipos import get_nome_setor

def map_peca_to_output(peca) -> PecaOutput:
    return PecaOutput(
        id_peca=peca.id_peca,
        descricao=peca.descricao,
        status=peca.status,
        local=peca.local,
        material=peca.material,
        quantidade=peca.quantidade,
        roteiro=peca.roteiro,
        plano_corte=peca.plano_corte,
        setor_destino=get_nome_setor(peca.plano_corte),
        numero_lote_pcp=peca.numero_lote_pcp,
        data_bipagem=peca.data_bipagem,
        pedido_numero=peca.modulo.ordem_producao.pedido.numero_pedido if peca.modulo and peca.modulo.ordem_producao and peca.modulo.ordem_producao.pedido else None,
        modulo_nome=peca.modulo.nome_modulo if peca.modulo else None
    )
