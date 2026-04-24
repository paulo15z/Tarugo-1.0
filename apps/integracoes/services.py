"""
Services para o app integracoes.

Responsabilidade: Regras de negócio (toda lógica reside aqui).
Padrão: Recebe dados validados via Pydantic, retorna schemas tipados.
"""

import json
from typing import Dict, Any, Optional
from django.db import transaction

from .models import MapeamentoMaterial, DinaboxClienteIndex
try:
    from .dinabox.schemas import (
        DinaboxProjectOperacional,
        DinaboxProjectLogistico,
        DinaboxProjectAdministrativo,
    )
except (ImportError, ModuleNotFoundError):
    # Travando erros de importação para manter o app rodável sem a API completa
    DinaboxProjectOperacional = None
    DinaboxProjectLogistico = None
    DinaboxProjectAdministrativo = None


class DinaboxIntegrationService:
    """
    Serviço central para processar dados brutos do Dinabox e convertê-los
    nas três visões setorizadas: Operacional, Logístico e Administrativo.
    
    Fluxo:
    1. Recebe JSON bruto do Dinabox (via API ou arquivo)
    2. Valida e converte para schemas Pydantic
    3. Retorna dados tipados para consumo por outros apps
    """

    @staticmethod
    def process_raw_json(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa JSON bruto do Dinabox e retorna as três visões validadas.
        
        Args:
            raw_data: Dicionário com dados brutos do Dinabox
            
        Returns:
            Dict com chaves: operacional, logistico, administrativo
            
        Raises:
            ValueError: Se o JSON não puder ser validado
        """
        try:
            return {
                "operacional": DinaboxProjectOperacional.model_validate(raw_data),
                "logistico": DinaboxProjectLogistico.model_validate(raw_data),
                "administrativo": DinaboxProjectAdministrativo.model_validate(raw_data),
            }
        except Exception as e:
            raise ValueError(f"Erro ao validar dados Dinabox: {str(e)}")

    @classmethod
    def process_file(cls, file_path: str) -> Dict[str, Any]:
        """
        Lê um arquivo JSON e processa.
        
        Args:
            file_path: Caminho para arquivo JSON
            
        Returns:
            Dict com dados processados
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.process_raw_json(data)

    @staticmethod
    def get_operacional_view(raw_data: Dict[str, Any]) -> DinaboxProjectOperacional:
        """Retorna apenas a visão operacional (fabricação, usinagem, rastreabilidade)."""
        return DinaboxProjectOperacional.model_validate(raw_data)

    @staticmethod
    def get_logistico_view(raw_data: Dict[str, Any]) -> DinaboxProjectLogistico:
        """Retorna apenas a visão logística (expedição, viagens, tracking)."""
        return DinaboxProjectLogistico.model_validate(raw_data)

    @staticmethod
    def get_administrativo_view(raw_data: Dict[str, Any]) -> DinaboxProjectAdministrativo:
        """Retorna apenas a visão administrativa (BOM, custos, compras)."""
        return DinaboxProjectAdministrativo.model_validate(raw_data)


class MaterialMappingService:
    """
    Serviço para gerenciar mapeamentos entre materiais Dinabox e Estoque.
    Essencial para o Gêmeo Digital.
    """

    @staticmethod
    @transaction.atomic
    def criar_mapeamento(
        nome_dinabox: str,
        produto_id: int,
        fator_conversao: float = 1.0
    ) -> MapeamentoMaterial:
        """
        Cria um novo mapeamento de material.
        
        Args:
            nome_dinabox: Nome exato do material no Dinabox
            produto_id: ID do Produto no Estoque
            fator_conversao: Multiplicador para consumo (default 1.0)
            
        Returns:
            MapeamentoMaterial criado
        """
        from apps.estoque.models.produto import Produto
        
        produto = Produto.objects.get(id=produto_id)
        mapeamento, created = MapeamentoMaterial.objects.get_or_create(
            nome_dinabox=nome_dinabox,
            defaults={
                "produto": produto,
                "fator_conversao": fator_conversao,
                "ativo": True
            }
        )
        return mapeamento

    @staticmethod
    def obter_mapeamento(nome_dinabox: str) -> Optional[MapeamentoMaterial]:
        """Busca mapeamento ativo por nome exato do Dinabox."""
        return MapeamentoMaterial.objects.filter(
            nome_dinabox=nome_dinabox,
            ativo=True
        ).select_related('produto').first()

    @staticmethod
    @transaction.atomic
    def desativar_mapeamento(mapeamento_id: int) -> None:
        """Desativa um mapeamento sem deletá-lo (auditoria)."""
        MapeamentoMaterial.objects.filter(id=mapeamento_id).update(ativo=False)


class DinaboxClienteService:
    """
    Serviço para sincronizar e gerenciar o índice de clientes Dinabox.
    """

    @staticmethod
    @transaction.atomic
    def sincronizar_cliente(customer_data: Dict[str, Any]) -> DinaboxClienteIndex:
        """
        Sincroniza um cliente individual do Dinabox.
        
        Args:
            customer_data: Dict com dados do cliente (customer_id, customer_name, etc)
            
        Returns:
            DinaboxClienteIndex criado ou atualizado
        """
        customer_id = str(customer_data.get("customer_id") or "").strip()
        if not customer_id:
            raise ValueError("customer_id é obrigatório")

        cliente, _ = DinaboxClienteIndex.objects.update_or_create(
            customer_id=customer_id,
            defaults={
                "customer_name": str(customer_data.get("customer_name") or ""),
                "customer_type": str(customer_data.get("customer_type") or ""),
                "customer_status": str(customer_data.get("customer_status") or ""),
                "customer_emails_text": str(customer_data.get("customer_emails") or ""),
                "customer_phones_text": str(customer_data.get("customer_phones") or ""),
                "raw_payload": customer_data,
            }
        )
        return cliente

    @staticmethod
    def obter_cliente(customer_id: str) -> Optional[DinaboxClienteIndex]:
        """Busca cliente indexado por ID."""
        return DinaboxClienteIndex.objects.filter(customer_id=customer_id).first()

    @staticmethod
    def buscar_clientes(query: str, limit: int = 10) -> list:
        """
        Busca clientes por nome normalizado.
        
        Args:
            query: Termo de busca
            limit: Número máximo de resultados
            
        Returns:
            Lista de DinaboxClienteIndex
        """
        query_normalized = DinaboxClienteIndex._normalize(query)
        return DinaboxClienteIndex.objects.filter(
            customer_name_normalized__icontains=query_normalized
        ).order_by('customer_name')[:limit]

    @staticmethod
    def refresh_from_remote(customer_id: str) -> DinaboxClienteIndex:
        """
        Busca o cliente na API Dinabox, processa via parser e atualiza o índice local.
        
        Fluxo:
        1. DinaboxApiService.get_customer_detail() → DinaboxCustomerDetail tipado
        2. parse_customer_detail() → estrutura normalizada (emails, phones, addresses)
        3. sincronizar_cliente() → atualiza DinaboxClienteIndex com payload bruto
        
        Args:
            customer_id: ID do cliente no Dinabox
            
        Returns:
            DinaboxClienteIndex atualizado
            
        Raises:
            ValueError: Se customer_id inválido ou resposta da API inválida
        """
        from apps.integracoes.dinabox.api_service import DinaboxApiService
        from apps.integracoes.dinabox.parsers.customer_detail import parse_customer_detail

        cid = str(customer_id or "").strip()
        if not cid:
            raise ValueError("customer_id é obrigatório")

        # Busca na API com tipagem
        try:
            api_service = DinaboxApiService()
            customer_detail = api_service.get_customer_detail(cid)
        except Exception as e:
            import json
            error_msg = f"Erro ao buscar cliente {cid} na API Dinabox: {str(e)}"
            raise ValueError(error_msg)

        # Converte para dict se Pydantic
        raw_payload = customer_detail.model_dump() if hasattr(customer_detail, "model_dump") else dict(customer_detail)
        
        # Processa com parser
        parsed = parse_customer_detail(raw_payload)

        # Prepara dados normalizados para índice
        normalized = {
            "customer_id": parsed.get("customer_id") or cid,
            "customer_name": parsed.get("customer_name") or "",
            "customer_type": parsed.get("customer_type") or "pf",
            "customer_status": parsed.get("customer_status") or "on",
            "customer_emails": ", ".join(parsed.get("emails") or []),
            "customer_phones": ", ".join(parsed.get("phones") or []),
        }

        # Sincroniza para índice, preservando payload completo
        index = DinaboxClienteService.sincronizar_cliente({**raw_payload, **normalized})
        return index
