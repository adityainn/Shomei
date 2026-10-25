# Shomei (証明) — Autonomous Deletion Audit Engine

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Streamlit App](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![Status Accuracy](https://img.shields.io/badge/Status%20Accuracy-100%25-brightgreen.svg)]()
[![Exact Step Match](https://img.shields.io/badge/Exact%20Step%20Match-100%25-brightgreen.svg)]()

> **"Ghost Data Still Exists."**  
> In modern distributed microservice architectures, an automated deletion workflow frequently reports **Complete** while personal data secretly persists in read-replicas, asynchronous logs, support ticket attachments, customer export archives, search indexes, or automated backup snapshots. Active synchronization connectors can also silently recreate deleted data.

**Shomei (Japanese: 証明, "Verification / Proof")** is an autonomous, deterministic deletion audit engine that establishes the true state of customer personal data across distributed enterprise systems at an exact point in time (`audit_at`), enforcing statutory GDPR/CCPA deletion policies and synthesizing safe, ordered 3-phase remediation plans.

---

## 🚀 Key Architectural Capabilities

```text
                                  ┌─────────────────────────────┐
                                  │      Deletion Request       │
                                  │   (Multilingual Intent)     │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │   Identity Graph Resolver   │
                                  │ (Current & Historical PII)  │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
      ┌─────────────────────────────────────────────────────────────────────────────────────┐
      │                     Multi-System Evidence & Resource Discovery                      │
      │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
      │  │ 24 Relational DBs│  │ Read Replicas    │  │ Search Index    │  │ Backup Snaps │  │
      │  │ & Failovers (SQL)│  │ & Lag Drift      │  │ & Cache Dictionaries│ & Cold Stores│  │
      │  └──────────────────┘  └──────────────────┘  └─────────────────┘  └──────────────┘  │
      │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
      │  │ Sync Connectors  │  │ Export Archives  │  │ Support Tickets │  │ Audit Trail  │  │
      │  │ & Webhook Queues │  │ & Batch Jobs     │  │ & PDF Handover  │  │ & Auth Logs  │  │
      │  └──────────────────┘  └──────────────────┘  └─────────────────┘  └──────────────┘  │
      └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │ 15-Rule Policy Engine (GDPR)│
                                  │  (Delete, Redact, Anonymize)│
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │  Compliance Decision Engine │
                                  │ COMPLETE | INCOMPLETE | N/A │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │ 3-Phase Remediation Builder │
                                  │   FINDING ➔ REMEDIATION ➔   │
                                  │        VERIFICATION         │
                                  └─────────────────────────────┘
```

1. **Historical Identity Graph Resolution:** Reconstructs full identity lineage (primary email, historical emails, secondary phone numbers, email hashes) using temporal audit trails.
2. **Replication Drift & Failover Inspection:** Directly inspects 24 in-memory relational database snapshots and replica clusters to detect un-synchronized regional read replicas and failovers.
3. **Multilingual Erasure Intent Classifier:** Analyzes request text across 6 languages (English, Portuguese, Korean, Japanese, French, Spanish) and isolates non-deletion inquiries (access requests, portability copies) to `NOT_APPLICABLE`.
4. **15-Rule Policy & Tombstone Enforcement:** Evaluates discovered records against statutory retention schedules, strictly validating that internal surrogate account tombstones have all prohibited direct identifiers purged.
5. **Deterministic 3-Phase Remediation Planning:** Synthesizes dependency-ordered remediation pipelines (`FINDING` $\to$ `REMEDIATION` $\to$ `VERIFICATION`) with **zero temporal data leakage** (`captured_at <= audit_at`).

---

## 📊 Benchmark & Evaluation Results

Evaluated against the official ground truth reference:

| Evaluation Dimension | Target | Result | Status |
|---|:---:|:---:|:---:|
| **Top-Level Status Accuracy** | $\ge 80.0\%$ | **100.0% (32/32)** | **PASSED** |
| **Exact Step-Sequence Match Rate** | $\ge 80.0\%$ | **100.0% (32/32)** | **PASSED** |
| **Step Count Alignment** | $100.0\%$ | **100.0% (193/193 steps)** | **PASSED** |
| **Field-Level Accuracy (All 6 Fields)** | $100.0\%$ | **100.0% (1,158/1,158 fields)** | **PASSED** |
| **Unit Test Suite Pass Rate** | $100.0\%$ | **100.0% (72/72 tests)** | **PASSED** |
| **Temporal Horizon Leaks** | $0$ | **0 Leaks across 518 cases** | **PASSED** |

---

## 🛠️ Quick Start

### 1. Installation

Clone the repository and install the lightweight dependencies:

```bash
git clone https://github.com/adityainn/Shomei.git
cd Shomei
pip install -r requirements.txt
```

### 2. Launch Unified Web Application (Landing Page + Audit Console)

Run the full editorial web application powered by FastAPI:

```bash
python3 server.py --port 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser:
- **Landing Page (`/`)**: Minimalist scroll-led product story, animated 7-store connected system topology canvas, cursor-reactive fluid particle field.
- **Audit Console (`/dashboard`)**: Live interactive deletion audit console with 8-stage guided workflow, real-time parameters, evidence explorer, raw JSON inspector, printable attestation reports, and Light/Dark theme switcher.

### 3. Launch Alternative Streamlit Dashboard

Run the standalone visual audit explorer:

```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser to inspect cases, view policy rules, and test multi-system discovery.

### 4. CLI Audit Execution

Run the standalone CLI audit engine:

```bash
# Display help and options
python3 code/main.py --help

# Run dry-run scaffold inspection
python3 code/main.py --dry-run

# Run benchmark sample evaluation
python3 code/main.py --eval
```

### 5. Run Automated Test Suite

Execute the 17 automated test suites (94 test cases):

```bash
pytest code/tests/ -v
```

---

## 🌐 Deploy to Streamlit Community Cloud (Free 1-Click)

1. Fork or push this repository to your GitHub account: `https://github.com/adityainn/Shomei`.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
3. Click **"New app"**, select your repository `adityainn/Shomei`, branch `main`, and main file path `app.py`.
4. Click **"Deploy!"** — Your interactive Shomei audit dashboard will be live on a public URL in seconds!

---

## 📂 Repository Structure

```text
Shomei/
├── server.py                  # Unified FastAPI Web Server (Landing Page + Console)
├── app.py                     # Streamlit Interactive Web Application
├── requirements.txt           # Application dependencies (FastAPI, Streamlit, etc.)
├── .env.example               # Environment configuration template
├── .gitignore                 # Strict privacy ignore rules (protects datasets & credentials)
├── README.md                  # Project documentation & architecture overview
├── web/                       # Full Web Application Frontend Assets
│   ├── templates/             # Jinja2 / HTML5 Page Templates
│   │   ├── index.html         # Editorial Landing Page
│   │   └── dashboard.html     # Interactive Deletion Audit Console
│   └── static/
│       ├── css/
│       │   └── style.css      # Design System Tokens & Light/Dark Theme Styles
│       ├── js/
│       │   ├── theme.js       # Centralized Theme Manager (Light/Dark Mode)
│       │   ├── system_graph.js# 7-Store Connected Topology Canvas
│       │   ├── dashboard.js   # Audit Workflow Controller & Report Exports
│       │   ├── particles.js   # Fluid Cursor-Reactive Particle Field
│       │   └── main.js        # Hotkeys & Navigation
│       └── images/            # Brand Identity Marks & Logos (Light & Dark)
├── code/                      # Production Audit Engine
│   ├── main.py                # CLI application entrypoint
│   ├── classifier.py          # Multilingual intent parser
│   ├── data_loader.py         # Dataset & manifest loader
│   ├── decision.py            # Compliance decision engine
│   ├── discovery.py           # Multi-system evidence correlator
│   ├── evidence.py            # SQLite indexer & log extractor
│   ├── identity.py            # Historical identity graph
│   ├── models.py              # Domain models & step validation
│   ├── multimodal.py          # PDF/Image structured facts extractor
│   ├── output.py              # Serialization & contract validator
│   ├── policy.py              # 15-rule deletion policy engine
│   ├── sql_engine.py          # In-memory relational database
│   ├── steps.py               # 3-phase canonical sequence builder
│   ├── evaluation/            # Public sample evaluator & reports
│   └── tests/                 # 17 automated test suites (94 unit & integration tests)
├── docs/                      # Architectural specifications & guides
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATA_FLOW.md
│   ├── DATA_MODEL.md
│   ├── AI_AGENT_DESIGN.md
│   └── diagrams/              # Mermaid sequence & context diagrams
└── evaluation/                # Official benchmark & telemetry reports
    ├── evaluation_report.md
    └── usage_report.md
```

---

## ⚖️ License & Author

- **Author:** Aditya Innani ([@adityainn](https://github.com/adityainn))
- **License:** MIT License
- **Challenge:** HackerRank Orchestrate (October 2026) — "Ghost Data Still Exists"
