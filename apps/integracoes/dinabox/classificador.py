def classificar_insumo(descricao: str, unidade: str) -> str:
    desc = descricao.lower()

    if "mdf" in desc or unidade == "m2":
        return "chapa"

    if "fita" in desc:
        return "fita_borda"

    if "dobradiça" in desc or "corrediça" in desc:
        return "ferragem"

    if unidade == "metro":
        return "perfil"

    return "outros"
