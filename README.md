## 🗺 Architecture

FlowClaw is a multi-tenant FastAPI backend behind a Next.js frontend. An auth layer (JWT + RBAC + org isolation) guards every route; three agent surfaces share one grounded RAG core, and every agent run is traced to Langfuse and surfaced in the in-app Observability dashboard.

```mermaid
flowchart TB
    subgraph Client["🖥️ Frontend — Next.js App Router"]
        Landing["Landing"]
        Login["Login / Register"]
        Dash["Dashboard"]
        subgraph Surfaces["Agent Surfaces"]
            QA["Document Q&A"]
            An["Analytics Agents"]
            Sup["Support Claw"]
            Obs["AI Observability"]
        end
    end

    Auth{{"🔐 Auth Layer<br/>JWT · bcrypt · RBAC<br/>org isolation"}}

    subgraph API["⚙️ FastAPI Backend"]
        AuthR["/auth/*"]
        DocR["/documents/*"]
        AnR["/analytics/*"]
        SupR["/support/*"]
        ObsR["/observability/*"]
    end

    subgraph Core["🧠 Shared RAG Core"]
        Embed["SentenceTransformers<br/>(all-MiniLM-L6-v2)"]
        FAISS[("FAISS<br/>vector index")]
    end

    subgraph Agents["🤖 Agent Logic"]
        Orch["support/orchestrator.py<br/>(deterministic control flow)"]
        Hermes["Hermes Agent runtime"]
        Eng["analytics/engine.py<br/>(pandas · numpy · sklearn)"]
        Narr["analytics/narrator.py"]
    end

    Groq["☁️ Groq LLM<br/>llama-3.x"]
    Drive["☁️ Google Drive<br/>(OAuth 2.0)"]
    Mongo[("MongoDB<br/>users · orgs · tickets<br/>metadata · audit")]
    LF["☁️ Langfuse<br/>(tracing, 8s timeout)"]

    Client --> Auth
    Login --> AuthR
    QA --> DocR
    An --> AnR
    Sup --> SupR
    Obs --> ObsR

    Auth -.guards.-> API

    DocR --> Core
    DocR --> Drive
    SupR --> Orch
    AnR --> Eng
    AnR --> Drive

    Orch --> Hermes
    Orch --> Core
    Hermes --> Groq
    Eng --> Narr
    Narr --> Groq
    Core --> Embed
    Embed --> FAISS

    AuthR --> Mongo
    SupR --> Mongo
    DocR --> Mongo
    AnR --> Mongo

    Orch -.traces.-> LF
    ObsR -.reads.-> LF

    classDef ext fill:#1e293b,stroke:#475569,color:#e2e8f0;
    classDef store fill:#312e81,stroke:#6366f1,color:#e0e7ff;
    class Groq,Drive,LF ext;
    class Mongo,FAISS store;
```

### Support Escalation Claw — workflow

The escalation decision is a **deterministic rule in Python, not the LLM** — so a critical issue is always escalated regardless of how confident the drafted answer sounds.

```mermaid
flowchart LR
    Q["Support query<br/>+ JWT (org-scoped)"] --> C["Classify<br/>issue type + severity<br/>(Hermes, keyword fallback)"]
    C --> R["Retrieve SOP context<br/>(FAISS, scoped to<br/>sop/faq/policy/runbook)"]
    R --> D["Draft grounded response<br/>(Hermes — says 'I don't know'<br/>rather than invent)"]
    D --> E{"Escalation decision<br/><b>deterministic rule</b>,<br/>not the LLM"}

    E -->|"grounded &<br/>low/medium"| RES["✅ RESOLVED"]
    E -->|"ungrounded draft"| TIC["🎫 TICKETED<br/>(human review)"]
    E -->|"high / critical"| ESC["🚨 ESCALATED"]

    RES --> A[("Audit trail + ticket<br/>persisted to MongoDB<br/>by run_id, org-scoped")]
    TIC --> A
    ESC --> A

    A -.every step traced.-> LF["☁️ Langfuse<br/>→ Observability dashboard"]

    classDef decision fill:#7c2d12,stroke:#f97316,color:#ffedd5;
    class E decision;
