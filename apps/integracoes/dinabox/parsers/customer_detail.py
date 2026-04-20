"""
Extrai dados essenciais de um cliente Dinabox.
Valida estrutura, normaliza campos (emails, phones, addresses).
"""

from __future__ import annotations

from typing import Any


def _as_dict(detail: Any) -> dict:
    """Converte detail para dict (suporta Pydantic e dict)."""
    if detail is None:
        return {}
    if hasattr(detail, "model_dump"):
        return detail.model_dump()
    if isinstance(detail, dict):
        return detail
    return {}


def _normalize_emails(raw_emails: Any) -> list[str]:
    """
    Extrai lista de e-mails a partir de diferentes formatos.
    Suporta: string separada por vírgula/semicolon, lista, ou campo único.
    
    Casos tratados:
    - None → []
    - [] → []
    - "user@example.com" → ["user@example.com"]
    - "user1@example.com, user2@example.com" → [...]
    - [{"email": "..."}] → [...]
    - ["user@example.com"] → [...]
    """
    if not raw_emails:
        return []
    
    if isinstance(raw_emails, list):
        if not raw_emails:  # lista vazia
            return []
        result = []
        for item in raw_emails:
            if isinstance(item, dict):
                email = item.get("value") or item.get("email") or str(item)
            else:
                email = str(item).strip() if item else ""
            if email and "@" in email:
                result.append(email)
        return result
    
    # String: separada por vírgula ou semicolon
    raw_str = str(raw_emails).strip() if raw_emails else ""
    if not raw_str or raw_str.lower() == "none":
        return []
    
    emails = []
    for sep in [",", ";"]:
        if sep in raw_str:
            emails = [e.strip() for e in raw_str.split(sep) if e.strip() and "@" in e]
            break
    
    if not emails and "@" in raw_str:
        emails = [raw_str]
    
    return emails


def _normalize_phones(raw_phones: Any) -> list[str]:
    """
    Extrai lista de telefones a partir de diferentes formatos.
    Suporta: string separada por vírgula/semicolon, lista, ou campo único.
    
    Casos tratados:
    - None → []
    - [] → []
    - "(11) 99999-9999" → ["(11) 99999-9999"]
    - "(11) 99999-9999; (21) 88888-8888" → [...]
    - [{"phone": "..."}] → [...]
    """
    if not raw_phones:
        return []
    
    if isinstance(raw_phones, list):
        if not raw_phones:  # lista vazia
            return []
        result = []
        for item in raw_phones:
            if isinstance(item, dict):
                phone = item.get("value") or item.get("phone") or str(item)
            else:
                phone = str(item).strip() if item else ""
            if phone:
                result.append(phone)
        return result
    
    # String: separada por vírgula ou semicolon
    raw_str = str(raw_phones).strip() if raw_phones else ""
    if not raw_str or raw_str.lower() == "none":
        return []
    
    phones = []
    for sep in [",", ";"]:
        if sep in raw_str:
            phones = [p.strip() for p in raw_str.split(sep) if p.strip()]
            break
    
    if not phones:
        phones = [raw_str] if raw_str else []
    
    return phones


def _normalize_addresses(raw_addresses: Any) -> list[dict[str, Any]]:
    """
    Extrai lista de endereços.
    Esperado: lista de dicts ou None.
    
    Casos tratados:
    - None → []
    - [] → []
    - [{"address": null, ...}] → filtra campos None
    """
    if not raw_addresses:
        return []
    
    if isinstance(raw_addresses, list):
        result = []
        for a in raw_addresses:
            if isinstance(a, dict):
                # Remove campos None/null para simplificar
                cleaned = {k: v for k, v in a.items() if v is not None and v != ""}
                if cleaned:  # só adiciona se houver algo
                    result.append(cleaned)
        return result
    
    if isinstance(raw_addresses, dict):
        cleaned = {k: v for k, v in raw_addresses.items() if v is not None and v != ""}
        return [cleaned] if cleaned else []
    
    return []


def parse_customer_detail(detail: Any) -> dict[str, Any]:
    """
    Processa dados brutos de um cliente Dinabox e retorna estrutura normalizada.
    
    Casos tratados:
    - Campos null/None recebem defaults apropriados
    - E-mails e telefones são normalizados em listas
    - Endereços são filtrados (removem campos null)
    - Tipo e status recebem defaults se null
    
    Args:
        detail: Resposta bruta do Dinabox (dict ou Pydantic model)
    
    Returns:
        Dict com estrutura tipada e normalizada:
        - customer_id, customer_name, customer_type, customer_status
        - emails: list[str]
        - phones: list[str]
        - addresses: list[dict]
        - customer_pf_data: dict | None
        - customer_pj_data: dict | None
        - custom_fields: dict | list | None
        - customer_note: str
        - metadata: info sobre o processamento
    """
    raw = _as_dict(detail)
    
    # Campos essenciais
    customer_id = str(raw.get("customer_id") or raw.get("id") or "").strip()
    customer_name = str(raw.get("customer_name") or "").strip()
    
    # Type e Status → defaults se None
    customer_type = str(raw.get("customer_type") or "pf").strip().lower()
    if customer_type in ("none", ""):
        customer_type = "pf"
    
    customer_status = str(raw.get("customer_status") or "on").strip().lower()
    if customer_status in ("none", ""):
        customer_status = "on"
    
    customer_note = str(raw.get("customer_note") or "").strip()
    
    # Normalizar listas de contato
    emails = _normalize_emails(raw.get("customer_emails"))
    phones = _normalize_phones(raw.get("customer_phones"))
    addresses = _normalize_addresses(raw.get("customer_addresses"))
    
    # Dados específicos por tipo
    customer_pf_data = raw.get("customer_pf_data")
    if customer_pf_data and isinstance(customer_pf_data, dict):
        # Remove campos None
        customer_pf_data = {k: v for k, v in customer_pf_data.items() if v is not None}
        customer_pf_data = customer_pf_data or None
    
    customer_pj_data = raw.get("customer_pj_data")
    if customer_pj_data and isinstance(customer_pj_data, dict):
        # Remove campos None
        customer_pj_data = {k: v for k, v in customer_pj_data.items() if v is not None}
        customer_pj_data = customer_pj_data or None
    
    custom_fields = raw.get("custom_fields")
    if isinstance(custom_fields, list) and not custom_fields:
        custom_fields = None
    elif isinstance(custom_fields, dict) and not custom_fields:
        custom_fields = None
    
    # Timestamps
    created_at = raw.get("created_at")
    updated_at = raw.get("updated_at")
    
    return {
        # Identificação
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_type": customer_type,
        "customer_status": customer_status,
        "customer_note": customer_note,
        
        # Contato normalizado
        "emails": emails,
        "phones": phones,
        "addresses": addresses,
        
        # Dados específicos
        "customer_pf_data": customer_pf_data,
        "customer_pj_data": customer_pj_data,
        "custom_fields": custom_fields,
        
        # Timestamps
        "created_at": created_at,
        "updated_at": updated_at,
        
        # Metadados
        "metadata": {
            "source": "dinabox",
            "raw_keys": list(raw.keys())[:50],
        },
    }
