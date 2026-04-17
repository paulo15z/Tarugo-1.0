from enum import Enum


class TipoMovimentacao(str, Enum):
    """Tipos permitidos no MVP (IA_CONTEXT.md)"""
    ENTRADA = "entrada"
    SAIDA = "saida"
    AJUSTE = "ajuste"

    @classmethod
    def choices(cls):
        return [(member.value, member.value.capitalize()) for member in cls]


class FamiliaProduto(str, Enum):
    """Famílias de produtos para o estoque Tarugo"""
    MDF = "mdf"
    FERRAGENS = "ferragens"
    FITAS_BORDA = "fitas_borda"
    QUIMICOS_INSUMOS = "quimicos_insumos"
    VIDROS_ESPELHOS = "vidros_espelhos"
    EMBALAGENS = "embalagens"
    EPIS_FERRAMENTAS = "epis_ferramentas"
    OUTROS = "outros"

    @classmethod
    def choices(cls):
        return [(member.value, member.value.replace("_", " ").title()) for member in cls]