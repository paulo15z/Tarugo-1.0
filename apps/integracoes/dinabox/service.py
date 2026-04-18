from io import BytesIO
import json
import pandas as pd
from pydantic import BaseModel, Field
from .schemas.dinabox_operacional import DinaboxProjectOperacional


EXPECTED_DINABOX_COLUMNS = [
    "NOME DO CLIENTE",
    "ID DO PROJETO",
    "NOME DO PROJETO",
    "REFERÊNCIA DA PEÇA",
    "DESCRIÇÃO MÓDULO",
    "QUANTIDADE",
    "LARGURA DA PEÇA",
    "ALTURA DA PEÇA",
    "METRO QUADRADO",
    "ESPESSURA",
    "CODIGO DO MATERIAL",
    "MATERIAL DA PEÇA",
    "VEIO",
    "BORDA_FACE_FRENTE",
    "BORDA_FACE_TRASEIRA",
    "BORDA_FACE_LE",
    "BORDA_FACE_LD",
    "LOTE",
    "OBSERVAÇÃO",
    "DESCRIÇÃO DA PEÇA",
    "ID DA PEÇA",
    "LOCAL",
    "DUPLAGEM",
    "FURO",
    "OBS",
    "REFERENCIA",
    "FURACAO_A",
    "FURACAO_B",
]

COLUMN_ALIASES = {
    "REFERÊNCIA DA PEÇA": ["REFERENCIA DA PECA", "REFERÃŠNCIA DA PEÃ‡A", "REFERENCIA DA PEÇA"],
    "DESCRIÇÃO MÓDULO": ["DESCRICAO MODULO", "DESCRIÃ‡ÃƒO MÃ“DULO", "DESCRICAO MÓDULO"],
    "LARGURA DA PEÇA": ["LARGURA DA PECA", "LARGURA DA PEÃ‡A"],
    "ALTURA DA PEÇA": ["ALTURA DA PECA", "ALTURA DA PEÃ‡A"],
    "MATERIAL DA PEÇA": ["MATERIAL DA PECA", "MATERIAL DA PEÃ‡A"],
    "OBSERVAÇÃO": ["OBSERVACAO", "OBSERVAÃ‡ÃƒO", "OBSERVA??O"],
    "DESCRIÇÃO DA PEÇA": ["DESCRICAO DA PECA", "DESCRIÃ‡ÃƒO DA PEÃ‡A", "DESCRI??O DA PE?A"],
    "ID DA PEÇA": ["ID DA PECA", "ID DA PEÃ‡A"],
}


class DinaboxFile(BaseModel):
    """Valida o input para o parser do Dinabox."""

    raw_file: bytes
    filename: str = Field(..., min_length=1)


class DinaboxService:
    """
    Servico central para importar e padronizar arquivos do Dinabox.
    Prioridade de mapeamento: posicao da coluna -> nome/alias.
    """

    @staticmethod
    def get_project_as_dataframe(project_id: str) -> pd.DataFrame:
        """Busca o projeto na API e converte para o formato DataFrame compatível com PCP."""
        from .client import DinaboxAPIClient
        client = DinaboxAPIClient()
        raw_data = client.get_project(project_id)
        project = DinaboxProjectOperacional.model_validate(raw_data)
        
        rows = []
        for module in project.woodwork:
            # Identificar se o módulo em si é um engrossado/duplado
            is_module_thickened = module.type == "thickened" or module.edge_thickness and module.edge_thickness > (module.thickness + 5)
            
            for part in module.parts:
                # Lógica de detecção de duplagem/engrosso refinada
                is_thickened = (
                    "_dup_" in (part.note or "").lower() or 
                    "duplagem" in (part.note or "").lower() or
                    is_module_thickened or
                    (part.edge_thickness and part.edge_thickness > (part.thickness + 5))
                )

                # Mapeamento para o formato legado do CSV esperado pelo PCP 1.0
                row = {
                    "NOME DO CLIENTE": project.project_customer_name,
                    "ID DO PROJETO": project.project_id,
                    "NOME DO PROJETO": project.project_description,
                    "REFERÊNCIA DA PEÇA": f"{module.ref} - {part.ref}",
                    "DESCRIÇÃO MÓDULO": module.name,
                    "QUANTIDADE": str(part.count),
                    "LARGURA DA PEÇA": str(part.width).replace(".", ","),
                    "ALTURA DA PEÇA": str(part.height).replace(".", ","),
                    "METRO QUADRADO": str(part.material.m2).replace(".", ",") if part.material else "0",
                    "ESPESSURA": str(part.thickness).replace(".", ","),
                    "CODIGO DO MATERIAL": part.material.id if part.material else "",
                    "MATERIAL DA PEÇA": part.material.name if part.material else "",
                    "VEIO": "Sim" if part.material and part.material.vein else "Não",
                    "BORDA_FACE_FRENTE": part.edge_top.name or "",
                    "BORDA_FACE_TRASEIRA": part.edge_bottom.name or "",
                    "BORDA_FACE_LE": part.edge_left.name or "",
                    "BORDA_FACE_LD": part.edge_right.name or "",
                    "LOTE": "", 
                    "OBSERVAÇÃO": part.note or "",
                    "DESCRIÇÃO DA PEÇA": part.name,
                    "ID DA PEÇA": part.id,
                    "LOCAL": module.name, # Substituindo entity por nome do módulo para ser mais útil
                    "DUPLAGEM": "Sim" if is_thickened else "", 
                    "FURO": "Sim" if (part.total_holes > 0 or (part.machining and len(part.machining) > 0)) else "Não",
                    "OBS": part.note or "",
                    "REFERENCIA": f"{module.ref} - {part.ref}",
                    "FURACAO_A": part.code_a or "",
                    "FURACAO_B": part.code_b or "",
                }
                rows.append(row)
        
        df = pd.DataFrame(rows)
        # Reordenar colunas para garantir que a ordem do XLS seja preservada
        df = df[EXPECTED_DINABOX_COLUMNS]
        return df

    @staticmethod
    def parse_to_dataframe(raw_file: bytes, filename: str) -> pd.DataFrame:
        file_data = DinaboxFile(raw_file=raw_file, filename=filename)
        ext = file_data.filename.rsplit(".", 1)[-1].lower()

        if ext == "csv":
            text = None
            for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                try:
                    text = file_data.raw_file.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                raise ValueError("Nao foi possivel decodificar o arquivo CSV. Verifique o encoding.")

            linhas = text.splitlines()
            corpo = [
                l.rstrip(";")
                for l in linhas
                if not (l.startswith("[") and "[LISTA]" not in l and "[/LISTA]" not in l)
            ]
            df = pd.read_csv(BytesIO("\n".join(corpo).encode("utf-8")), sep=";", dtype=str).fillna("")
        else:
            df = pd.read_excel(BytesIO(file_data.raw_file), dtype=str).fillna("")

        df.columns = [str(c).strip() for c in df.columns]
        df = df[[c for c in df.columns if c]]

        df = DinaboxService._canonicalize_columns(df)

        if "NOME DO CLIENTE" in df.columns:
            df = df[~df["NOME DO CLIENTE"].astype(str).str.strip().isin(["RODAPÉ", "RODAPE", ""])]

        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].astype(str).str.strip()

        obrigatorias = ["LOCAL", "FURO", "DUPLAGEM", "DESCRIÇÃO DA PEÇA"]
        faltando = [c for c in obrigatorias if c not in df.columns]
        if faltando:
            raise ValueError(f"Colunas obrigatorias do Dinabox nao encontradas no arquivo: {', '.join(faltando)}")

        return df

    @staticmethod
    def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        # 1) Posicao definida primeiro.
        if len(df.columns) >= len(EXPECTED_DINABOX_COLUMNS):
            mapped = {}
            for idx, expected_col in enumerate(EXPECTED_DINABOX_COLUMNS):
                mapped[expected_col] = df.iloc[:, idx]

            canonical_df = pd.DataFrame(mapped, index=df.index)

            for idx in range(len(EXPECTED_DINABOX_COLUMNS), len(df.columns)):
                extra_name = str(df.columns[idx]).strip() or f"EXTRA_{idx}"
                if extra_name in canonical_df.columns:
                    extra_name = f"{extra_name}_{idx}"
                canonical_df[extra_name] = df.iloc[:, idx]

            return canonical_df

        # 2) Fallback por aliases de nome.
        rename_map = {}
        for canonical, aliases in COLUMN_ALIASES.items():
            if canonical in df.columns:
                continue
            for alias in aliases:
                if alias in df.columns:
                    rename_map[alias] = canonical
                    break

        if rename_map:
            df = df.rename(columns=rename_map)

        return df