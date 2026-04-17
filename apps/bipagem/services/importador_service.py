from django.db import transaction

from apps.bipagem.models import (
    Pedido,
    OrdemProducao,
    Modulo,
    Peca
)

from apps.bipagem.schemas.importador_schema import (
    ImportacaoInput,
    ImportacaoOutput
)

from apps.bipagem.mappers.importador_mapper import (
    map_linha_to_peca_data
)


def importar_csv(data: dict) -> dict:

    # 🔹 validação Pydantic
    try:
        payload = ImportacaoInput(**data)
    except Exception:
        return ImportacaoOutput(
            sucesso=False,
            erro="CSV inválido"
        ).dict()

    try:
        with transaction.atomic():

            pedidos_map = {}
            ordens_map = {}
            modulos_map = {}

            total_pecas = 0

            for linha in payload.linhas:

                # 🧱 PEDIDO
                if linha.pedido not in pedidos_map:
                    pedido_obj, _ = Pedido.objects.get_or_create(
                        codigo=linha.pedido
                    )
                    pedidos_map[linha.pedido] = pedido_obj

                pedido = pedidos_map[linha.pedido]

                # 🧱 ORDEM
                ordem_key = (linha.pedido, linha.ordem)

                if ordem_key not in ordens_map:
                    ordem_obj, _ = OrdemProducao.objects.get_or_create(
                        codigo=linha.ordem,
                        pedido=pedido
                    )
                    ordens_map[ordem_key] = ordem_obj

                ordem = ordens_map[ordem_key]

                # 🧱 MODULO
                modulo_key = (linha.pedido, linha.ordem, linha.modulo)

                if modulo_key not in modulos_map:
                    modulo_obj, _ = Modulo.objects.get_or_create(
                        nome=linha.modulo,
                        ordem_producao=ordem
                    )
                    modulos_map[modulo_key] = modulo_obj

                modulo = modulos_map[modulo_key]

                # 🧱 PEÇA
                peca_data = map_linha_to_peca_data(linha)

                Peca.objects.create(
                    modulo=modulo,
                    **peca_data
                )

                total_pecas += 1

            return ImportacaoOutput(
                sucesso=True,
                total_pecas=total_pecas,
                pedidos_criados=len(pedidos_map)
            ).dict()

    except Exception:
        return ImportacaoOutput(
            sucesso=False,
            erro="Erro ao importar CSV"
        ).dict()
