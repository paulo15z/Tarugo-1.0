import os
import sys
from pathlib import Path

import django


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from django.utils.text import slugify

from apps.estoque.models import CategoriaProduto, Produto, SaldoMDF
from apps.estoque.services.produto_service import ProdutoService


ESPESSURAS_PADRAO = (6, 15, 18, 25)

MDF_FINISHES = [
    ("Bruma", "Flora", "Instantes da Floresta (2026)"),
    ("Alvorecer", "Flora", "Instantes da Floresta (2026)"),
    ("Tauari Zenite", "Flora", "Instantes da Floresta (2026)"),
    ("Jequitiba Poente", "Flora", "Instantes da Floresta (2026)"),
    ("Crepusculo", "Flora", "Instantes da Floresta (2026)"),
    ("Carvalho Amanhecer", "Flora", "Instantes da Floresta (2026)"),
    ("Freijo Puro", "Duratex", "Essencial Wood"),
    ("Carvalho Brizza", "Duratex", "Essencial Wood"),
    ("Carvalho Malva", "Duratex", "Essencial Wood"),
    ("Branco Diamante", "Duratex", "Essencial"),
    ("Preto", "Duratex", "Essencial"),
    ("Carbono", "Duratex", "Velluto"),
    ("Alecrim", "Duratex", "Velluto"),
    ("Moss", "Duratex", "Velluto"),
    ("Ocre", "Duratex", "Velluto"),
    ("Gianduia", "Duratex", "Cristallo (Alto Brilho)"),
    ("Titanio", "Duratex", "Cristallo (Alto Brilho)"),
    ("Gaia", "Duratex", "Design"),
    ("Nogueira Florida", "Duratex", "Design"),
    ("Azul Marinho", "Guararapes", "Aris (Superfosco)"),
    ("Ametista", "Guararapes", "Aris (Superfosco)"),
    ("Nogueira Ambar", "Guararapes", "Madeiras do Mundo"),
    ("Carvalho Capri", "Guararapes", "Madeiras do Mundo"),
    ("Salerno", "Guararapes", "Madeiras do Mundo"),
    ("Nogueira Rubi", "Guararapes", "Madeiras do Mundo"),
    ("Metal Champagne", "Guararapes", "Metalizados"),
    ("Fresno Acores", "Guararapes", "Syncro Ash"),
    ("Fresno Aveiro", "Guararapes", "Syncro Ash"),
    ("Pau-Ferro", "Guararapes", "Dual Syncro"),
    ("Savana", "Guararapes", "Dual Syncro"),
    ("Cinza Sagrado", "Arauco", "Matt"),
    ("Verde Jade", "Arauco", "Matt"),
    ("Terracotta", "Arauco", "Matt"),
    ("Nude", "Arauco", "Matt"),
    ("Grafite", "Arauco", "Matt"),
    ("Noce Oro", "Arauco", "Woods"),
    ("Louro Freijo", "Arauco", "Woods"),
    ("Carvalho Treviso", "Arauco", "Woods"),
    ("Cumaru", "Arauco", "Woods"),
    ("Jequitiba", "Arauco", "Woods"),
    ("Branco TX", "Leo Madeiras", "Premium"),
    ("Nogueira Sevilha", "Leo Madeiras", "Premium"),
    ("Canario", "Sudati", "Cores"),
    ("Arpoador", "Sudati", "Madeirados"),
    ("Itaparica", "Sudati", "Madeirados"),
    ("Jalapao", "Sudati", "Madeirados"),
    ("Arenas", "Eucatex", "Matt Soft"),
    ("Cinnamon", "Eucatex", "Matt Soft"),
    ("Verde Eucalipto", "Eucatex", "Matt Soft"),
    ("Mineral", "Eucatex", "Lacca AD"),
    ("Argento", "Eucatex", "Lacca AD"),
    ("Carvalho Hanover", "Eucatex", "Wood"),
    # Extras para ampliar catalogo
    ("Off White", "Duratex", "Essencial"),
    ("Cinza Cristal", "Duratex", "Velluto"),
    ("Nero", "Duratex", "Design"),
    ("Linho", "Arauco", "Matt"),
    ("Areia", "Arauco", "Matt"),
    ("Concreto", "Arauco", "Woods"),
    ("Rovere Naturale", "Guararapes", "Madeiras do Mundo"),
    ("Freijo Imperial", "Guararapes", "Syncro Ash"),
    ("Amendoa", "Sudati", "Madeirados"),
    ("Noce Milano", "Eucatex", "Wood"),
]


def build_sku(fabricante: str, acabamento: str) -> str:
    sku = f"MDF-FIN-{slugify(fabricante)}-{slugify(acabamento)}".upper()
    return sku[:100]


def find_existing_mdf_finish(categoria_mdf: CategoriaProduto, nome: str, fabricante: str):
    candidatos = Produto.objects.filter(categoria=categoria_mdf, nome=nome)
    for produto in candidatos:
        atributos = produto.atributos_especificos or {}
        if atributos.get("fabricante") == fabricante:
            return produto
    return candidatos.first()


def ensure_espessuras(produto: Produto) -> None:
    for espessura in ESPESSURAS_PADRAO:
        SaldoMDF.objects.get_or_create(
            produto=produto,
            espessura=espessura,
            defaults={"quantidade": 0},
        )


def upsert_acabamento(categoria_mdf: CategoriaProduto, acabamento: str, fabricante: str, linha: str):
    nome = f"MDF {acabamento}"
    atributos = {
        "acabamento": acabamento,
        "fabricante": fabricante,
        "linha": linha,
    }

    produto_existente = find_existing_mdf_finish(categoria_mdf, nome, fabricante)

    if produto_existente:
        changed_fields = []
        if produto_existente.unidade_medida != "m2":
            produto_existente.unidade_medida = "m2"
            changed_fields.append("unidade_medida")
        if produto_existente.categoria_id != categoria_mdf.id:
            produto_existente.categoria = categoria_mdf
            changed_fields.append("categoria")
        if produto_existente.estoque_minimo != 0:
            produto_existente.estoque_minimo = 0
            changed_fields.append("estoque_minimo")
        if produto_existente.atributos_especificos != atributos:
            produto_existente.atributos_especificos = atributos
            changed_fields.append("atributos_especificos")

        if changed_fields:
            produto_existente.save(update_fields=changed_fields)

        ensure_espessuras(produto_existente)
        fitas_criadas = ProdutoService.sincronizar_fitas_borda_para_mdf(produto_existente)
        return False, fitas_criadas

    sku = build_sku(fabricante, acabamento)
    produto, created = Produto.objects.update_or_create(
        sku=sku,
        defaults={
            "nome": nome,
            "categoria": categoria_mdf,
            "unidade_medida": "m2",
            "estoque_minimo": 0,
            "quantidade": 0,
            "atributos_especificos": atributos,
        },
    )
    ensure_espessuras(produto)
    fitas_criadas = ProdutoService.sincronizar_fitas_borda_para_mdf(produto)
    return created, fitas_criadas


def run() -> None:
    try:
        categoria_mdf = CategoriaProduto.objects.get(
            nome="MDF",
            parent__nome="Matéria-Prima",
        )
    except CategoriaProduto.DoesNotExist:
        print("Erro: categoria MDF nao encontrada. Rode: py manage.py seed_categorias")
        return

    total = len(MDF_FINISHES)
    criados = 0
    existentes = 0
    fitas_criadas = 0

    print(f"Iniciando carga de {total} acabamentos MDF...")

    with transaction.atomic():
        for acabamento, fabricante, linha in MDF_FINISHES:
            created, fitas = upsert_acabamento(categoria_mdf, acabamento, fabricante, linha)
            criados += int(created)
            existentes += int(not created)
            fitas_criadas += fitas

    print("Carga concluida.")
    print(f"Criados: {criados}")
    print(f"Atualizados/Existentes: {existentes}")
    print(f"Fitas de bordo criadas: {fitas_criadas}")


if __name__ == "__main__":
    run()
