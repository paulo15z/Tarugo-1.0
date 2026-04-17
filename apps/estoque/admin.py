# apps/estoque/admin.py
from django.contrib import admin
from django.utils.html import format_html

from apps.estoque.models.categoria import CategoriaProduto
from apps.estoque.models.produto import Produto
from apps.estoque.models.movimentacao import Movimentacao
from apps.estoque.models.reserva import Reserva


# ===================== CATEGORIAS =====================
@admin.register(CategoriaProduto)
class CategoriaProdutoAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'ordem']
    list_filter = ['parent']
    search_fields = ['nome']
    ordering = ['ordem', 'nome']
    list_editable = ['ordem']

    def nome_completo(self, obj):
        return str(obj)
    nome_completo.short_description = "Categoria"


# ===================== PRODUTOS =====================
@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """Admin SIMPLES e funcional - Tarugo MVP"""

    list_display = [
        'nome',
        'sku',
        'categoria_nome',
        'unidade_medida',
        'quantidade',
        'estoque_minimo',
        'preco_custo',
        'lote',
        'localizacao',
        'ativo',
    ]

    list_filter = ['categoria', 'ativo', 'unidade_medida']
    search_fields = ['nome', 'sku', 'lote']
    ordering = ['categoria__nome', 'nome']

    readonly_fields = ['criado_em', 'atualizado_em', 'quantidade']

    # Apenas campos reais do model
    list_editable = ['estoque_minimo', 'preco_custo', 'ativo', 'localizacao']

    fieldsets = [
        ("Básico", {
            'fields': ('nome', 'sku', 'categoria', 'unidade_medida', 'ativo')
        }),
        ("Estoque", {
            'fields': ('quantidade', 'estoque_minimo', 'lote', 'localizacao')
        }),
        ("Financeiro", {
            'fields': ('preco_custo',)
        }),
        ("Atributos Específicos", {
            'fields': ('atributos_especificos',),
            'classes': ('collapse',)
        }),
        ("Datas", {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    ]

    def categoria_nome(self, obj):
        return obj.categoria
    categoria_nome.short_description = "Categoria"
    categoria_nome.admin_order_field = 'categoria__nome'


# ===================== MOVIMENTAÇÕES =====================
@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'produto', 'quantidade', 'usuario', 'criado_em']
    list_filter = ['tipo', 'criado_em']
    search_fields = ['produto__nome', 'observacao']
    ordering = ['-criado_em']
    readonly_fields = ['criado_em']


# ===================== RESERVAS =====================
@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['projeto_display', 'origem_externa', 'produto', 'quantidade', 'status', 'criado_em']
    list_filter = ['status', 'origem_externa', 'criado_em']
    search_fields = ['projeto_legado', 'referencia_externa', 'produto__nome', 'produto__sku']
    ordering = ['-criado_em']
    readonly_fields = ['criado_em', 'atualizado_em']

    def projeto_display(self, obj):
        return obj.projeto
    projeto_display.short_description = "Projeto/Pedido"
    projeto_display.admin_order_field = 'referencia_externa'
