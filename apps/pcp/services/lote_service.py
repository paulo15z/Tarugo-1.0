import pandas as pd
from django.db import transaction

from apps.pcp.models.lote import AmbientePCP, LotePCP, ModuloPCP, PecaPCP
from apps.pcp.schemas.peca import Ambiente, Cliente, LotePCPInput, Modulo, Peca
from .utils import calcular_roteiro, determinar_plano_de_corte


class LotePCPService:
    """Regras de negocio do PCP: criacao de lote e bipagem."""

    @staticmethod
    def _get_valor_texto(row, *colunas: str) -> str:
        """Retorna o primeiro valor textual util dentre as colunas informadas."""
        for coluna in colunas:
            valor = row.get(coluna, "")
            if pd.isna(valor):
                continue
            texto = str(valor).strip()
            if texto and texto.lower() != "nan":
                return texto
        return ""

    @staticmethod
    @transaction.atomic
    def criar_lote_a_partir_de_dataframe(
        df: pd.DataFrame,
        pid: str,
        nome_arquivo: str,
        ordem_producao: str | None = None,
    ) -> LotePCP:
        """Fluxo principal: DataFrame -> Pydantic -> Models.

        Importante: se o DataFrame ja vier com ROTEIRO/PLANO calculados pelo
        processamento do PCP, nao recalcular para evitar divergencia entre PCP
        e Bipagem.
        """
        df = df.copy()
        if "ROTEIRO" not in df.columns:
            df["ROTEIRO"] = df.apply(calcular_roteiro, axis=1)
        if "PLANO" not in df.columns:
            df["PLANO"] = df.apply(
                lambda row: determinar_plano_de_corte(row, row["ROTEIRO"]),
                axis=1,
            )

        lote_input = LotePCPService._build_lote_input(df, pid, nome_arquivo, ordem_producao)
        return LotePCPService._persist_lote(lote_input)

    @staticmethod
    def _build_lote_input(
        df: pd.DataFrame,
        pid: str,
        nome_arquivo: str,
        ordem_producao: str | None,
    ) -> LotePCPInput:
        """Agrupa DataFrame em Cliente -> Ambientes -> Modulos -> Pecas."""
        cliente_nome = str(df["NOME DO CLIENTE"].iloc[0]).strip() if not df.empty else ""
        id_projeto = str(df.get("ID DO PROJETO", pd.Series([""])).iloc[0]).strip()

        ambientes_dict: dict[str, Ambiente] = {}

        for _, row in df.iterrows():
            ambiente_nome = str(row.get("NOME DO PROJETO", "")).strip() or "SEM AMBIENTE"
            modulo_nome = str(row.get("DESCRIÇÃO MÓDULO", "")).strip() or "SEM MÓDULO"
            id_peca_dinabox = LotePCPService._get_valor_texto(
                row,
                "ID DA PEÇA",
                "ID DA PECA",
                "ID DA PEÃ‡A",
                "ID DA PEÃƒâ€¡A",
            )
            ref_bruta = LotePCPService._get_valor_texto(
                row,
                "REFERENCIA",
                "REFERÊNCIA DA PEÇA",
                "ID DA PEÇA",
            )
            if not ref_bruta:
                continue

            quantidade = int(float(row.get("QUANTIDADE", 0) or 0))
            if quantidade <= 0:
                continue

            peca_data = {
                "referencia": ref_bruta,
                "descricao": str(row.get("DESCRIÇÃO DA PEÇA", "")),
                "local": row.get("LOCAL"),
                "material": row.get("MATERIAL DA PEÇA"),
                "codigo_material": row.get("CODIGO DO MATERIAL"),
                "quantidade": quantidade,
                # Etiqueta deve respeitar exatamente o ID DA PEÇA.
                # So cai para parsing de REFERENCIA quando o ID nao vier no arquivo.
                "codigo_peca": id_peca_dinabox or None,
                "roteiro": row.get("ROTEIRO"),
                "plano": row.get("PLANO"),
                "observacoes": row.get("OBSERVAÇÃO") or row.get("OBS"),
                "lote": row.get("LOTE"),
                "id_peca_dinabox": id_peca_dinabox or None,
                **{k: v for k, v in row.items() if k not in ["ROTEIRO", "PLANO"]},
            }
            peca = Peca.model_validate(peca_data)

            if ambiente_nome not in ambientes_dict:
                ambientes_dict[ambiente_nome] = Ambiente(nome=ambiente_nome, modulos=[])

            modulo_existente = next(
                (m for m in ambientes_dict[ambiente_nome].modulos if m.nome == modulo_nome),
                None,
            )
            if not modulo_existente:
                modulo_existente = Modulo(
                    nome=modulo_nome,
                    codigo_modulo=peca.codigo_modulo,
                    pecas=[],
                )
                ambientes_dict[ambiente_nome].modulos.append(modulo_existente)

            modulo_existente.pecas.append(peca)

        cliente = Cliente(
            nome=cliente_nome,
            id_projeto=id_projeto,
            ambientes=list(ambientes_dict.values()),
        )

        return LotePCPInput(
            pid=pid,
            arquivo_original=nome_arquivo,
            cliente=cliente,
            ordem_producao=ordem_producao,
        )

    @staticmethod
    def _persist_lote(lote_input: LotePCPInput) -> LotePCP:
        """Persiste a hierarquia completa."""
        lote = LotePCP.objects.create(
            pid=lote_input.pid,
            arquivo_original=lote_input.arquivo_original,
            cliente_nome=lote_input.cliente.nome,
            cliente_id_projeto=lote_input.cliente.id_projeto,
            ordem_producao=lote_input.ordem_producao,
        )

        for amb_schema in lote_input.cliente.ambientes:
            ambiente = AmbientePCP.objects.create(lote=lote, nome=amb_schema.nome)

            for mod_schema in amb_schema.modulos:
                modulo = ModuloPCP.objects.create(
                    ambiente=ambiente,
                    nome=mod_schema.nome,
                    codigo_modulo=mod_schema.codigo_modulo,
                )

                for peca_schema in mod_schema.pecas:
                    PecaPCP.objects.create(
                        modulo=modulo,
                        referencia_bruta=peca_schema.referencia,
                        codigo_modulo=peca_schema.codigo_modulo,
                        codigo_peca=peca_schema.codigo_peca,
                        descricao=peca_schema.descricao,
                        local=peca_schema.local,
                        material=peca_schema.material,
                        codigo_material=peca_schema.codigo_material,
                        comprimento=peca_schema.dimensoes.comprimento,
                        largura=peca_schema.dimensoes.largura,
                        espessura=peca_schema.dimensoes.espessura,
                        metro_quadrado=peca_schema.dimensoes.metro_quadrado,
                        quantidade_planejada=peca_schema.quantidade,
                        atributos_tecnicos=peca_schema.atributos.model_dump(),
                        roteiro=peca_schema.roteiro,
                        plano=peca_schema.plano,
                        observacoes=peca_schema.observacoes,
                        lote_dinabox=peca_schema.lote,
                        id_peca_dinabox=peca_schema.id_peca_dinabox,
                    )

        return lote

    @staticmethod
    def bipar_peca(peca_id: int, quantidade: int, usuario: str | None = None) -> PecaPCP:
        """Bipagem simples: so atualiza PCP."""
        peca = PecaPCP.objects.get(id=peca_id)
        peca.quantidade_produzida += quantidade
        if peca.quantidade_produzida >= peca.quantidade_planejada:
            peca.status = "finalizado"
        else:
            peca.status = "em_producao"
        peca.save(update_fields=["quantidade_produzida", "status"])
        return peca
