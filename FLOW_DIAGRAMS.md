# NeuroLake Platform - Interactive Flow Diagrams

**Mermaid Diagrams for Visualization**

These diagrams can be rendered in GitHub, GitLab, and most modern markdown viewers.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "User Interfaces"
        UI1[Web Dashboard]
        UI2[NDM + NUIC UI]
        UI3[Migration UI]
        UI4[Notebook UI]
    end

    subgraph "API Gateway"
        API[FastAPI Gateway]
        API --> Router1[Query Router]
        API --> Router2[NeuroLake Router]
        API --> Router3[Notebook Router]
        API --> Router4[Migration Router]
    end

    subgraph "Core Logic"
        subgraph "AI Control Plane"
            LLM[LLM Factory]
            Intent[Intent Parser]
            Agent[Agent Orchestrator]
        end

        subgraph "NDM - Data Management"
            Ingest[Smart Ingestor]
            Quality[Quality Assessment]
        end

        subgraph "NUIC - Unified Catalog"
            Catalog[Catalog Engine]
            Lineage[Lineage Graph]
            Schema[Schema Evolution]
        end

        subgraph "Query Engine"
            Optimizer[Query Optimizer]
            Executor[Query Executor]
            Cache[Cache Manager]
        end
    end

    subgraph "Storage Layer"
        PG[(PostgreSQL)]
        Minio[(MinIO)]
        Redis[(Redis)]
        Local[(Local Storage)]
    end

    UI1 --> API
    UI2 --> API
    UI3 --> API
    UI4 --> API

    Router1 --> Optimizer
    Router2 --> Ingest
    Router2 --> Catalog
    Router3 --> Executor

    Ingest --> Quality
    Quality --> Local
    Quality --> Catalog

    Optimizer --> Cache
    Optimizer --> Executor
    Executor --> Local
    Executor --> Minio

    Catalog --> PG
    Lineage --> PG
    Schema --> PG
    Cache --> Redis
```

---

## 2. Data Ingestion Flow (Detailed)

```mermaid
sequenceDiagram
    participant User
    participant UI as NDM UI
    participant API as API Gateway
    participant Ingestor as SmartIngestor
    participant Quality as Quality Engine
    participant Storage as Storage Layer
    participant Catalog as NUIC Catalog
    participant Lineage as Lineage Tracker

    User->>UI: Upload File (CSV/JSON/Parquet)
    UI->>API: POST /api/neurolake/ingestion/upload
    API->>Ingestor: Process File

    activate Ingestor
    Ingestor->>Ingestor: Detect File Type
    Ingestor->>Ingestor: Parse Data
    Ingestor->>Ingestor: Extract Schema
    Ingestor->>Ingestor: Profile Data

    Ingestor->>Quality: Assess Quality (8 Dimensions)
    activate Quality
    Quality-->>Ingestor: Quality Score (0.0-1.0)
    deactivate Quality

    alt Quality >= 0.8
        Ingestor->>Ingestor: Route to Gold Zone
    else Quality >= 0.5
        Ingestor->>Ingestor: Route to Silver Zone
    else Quality < 0.5
        Ingestor->>Ingestor: Route to Bronze Zone
    end

    Ingestor->>Ingestor: Apply Transformations
    Ingestor->>Storage: Write Parquet File
    deactivate Ingestor

    Storage-->>Ingestor: Storage Location

    Ingestor->>Catalog: Register Dataset
    activate Catalog
    Catalog->>Catalog: Store Metadata
    Catalog->>Catalog: Store Schema
    Catalog-->>Ingestor: Dataset ID
    deactivate Catalog

    Ingestor->>Lineage: Track Ingestion Event
    activate Lineage
    Lineage->>Lineage: Record Source
    Lineage->>Lineage: Link to Dataset
    deactivate Lineage

    Ingestor-->>API: Ingestion Result
    API-->>UI: Success Response
    UI-->>User: Display Results
```

---

## 3. Query Execution Flow (Detailed)

```mermaid
sequenceDiagram
    participant User
    participant UI as SQL Editor
    participant API as API Gateway
    participant Intent as Intent Parser
    participant Compliance as Compliance Engine
    participant Optimizer as Query Optimizer
    participant Cache as Cache Manager
    participant Engine as Query Engine
    participant Storage as Storage Layer

    User->>UI: Enter Query (NL or SQL)
    UI->>API: POST /api/query/execute

    alt Natural Language Query
        API->>Intent: Parse Intent
        activate Intent
        Intent->>Intent: Extract Entities
        Intent->>Intent: Generate SQL
        Intent-->>API: SQL Query
        deactivate Intent
    end

    API->>Compliance: Validate Query
    activate Compliance
    Compliance->>Compliance: Detect PII
    Compliance->>Compliance: Check Policies
    Compliance->>Compliance: Apply Masking
    Compliance-->>API: Rewritten Query
    deactivate Compliance

    API->>Optimizer: Optimize Query
    activate Optimizer
    Optimizer->>Optimizer: Parse SQL
    Optimizer->>Optimizer: Estimate Cost
    Optimizer->>Optimizer: Apply Rules
    Optimizer->>Optimizer: Generate Plan
    Optimizer-->>API: Execution Plan
    deactivate Optimizer

    API->>Cache: Check Cache
    activate Cache

    alt Cache Hit
        Cache-->>API: Cached Results
        API-->>UI: Return Results
        UI-->>User: Display Data
    else Cache Miss
        Cache-->>API: Cache Miss
        deactivate Cache

        API->>Engine: Execute Query
        activate Engine
        Engine->>Storage: Scan Data
        Storage-->>Engine: Data Blocks
        Engine->>Engine: Apply Filters
        Engine->>Engine: Apply Joins
        Engine->>Engine: Apply Aggregations
        Engine-->>API: Query Results
        deactivate Engine

        API->>Cache: Store Results
        API-->>UI: Return Results
        UI-->>User: Display Data
    end
```

---

## 4. Lineage Tracking Flow

```mermaid
graph LR
    subgraph "Source Layer"
        S1[CSV File 1]
        S2[JSON File 2]
        S3[Parquet File 3]
    end

    subgraph "Bronze Zone - Raw Data"
        B1[raw_customers]
        B2[raw_orders]
        B3[raw_products]
    end

    subgraph "Silver Zone - Cleaned"
        SV1[cleaned_customers]
        SV2[cleaned_orders]
        SV3[cleaned_products]
    end

    subgraph "Gold Zone - Curated"
        G1[customer_360]
        G2[sales_metrics]
    end

    subgraph "Query Layer"
        Q1[Daily Sales Report]
        Q2[Customer Analytics]
    end

    S1 -->|Ingest| B1
    S2 -->|Ingest| B2
    S3 -->|Ingest| B3

    B1 -->|Transform| SV1
    B2 -->|Transform| SV2
    B3 -->|Transform| SV3

    SV1 -->|Join| G1
    SV2 -->|Join| G1
    SV1 -->|Aggregate| G2
    SV2 -->|Aggregate| G2
    SV3 -->|Join| G2

    G1 -->|Query| Q1
    G2 -->|Query| Q1
    G1 -->|Query| Q2
    G2 -->|Query| Q2

    style S1 fill:#ff9999
    style S2 fill:#ff9999
    style S3 fill:#ff9999
    style B1 fill:#ffcc99
    style B2 fill:#ffcc99
    style B3 fill:#ffcc99
    style SV1 fill:#99ccff
    style SV2 fill:#99ccff
    style SV3 fill:#99ccff
    style G1 fill:#99ff99
    style G2 fill:#99ff99
    style Q1 fill:#ffff99
    style Q2 fill:#ffff99
```

---

## 5. Component Interaction Diagram

```mermaid
graph TB
    subgraph "Frontend Layer"
        Dashboard[Dashboard UI]
        NDM_UI[NDM + NUIC UI]
    end

    subgraph "API Layer"
        Gateway[FastAPI Gateway]
        NL_Router[NeuroLake Router]
    end

    subgraph "Business Logic"
        Ingestor[SmartIngestor]
        NUIC[NUIC Engine]
        CatalogAPI[Catalog API]
        LineageGraph[Lineage Graph]
        SchemaEvo[Schema Evolution]
    end

    subgraph "Data Access"
        DB[(SQLite/PostgreSQL)]
        Files[(Local/MinIO Storage)]
    end

    Dashboard -->|HTTP| Gateway
    NDM_UI -->|HTTP| Gateway
    Gateway --> NL_Router
    NL_Router --> Ingestor
    NL_Router --> CatalogAPI
    NL_Router --> LineageGraph
    NL_Router --> SchemaEvo

    Ingestor --> NUIC
    CatalogAPI --> NUIC
    LineageGraph --> NUIC
    SchemaEvo --> NUIC

    NUIC --> DB
    Ingestor --> Files
    NUIC --> Files

    style Dashboard fill:#e1f5ff
    style NDM_UI fill:#e1f5ff
    style Gateway fill:#fff9c4
    style Ingestor fill:#c8e6c9
    style NUIC fill:#ffccbc
    style DB fill:#f8bbd0
    style Files fill:#f8bbd0
```

---

## 6. Data Quality Assessment Flow

```mermaid
graph TD
    A[Raw Data] --> B[Quality Assessment Engine]

    B --> C1[Completeness Check]
    B --> C2[Accuracy Check]
    B --> C3[Consistency Check]
    B --> C4[Timeliness Check]
    B --> C5[Validity Check]
    B --> C6[Uniqueness Check]
    B --> C7[Integrity Check]
    B --> C8[Conformity Check]

    C1 --> D{Calculate Scores}
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    C6 --> D
    C7 --> D
    C8 --> D

    D --> E[Weighted Average]
    E --> F[Overall Quality Score]

    F --> G{Score >= 0.8?}
    G -->|Yes| H[Route to Gold]
    G -->|No| I{Score >= 0.5?}
    I -->|Yes| J[Route to Silver]
    I -->|No| K[Route to Bronze]

    H --> L[Store with Metadata]
    J --> L
    K --> L

    L --> M[Register in Catalog]
    M --> N[Track Lineage]

    style A fill:#ffcccc
    style F fill:#fff9c4
    style H fill:#c8e6c9
    style J fill:#b3e5fc
    style K fill:#ffccbc
```

---

## 7. Schema Evolution Tracking

```mermaid
graph LR
    V1[Version 1<br/>schema.v1] --> Change1[Add Column<br/>email]
    Change1 --> V2[Version 2<br/>schema.v2]

    V2 --> Change2[Modify Column<br/>phone type]
    Change2 --> V3[Version 3<br/>schema.v3]

    V3 --> Change3[Remove Column<br/>fax]
    Change3 --> V4[Version 4<br/>schema.v4]

    V4 --> Change4[Add Index<br/>on email]
    Change4 --> V5[Version 5<br/>schema.v5]

    subgraph "Change Types"
        CT1[Add Column - Compatible]
        CT2[Remove Column - Breaking]
        CT3[Modify Type - Breaking]
        CT4[Add Index - Compatible]
    end

    style V1 fill:#e3f2fd
    style V2 fill:#e3f2fd
    style V3 fill:#e3f2fd
    style V4 fill:#e3f2fd
    style V5 fill:#c8e6c9
    style Change1 fill:#fff9c4
    style Change2 fill:#ffccbc
    style Change3 fill:#ffccbc
    style Change4 fill:#fff9c4
```

---

## 8. Deployment Architecture (Kubernetes)

```mermaid
graph TB
    subgraph "Ingress Layer"
        Ingress[NGINX Ingress Controller]
    end

    subgraph "Application Pods"
        App1[Dashboard Pod 1]
        App2[Dashboard Pod 2]
        App3[Dashboard Pod 3]
    end

    subgraph "Data Layer"
        subgraph "PostgreSQL"
            PG_Primary[(Primary)]
            PG_Replica1[(Replica 1)]
            PG_Replica2[(Replica 2)]
        end

        subgraph "Redis Cluster"
            Redis1[(Redis Node 1)]
            Redis2[(Redis Node 2)]
            Redis3[(Redis Node 3)]
        end

        subgraph "MinIO Cluster"
            Minio1[(MinIO Node 1)]
            Minio2[(MinIO Node 2)]
            Minio3[(MinIO Node 3)]
            Minio4[(MinIO Node 4)]
        end
    end

    subgraph "Observability"
        Prometheus[Prometheus]
        Grafana[Grafana]
    end

    Ingress --> App1
    Ingress --> App2
    Ingress --> App3

    App1 --> PG_Primary
    App2 --> PG_Primary
    App3 --> PG_Primary

    PG_Primary -.->|Replicate| PG_Replica1
    PG_Primary -.->|Replicate| PG_Replica2

    App1 --> Redis1
    App2 --> Redis2
    App3 --> Redis3

    Redis1 -.->|Cluster| Redis2
    Redis2 -.->|Cluster| Redis3

    App1 --> Minio1
    App2 --> Minio2
    App3 --> Minio3

    Minio1 -.->|Erasure Coding| Minio2
    Minio2 -.->|Erasure Coding| Minio3
    Minio3 -.->|Erasure Coding| Minio4

    App1 -.->|Metrics| Prometheus
    App2 -.->|Metrics| Prometheus
    App3 -.->|Metrics| Prometheus

    Prometheus --> Grafana
```

---

## 9. AI/LLM Integration Flow

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant Gateway
    participant LLM as LLM Factory
    participant Agent as Data Engineer Agent
    participant Engine as Query Engine

    User->>UI: "Show me sales trends for Q4"
    UI->>Gateway: POST /api/ai/nl-to-sql

    Gateway->>LLM: Initialize LLM Client
    activate LLM

    Gateway->>Agent: Create Agent with Context
    activate Agent

    Agent->>Agent: Understand Intent
    Agent->>Agent: Check Available Tables
    Agent->>Agent: Formulate Query Plan

    Agent->>LLM: Generate SQL Query
    LLM-->>Agent: SQL: SELECT * FROM sales...

    Agent->>Agent: Validate SQL
    Agent->>Engine: Execute Query
    deactivate Agent

    activate Engine
    Engine->>Engine: Run Query
    Engine-->>LLM: Query Results
    deactivate Engine

    LLM->>LLM: Format Results
    LLM->>LLM: Add Insights
    LLM-->>Gateway: Natural Language Response
    deactivate LLM

    Gateway-->>UI: Formatted Response
    UI-->>User: Display Results + Insights
```

---

## 10. Catalog Search and Discovery Flow

```mermaid
graph TD
    A[User Search Query] --> B{Search Type}

    B -->|Text Search| C[Full-Text Search]
    B -->|Tag Filter| D[Tag-Based Search]
    B -->|Quality Filter| E[Quality-Based Search]
    B -->|Column Search| F[Column-Level Search]

    C --> G[NUIC Catalog Engine]
    D --> G
    E --> G
    F --> G

    G --> H[Query SQLite/PostgreSQL]
    H --> I[Apply Filters]
    I --> J[Rank Results]
    J --> K[Pagination]

    K --> L[Enrich with Metadata]
    L --> M[Add Quality Scores]
    M --> N[Add Tags]
    N --> O[Add Lineage Info]

    O --> P[Return Results]
    P --> Q[Display in UI]

    Q --> R{User Action}
    R -->|View Details| S[Load Full Metadata]
    R -->|View Lineage| T[Load Lineage Graph]
    R -->|View Quality| U[Load Quality Metrics]
    R -->|View Schema| V[Load Schema History]

    style A fill:#e1f5ff
    style G fill:#ffccbc
    style H fill:#f8bbd0
    style Q fill:#c8e6c9
```

---

## 11. Migration Module Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Migration UI
    participant API as Migration API
    participant Parser as Code Parser
    participant Converter as AI Converter
    participant Generator as NCF Generator
    participant Storage

    User->>UI: Upload Legacy Code
    UI->>API: POST /api/migration/upload
    API->>Storage: Store Original File

    API->>Parser: Parse Code
    activate Parser
    Parser->>Parser: Detect Source Platform
    Parser->>Parser: Extract Logic (10 Dimensions)
    Parser-->>API: Parsed Structure
    deactivate Parser

    API->>Converter: Convert to Target Platform
    activate Converter
    Converter->>Converter: Map Syntax
    Converter->>Converter: Transform Functions
    Converter->>Converter: Optimize Logic
    Converter-->>API: Converted Code
    deactivate Converter

    API->>Generator: Generate NCF Project
    activate Generator
    Generator->>Generator: Create Structure
    Generator->>Generator: Generate Metadata
    Generator->>Generator: Create Framework Files
    Generator-->>API: NCF Package
    deactivate Generator

    API->>Storage: Store Converted Files
    API-->>UI: Conversion Complete
    UI-->>User: Download Results
```

---

## 12. Monitoring and Observability Flow

```mermaid
graph TB
    subgraph "Application"
        App1[Dashboard Instance 1]
        App2[Dashboard Instance 2]
        App3[Dashboard Instance 3]
    end

    subgraph "Metrics Collection"
        App1 -->|/metrics| Prometheus[Prometheus Server]
        App2 -->|/metrics| Prometheus
        App3 -->|/metrics| Prometheus
    end

    subgraph "Metrics Types"
        Prometheus --> M1[Request Count]
        Prometheus --> M2[Response Time]
        Prometheus --> M3[Error Rate]
        Prometheus --> M4[Cache Hit Rate]
        Prometheus --> M5[Query Duration]
        Prometheus --> M6[Ingestion Count]
    end

    subgraph "Alerting"
        Prometheus --> Alert1[High Error Rate]
        Prometheus --> Alert2[Slow Queries]
        Prometheus --> Alert3[Low Cache Hit]
    end

    subgraph "Visualization"
        Prometheus --> Grafana[Grafana]
        Grafana --> D1[System Overview]
        Grafana --> D2[Query Performance]
        Grafana --> D3[Ingestion Stats]
        Grafana --> D4[Quality Metrics]
    end

    Alert1 --> Notify[Alert Manager]
    Alert2 --> Notify
    Alert3 --> Notify
    Notify --> Email[Email/Slack]

    style Prometheus fill:#ff9999
    style Grafana fill:#99ccff
    style Notify fill:#ffcc99
```

---

## How to View These Diagrams

### GitHub/GitLab
These Mermaid diagrams will render automatically when viewing this file on GitHub or GitLab.

### VS Code
Install the "Markdown Preview Mermaid Support" extension to view diagrams in VS Code.

### Online
Copy any diagram code block and paste it into:
- https://mermaid.live/
- https://mermaid.ink/

### Export
Use the Mermaid CLI to export diagrams as PNG or SVG:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i FLOW_DIAGRAMS.md -o output.png
```

---

**Generated**: November 7, 2025
**Format**: Mermaid
**Version**: 1.0
