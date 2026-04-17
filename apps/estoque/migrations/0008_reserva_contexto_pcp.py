from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("estoque", "0007_reserva_desacopla_bipagem_e_saldo_industrial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reserva",
            name="ambiente",
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name="Ambiente / Setor"),
        ),
        migrations.AddField(
            model_name="reserva",
            name="lote_pcp_id",
            field=models.CharField(
                blank=True,
                help_text="Identificador do lote no PCP.",
                max_length=50,
                null=True,
                verbose_name="Lote PCP",
            ),
        ),
        migrations.AddField(
            model_name="reserva",
            name="modulo_id",
            field=models.CharField(
                blank=True,
                help_text="Quando aplicavel.",
                max_length=50,
                null=True,
                verbose_name="Modulo PCP",
            ),
        ),
        migrations.AddIndex(
            model_name="reserva",
            index=models.Index(fields=["lote_pcp_id"], name="estoque_res_lote_pcp_idx"),
        ),
    ]
