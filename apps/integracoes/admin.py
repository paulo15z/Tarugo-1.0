"""Admin interface para o app integracoes."""

from django.contrib import admin

from .models import DinaboxClienteIndex, DinaboxImportacaoProjeto, MapeamentoMaterial


@admin.register(MapeamentoMaterial)
class MapeamentoMaterialAdmin(admin.ModelAdmin):
    """Admin para mapeamentos de materiais."""

    list_display = ("nome_dinabox", "produto", "fator_conversao", "ativo", "atualizado_em")
    list_filter = ("ativo", "atualizado_em")
    search_fields = ("nome_dinabox", "produto__nome")
    readonly_fields = ("criado_em", "atualizado_em")
    fieldsets = (
        ("Informacoes Basicas", {"fields": ("nome_dinabox", "produto", "fator_conversao", "ativo")}),
        ("Auditoria", {"fields": ("criado_em", "atualizado_em"), "classes": ("collapse",)}),
    )


@admin.register(DinaboxClienteIndex)
class DinaboxClienteIndexAdmin(admin.ModelAdmin):
    """Admin para indice local de clientes Dinabox."""

    list_display = ("customer_id", "customer_name", "customer_type", "customer_status", "synced_at")
    list_filter = ("customer_type", "customer_status", "synced_at")
    search_fields = ("customer_id", "customer_name", "customer_name_normalized")
    readonly_fields = ("customer_name_normalized", "synced_at", "raw_payload")
    fieldsets = (
        (
            "Informacoes do Cliente",
            {"fields": ("customer_id", "customer_name", "customer_name_normalized", "customer_type", "customer_status")},
        ),
        ("Contato", {"fields": ("customer_emails_text", "customer_phones_text"), "classes": ("collapse",)}),
        ("Dados Brutos", {"fields": ("raw_payload",), "classes": ("collapse",)}),
        ("Sincronizacao", {"fields": ("synced_at",), "classes": ("collapse",)}),
    )


@admin.register(DinaboxImportacaoProjeto)
class DinaboxImportacaoProjetoAdmin(admin.ModelAdmin):
    """Admin para acompanhar a fila de importacoes de projetos Dinabox."""

    list_display = (
        "project_id",
        "project_description",
        "project_customer_id",
        "status",
        "prioridade",
        "tentativas",
        "origem",
        "criado_em",
        "concluido_em",
    )
    list_filter = ("status", "origem", "prioridade", "criado_em", "concluido_em")
    search_fields = ("project_id", "project_customer_id", "project_description", "ultimo_erro")
    ordering = ("status", "prioridade", "-criado_em")
    readonly_fields = (
        "project_id",
        "project_customer_id",
        "project_description",
        "status",
        "tentativas",
        "prioridade",
        "origem",
        "payload_bruto",
        "resultado_resumo",
        "ultimo_erro",
        "criado_em",
        "atualizado_em",
        "iniciado_em",
        "concluido_em",
    )
    fieldsets = (
        ("Identificacao", {"fields": ("project_id", "project_customer_id", "project_description", "origem")}),
        ("Execucao", {"fields": ("status", "prioridade", "tentativas", "ultimo_erro")}),
        ("Payloads", {"fields": ("payload_bruto", "resultado_resumo"), "classes": ("collapse",)}),
        ("Auditoria", {"fields": ("criado_em", "atualizado_em", "iniciado_em", "concluido_em"), "classes": ("collapse",)}),
    )
