"""
GUIA DE USO - 3 SCHEMAS DINABOX ESPECIALIZADOS

Arquitetura: Um JSON da API Dinabox é roteado para 3 schemas Pydantic especializados,
cada um extraindo os dados relevantes para seu domínio.

Estrutura:
├── dinabox_administrativo.py   (PCP, Financeiro, Compras, Estoque)
├── dinabox_operacional.py      (Bipagem, Fabricação, Rastreabilidade)
├── dinabox_logistico.py        (Expedição, Viagens, Entregas)
└── router.py                   (Coordenador de roteamento)

═════════════════════════════════════════════════════════════════════════════════
"""

# EXEMPLO 1: Usar o router para distribuir dados
# ═════════════════════════════════════════════════

from apps.integracoes.dinabox.schemas.router import DinaboxRouter
import json

# Carregar JSON da API Dinabox
raw_json = json.load(open("response3.json"))

# Criar router
router = DinaboxRouter(raw_json)

# Obter dados para cada frontend/app
admin_data = router.administrativo()      # apps/pcp/ usa isso
ops_data = router.operacional()           # apps/bipagem/ usa isso
log_data = router.logistico()             # apps/logistica/ usa isso


# ═════════════════════════════════════════════════════════════════════════════════
# EXEMPLO 2: Usar schema administrativo para gerar BOM
# ═════════════════════════════════════════════════════════════════════════════════

from apps.integracoes.dinabox.schemas.dinabox_administrativo import DinaboxProjectAdministrativo

admin = DinaboxProjectAdministrativo.model_validate(raw_json)

# Resumo de BOM
bom = admin.get_bom_summary()
print(f"Materiais únicos: {len(bom['materials'])}")
print(f"Hardware necessário: {len(bom['hardware'])}")
print(f"Custo total do projeto: R$ {bom['total_cost']:.2f}")

# Iterar por módulos
for module in admin.woodwork:
    print(f"\nMódulo: {module.name}")
    print(f"  - Peças: {len(module.parts)}")
    print(f"  - Insumos: {len(module.inputs)}")
    print(f"  - Custo: R$ {module.total_cost:.2f}")


# ═════════════════════════════════════════════════════════════════════════════════
# EXEMPLO 3: Usar schema operacional para planning de fábrica
# ═════════════════════════════════════════════════════════════════════════════════

from apps.integracoes.dinabox.schemas.dinabox_operacional import DinaboxProjectOperacional

ops = DinaboxProjectOperacional.model_validate(raw_json)

# Resumo de fabricação
summary = ops.get_manufacturing_summary()
print(f"Total de módulos: {summary['total_modules']}")
print(f"Total de peças: {summary['total_parts']}")
print(f"Total de operações de usinagem: {summary['total_holes']}")
print(f"Total de rebordos a processar: {summary['total_edges_to_band']}")

# Iterar por módulos
for module in ops.woodwork:
    print(f"\nMódulo: {module.name}")
    print(f"  - Peças: {module.total_parts}")
    print(f"  - Furos/rasgos: {module.total_holes}")
    print(f"  - Rebordos: {module.total_edges_to_band}")
    
    # Detalhar peças
    for part in module.parts:
        print(f"    • {part.name}")
        print(f"      - Dimensões: {part.width}x{part.height}x{part.thickness}mm")
        print(f"      - Material: {part.material.name if part.material else 'N/A'}")
        if part.total_holes > 0:
            print(f"      - Usinagem: {part.total_holes} operações")


# ═════════════════════════════════════════════════════════════════════════════════
# EXEMPLO 4: Usar schema logístico para expedição
# ═════════════════════════════════════════════════════════════════════════════════

from apps.integracoes.dinabox.schemas.dinabox_logistico import DinaboxProjectLogistico

log = DinaboxProjectLogistico.model_validate(raw_json)

# Resumo para expedição
shipment = log.get_shipment_summary()
print(f"Projeto: {shipment['project_id']}")
print(f"Customer: {shipment['customer']['name']}")
print(f"Endereço: {shipment['customer']['address']}")
print(f"Conteúdo:")
print(f"  - Módulos: {shipment['content']['total_modules']}")
print(f"  - Itens: {shipment['content']['total_items']}")
print(f"  - Volume: {shipment['content']['estimated_volume_m3']:.2f} m³")

# Detalhar itens para conferência
for item in shipment['items_detail']:
    print(f"  • {item['name']} (Qtd: {item['quantity']})")


# ═════════════════════════════════════════════════════════════════════════════════
# EXEMPLO 5: Integração em aplicações Django
# ═════════════════════════════════════════════════════════════════════════════════

# Em apps/pcp/views.py
from apps.integracoes.dinabox.schemas.router import DinaboxRouter

def processar_projeto_dinabox(request, project_id):
    # Buscar JSON do Dinabox (via API ou banco)
    raw_json = fetch_from_dinabox_api(project_id)
    
    # Distribuir para os apps especializados
    router = DinaboxRouter(raw_json)
    
    # PCP processa dados administrativos
    admin_data = router.administrativo()
    criar_lote_pcp_from_admin(admin_data)
    
    # Bipagem processa dados operacionais
    ops_data = router.operacional()
    criar_modulos_bipagem_from_ops(ops_data)
    
    # Logística processa dados de expedição
    log_data = router.logistico()
    preparar_expedica_from_log(log_data)
    
    return JsonResponse({"status": "success"})


# ═════════════════════════════════════════════════════════════════════════════════
# EXEMPLO 6: Validação de integridade em todos os 3 schemas
# ═════════════════════════════════════════════════════════════════════════════════

router = DinaboxRouter(raw_json)

# Validar em todos os 3 contextos
is_valid = router.validate_all()

if not is_valid:
    print("Erros de validação encontrados:")
    for error in router.errors:
        print(f"  - {error}")
else:
    print("✅ Projeto validado com sucesso em todos os 3 contextos!")


# ═════════════════════════════════════════════════════════════════════════════════
# CAMPOS DISPONÍVEIS EM CADA SCHEMA
# ═════════════════════════════════════════════════════════════════════════════════

"""
ADMINISTRATIVO (admin_data)
├── project_id
├── project_customer_name
├── project_created
├── total_modules
├── total_parts
├── total_inputs
├── total_materials_cost
└── woodwork[]
    ├── ModuleAdministrativo
    ├── parts[]
    │   ├── code_a, code_b, code_a2, code_b2
    │   ├── name
    │   ├── width, height, thickness
    │   ├── material (MaterialInfo)
    │   ├── factory_price, buy_price, sale_price
    │   └── count
    └── inputs[]
        ├── name
        ├── category_name
        ├── qt
        ├── factory_price, buy_price, sale_price
        └── manufacturer


OPERACIONAL (ops_data)
├── project_id
├── project_customer_name
├── total_modules
├── total_parts
├── total_holes
├── total_edges_to_band
└── woodwork[]
    ├── ModuleOperacional
    ├── parts[]
    │   ├── code_a, code_b, code_a2, code_b2
    │   ├── name
    │   ├── width, height, thickness
    │   ├── material (MaterialInfo)
    │   ├── edge_left, edge_right, edge_top, edge_bottom
    │   ├── holes (PartHoles)        ← CRÍTICO para usinagem
    │   └── total_holes (propriedade)
    └── inputs[]
        ├── name
        ├── category_name
        ├── qt
        ├── unit


LOGÍSTICO (log_data)
├── project_id
├── project_description
├── customer
│   ├── customer_id
│   ├── customer_name
│   ├── customer_address
├── total_modules
├── total_volume_m3
├── total_items
└── holes_summary[]
    └── ProjectHoleSummary


═════════════════════════════════════════════════════════════════════════════════
NOTAS IMPLEMENTAÇÃO
═════════════════════════════════════════════════════════════════════════════════

1. **Campos Flat do Dinabox JSON**: Os 3 schemas usam model_validate() para consolidar
   campos prefixados (material_*, edge_*) em estruturas aninhadas.

2. **Material Optional**: Material pode vir None para algumas peças especiais.
   Use `Part.material if part.material else "N/A"`.

3. **Edges**: Podem vir como None, string, ou dict. Sempre normalizado para EdgeDetail().

4. **Validação**: Use router.validate_all() para garantir que o JSON do Dinabox
   passa em todos os 3 contextos antes de processar.

5. **Extensibilidade**: Cada schema tem `extra="allow"` para compatibilidade futura
   com novos campos do Dinabox.

6. **Performance**: Cada schema em router extrai o mesmo JSON 3 vezes. Se a performance
   for crítica, considere memoization ou um single parse com projection.
"""
