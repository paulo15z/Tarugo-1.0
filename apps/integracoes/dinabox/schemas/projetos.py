from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------------
# SCHEMAS DE CONTRATO (API DINABOX) - PROJETOS
# ---------------------------------------------------------------------------------
# Objetivo: Validar e tipar exatamente o que vem da API Dinabox.
# Regra de Ouro: Use 'Field(alias="campo_api")' para manter o nome Pythonico internamente.
# ---------------------------------------------------------------------------------

# GET - /projects
# Lista resumida de projetos

class DinaboxProjectSummary(BaseModel):
    """Resumo de projeto retornado na listagem (/projects)."""
    # project_id: str = Field(..., alias="project_id")
    # project_description: Optional[str] = Field(None, alias="project_description")
    # ... adicione os campos da listagem aqui
    pass

class DinaboxProjectListResponse(BaseModel):
    """Resposta da listagem paginada de projetos."""
    # page: int
    # total: int
    # projects: List[DinaboxProjectSummary]
    pass


# GET - /v1/project?project_id={id}
# Detalhes completos do projeto (Woodwork, Holes, Inputs)

class DinaboxTemplateFuracaoSchema(BaseModel):
    """Esquema para furações (Holes)."""
    id: str
    ref: str
    uref: str
    name: str
    dimensions: str
    weight: float
    qt: int
    factory_price: float
    buy_price: float
    sale_price: float

    pass
 #"holes": [
    #    {
    #        "id": "minifix",
    #        "ref": "minifix",
    #        "uref": "minifix",
    #        "name": "Minifix e Tambor",
    #        "dimensions": "---",
    #        "weight": 0.1,
    #        "qt": 19,
    #        "factory_price": 0,
    #        "buy_price": 0,
    #        "sale_price": 0

class DinaboxMaterialSchema(BaseModel):
    """ sub schema para agrupar material flat do JSON """

    fabricante: Optional[str] = Field(None, alias="material_manufacturer")
    colecao: Optional[str] = Field(None, alias="material_collection")
    acabamento: str = Field(..., alias="material_name")
    id_material: str = Field(..., alias="material_id")
    m2: Optional[float] = Field(0.0, alias="material_m2")
    preco_fabrica: Optional[float] = Field(0.0, alias="material_factory")
    preco_compra: Optional[float] = Field(0.0, alias="material_buy")
    preco_venda: Optional[float] = Field(0.0, alias="material_sale")
    veio_material = bool = Field(False, alias="material_vein")
    largura_chapa: Optional[str] = Field(None, alias="material width")
    altura_chapa: Optional[str] = Field(None, alias="material_height")
    link_material: Optional[str] = Field(None, alias="material_thumbnail")
    faces: Optional[str] = Field(None, alias="material_face")
    ref_material: Optional[str] = Field(None, alias="material_ref")
    uref_material: Optional[str] = Field(None, alias="material_uref")
    anotacoes: Optional[str] = Field(None, alias="material_note")

    pass
       

class DinaboxOperacoesCNCSchema(BaseModel):
    """ sub schema para mapear as operações de furação
        e usinagens """

    tipo: str = Field(..., alias="t")
    pos_x: Optional[float] = Field(0.0, alias="x")
    pos_y: Optional[float] = Field(0.0, alias="y")
    prof_z: Optional[float] = Field(0.0, alias="z")
    diametro: Optional[float] = Field(0.0, alias="d")
    ref_1: Optional[str] = Field(None, alias="r1")
    ref_2: Optional[str] = Field(None, alias="r2")
    pass 


class DinaboxLadoCNCSchema(BaseModel):
    """ subs squema e agrupamento por face (6)"""

    face_a: Optional[List[DinaboxOperacoesCNCSchema]] = Field(None, alias="A")
    face_b: Optional[List[DinaboxOperacoesCNCSchema]] = Field(None, alias="B")
    face_C: Optional[List[DinaboxOperacoesCNCSchema]] = Field(None, alias="C")
    face_d: Optional[List[DinaboxOperacoesCNCSchema]] = Field(None, alias="D")
    face_e: Optional[List[DinaboxOperacoesCNCSchema]] = Field(None, alias="E")
    face_f: Optional[List[DinaboxOperacoesCNCSchema]] = Field(None, alias="F")
    invertido: bool = Field(False, alias="invert")
    pass

class DinaboxBordaSchema(BaseModel):
    """ sub schema para as fitas de bordo 
        campos base para cada lado de fita de bordo, validando dps
    """
    nome: Optional[str] = None 
    id_material: Optional[str] = Field(None, alias="id")
    uref: str = Field("", alias="uref")
    perimetro: float = Field(0.0, alias="perimeter")
    espessura_fita: str = Field(None, alias="abs")
    preco_fabrica: float = Field(0.0, alias="factory")
    preco_compra: float = Field(0.0, alias="buy")
    preco_venda: float = Field(0.0, alias="sale")

    pass 
             

class DinaboxPecaSchema(BaseModel):
    """Esquema para peças individuais (Parts) dentro de um item de marcenaria."""
    id: str = Field(..., alias="id")
    ref: str = 
    uref: str = "" #pode ser vazio ""
    type: str
    entity: str
    count: int
    code_a: Optional[str] = None  #pode ser null
    code_b: Optional[str] = None #pode ser null
    code_a2: Optional[str] = None
    code_b2: Optional[str] = None
    name: str
    note: str = "" #pode ser vazio ""
    width: float = 0.0 
    height: float = 0.0
    increase_width: float = 0.0
    increase_height: float = 0.0
    thickness: float
    weight: float
    factory_price: float
    buy_price: float
    sale_price: float

    # material: 
    # furacoes
    # borda
    
    pass


class DinaboxModuloSchema(BaseModel):
    """Esquema para itens de marcenaria (Módulos/Conjuntos)."""
    # id: str
    # name: str
    # type: str
    # parts: List[DinaboxPecaSchema] = []
    pass

class DinaboxInsumoSchema(BaseModel):
    """Esquema para insumos e ferragens (Inputs)."""
    # id: str
    # name: str
    # category_name: str
    # qt: float
    pass

class DinaboxProjetoSchema(BaseModel):
    """Esquema mestre para o detalhe completo de um projeto."""
    # project_id: str
    # project_customer_name: Optional[str] = None
    # woodwork: List[DinaboxWoodworkItemSchema] = []
    # holes: List[DinaboxHoleSchema] = []
    # inputs: List[DinaboxInputSchema] = []
    pass
