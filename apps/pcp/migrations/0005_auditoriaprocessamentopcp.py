from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pcp', '0004_lotepcp_ambientepcp_modulopcp_pecapcp'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditoriaProcessamentoPCP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('processamento_id', models.CharField(db_index=True, max_length=8)),
                ('lote', models.PositiveIntegerField(blank=True, null=True)),
                ('nome_arquivo', models.CharField(max_length=255)),
                ('acao', models.CharField(choices=[('EXCLUSAO', 'Exclusao')], max_length=20)),
                ('motivo', models.TextField()),
                ('criado_em', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('snapshot', models.JSONField(blank=True, default=dict)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Auditoria de Processamento PCP',
                'verbose_name_plural': 'Auditorias de Processamentos PCP',
                'ordering': ['-criado_em'],
            },
        ),
    ]
