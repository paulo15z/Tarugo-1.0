from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.integracoes.dinabox.client import (
    DinaboxAPIClient,
    DinaboxAuthError,
    DinaboxRequestError,
)


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _sanitize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


@dataclass
class FlatPart:
    project_id: str
    module_id: str
    module_ref: str
    module_name: str
    module_type: str
    module_qt: int
    part_id: str
    part_ref: str
    part_name: str
    part_entity: str
    part_count: int
    width_mm: float
    height_mm: float
    thickness_mm: float
    material_name: str
    material_id: str
    local_hint: str


class Command(BaseCommand):
    help = "Gera manifesto operacional (JSON/CSV) de um projeto Dinabox para bipagem/conferencia/expedicao."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", required=True, help="ID do projeto na Dinabox.")
        parser.add_argument(
            "--output-dir",
            default="tmp/dinabox-json",
            help="Pasta de saida para os arquivos gerados.",
        )
        parser.add_argument(
            "--prefix",
            default="",
            help="Prefixo opcional dos arquivos. Padrao: project_<ID>.",
        )
        parser.add_argument(
            "--include-raw",
            action="store_true",
            help="Tambem salva o JSON cru retornado por /api/v1/project.",
        )

    def handle(self, *args, **options):
        project_id = _sanitize_text(options["project_id"])
        output_dir = Path(options["output_dir"]).resolve()
        prefix = _sanitize_text(options["prefix"]) or f"project_{project_id}"
        include_raw = bool(options["include_raw"])

        output_dir.mkdir(parents=True, exist_ok=True)

        client = DinaboxAPIClient()

        try:
            project = client.get_project(project_id=project_id)
        except DinaboxAuthError as exc:
            raise CommandError(f"Falha de autenticacao Dinabox: {exc}") from exc
        except DinaboxRequestError as exc:
            raise CommandError(f"Falha de requisicao Dinabox: {exc}") from exc

        manifest = self._build_manifest(project_id=project_id, project=project)

        manifest_file = output_dir / f"{prefix}_manifest.json"
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        modules_file = output_dir / f"{prefix}_modules.csv"
        parts_file = output_dir / f"{prefix}_parts.csv"
        conf_file = output_dir / f"{prefix}_conference.csv"
        exp_file = output_dir / f"{prefix}_expedition.csv"

        self._write_csv(modules_file, manifest["modules"])
        self._write_csv(parts_file, manifest["parts_flat"])
        self._write_csv(conf_file, manifest["groupings"]["conference_checklist"])
        self._write_csv(exp_file, manifest["groupings"]["expedition_checklist"])

        if include_raw:
            raw_file = output_dir / f"{prefix}_raw_project_detail.json"
            raw_file.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Manifesto operacional gerado com sucesso."))
        self.stdout.write(f"Projeto: {project_id}")
        self.stdout.write(f"Modulos: {manifest['totals']['modules']}")
        self.stdout.write(f"Pecas unicas: {manifest['totals']['parts_unique']}")
        self.stdout.write(f"Pecas totais (com quantidade): {manifest['totals']['parts_total_qty']}")
        self.stdout.write(f"JSON: {manifest_file}")
        self.stdout.write(f"CSV modulos: {modules_file}")
        self.stdout.write(f"CSV pecas: {parts_file}")
        self.stdout.write(f"CSV conferencia: {conf_file}")
        self.stdout.write(f"CSV expedicao: {exp_file}")

    def _build_manifest(self, project_id: str, project: dict[str, Any]) -> dict[str, Any]:
        woodwork = project.get("woodwork") or []

        modules: list[dict[str, Any]] = []
        flat_parts: list[FlatPart] = []

        parts_by_material: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"material_name": "", "parts_unique": 0, "parts_total_qty": 0}
        )
        parts_by_thickness: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"thickness_mm": "", "parts_unique": 0, "parts_total_qty": 0}
        )
        parts_by_module: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "module_ref": "",
                "module_name": "",
                "module_id": "",
                "parts_unique": 0,
                "parts_total_qty": 0,
            }
        )
        modules_by_type: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"module_type": "", "modules": 0, "parts_total_qty": 0}
        )

        for module in woodwork:
            module_id = _sanitize_text(module.get("id"))
            module_ref = _sanitize_text(module.get("ref") or module.get("mid") or module_id)
            module_name = _sanitize_text(module.get("name") or module_ref)
            module_type = _sanitize_text(module.get("type") or "unknown")
            module_qt = max(1, _to_int(module.get("qt"), default=1))
            module_width = _to_float(module.get("width"))
            module_height = _to_float(module.get("height"))
            module_depth = _to_float(module.get("thickness"))
            module_thumbnail = _sanitize_text(module.get("thumbnail"))

            module_parts = module.get("parts") or []
            module_parts_unique = 0
            module_parts_total_qty = 0

            for part in module_parts:
                part_id = _sanitize_text(part.get("id"))
                part_ref = _sanitize_text(part.get("ref") or part.get("code_a") or part_id)
                part_name = _sanitize_text(part.get("name") or part_ref)
                part_entity = _sanitize_text(part.get("entity"))
                part_count = max(1, _to_int(part.get("count"), default=1))
                width_mm = _to_float(part.get("width"))
                height_mm = _to_float(part.get("height"))
                thickness_mm = _to_float(part.get("thickness"))
                material_name = _sanitize_text(part.get("material_name"))
                material_id = _sanitize_text(part.get("material_id"))
                local_hint = _sanitize_text(part.get("local") or part.get("note"))

                module_parts_unique += 1
                module_parts_total_qty += part_count

                flat = FlatPart(
                    project_id=project_id,
                    module_id=module_id,
                    module_ref=module_ref,
                    module_name=module_name,
                    module_type=module_type,
                    module_qt=module_qt,
                    part_id=part_id,
                    part_ref=part_ref,
                    part_name=part_name,
                    part_entity=part_entity,
                    part_count=part_count,
                    width_mm=width_mm,
                    height_mm=height_mm,
                    thickness_mm=thickness_mm,
                    material_name=material_name,
                    material_id=material_id,
                    local_hint=local_hint,
                )
                flat_parts.append(flat)

                material_key = material_name or "SEM_MATERIAL"
                parts_by_material[material_key]["material_name"] = material_key
                parts_by_material[material_key]["parts_unique"] += 1
                parts_by_material[material_key]["parts_total_qty"] += part_count

                thickness_key = str(thickness_mm).rstrip("0").rstrip(".") if thickness_mm else "0"
                parts_by_thickness[thickness_key]["thickness_mm"] = thickness_key
                parts_by_thickness[thickness_key]["parts_unique"] += 1
                parts_by_thickness[thickness_key]["parts_total_qty"] += part_count

                module_key = f"{module_ref}|{module_id}"
                parts_by_module[module_key]["module_ref"] = module_ref
                parts_by_module[module_key]["module_name"] = module_name
                parts_by_module[module_key]["module_id"] = module_id
                parts_by_module[module_key]["parts_unique"] += 1
                parts_by_module[module_key]["parts_total_qty"] += part_count

            modules.append(
                {
                    "project_id": project_id,
                    "module_id": module_id,
                    "module_ref": module_ref,
                    "module_name": module_name,
                    "module_type": module_type,
                    "module_qt": module_qt,
                    "module_width_mm": module_width,
                    "module_height_mm": module_height,
                    "module_depth_mm": module_depth,
                    "module_thumbnail": module_thumbnail,
                    "parts_unique": module_parts_unique,
                    "parts_total_qty": module_parts_total_qty,
                }
            )

            modules_by_type[module_type]["module_type"] = module_type
            modules_by_type[module_type]["modules"] += 1
            modules_by_type[module_type]["parts_total_qty"] += module_parts_total_qty

        parts_flat = [vars(item) for item in flat_parts]

        conference_checklist: list[dict[str, Any]] = []
        expedition_checklist: list[dict[str, Any]] = []

        for module_item in modules:
            conference_checklist.append(
                {
                    "project_id": project_id,
                    "module_ref": module_item["module_ref"],
                    "module_name": module_item["module_name"],
                    "module_id": module_item["module_id"],
                    "parts_unique_expected": module_item["parts_unique"],
                    "parts_total_qty_expected": module_item["parts_total_qty"],
                    "check_status": "PENDENTE",
                }
            )

            dominant_material = self._dominant_material(module_item["module_id"], flat_parts)
            expedition_checklist.append(
                {
                    "project_id": project_id,
                    "module_ref": module_item["module_ref"],
                    "module_name": module_item["module_name"],
                    "module_id": module_item["module_id"],
                    "parts_total_qty": module_item["parts_total_qty"],
                    "suggested_volumes": 1,
                    "dominant_material": dominant_material,
                    "expedition_status": "PENDENTE",
                }
            )

        return {
            "project": {
                "project_id": _sanitize_text(project.get("project_id") or project_id),
                "project_description": _sanitize_text(project.get("project_description")),
                "project_status": _sanitize_text(project.get("project_status")),
                "project_customer_id": _sanitize_text(project.get("project_customer_id")),
                "project_customer_name": _sanitize_text(project.get("project_customer_name")),
                "project_author_name": _sanitize_text(project.get("project_author_name")),
                "project_created": _sanitize_text(project.get("project_created")),
                "project_last_modified": _sanitize_text(project.get("project_last_modified")),
            },
            "totals": {
                "modules": len(modules),
                "parts_unique": len(parts_flat),
                "parts_total_qty": sum(item["part_count"] for item in parts_flat),
            },
            "modules": modules,
            "parts_flat": parts_flat,
            "groupings": {
                "modules_by_type": sorted(
                    modules_by_type.values(),
                    key=lambda row: (row["module_type"], -row["modules"]),
                ),
                "parts_by_material": sorted(
                    parts_by_material.values(),
                    key=lambda row: (-row["parts_total_qty"], row["material_name"]),
                ),
                "parts_by_thickness": sorted(
                    parts_by_thickness.values(),
                    key=lambda row: float(row["thickness_mm"]) if row["thickness_mm"] else 0.0,
                ),
                "parts_by_module": sorted(
                    parts_by_module.values(),
                    key=lambda row: (row["module_ref"], row["module_id"]),
                ),
                "conference_checklist": conference_checklist,
                "expedition_checklist": expedition_checklist,
            },
            "automation_readiness": {
                "bipagem_ready": len(parts_flat) > 0,
                "conferencia_ready": len(conference_checklist) > 0,
                "expedicao_ready": len(expedition_checklist) > 0,
                "machine_export_ready": False,
                "notes": [
                    "A API de projeto retorna estrutura de modulo/peca suficiente para rastreio operacional.",
                    "Para exportacao de maquinas, ainda e necessario mapear formato-alvo (ex.: XML/CSV proprietario por maquina).",
                    "Para roteiro de fabrica, recomenda-se acoplar regras de roteiro/plano do modulo PCP antes da importacao.",
                ],
            },
        }

    def _dominant_material(self, module_id: str, flat_parts: list[FlatPart]) -> str:
        acc: dict[str, int] = defaultdict(int)
        for item in flat_parts:
            if item.module_id != module_id:
                continue
            key = item.material_name or "SEM_MATERIAL"
            acc[key] += item.part_count
        if not acc:
            return "SEM_MATERIAL"
        return max(acc.items(), key=lambda x: x[1])[0]

    def _write_csv(self, file_path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            file_path.write_text("", encoding="utf-8")
            return
        fieldnames = list(rows[0].keys())
        with file_path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

