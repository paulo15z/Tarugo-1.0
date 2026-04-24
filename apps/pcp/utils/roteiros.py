"""
Shim para manter compatibilidade com o fluxo de processamento via DataFrame.
Redireciona para as implementações que residem em apps.pcp.services.utils.
"""
from apps.pcp.services.utils import calcular_roteiro, determinar_plano_de_corte

__all__ = ['calcular_roteiro', 'determinar_plano_de_corte']
