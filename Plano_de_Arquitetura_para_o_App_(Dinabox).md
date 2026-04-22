# Plano de Arquitetura para o App `integracoes` (Dinabox)

## 1. Introdução

Este documento detalha a proposta de arquitetura para o aplicativo `integracoes` no projeto Tarugo-1.0, com foco na integração da API do Dinabox. O objetivo principal é garantir uma integração clara, robusta e que suporte o conceito de "Pedido Único" em todo o fluxo de processos do Tarugo.

## 2. Análise do Payload da API Dinabox (JSON de Exemplo)

O JSON de exemplo (`response.json`) do Dinabox revela uma estrutura hierárquica e rica em detalhes, contendo informações sobre:

*   **`project_id` e Metadados do Projeto**: Identificação única do projeto, status, datas de criação/modificação, autor, descrição e notas.
*   **`project_customer_id` e Dados do Cliente**: Identificação e nome do cliente associado ao projeto.
*   **`holes` (Furações)**: Lista de furações com `id`, `ref`, `name`, `dimensions`, `weight`, `qt` (quantidade), e informações de preço.
*   **`woodwork` (Peças de Marcenaria)**: Esta é a seção mais complexa e crucial, contendo uma lista de itens, onde cada item representa uma peça ou um conjunto de peças. Cada item possui:
    *   `id`, `mid`, `ref`, `uref`, `type`, `qt`, `count`, `number`, `name`, `note`.
    *   `width`, `height`, `thickness`, `weight`.
    *   `thumbnail` (URL da imagem).
    *   `material_name`, `material_id`, `material_width`, `material_height`, `material_thumbnail`.
    *   `edge_thickness`, `edge_left`, `edge_right`, `edge_bottom`, `edge_top` (informações de borda).
    *   `parts` (Sub-peças): Uma lista aninhada de peças individuais que compõem o item `woodwork` principal. Cada `part` possui sua própria `id`, `ref`, `name`, `width`, `height`, `thickness`, `material_name`, `material_id`, `edge_left`, `edge_right`, `edge_bottom`, `edge_top`, `holes`, entre outros detalhes.
*   **`inputs` (Insumos/Ferragens)**: Lista de insumos com `id`, `unique_id`, `category_id`, `category_name`, `name`, `description`, `manufacturer`, `ref`, `unit`, `qt` (quantidade), e informações de preço.

## 3. Princípios de Design para o App `integracoes`

Para garantir uma integração eficaz e manutenível, o app `integracoes` seguirá os seguintes princípios:

*   **Desacoplamento**: O app `integracoes` deve ser o único responsável por interagir com a API externa do Dinabox. Ele não deve conter lógica de negócio dos outros módulos (Estoque, PCP), mas sim fornecer dados limpos e mapeados para o domínio do Tarugo.
*   **API-First**: A integração será tratada como uma API externa, com schemas bem definidos para entrada e saída de dados.
*   **Transparência e Rastreabilidade**: Manter um registro claro dos dados brutos recebidos do Dinabox e dos processos de transformação aplicados.
*   **Extensibilidade**: A arquitetura deve permitir a fácil adição de novas integrações ou modificações nas existentes sem impactar os módulos consumidores.
*   **Delegação de Responsabilidade**: Seguir o padrão de `Models`, `Selectors`, `Services` e `Schemas` para organizar o código e as responsabilidades.

## 4. Arquitetura Proposta para o App `integracoes`

### 4.1. Schemas (Pydantic)

Serão definidos schemas Pydantic para representar a estrutura dos dados recebidos da API do Dinabox. Isso garantirá validação de dados e tipagem clara, facilitando o mapeamento para os modelos internos do Tarugo.

**Exemplos de Schemas:**

*   `DinaboxProjectSchema`: Representa a estrutura geral do projeto Dinabox.
    *   `project_id: str`
    *   `project_customer_id: str`
    *   `project_customer_name: str`
    *   `project_description: str`
    *   `holes: List[DinaboxHoleSchema]`
    *   `woodwork: List[DinaboxWoodworkItemSchema]`
    *   `inputs: List[DinaboxInputSchema]`
*   `DinaboxHoleSchema`: Para as furações.
*   `DinaboxWoodworkItemSchema`: Para os itens de marcenaria (que podem conter `parts`).
*   `DinaboxPartSchema`: Para as sub-peças dentro de `woodwork`.
*   `DinaboxInputSchema`: Para os insumos/ferragens.

### 4.2. Services

Os serviços serão responsáveis pela lógica de negócio específica da integração, como a comunicação com a API do Dinabox, a validação dos dados recebidos e a orquestração do mapeamento.

*   `DinaboxAPIService`: Responsável por fazer as requisições HTTP para a API do Dinabox, autenticação e tratamento de erros de comunicação.
*   `DinaboxImportService`: Orquestra o processo de importação de um `project_id` do Dinabox. Ele receberá o `project_id`, chamará o `DinaboxAPIService` para obter os dados brutos, validará-os com os schemas Pydantic e, em seguida, utilizará os mapeadores para transformar esses dados em objetos do domínio do Tarugo.

### 4.3. Mapeadores (Mappers)

Os mapeadores serão classes ou funções dedicadas a transformar os schemas Pydantic (dados do Dinabox) em modelos do Django (domínio do Tarugo). Esta é uma camada crucial para garantir que a lógica de negócio do Tarugo não seja poluída com detalhes da API externa.

**Exemplos de Mapeadores:**

*   `DinaboxProjectMapper`: Mapeia `DinaboxProjectSchema` para um modelo `Pedido` (ou `LotePCP`) do Tarugo.
*   `DinaboxMaterialMapper`: Mapeia `material_name` e `material_id` do Dinabox para `Produto` do Estoque, utilizando o `MapeamentoMaterial` existente ou criando novos se necessário.
*   `DinaboxPecaMapper`: Mapeia `DinaboxPartSchema` (e `DinaboxWoodworkItemSchema`) para `PecaPCP` do Tarugo.
*   `DinaboxInsumoMapper`: Mapeia `DinaboxInputSchema` para `Produto` (ou um novo modelo `Insumo`) do Estoque.

### 4.4. Models (Django ORM)

Os modelos do Django no app `integracoes` devem ser mínimos e focados em persistir dados relacionados à própria integração, como logs de importação, status de sincronização e mapeamentos. Os modelos de domínio (`Pedido`, `LotePCP`, `Produto`, `PecaPCP`) devem residir em seus respectivos aplicativos (`core`, `pcp`, `estoque`).

*   `DinaboxImportacaoProjeto` (existente): Pode ser aprimorado para registrar o `raw_payload` completo e o `resultado_resumo` do processo de importação.
*   `MapeamentoMaterial` (existente): Essencial para vincular materiais do Dinabox aos produtos do Estoque.
*   `DinaboxClienteIndex` (existente): Para indexação local de clientes.

## 5. Fluxo de Integração (Alto Nível)

1.  **Requisição de Importação**: Um `project_id` do Dinabox é recebido (via API, admin, ou comando de gerenciamento).
2.  **Busca na API Dinabox**: O `DinaboxAPIService` busca os dados completos do projeto na API do Dinabox.
3.  **Validação e Normalização**: Os dados brutos são validados contra os schemas Pydantic definidos.
4.  **Mapeamento para Domínio Tarugo**: Os mapeadores transformam os dados validados em objetos do domínio do Tarugo (e.g., `LotePCP`, `PecaPCP`, `Produto`). Esta etapa deve incluir a lógica para o "Pedido Único", garantindo que um `project_id` do Dinabox corresponda a um único `LotePCP` ou `Pedido` no Tarugo.
5.  **Persistência**: Os objetos do domínio do Tarugo são salvos em seus respectivos módulos (PCP, Estoque).
6.  **Registro de Auditoria**: O `DinaboxImportacaoProjeto` é atualizado com o status, payload bruto e resumo do resultado da importação.

## 6. Próximos Passos

Com esta arquitetura em mente, os próximos passos serão:

1.  **Definir Schemas Pydantic**: Criar os arquivos `.py` com as classes Pydantic para cada entidade do Dinabox.
2.  **Implementar `DinaboxAPIService`**: Desenvolver o serviço para comunicação com a API.
3.  **Desenvolver Mapeadores**: Criar os mapeadores para transformar os dados do Dinabox nos modelos do Tarugo, com especial atenção à lógica de "Pedido Único" e ao `MapeamentoMaterial`.
4.  **Implementar `DinaboxImportService`**: Orquestrar o fluxo de importação, utilizando os serviços e mapeadores definidos.

Este plano servirá como base para a implementação do app `integracoes`, garantindo que a integração com o Dinabox seja robusta, escalável e alinhada com a visão de um "Pedido Único" no Tarugo.

## 7. Definição do Fluxo do "Pedido Único" (Dinabox, PCP e Estoque)

O conceito de "Pedido Único" é central para a rastreabilidade e a gestão integrada no Tarugo. Ele representa a visão consolidada de um projeto do Dinabox, transformado em entidades de domínio que fluem pelos módulos de PCP e Estoque. O `project_id` do Dinabox será a chave primária para esse "Pedido Único".

### 7.1. Mapeamento do Projeto Dinabox para o Pedido Único

Quando um `project_id` do Dinabox é importado, ele será mapeado para uma entidade central no Tarugo, que pode ser um `LotePCP` (se o PCP for o módulo central de orquestração de pedidos) ou um novo modelo `Pedido` no `apps.core` ou `apps.integracoes` que agregue informações de todos os módulos. Para manter a simplicidade e alavancar a estrutura existente, propõe-se que o `LotePCP` seja a representação inicial do "Pedido Único" no sistema, com campos adicionais para armazenar metadados do projeto Dinabox.

**Entidade Central: `LotePCP` (aprimorado)**

O modelo `LotePCP` (`apps/pcp/models/lote.py`) será estendido para incluir informações cruciais do projeto Dinabox, garantindo que ele atue como o "Pedido Único":

*   `project_id_dinabox`: `CharField(max_length=64, unique=True, db_index=True)` - Chave primária do projeto Dinabox.
*   `project_status_dinabox`: `CharField(max_length=50)` - Status do projeto no Dinabox.
*   `project_created_dinabox`: `DateTimeField` - Data de criação no Dinabox.
*   `project_last_modified_dinabox`: `DateTimeField` - Última modificação no Dinabox.
*   `project_author_name_dinabox`: `CharField(max_length=255)` - Autor do projeto no Dinabox.
*   `project_description_dinabox`: `TextField` - Descrição do projeto no Dinabox.
*   `project_note_dinabox`: `TextField` - Notas do projeto no Dinabox.
*   `project_customer_address_dinabox`: `TextField` - Endereço do cliente no Dinabox.

Esses campos garantirão que todas as informações de alto nível do projeto Dinabox estejam diretamente associadas ao `LotePCP`, tornando-o o ponto central de referência para o "Pedido Único".

### 7.2. Fluxo de Dados e Interação entre Módulos

O fluxo de dados do Dinabox para o Tarugo, com o `LotePCP` como "Pedido Único", será o seguinte:

1.  **`integracoes` (DinaboxImportService)**:
    *   Recebe o `project_id` do Dinabox.
    *   Chama `DinaboxAPIService` para obter o JSON completo do projeto.
    *   Valida o JSON contra os schemas Pydantic.
    *   **Cria/Atualiza `LotePCP`**: Utiliza o `DinaboxProjectMapper` para criar ou atualizar uma instância de `LotePCP` no módulo `PCP`, preenchendo os novos campos `project_id_dinabox`, `project_customer_name_dinabox`, etc.
    *   **Processa `woodwork` (Peças)**: Itera sobre a lista `woodwork` do JSON. Para cada item e suas `parts` aninhadas:
        *   Utiliza o `DinaboxPecaMapper` para criar instâncias de `PecaPCP` associadas ao `LotePCP` recém-criado/atualizado. Isso inclui mapear dimensões, materiais, bordas e furações.
        *   **Interação com `estoque` (Mapeamento de Materiais)**: Para cada `material_name` e `material_id` das peças, o `DinaboxMaterialMapper` verificará o `MapeamentoMaterial` (`apps/integracoes/models.py`). Se o material não estiver mapeado para um `Produto` existente no `estoque`, ele pode:
            *   Criar um novo `Produto` genérico no `estoque` (com status de "pendente de revisão").
            *   Gerar um alerta para o usuário mapear manualmente o material.
            *   Usar um produto padrão para materiais não mapeados.
    *   **Processa `inputs` (Insumos/Ferragens)**: Itera sobre a lista `inputs` do JSON.
        *   Utiliza o `DinaboxInsumoMapper` para mapear os insumos para `Produto` no `estoque` (ou um modelo `Insumo` dedicado, se criado). Similar ao mapeamento de materiais, pode criar novos produtos ou alertar para mapeamento.
    *   Registra o status da importação em `DinaboxImportacaoProjeto`.

2.  **`PCP` (Planejamento e Controle da Produção)**:
    *   O `LotePCP` (agora o "Pedido Único") e suas `PecaPCP` associadas são a base para o planejamento da produção.
    *   O `PCP` pode então enriquecer essas `PecaPCP` com informações de roteamento, planos de corte, etc.
    *   A interface de `Bipagem` (que será refatorada para consumir os serviços do `PCP`) operará diretamente sobre as `PecaPCP` associadas a este `LotePCP`.

3.  **`estoque` (Gestão de Estoque)**:
    *   Os `Produtos` (materiais e insumos) criados ou atualizados pelo `integracoes` estarão disponíveis no `estoque`.
    *   O `estoque` será responsável por gerenciar a disponibilidade desses produtos, movimentações e reservas, que serão consumidas pelo `PCP` para verificar a viabilidade da produção.

### 7.3. Garantindo a Consistência do Pedido Único

*   **ID Único**: O `project_id_dinabox` no `LotePCP` garante que cada projeto Dinabox corresponda a um único "Pedido Único" no Tarugo.
*   **Atualizações**: Se um projeto Dinabox for modificado, o `DinaboxImportService` deve ser capaz de atualizar o `LotePCP` e suas `PecaPCP` e `Produto` associados, mantendo a integridade dos dados.
*   **Transações**: As operações de importação e mapeamento devem ser transacionais para garantir que o estado do sistema seja consistente em caso de falhas.

Este fluxo estabelece uma clara separação de responsabilidades e um caminho bem definido para os dados do Dinabox se transformarem em um "Pedido Único" gerenciável pelos módulos de PCP e Estoque.
