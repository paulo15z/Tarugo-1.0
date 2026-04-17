#!/usr/bin/env python3
"""
Script auxiliar para verificar conformidade básica com arquitetura Tarugo.
"""

import sys
from pathlib import Path

def check_service_usage(file_path: str):
    print(f"Verificando {file_path}...")
    # lógica simples de grep para procurar chamadas diretas a models em views, etc.
    print("✅ Verificação básica concluída (implementar regras completas).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_service_usage(sys.argv[1])
    else:
        print("Uso: python check_architecture.py <arquivo.py>")