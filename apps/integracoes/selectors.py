"""
Selectors para o app integracoes.

Responsabilidade: Consultas complexas e reutilizáveis ao banco de dados.
Padrão: Centralizar queries aqui, não nas views/services.
"""

from typing import List, Optional, Any
from django.db.models import Q, QuerySet

from .models import MapeamentoMaterial, DinaboxClienteIndex


class MapeamentoMaterialSelector:
    """Seletores para consultas de mapeamentos de materiais."""

    @staticmethod
    def get_by_nome_dinabox(nome_dinabox: str) -> Optional[MapeamentoMaterial]:
        """Busca mapeamento ativo por nome exato do Dinabox."""
        return MapeamentoMaterial.objects.filter(
            nome_dinabox=nome_dinabox,
            ativo=True
        ).select_related('produto').first()

    @staticmethod
    def list_ativos() -> QuerySet:
        """Lista todos os mapeamentos ativos."""
        return MapeamentoMaterial.objects.filter(
            ativo=True
        ).select_related('produto').order_by('nome_dinabox')

    @staticmethod
    def list_inativos() -> QuerySet:
        """Lista todos os mapeamentos inativos."""
        return MapeamentoMaterial.objects.filter(
            ativo=False
        ).select_related('produto').order_by('nome_dinabox')

    @staticmethod
    def list_por_produto(produto_id: int) -> QuerySet:
        """Lista mapeamentos de um produto específico."""
        return MapeamentoMaterial.objects.filter(
            produto_id=produto_id,
            ativo=True
        ).order_by('nome_dinabox')

    @staticmethod
    def search(query: str) -> QuerySet:
        """Busca mapeamentos por nome (parcial)."""
        return MapeamentoMaterial.objects.filter(
            Q(nome_dinabox__icontains=query) | Q(produto__nome__icontains=query),
            ativo=True
        ).select_related('produto').order_by('nome_dinabox')

    @staticmethod
    def count_ativos() -> int:
        """Conta mapeamentos ativos."""
        return MapeamentoMaterial.objects.filter(ativo=True).count()


class DinaboxClienteSelector:
    """Seletores para consultas de clientes Dinabox."""

    @staticmethod
    def get_by_customer_id(customer_id: str) -> Optional[DinaboxClienteIndex]:
        """Busca cliente por ID."""
        return DinaboxClienteIndex.objects.filter(customer_id=customer_id).first()

    @staticmethod
    def list_todos() -> QuerySet:
        """Lista todos os clientes indexados."""
        return DinaboxClienteIndex.objects.all().order_by('customer_name')

    @staticmethod
    def list_por_tipo(customer_type: str) -> QuerySet:
        """Lista clientes por tipo (PF/PJ)."""
        return DinaboxClienteIndex.objects.filter(
            customer_type=customer_type
        ).order_by('customer_name')

    @staticmethod
    def list_por_status(customer_status: str) -> QuerySet:
        """Lista clientes por status."""
        return DinaboxClienteIndex.objects.filter(
            customer_status=customer_status
        ).order_by('customer_name')

    @staticmethod
    def search_por_nome(query: str, limit: int = 10) -> QuerySet:
        """
        Busca clientes por nome normalizado.
        
        Args:
            query: Termo de busca
            limit: Número máximo de resultados
            
        Returns:
            QuerySet de clientes
        """
        query_normalized = DinaboxClienteIndex._normalize(query)
        return DinaboxClienteIndex.objects.filter(
            customer_name_normalized__icontains=query_normalized
        ).order_by('customer_name')[:limit]

    @staticmethod
    def count_total() -> int:
        """Conta total de clientes indexados."""
        return DinaboxClienteIndex.objects.count()

    @staticmethod
    def count_por_tipo() -> dict:
        """Retorna contagem de clientes por tipo."""
        from django.db.models import Count
        
        result = DinaboxClienteIndex.objects.values('customer_type').annotate(
            total=Count('id')
        )
        return {item['customer_type']: item['total'] for item in result}

    @staticmethod
    def count_por_status() -> dict:
        """Retorna contagem de clientes por status."""
        from django.db.models import Count
        
        result = DinaboxClienteIndex.objects.values('customer_status').annotate(
            total=Count('id')
        )
        return {item['customer_status']: item['total'] for item in result}

    @staticmethod
    def list_recentemente_sincronizados(dias: int = 7) -> QuerySet:
        """Lista clientes sincronizados nos últimos N dias."""
        from django.utils import timezone
        from datetime import timedelta
        
        data_limite = timezone.now() - timedelta(days=dias)
        return DinaboxClienteIndex.objects.filter(
            synced_at__gte=data_limite
        ).order_by('-synced_at')

    @staticmethod
    def get_cliente_para_comercial(customer_id: str) -> Optional[dict[str, Any]]:
        """
        Busca cliente e retorna estrutura formatada para consumo do comercial.
        
        Estrutura retornada:
        {
            "customer_id": str,
            "customer_name": str,
            "customer_type": str (pf|pj),
            "customer_status": str (on|off),
            "customer_note": str,
            "emails": list[str],
            "phones": list[str],
            "addresses": list[dict],
            "metadata": {
                "synced_at": datetime,
                "raw_keys": list[str],
            }
        }
        
        Args:
            customer_id: ID do cliente no Dinabox
            
        Returns:
            Dict formatado ou None se não encontrado
        """
        cliente = DinaboxClienteSelector.get_by_customer_id(customer_id)
        if not cliente:
            return None
        
        # Extrai emails e phones do texto indexado
        from apps.integracoes.dinabox.parsers.customer_detail import _normalize_emails, _normalize_phones
        
        raw_payload = cliente.raw_payload or {}
        emails = _normalize_emails(raw_payload.get("customer_emails") or cliente.customer_emails_text)
        phones = _normalize_phones(raw_payload.get("customer_phones") or cliente.customer_phones_text)
        addresses = raw_payload.get("customer_addresses") or []
        
        return {
            "customer_id": cliente.customer_id,
            "customer_name": cliente.customer_name,
            "customer_type": cliente.customer_type,
            "customer_status": cliente.customer_status,
            "customer_note": raw_payload.get("customer_note", ""),
            "emails": emails,
            "phones": phones,
            "addresses": addresses if isinstance(addresses, list) else [],
            "metadata": {
                "synced_at": cliente.synced_at,
                "raw_keys": list(raw_payload.keys())[:50] if raw_payload else [],
            },
        }
