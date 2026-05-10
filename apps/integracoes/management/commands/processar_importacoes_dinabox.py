from __future__ import annotations

import asyncio

from django.core.management.base import BaseCommand

from apps.integracoes.services_importacao import DinaboxImportacaoProjetoService


class Command(BaseCommand):
    help = "Processa a fila de importacoes de projetos Dinabox para ingestao."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--concorrencia", type=int, default=2)

    def handle(self, *args, **options):
        limit = max(1, int(options["limit"]))
        concorrencia = max(1, int(options["concorrencia"]))

        self.stdout.write(
            self.style.NOTICE(
                f"Processando fila Dinabox: limit={limit}, concorrencia={concorrencia}"
            )
        )
        resultados = asyncio.run(
            DinaboxImportacaoProjetoService.processar_fila_async(
                limit=limit,
                concorrencia=concorrencia,
            )
        )

        concluidos = 0
        falhas = 0
        for resultado in resultados:
            if isinstance(resultado, Exception):
                falhas += 1
                self.stdout.write(self.style.ERROR(str(resultado)))
                continue
            concluidos += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{resultado.get('provider', 'provider')}] "
                    f"{resultado.get('project_id', '-')} -> "
                    f"{resultado.get('project_description', '-')}"
                )
            )

        self.stdout.write(
            self.style.NOTICE(
                f"Fila Dinabox finalizada. Concluidos={concluidos}, falhas={falhas}"
            )
        )
