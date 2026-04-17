from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('pcp', '0005_auditoriaprocessamentopcp'),
        ('bipagem', '0007_alter_eventobipagem_id_alter_loteproducao_id_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EventoBipagem',
        ),
        migrations.CreateModel(
            name='EventoBipagem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('BIPAGEM', 'Bipagem'), ('ESTORNO', 'Estorno')], default='BIPAGEM', max_length=20)),
                ('quantidade', models.PositiveIntegerField(default=1)),
                ('momento', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('usuario', models.CharField(default='SISTEMA', max_length=100)),
                ('localizacao', models.CharField(blank=True, max_length=100)),
                ('motivo', models.TextField(blank=True)),
                ('peca', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eventos_bipagem', to='pcp.pecapcp')),
            ],
            options={
                'verbose_name': 'Evento de Bipagem',
                'verbose_name_plural': 'Eventos de Bipagem',
                'ordering': ['-momento'],
                'indexes': [models.Index(fields=['peca', 'momento'], name='bipagem_eve_peca_id_0d64d9_idx')],
            },
        ),
    ]
