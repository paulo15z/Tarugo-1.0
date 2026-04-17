import csv
from io import StringIO


def parse_corte(csv_content: str):
    reader = csv.DictReader(StringIO(csv_content), delimiter=';')

    pecas = []

    for row in reader:
        try:
            pecas.append({
                "descricao": row.get("DESCRIÇÃO DA PEÇA"),
                "material": row.get("MATERIAL DA PEÇA"),
                "largura": _to_float(row.get("LARGURA DA PEÇA")),
                "altura": _to_float(row.get("ALTURA DA PEÇA")),
                "espessura": _to_float(row.get("ESPESSURA")),
                "quantidade": int(row.get("QUANTIDADE") or 1),
            })
        except Exception:
            continue

    return {"pecas": pecas}


def _to_float(val):
    if not val:
        return None
    return float(val.replace(",", "."))
