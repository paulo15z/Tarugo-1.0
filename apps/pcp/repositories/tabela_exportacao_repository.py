from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Any
import re
import unicodedata

import pandas as pd

from apps.pcp.schemas.peca import BordaInfo, Dimensoes, PecaOperacional
from apps.pcp.schemas.csv_input import CsvInputRow


def _normalizar_coluna(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value or ""))
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return value


def _valor(row: dict[str, Any], *aliases: str, default: Any = "") -> Any:
    for alias in aliases:
        key = _normalizar_coluna(alias)
        value = row.get(key)
        if value is not None and str(value).strip() not in {"", "nan", "NaN", "None"}:
            return value
    return default


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    text = str(value).strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except Exception:
        return Decimal(default)


def _inteiro(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(float(str(value).strip().replace(",", "."))))
    except Exception:
        return default


class TabelaExportacaoRepository:
    """Converte CSV/XLS/XLSX padrao de exportacao para pecas operacionais."""

    @staticmethod
    def parsear_arquivo(file_obj) -> list[PecaOperacional]:
        nome = str(getattr(file_obj, "name", "") or "").lower()
        content = file_obj.read()
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        if nome.endswith(".csv"):
            df = TabelaExportacaoRepository._ler_csv(content)
        elif nome.endswith((".xls", ".xlsx")):
            df = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Formato nao suportado. Envie CSV, XLS ou XLSX.")

        return TabelaExportacaoRepository.parsear_dataframe(df)

    @staticmethod
    def _ler_csv(content: bytes) -> pd.DataFrame:
        for encoding in ("utf-8-sig", "utf-8", "latin1"):
            for sep in (";", ",", "\t"):
                try:
                    df = pd.read_csv(BytesIO(content), encoding=encoding, sep=sep)
                    if len(df.columns) > 1:
                        return df
                except Exception:
                    continue
        raise ValueError("Nao foi possivel ler o CSV enviado.")

    @staticmethod
    def parsear_dataframe(df: pd.DataFrame) -> list[PecaOperacional]:
        if df.empty:
            raise ValueError("Tabela vazia.")

        normalized = df.copy()
        normalized.columns = [_normalizar_coluna(col) for col in normalized.columns]

        pecas: list[PecaOperacional] = []
        for index, raw in normalized.iterrows():
            row = raw.to_dict()

            # Criar e validar linha do CSV com Pydantic
            try:
                csv_row = CsvInputRow(**{
                    'nome_do_cliente': _valor(row, "NOME DO CLIENTE", default=""),
                    'id_do_projeto': _valor(row, "ID DO PROJETO", default=""),
                    'nome_do_projeto': _valor(row, "NOME DO PROJETO", default=""),
                    'referencia_da_peca': _valor(row, "REFERENCIA DA PECA", default=None),
                    'descricao_modulo': _valor(row, "DESCRICAO DO MODULO", "DESCRICAO MODULO", default=""),
                    'quantidade': _inteiro(_valor(row, "QUANTIDADE", "QTDE", "QTD", default=1)),
                    'largura_da_peca': _decimal(_valor(row, "LARGURA DA PECA", "LARGURA", "WIDTH", default=0)),
                    'altura_da_peca': _decimal(_valor(row, "ALTURA DA PECA", "ALTURA", "HEIGHT", default=0)),
                    'metro_quadrado': _decimal(_valor(row, "METRO QUADRADO", default=0)) if _valor(row, "METRO QUADRADO") else None,
                    'espessura': _decimal(_valor(row, "ESPESSURA", "THICKNESS", default=0)),
                    'codigo_do_material': _valor(row, "CODIGO DO MATERIAL", "MATERIAL ID", default=""),
                    'material_da_peca': _valor(row, "MATERIAL DA PECA", "MATERIAL", default=""),
                    'veio': _valor(row, "VEIO", default=None),
                    'borda_face_frente': _valor(row, "BORDA_FACE_FRENTE", "BORDA FRENTE", default=None),
                    'borda_face_traseira': _valor(row, "BORDA_FACE_TRASEIRA", "BORDA TRASEIRA", default=None),
                    'borda_face_le': _valor(row, "BORDA_FACE_LE", "BORDA LE", default=None),
                    'borda_face_ld': _valor(row, "BORDA_FACE_LD", "BORDA LD", default=None),
                    'lote': _valor(row, "LOTE", default=None),
                    'observacao': _valor(row, "OBSERVACAO", "OBS", "NOTE", default=None),
                    'descricao_da_peca': _valor(row, "DESCRIÇÃO DA PEÇA", "DESCRICAO DA PECA", "DESCRICAO", "PECA", default=""),
                    'id_da_peca': _valor(row, "ID DA PECA", "ID", "CODIGO", "CODIGO PECA", default=str(index + 1)),
                    'local': _valor(row, "LOCAL", "MODULO", "AMBIENTE", default="GERAL"),
                    'duplagem': _valor(row, "DUPLAGEM", default=None),
                    'furo': _valor(row, "FURO", default=None),
                    'obs': _valor(row, "OBS", default=None),
                    'referencia': _valor(row, "REFERENCIA", default=None),
                    'furo_a': _valor(row, "FURO A", "CODE A", default=None),
                    'furo_b': _valor(row, "FURO B", "CODE B", default=None),
                })
            except Exception as e:
                raise ValueError(f"Erro na validação da linha {index + 1}: {e}") from e

            # Aplicar regras de negócio para transformar em PecaOperacional
            peca = TabelaExportacaoRepository._csv_row_para_peca_operacional(csv_row)
            pecas.append(peca)

        if not pecas:
            raise ValueError("Nenhuma peca valida encontrada na tabela.")

        return pecas

    @staticmethod
    def _csv_row_para_peca_operacional(csv_row: CsvInputRow) -> PecaOperacional:
        """Aplica regras de negócio para converter linha validada do CSV em PecaOperacional."""

        # Regras de negócio para determinar se é duplada
        eh_duplada = False
        if csv_row.duplagem and "encaminhar para duplagem" in csv_row.duplagem.lower():
            eh_duplada = True

        # Regras de negócio para bordas
        bordas = {
            "top": BordaInfo(face="top", nome=csv_row.borda_face_frente or ""),
            "bottom": BordaInfo(face="bottom", nome=csv_row.borda_face_traseira or ""),
            "left": BordaInfo(face="left", nome=csv_row.borda_face_le or ""),
            "right": BordaInfo(face="right", nome=csv_row.borda_face_ld or ""),
        }

        # Regras de negócio para furacoes
        furacoes = {}
        if csv_row.furo_a:
            furacoes["A"] = csv_row.furo_a
        if csv_row.furo_b:
            furacoes["B"] = csv_row.furo_b

        # Regras de negócio para material com veio
        material_com_veio = csv_row.veio is not None and csv_row.veio.strip() != ""

        # Regras de negócio para contexto e módulo
        modulo_nome = csv_row.local or "GERAL"
        contexto = csv_row.local or modulo_nome

        # Regra especial: se LOCAL é 'GAVETA', alterar para 'MCX' se indústria possui COR, BOR ou FUR
        # Como não temos acesso direto à indústria aqui, vamos marcar para processamento posterior
        # Por enquanto, manter como está e ajustar no roteiro se necessário

        # Combinar observações
        observacoes_combinadas = []
        if csv_row.observacao:
            observacoes_combinadas.append(csv_row.observacao)
        if csv_row.obs:
            observacoes_combinadas.append(csv_row.obs)
        observacoes_original = " | ".join(observacoes_combinadas) if observacoes_combinadas else None

        # Tags baseadas em regras de negócio
        tags = set()
        descricao_lower = csv_row.descricao_da_peca.lower()
        if "ripa" in descricao_lower or "_ripa_" in (observacoes_original or "").lower():
            tags.add("_ripa_")
        if eh_duplada:
            tags.add("_dup_")
        if material_com_veio:
            tags.add("_veio_")

        return PecaOperacional(
            id_dinabox=csv_row.id_da_peca,
            ref_completa=csv_row.referencia_da_peca or csv_row.id_da_peca,
            ref_modulo=csv_row.referencia_da_peca,
            ref_peca=csv_row.referencia,
            descricao=csv_row.descricao_da_peca,
            modulo_ref=csv_row.referencia_da_peca or csv_row.descricao_modulo,
            modulo_nome=modulo_nome,
            contexto=contexto,
            nome_do_cliente=csv_row.nome_do_cliente,
            id_do_projeto=csv_row.id_do_projeto,
            nome_do_projeto=csv_row.nome_do_projeto,
            descricao_modulo=csv_row.descricao_modulo,
            quantidade=csv_row.quantidade,
            dimensoes=Dimensoes(
                largura=csv_row.largura_da_peca,
                altura=csv_row.altura_da_peca,
                espessura=csv_row.espessura,
                metro_quadrado=csv_row.metro_quadrado,
            ),
            material_id=csv_row.codigo_do_material,
            material_nome=csv_row.material_da_peca,
            material_com_veio=material_com_veio,
            bordas=bordas,
            furacoes=furacoes,
            eh_duplada=eh_duplada,
            uref=csv_row.referencia,
            observacoes_original=observacoes_original,
            tags_markdown=tags,
            atributos_tecnicos={
                "cliente": csv_row.nome_do_cliente,
                "projeto_id": csv_row.id_do_projeto,
                "projeto_nome": csv_row.nome_do_projeto,
                "lote": csv_row.lote,
            }
        )
