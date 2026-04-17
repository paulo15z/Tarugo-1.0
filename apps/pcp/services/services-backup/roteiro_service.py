from io import BytesIO
import uuid

import pandas as pd
from pydantic import BaseModel, ValidationError

from django.core.files.base import ContentFile

from apps.pcp.models.processamento import ProcessamentoPCP
from apps.pcp.utils.parsers import ler_arquivo_dinabox
from apps.pcp.utils.ripas import consolidar_ripas
from apps.pcp.utils.roteiros import calcular_roteiro, determinar_plano_de_corte
from apps.pcp.utils.excel import gerar_xls_roteiro


class ProcessarRoteiroInput(BaseModel):
    """Input validado com Pydantic (mt divertido)"""
    file: bytes
    filename: str
    usuario_id: int | None = None   # futuro: auditoria / multi-tenant


from io import BytesIO
import uuid
import pandas as pd

from django.core.files.base import ContentFile

from apps.pcp.models.processamento import ProcessamentoPCP
from apps.pcp.utils.parsers import ler_arquivo_dinabox
from apps.pcp.utils.ripas import consolidar_ripas
from apps.pcp.utils.roteiros import calcular_roteiro, determinar_plano_de_corte
from apps.pcp.utils.excel import gerar_xls_roteiro


def processar_arquivo_roteiro_pcp(uploaded_file) -> dict:
    """
    Service simplificado - sem Pydantic por enquanto (mais estável com MultiPartParser)
    """
    try:
        # 1. Ler arquivo
        df = ler_arquivo_dinabox(uploaded_file.read(), uploaded_file.name)

        # 2. Processamento
        df = consolidar_ripas(df)
        df['ROTEIRO'] = df.apply(calcular_roteiro, axis=1)
        df['PLANO'] = df.apply(
            lambda row: determinar_plano_de_corte(row, row.get('ROTEIRO', '')), axis=1
        )

        # 3. Limpeza
        for col in ['LARGURA_NUM', 'QTD_NUM']:
            if col in df.columns:
                df = df.drop(columns=[col], errors='ignore')

        for col in ['OBSERVAÇÃO', 'OBS']:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(r' *_(pin|tap|led|curvo|painel|ripa|lamina)_ *', ' ', case=False, regex=True)
                    .str.strip()
                )

        # Normaliza duplagem
        if 'DUPLAGEM' in df.columns:
            df['DUPLAGEM'] = df['DUPLAGEM'].astype(str).str.lower().str.strip()
            mask = df['DUPLAGEM'].str.contains('duplagem', na=False)
            if mask.any():
                df.loc[mask, 'OBSERVAÇÃO'] = df.loc[mask, 'OBSERVAÇÃO'].fillna('') + ' _dup_ '

        # 4. Gerar XLS
        xls_buf = gerar_xls_roteiro(df)
        xls_bytes = xls_buf.getvalue()

        # 5. Salvar no model
        pid = str(uuid.uuid4())[:8]
        nome_saida = f"{pid}_{uploaded_file.name.rsplit('.', 1)[0]}.xls"

        processamento = ProcessamentoPCP.objects.create(
            id=pid,
            nome_arquivo=uploaded_file.name,
            total_pecas=len(df),
        )

        arquivo_content = ContentFile(xls_bytes, name=nome_saida)
        processamento.arquivo_saida.save(nome_saida, arquivo_content, save=True)

        # 6. Preparar resposta
        cols_previa = ['DESCRIÇÃO DA PEÇA', 'LOCAL', 'PLANO', 'ROTEIRO']
        if 'OBSERVAÇÃO' in df.columns:
            cols_previa.insert(2, 'OBSERVAÇÃO')
        elif 'OBS' in df.columns:
            cols_previa.insert(2, 'OBS')

        previa = df[cols_previa].head(50).fillna('').to_dict(orient='records')

        resumo_df = df['ROTEIRO'].fillna('SEM ROTEIRO').astype(str).value_counts().reset_index()
        resumo_df.columns = ['roteiro', 'qtd']
        resumo = resumo_df.to_dict(orient='records')

        return {
            'pid': pid,
            'total': len(df),
            'previa': previa,
            'resumo': resumo,
            'nome_saida': nome_saida,
        }

    except Exception as e:
        raise RuntimeError(f"Erro ao processar arquivo PCP: {str(e)}") from e