# Generated manually for Sprint 01 foundation
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("estoque", "0006_saldomdf_preco_custo"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="reserva",
            name="pedido",
        ),
        migrations.AddField(
            model_name="reserva",
            name="origem_externa",
            field=models.CharField(
                choices=[("pcp", "PCP"), ("manual", "Manual"), ("integracao", "Integracao")],
                default="pcp",
                max_length=20,
                verbose_name="Origem",
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="referencia_externa",
            field=models.CharField(
                blank=True,
                help_text="Codigo externo (pedido, lote, modulo ou projeto).",
                max_length=120,
                null=True,
                verbose_name="Referencia Externa",
            ),
        ),
        migrations.AlterField(
            model_name="reserva",
            name="quantidade",
            field=models.PositiveIntegerField(verbose_name="Quantidade"),
        ),
        migrations.AddIndex(
            model_name="reserva",
            index=models.Index(fields=["status", "produto"], name="estoque_res_status_87f295_idx"),
        ),
    ]
