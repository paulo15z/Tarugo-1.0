def map_linha_to_peca_data(linha):
    return {
        "id_peca": linha.id_peca,
        "descricao": linha.descricao,
        "status": "PENDENTE",
    }
