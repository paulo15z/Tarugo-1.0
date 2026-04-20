# 🏗️ Proposta de Infraestrutura e Processamento Assíncrono: Tarugo

## 1. Diagnóstico da Infraestrutura Atual (Proxmox CT)

Atualmente, o Tarugo opera em um ambiente restrito (2GB RAM / 20GB Disco) com SQLite. Para suportar o "Gêmeo Digital" e a riqueza de dados da API Dinabox, precisamos de uma base de dados que suporte concorrência, integridade referencial e consultas complexas (indexação de peças, módulos e furações).

### Limitações do SQLite para Produção:
*   **Concorrência**: Bloqueios de escrita (Database is locked) ao processar grandes importações de forma assíncrona.
*   **Tipagem**: Falta de suporte nativo robusto para `JSONField` (essencial para os metadados do Dinabox).
*   **Escalabilidade**: Dificuldade em manter backups consistentes e alta disponibilidade.

---

## 2. Nova Arquitetura de Dados (PostgreSQL)

A recomendação é a migração para o **PostgreSQL**. No Proxmox, você tem duas opções principais:

### Opção A: PostgreSQL no mesmo CT (Vertical)
*   **Prós**: Menor latência, configuração simples.
*   **Contras**: Disputa de recursos (RAM) entre o Django e o Banco.
*   **Ajuste**: Com 2GB de RAM, é possível rodar ambos se o tráfego for baixo, mas o banco deve ser tunado para consumir pouco (ex: `shared_buffers = 256MB`).

### Opção B: PostgreSQL em um novo CT dedicado (Horizontal) - **RECOMENDADO**
*   **Prós**: Isolamento total. Se o Django travar por falta de memória, o banco continua íntegro. Facilita backups via Proxmox (Snapshots do CT do banco).
*   **Configuração Sugerida**: CT Debian/Ubuntu com 1GB RAM e 10GB Disco (SSD).

---

## 3. Processamento Assíncrono (Celery + Redis)

Para evitar que o usuário espere a API do Dinabox responder e o Django processar milhares de peças, utilizaremos o padrão **Async Task**.

### Fluxo de Sinalização:
1.  **Ação do Usuário**: O projetista marca o ambiente como "Finalizado" no Tarugo.
2.  **Trigger**: O Django dispara uma tarefa assíncrona (Celery Task).
3.  **Processamento**:
    *   A Task busca o `project_id` na API Dinabox.
    *   Valida os dados via **Pydantic Schemas** (criados anteriormente).
    *   Persiste nos **Modelos Canônicos** (PostgreSQL).
    *   Notifica o usuário via WebSocket ou atualização de status na UI.

### Infraestrutura Necessária:
*   **Redis**: Atuará como o "Broker" (mensageiro) para o Celery. Pode rodar no mesmo CT do Django (consome pouquíssima RAM, ~100MB).

---

## 4. Roadmap de Implementação

| Etapa | Ação | Objetivo |
| :--- | :--- | :--- |
| **1. DB Migration** | Instalar PostgreSQL e migrar dados do SQLite. | Estabilidade e suporte a JSONField. |
| **2. Async Setup** | Instalar Redis e configurar Celery no Django. | Desacoplar a API externa do tempo de resposta da UI. |
| **3. Signal Logic** | Implementar o endpoint/botão de "Sincronizar" ou "Finalizar". | Iniciar o fluxo de captura de dados. |
| **4. Indexer Task** | Criar a task que consome a API e popula o banco. | Automação do Gêmeo Digital. |

---

## 5. Próximos Passos Sugeridos

1.  **Criar um novo CT no Proxmox** para o PostgreSQL (ou preparar o atual para a instalação).
2.  **Configurar o `django-environ`** para gerenciar as credenciais do banco e do Redis.
3.  **Implementar a Task de Importação** usando os schemas Pydantic que já validamos.

---
**Autor**: Manus AI
**Data**: 09 de abril de 2026

## 6. Fluxo de Sinalização e Processamento Assíncrono

Para garantir que o sistema seja responsivo e que o processamento de dados pesados não bloqueie a interface do usuário, propomos o seguinte fluxo de trabalho baseado em eventos:

### 6.1. O Gatilho (Trigger)
O fluxo se inicia quando um usuário (Projetista ou Comercial) altera o status de um projeto para "Finalizado" ou clica em um botão de "Sincronizar com Dinabox".

*   **Django Signal**: Podemos usar um `post_save` signal no modelo de Projeto ou uma chamada direta no `Service` correspondente.
*   **Ação**: O Django envia uma mensagem para o Redis (Broker) contendo o `project_id` e o `user_id`.

### 6.2. A Fila de Processamento (Celery Worker)
Um worker do Celery, rodando em segundo plano, captura a mensagem e inicia a tarefa `import_dinabox_project_task`.

1.  **Fetch**: O worker faz a requisição para a API Dinabox.
2.  **Validate**: O payload JSON é passado pelo schema Pydantic (`DinaboxProjectResponse`).
3.  **Persist**: Os dados validados são salvos no PostgreSQL, criando a hierarquia de `DinaboxProject`, `DinaboxModule` e `DinaboxPart`.
4.  **Notify**: Ao finalizar, o worker pode disparar uma notificação via WebSocket (Django Channels) para atualizar a tela do usuário em tempo real, ou simplesmente atualizar um campo `last_sync_status` no banco.

### 6.3. Vantagens do Modelo Assíncrono
*   **Resiliência**: Se a API do Dinabox estiver lenta ou fora do ar, o Celery pode tentar novamente (retries) sem que o usuário perceba.
*   **Escalabilidade**: Se o volume de projetos aumentar, você pode simplesmente subir mais workers do Celery no Proxmox sem alterar o código da aplicação.
*   **User Experience**: O usuário recebe um feedback imediato ("Importação iniciada") e pode continuar trabalhando em outras tarefas.

---

## 7. Conclusão e Próximos Passos

A transição para o PostgreSQL e a adoção de processamento assíncrono são os pilares que permitirão ao Tarugo se tornar um SaaS de alto nível. Com essa estrutura, o "Gêmeo Digital" deixará de ser apenas um conceito e passará a ser uma base de dados viva e consultável para todas as etapas da fábrica.

**Próxima Ação Recomendada**: Iniciar a configuração do ambiente PostgreSQL no Proxmox e a instalação do Redis/Celery no CT atual do Tarugo.
