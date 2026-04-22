"""
Repository responsável por transformar JSON da API Dinabox em objetos de domínio.
"""
from typing import List, Set, Dict
import re
from apps.integracoes.dinabox.api_service import DinaboxApiService   
from apps.pcp.schemas.dinabox import ProjectoDinabox
from apps.pcp.schemas.peca import PecaOperacional, Dimensoes, BordaInfo

class DinaboxRepository:
    """Converte dados brutos da API Dinabox → PecaOperacional validada."""

    @staticmethod
    def parsear_para_pecas_operacionais(project_data: dict) -> List[PecaOperacional]:
        """
        Fluxo:
        1. Valida com Pydantic (ProjectoDinabox)
        2. Extrai módulos + peças
        3. Enriquecer com tags, bordas, furações, etc.
        """
        try:
            projeto = ProjectoDinabox.model_validate(project_data)
        except Exception as e:
            raise ValueError(f"JSON Dinabox inválido: {e}")

        if not projeto.woodwork:
            raise ValueError("Projeto sem marcenaria (nenhuma peça encontrada)")

        pecas: List[PecaOperacional] = []
        for modulo in projeto.woodwork:
            # Extrair insumos do módulo para futura lógica de MCX
            insumos_modulo = modulo.inputs or []
            
            for parte in modulo.parts:
                # Regras de negócio leves
                eh_duplada = DinaboxRepository._detectar_duplagem(parte.note)
                tags = DinaboxRepository._extrair_tags(parte.note)
                bordas = DinaboxRepository._mapear_bordas(parte, modulo)
                furacoes = DinaboxRepository._mapear_furacoes(parte)
                
                dinabox_entity = getattr(parte, "entity", None) or getattr(parte, "type", None) or None
                dinabox_type = getattr(parte, "type", None) or getattr(modulo, "type", None) or None
                uref = getattr(parte, "uref", None) or getattr(parte, "user_reference", None) or None

                # Extração de material exclusiva da peça (sem herança do módulo)
                material_id = None
                material_nome = None
                material_com_veio = False

                if parte.material:
                    material_id = parte.material.id
                    material_nome = parte.material.name
                    material_com_veio = parte.material.vein
                else:
                    # Fallback para campos diretos caso o objeto material não exista
                    material_id = getattr(parte, "material_id", None)
                    material_nome = getattr(parte, "material_name", None)

                peca = PecaOperacional(
                    id_dinabox=parte.id,
                    ref_completa=f"{modulo.ref} - {parte.ref}",
                    ref_modulo=modulo.ref,
                    ref_peca=parte.ref,
                    descricao=parte.name,
                    modulo_ref=modulo.ref,
                    modulo_nome=modulo.name,
                    contexto=f"MOD: {modulo.name} ({modulo.ref})",
                    quantidade=parte.count,
                    dimensoes=Dimensoes(
                        largura=parte.width,
                        altura=parte.height,
                        espessura=parte.thickness,
                    ),
                    dinabox_entity=dinabox_entity,
                    dinabox_type=dinabox_type,
                    material_id=material_id,
                    material_nome=material_nome,
                    material_com_veio=material_com_veio,
                    bordas=bordas,
                    furacoes=furacoes,
                    eh_duplada=eh_duplada,
                    uref=uref,
                    observacoes_original=parte.note,
                    tags_markdown=tags,
                    # Armazenar insumos do módulo na peça para auditoria/lógica futura
                    atributos_tecnicos={
                        "insumos_modulo": insumos_modulo
                    }
                )
                pecas.append(peca)

        return pecas

    @staticmethod
    def _detectar_duplagem(note: str | None) -> bool:
        if not note:
            return False
        n = note.lower()
        return "_dup_" in n or "duplagem" in n or "engrossado" in n

    @staticmethod
    def _extrair_tags(note: str | None) -> Set[str]:
        if not note:
            return set()
        return set(re.findall(r"_(\w+)_", note))

    @staticmethod
    def _mapear_bordas(parte, modulo) -> Dict[str, BordaInfo]:
        bordas = {}
        for face in ["left", "right", "top", "bottom"]:
            edge = getattr(parte, f"edge_{face}", None) or getattr(modulo, f"edge_{face}", None)
            bordas[face] = BordaInfo(
                face=face,
                nome=edge.name if edge else None,
                perimetro_mm=getattr(edge, "perimeter", 0) if edge else 0,
                espessura_mm=getattr(edge, "thickness", 0) if edge else 0,
            )
        return bordas

    @staticmethod
    def _mapear_furacoes(parte) -> Dict[str, str | None]:
        return {
            "A": getattr(parte, "code_a", None),
            "B": getattr(parte, "code_b", None),
            "A2": getattr(parte, "code_a2", None),
            "B2": getattr(parte, "code_b2", None),
        }
