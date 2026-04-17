from bs4 import BeautifulSoup
import re
from ..classificador import classificar_insumo

def parse_compras(html: str):
    soup = BeautifulSoup(html, "html.parser")

    
    resultado = {
        "projeto": {},
        "cliente": {},
        "insumos": []
    }

    categoria_atual = None

    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)

        match_categoria = re.match(r"(\d+)\s*-\s*(.*)", text)
        if match_categoria:
            categoria_atual = match_categoria.group(2).strip() or "SEM_CATEGORIA"
            continue

        for row in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in row.find_all("td")]

            if len(cols) != 4:
                continue

            indice, qtd, desc, dim = cols

            if not indice.isdigit():
                continue

            if "INSUMO DELETADO" in desc:
                continue

            resultado["insumos"].append({
                "categoria": categoria_atual,
                "descricao": desc,
                "quantidade": _parse_qtd(qtd),
                "dimensoes": _parse_dim(dim)
            })

    return resultado


def _parse_qtd(qtd):
    qtd = qtd.replace(",", ".")
    match = re.search(r"[\d\.]+", qtd)

    if not match:
        return {"valor": 0, "unidade": "un"}

    valor = float(match.group())

    if "m²" in qtd:
        unidade = "m2"
    elif "mt" in qtd:
        unidade = "metro"
    else:
        unidade = "un"

    return {"valor": valor, "unidade": unidade}


def _parse_dim(dim):
    if not dim or dim == "---":
        return None

    match = re.match(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", dim)
    if match:
        return {
            "largura": int(match.group(1)),
            "altura": int(match.group(2)),
            "unidade": "mm"
        }

    return {"raw": dim}
