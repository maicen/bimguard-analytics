# BIMGUARD AI — Analytics Repository

> **OpenBIM corrosion compliance checker** | IFC ISO 16739-1 · BCF 2.1 · Power BI analytics  
> Masters in BIM Management — Zigurat Global Institute of Technology — Group 5 FMP

---

## What this repository contains

This repository is the **analytics deliverable only**: the Power BI semantic
model, the data contract it consumes, and the sample data used to develop
against it. The compliance application that produces that data lives
upstream in [`maicen/bim-guard`](https://github.com/maicen/bim-guard).

| Folder | Contents |
|---|---|
| `powerbi/` | Power BI PBIP project — `BIMGuardAnalytics.SemanticModel/` (incl. `model.bim`) + `BIMGuardAnalytics.Report/`, with `.pbip` and `.pbix` |
| `data/schema/` | `data-contract.md` — the versioned CSV pack specification |
| `data/samples/` | Sample data for Power BI development (rulesets, BCF exports, issue history) |
| `docs/` | `dashboard-blueprint.md` |
| `scripts/` | Utility scripts (currently empty) |
| `.github/workflows/` | CI — `validate-model.yml`, `analytics-schema-check.yml` |

---

## Architecture

```
UPSTREAM — maicen/bim-guard
  IFC file (ISO 16739-1)
        │
        ▼
  ifc_parser / compliance_runner   ← ifcopenshell, corrosion engines
  bcf_generator                    ← BCF 2.1 output
  analytics export                 ← Power BI CSV pack
        │
        ▼
  analytics_export/
    facts/issues.csv               → Fact table (35 columns)
    facts/issue_status_history.csv
    dimensions/dim_*.csv (×9)
    meta/export_manifest.json
════════════════════════════════════ repository boundary
THIS REPOSITORY
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

The boundary is the CSV pack defined in `data/schema/data-contract.md`.
Everything above it is produced upstream; everything below it is this
repository's responsibility.

---

## Engine Coverage

Which corrosion engines reach this repository's data contract. Status is
what the upstream engines actually do, not what is specified for them.

| Engine | Standard | Status |
|---|---|---|
| **GC-001** Galvanic Corrosion | NASA-STD-6012 / WorldStainless | ✅ Implemented — reaches the CSV pack |
| **CC-001** Crevice Corrosion | EN ISO 15329 / ASTM G48 / CIRIA C692 | ✅ Implemented — reaches the CSV pack |
| **MC-001** Microbially Influenced Corrosion | CIBSE Guide G / ASHRAE 188 | ✅ Implemented — reaches the CSV pack |
| **MM-001** Material–Media Compatibility | — | 🔲 Post-FMP roadmap |
| **XM-001** Cross-Material Galvanic | — | 🔲 Post-FMP roadmap |

**Validation caveat.** A 37-model sweep over third-party IFC files
(Appendix A in the core repository) found that the three implemented
engines are limited less by their logic than by the data available in
federated models: the inputs they require are present on a very small
fraction of real elements, so their output on third-party models is close
to constant. Dashboard figures derived from them should be read as
demonstrating the analytics pipeline, not as calibrated corrosion risk.
MM-001 and XM-001 do not currently load against their shipped rule packs
and produce no findings at all — hence roadmap, not released.

---

## Getting started

### Open the Power BI dashboard

1. Open `powerbi/BIMGuardAnalytics.pbip` in Power BI Desktop
2. In Transform Data → Manage Parameters, set `DataFolderPath` to an
   `analytics_export/` folder produced upstream, or to `data/samples/` to
   develop against the sample data in this repository
3. Refresh — all tables load from the CSV pack

### Produce the CSV pack

The export tooling is **not** in this repository. Generate the pack from
the upstream application ([`maicen/bim-guard`](https://github.com/maicen/bim-guard))
and point `DataFolderPath` at the result. The pack's required shape —
`facts/issues.csv` (35 columns), `facts/issue_status_history.csv`,
`dimensions/dim_*.csv` (×9), `meta/export_manifest.json` — is specified in
`data/schema/data-contract.md`, which is the authority for the contract
regardless of which tool writes it.

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

The upstream BIMGUARD AI application exports a Power BI-ready CSV pack.  
The schema is versioned at `data/schema/data-contract.md` and is the
interface between the two repositories: this repository consumes the pack
and makes no assumptions about how it was produced.

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
