from django.contrib import admin

from apps.integracoes.models import DinaboxClienteIndex, MapeamentoMaterial


@admin.register(MapeamentoMaterial)
class MapeamentoMaterialAdmin(admin.ModelAdmin):
    list_display = ("nome_dinabox", "produto", "fator_conversao", "ativo", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("nome_dinabox", "produto__nome")


@admin.register(DinaboxClienteIndex)
class DinaboxClienteIndexAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "customer_name", "customer_type", "customer_status", "synced_at")
    list_filter = ("customer_type", "customer_status")
    search_fields = ("customer_id", "customer_name", "customer_emails_text", "customer_phones_text")
