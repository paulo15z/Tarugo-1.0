# apps/pcp/services/processamento_service.py
from io import BytesIO
import re
import unicodedata
import uuid

import pandas as pd

from django.core.files.base import ContentFile

from pydantic import ValidationError

from apps.pcp.models.processamento import ProcessamentoPCP
from apps.pcp.services.schemas import PCPProcessRequest   # ← corrigido

# Utils
from apps.integracoes.dinabox.service import DinaboxService
from apps.pcp.utils.ripas import consolidar_ripas
from apps.pcp.utils.roteiros import calcular_roteiro, determinar_plano_de_corte
from apps.pcp.utils.excel import gerar_xls_roteiro

def _normalizar_chave(chave: str) -> str:
    """Converte 'DESCRIÇÃO DA PEÇA' → 'DESCRICAO_DA_PECA' (válido no template Django)."""
    chave = unicodedata.normalize('NFD', chave)
    chave = ''.join(c for c in chave if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', '_', chave).strip('_').upper()


class ProcessamentoPCPService:

    @staticmethod
    def gerar_coluna_lote(df: pd.DataFrame, lote: int) -> pd.DataFrame:
        """Substitui a coluna LOTE por lote-plano (ex: 305-06)"""
        df = df.copy()
        df['PLANO'] = df['PLANO'].astype(str).str.strip()
        df['LOTE'] = df['PLANO'].apply(lambda plano: f"{lote}-{plano}")
        return df

    @staticmethod
    def processar_arquivo(uploaded_file, lote: int, usuario=None):
        try:
            input_data = PCPProcessRequest(
                lote=lote,
                filename=uploaded_file.name,
                file_bytes=uploaded_file.read()
            )
        except ValidationError as e:
            raise ValueError(f"Erro de validação: {e}") from e

        # 1. Ler arquivo via Service de Integração
        df = DinaboxService.parse_to_dataframe(input_data.file_bytes, input_data.filename)

        # 2. Processamento
        df = consolidar_ripas(df)
        df['ROTEIRO'] = df.apply(calcular_roteiro, axis=1)
        df['PLANO'] = df.apply(
            lambda row: determinar_plano_de_corte(row, row.get('ROTEIRO', '')), 
            axis=1
        )

        # 3. Gerar coluna R
        df = ProcessamentoPCPService.gerar_coluna_lote(df, lote=input_data.lote)

        # 4. Processar colunas de Furo
        for col in ['FURO A', 'FURO B']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('nan', '').str.strip()

        # 5. Reordenar colunas para o XLS de saída
        colunas_ordem = [
            "LOTE", "ID DA PEÇA", "REFERÊNCIA DA PEÇA", "DESCRIÇÃO DA PEÇA", "LOCAL",
            "MATERIAL DA PEÇA", "CÓDIGO DO MATERIAL", "ESPESSURA",
            "LARGURA DA PEÇA", "ALTURA DA PEÇA", "QUANTIDADE",
            "BORDA_FACE_FRENTE", "BORDA_FACE_TRASEIRA", "BORDA_FACE_LE", "BORDA_FACE_LD",
            "FURO", "FURO A", "FURO B", "UREF", "PLANO", "ROTEIRO", "CONTEXTO", "OBSERVAÇÃO"
        ]
        # Mantém apenas as colunas que existem no DF e na ordem desejada
        colunas_existentes = [c for c in colunas_ordem if c in df.columns]
        # Adiciona quaisquer outras colunas que não estavam na lista mas existem no DF
        outras_colunas = [c for c in df.columns if c not in colunas_existentes]
        df = df[colunas_existentes + outras_colunas]

        # 6. Limpeza
        for col in ['LARGURA_NUM', 'QTD_NUM']:
            if col in df.columns:
                df = df.drop(columns=[col], errors='ignore')

        for col in ['OBSERVAÇÃO', 'OBS']:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(r' *_(pin|tamp|tap|led|curvo|painel|ripa|lamina|tamponamento)_ *', ' ', case=False, regex=True)
                    .str.strip()
                )

        if 'DUPLAGEM' in df.columns:
            df['DUPLAGEM'] = df['DUPLAGEM'].astype(str).str.lower().str.strip()
            mask = df['DUPLAGEM'].str.contains('duplagem', na=False)
            if mask.any():
                df.loc[mask, 'OBSERVAÇÃO'] = df.loc[mask, 'OBSERVAÇÃO'].fillna('') + ' _dup_ '

        # 7. Gerar XLS
        # A função gerar_xls_roteiro já retorna bytes brutos
        xls_bytes = gerar_xls_roteiro(df)

        # 8. Salvar
        pid = str(uuid.uuid4())[:8]
        nome_saida = f"{pid}_Lote-{lote}_{uploaded_file.name.rsplit('.', 1)[0]}.xls"

        processamento = ProcessamentoPCP.objects.create(
            id=pid,
            nome_arquivo=uploaded_file.name,
            lote=lote,
            total_pecas=len(df),
            usuario=usuario
        )

        arquivo_content = ContentFile(xls_bytes, name=nome_saida)
        processamento.arquivo_saida.save(nome_saida, arquivo_content, save=True)

        # 7. Resposta
        cols_previa = ['LOTE', 'DESCRIÇÃO DA PEÇA', 'LOCAL', 'PLANO', 'ROTEIRO']
        if 'OBSERVAÇÃO' in df.columns:
            cols_previa.insert(3, 'OBSERVAÇÃO')

        # Normaliza chaves para uso no template Django (sem espaços/acentos)
        previa_raw = df[cols_previa].head(50).fillna('').to_dict(orient='records')
        previa = [{_normalizar_chave(k): v for k, v in row.items()} for row in previa_raw]

        resumo_df = df['ROTEIRO'].fillna('SEM ROTEIRO').astype(str).value_counts().reset_index()
        resumo_df.columns = ['roteiro', 'qtd']
        resumo = resumo_df.to_dict(orient='records')

        # REMOVIDO: A importação agora é manual via liberar_lote()
        # resultado_bipagem = importar_de_pcp(df, uploaded_file.name, numero_lote=str(lote))

        return {
            'pid': pid,
            'lote': lote,
            'total_pecas': len(df),
            'previa': previa,
            'resumo': resumo,
            'nome_saida': nome_saida,
        }

    @staticmethod
    def liberar_lote(pid: str, usuario=None):
        """
        Marca o lote como liberado para a bipagem operacional.

        A Bipagem agora consome diretamente as pecas do PCP, sem espelhar dados
        em modelos proprios.
        """
        from django.utils import timezone
        from apps.pcp.models.processamento import ProcessamentoPCP

        processamento = ProcessamentoPCP.objects.get(id=pid)

        if processamento.liberado_para_bipagem:
            return {'sucesso': True, 'mensagem': 'Lote ja liberado anteriormente.'}

        processamento.liberado_para_bipagem = True
        processamento.data_liberacao = timezone.now()
        processamento.save(update_fields=['liberado_para_bipagem', 'data_liberacao'])

        return {
            'sucesso': True,
            'mensagem': f'Lote {processamento.lote} liberado para bipagem.',
            'pid': processamento.id,
            'lote': processamento.lote,
        }
