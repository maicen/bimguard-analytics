# BIMGUARD AI — Analytics Repository

> **OpenBIM corrosion compliance checker** | IFC ISO 16739-1 · BCF 2.1 · Power BI analytics  
> Masters in BIM Management — Zigurat Global Institute of Technology — Group 5 FMP

---

## What this repository contains

| Folder | Contents |
|---|---|
| `bimguard_app/` | Python/Streamlit compliance application |
| `bimguard_app/modules/` | IFC parser, compliance runner, BCF generator, analytics export |
| `powerbi/` | Power BI PBIP project (SemanticModel + Report) |
| `data/schema/` | Data contract specification |
| `data/samples/` | Synthetic sample CSVs for Power BI development |
| `docs/` | Dashboard blueprint, architecture notes |
| `scripts/` | Utility scripts |
| `.github/workflows/` | CI — model validation, data sync |

---

## Architecture

```
IFC file (ISO 16739-1)
        │
        ▼
┌─────────────────────┐
│  ifc_parser.py      │  ← ifcopenshell (OpenBIM)
│  compliance_runner  │  ← GC-001 + CC-001 engines
│  bcf_generator      │  ← BCF 2.1 output
│  analytics_export   │  ← Power BI CSV pack
└─────────────────────┘
        │
        ▼
analytics_export/
  facts/issues.csv              → Fact table (35 columns)
  facts/issue_status_history.csv
  dimensions/dim_*.csv (×9)
  meta/export_manifest.json
        │
        ▼
┌─────────────────────┐
│  Power BI PBIP      │  ← Star schema, DAX measures
│  BIMGuardAnalytics  │  ← 4 dashboard pages
└─────────────────────┘
        │
        ▼
  Power BI Service (via GitHub Git integration)
```

---

## Corrosion compliance engines

| Engine | Standard | Status |
|---|---|---|
| **GC-001** Galvanic Corrosion | NASA-STD-6012 / WorldStainless | ✅ Released v1.0.0 |
| **CC-001** Crevice Corrosion | EN ISO 15329 / ASTM G48 / CIRIA C692 | ✅ Released v1.0.0 |
| **MC-001** Microbially Influenced Corrosion | CIBSE Guide G / ASHRAE 188 | 🔲 Planned |

---

## Getting started

### Run the Streamlit application

```bash
pip install streamlit ifcopenshell laspy numpy pandas plotly
streamlit run bimguard_app/app.py
# Opens at http://localhost:8501
```

### Run analytics export (standalone)

```bash
python bimguard_app/modules/analytics_export.py
# Writes analytics_export/ with all 12 Power BI CSVs
```

### Open the Power BI dashboard

1. Open `powerbi/BIMGuardAnalytics.pbip` in Power BI Desktop
2. In Transform Data → Manage Parameters, set `DataFolderPath` to your local `analytics_export/` folder
3. Refresh — all tables load from the CSV pack

---

## Branch strategy

| Branch | Purpose |
|---|---|
| `main` | Production — protected, requires PR |
| `dev` | Integration — merge feature branches here first |
| `staging` | Pre-production review |
| `feat/measures-*` | New DAX measures |
| `feat/model-*` | Semantic model changes |
| `feat/report-*` | Report page / visual changes |

**Rule:** model changes and report-only changes go on separate feature branches.  
Always merge `feat/*` → `dev` first, then `dev` → `main` via PR.

---

## Data contract

The BIMGUARD AI Streamlit app exports a Power BI-ready CSV pack via `analytics_export.py`.  
The schema is versioned at `data/schema/data-contract.md`.

Current schema version: **1.0.0**

---

## Standards referenced

| Standard | Application |
|---|---|
| ISO 16739-1 | IFC open BIM exchange format |
| buildingSMART BCF 2.1 | Issue tracking with viewpoints |
| NASA-STD-6012 | Galvanic voltage thresholds |
| EN ISO 15329:2007 | Crevice corrosion wetting classes |
| ASTM G48 Method B | Critical Crevice Corrosion Temperature values |
| CIRIA C692 | Stainless steel in construction |
| ISO 19650 | BIM information management |
| Building Safety Act 2022 | Golden Thread requirements |

---

## Licence

Academic project — Zigurat Global Institute of Technology, Masters in BIM Management, Group 5.  
Not licensed for commercial use without permission.
