"""
Serviço responsável por importar dados já processados pelo roteiro para a estrutura de Bipagem.

Fluxo:
PCP Service → DataFrame tratado → ImportadorPCP → LoteProducao → Pedido → OrdemProducao → Modulo → Peca
"""

import pandas as pd
from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone

from apps.bipagem.models import Pedido, OrdemProducao, Modulo, Peca, LoteProducao
from apps.pcp.models.processamento import ProcessamentoPCP


def _limpar_valor(val: Any) -> str:
    """Limpa valores do DataFrame"""
    if pd.isna(val) or val == '' or val is None:
        return ''
    return str(val).strip()


def _extrair_numero_pedido(df: pd.DataFrame) -> str:
    """Tenta extrair o número do pedido de várias formas"""
    # Primeira linha geralmente tem o número no nome do cliente
    primeira = df.iloc[0] if not df.empty else pd.Series()
    
    nome_cliente_raw = _limpar_valor(primeira.get('NOME DO CLIENTE', ''))
    
    if '-' in nome_cliente_raw:
        possivel_numero = nome_cliente_raw.split('-', 1)[0].strip()
        if possivel_numero.isdigit():
            return possivel_numero
    
    # Fallback: tenta pegar de outras colunas
    for col in ['LOTE', 'ID DO PROJETO', 'NUMERO PEDIDO']:
        valor = _limpar_valor(primeira.get(col, ''))
        if valor.isdigit():
            return valor
    
    # Último fallback (para testes)
    return '999999'


def importar_de_pcp(
    df: pd.DataFrame, 
    arquivo_nome: str = "", 
    numero_lote: str = "", 
    processamento_id: Optional[str] = None
) -> Dict:
    """
    Importa DataFrame tratado pelo PCP para o sistema de bipagem.
    
    Args:
        df: DataFrame já processado pelo pcp_service (com ROTEIRO e PLANO)
        arquivo_nome: Nome original do arquivo (para logging)
        numero_lote: O número do lote inserido manualmente pelo usuário no app PCP (Lote Base)
        processamento_id: ID do ProcessamentoPCP que gerou este DataFrame
    
    Returns:
        Dict com resultado da importação
    """
    if df.empty:
        return {
            'sucesso': False,
            'mensagem': 'DataFrame vazio',
            'erros': ['Nenhum dado para importar']
        }

    erros = []
    total_pecas_criadas = 0

    try:
        with transaction.atomic():
            numero_pedido = _extrair_numero_pedido(df)
            
            # 1. Obter ProcessamentoPCP e Criar LoteProducao
            processamento = None
            if processamento_id:
                processamento = ProcessamentoPCP.objects.filter(id=processamento_id).first()
            
            if not processamento:
                # Fallback caso não venha ID (ex: testes ou importação manual)
                # Tenta achar pelo número do lote se existir
                processamento = ProcessamentoPCP.objects.filter(lote=numero_lote).first()
            
            if not processamento:
                raise ValueError(f"Processamento PCP não encontrado para o lote {numero_lote}")

            # Criar o LoteProducao (1 por ProcessamentoPCP)
            # Usamos o numero_lote (lote base) como identificador
            lote_producao, _ = LoteProducao.objects.get_or_create(
                numero_lote=str(numero_lote),
                processamento_pcp=processamento,
                defaults={
                    'liberado_para_bipagem': processamento.liberado_para_bipagem,
                    'observacoes': f"Importado do arquivo: {arquivo_nome}"
                }
            )

            # 2. Criar ou obter Pedido
            cliente_nome = _limpar_valor(df.iloc[0].get('NOME DO CLIENTE', 'Cliente Desconhecido'))
            if '-' in cliente_nome:
                cliente_nome = cliente_nome.split('-', 1)[1].strip()
            
            pedido, pedido_criado = Pedido.objects.update_or_create(
                numero_pedido=numero_pedido,
                defaults={
                    'cliente_nome': cliente_nome,
                }
            )

            # 3. Agrupar por Ordem de Produção (nome_ambiente = NOME DO PROJETO)
            grupos_ordem = df.groupby('NOME DO PROJETO')

            for nome_ambiente, df_ordem in grupos_ordem:
                nome_ambiente = _limpar_valor(nome_ambiente)
                if not nome_ambiente:
                    nome_ambiente = "Sem Nome"

                ordem_producao, _ = OrdemProducao.objects.get_or_create(
                    pedido=pedido,
                    nome_ambiente=nome_ambiente,
                    defaults={'referencia_principal': ''}
                )

                # 4. Agrupar por Módulo dentro da Ordem de Produção
                df_ordem['referencia_modulo'] = df_ordem['REFERÊNCIA DA PEÇA'].apply(
                    lambda x: _limpar_valor(x).split('-')[0].strip() if '-' in str(x) else _limpar_valor(x)
                )
                
                grupos_modulo = df_ordem.groupby('referencia_modulo')

                for ref_modulo, df_modulo in grupos_modulo:
                    ref_modulo = _limpar_valor(ref_modulo)
                    if not ref_modulo:
                        ref_modulo = "ITENS_ESPECIAIS"

                    nome_modulo = _limpar_valor(df_modulo.iloc[0].get('DESCRIÇÃO MÓDULO', ref_modulo))

                    modulo, _ = Modulo.objects.get_or_create(
                        ordem_producao=ordem_producao,
                        referencia_modulo=ref_modulo,
                        defaults={'nome_modulo': nome_modulo}
                    )

                    # 5. Criar as peças
                    pecas_para_criar = []

                    for _, row in df_modulo.iterrows():
                        id_peca = _limpar_valor(row.get('ID DA PEÇA', ''))
                        if not id_peca:
                            continue

                        descricao = _limpar_valor(row.get('DESCRIÇÃO DA PEÇA', ''))
                        local = _limpar_valor(row.get('LOCAL', 'Sem local'))

                        try:
                            largura = float(str(row.get('LARGURA DA PEÇA', 0)).replace(',', '.'))
                            altura = float(str(row.get('ALTURA DA PEÇA', 0)).replace(',', '.'))
                            espessura = float(str(row.get('ESPESSURA', 0)).replace(',', '.'))
                        except:
                            largura = altura = espessura = None

                        quantidade = int(float(str(row.get('QUANTIDADE', 1)).replace(',', '.')) or 1)

                        roteiro = _limpar_valor(row.get('ROTEIRO', ''))
                        plano = _limpar_valor(row.get('PLANO', ''))
                        
                        lote_composto = _limpar_valor(row.get('LOTE', ''))
                        if not lote_composto or lote_composto == 'nan':
                            lote_composto = f"{numero_lote}-{plano}" if plano else str(numero_lote)

                        # Verifica se já existe para evitar erro de integridade
                        if not Peca.objects.filter(modulo=modulo, id_peca=id_peca).exists():
                            peca = Peca(
                                modulo=modulo,
                                lote_producao=lote_producao, # Associação com o novo LoteProducao
                                id_peca=id_peca,
                                numero_lote_pcp=lote_composto,
                                descricao=descricao,
                                local=local,
                                material=_limpar_valor(row.get('MATERIAL DA PEÇA', '')),
                                largura_mm=largura,
                                altura_mm=altura,
                                espessura_mm=espessura,
                                quantidade=quantidade,
                                roteiro=roteiro,
                                plano_corte=plano,
                                status='PENDENTE'
                            )
                            pecas_para_criar.append(peca)

                    if pecas_para_criar:
                        Peca.objects.bulk_create(pecas_para_criar, batch_size=500)
                        total_pecas_criadas += len(pecas_para_criar)

            mensagem = f'Importação concluída: {total_pecas_criadas} peças importadas (Pedido {numero_pedido}, Lote Produção {numero_lote})'

            return {
                'sucesso': True,
                'mensagem': mensagem,
                'numero_pedido': numero_pedido,
                'numero_lote': numero_lote,
                'lote_producao_id': lote_producao.id,
                'total_pecas': total_pecas_criadas,
                'erros': erros,
                'pedido_criado': pedido_criado
            }

    except Exception as e:
        return {
            'sucesso': False,
            'mensagem': f'Erro durante importação: {str(e)}',
            'erros': [str(e)],
            'numero_pedido': numero_pedido if 'numero_pedido' in locals() else 'desconhecido'
        }
