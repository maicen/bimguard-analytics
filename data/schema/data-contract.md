# BIMGUARD AI — Analytics Data Contract
## Schema version 1.0.0

This document defines the CSV schema that `analytics_export.py` must produce  
and that the Power BI semantic model (`model.bim`) consumes.

Any change to column names, types, or required status is a **breaking change**  
and requires a schema version bump and a `feat/model-*` PR to update `model.bim`.

---

## Folder structure

```
analytics_export/
├── facts/
│   ├── issues.csv
│   └── issue_status_history.csv
├── dimensions/
│   ├── dim_projects.csv
│   ├── dim_models.csv
│   ├── dim_rules.csv
│   ├── dim_locations.csv
│   ├── dim_assignments.csv
│   ├── dim_issue_types.csv
│   ├── dim_severity.csv
│   ├── dim_status.csv
│   └── dim_mechanism.csv
└── meta/
    └── export_manifest.json
```

---

## Fact table: `issues.csv`

One row per compliance issue raised by GC-001 or CC-001.

| Column | Type | Required | Notes |
|---|---|---|---|
| IssueID | Text | ✅ | Format: `ISS-{RunID}-{NNNN}` |
| ProjectID | Text | ✅ | FK → dim_projects |
| ModelID | Text | ✅ | FK → dim_models |
| RuleID | Text | ✅ | FK → dim_rules (`RULE-GC001`, `RULE-CC001`) |
| LocationID | Text | ✅ | FK → dim_locations |
| AssigneeID | Text | ✅ | FK → dim_assignments |
| SeverityID | Text | ✅ | FK → dim_severity (`SEV-LOW/MED/HIGH/CRIT`) |
| StatusID | Text | ✅ | FK → dim_status (`STS-OPEN` etc.) |
| IssueTypeID | Text | ✅ | FK → dim_issue_types |
| IFCGUID | Text | ✅ | IFC element GlobalId (UUID format) |
| BCFGuid | Text | ✅ | BCF 2.1 topic GUID |
| ElementID | Text | ✅ | Internal element identifier |
| ElementType | Text | ✅ | IFC class (`IfcPipeSegment` etc.) |
| MaterialPrimary | Text | ✅ | Primary material name |
| MaterialSecondary | Text | | Secondary material (for galvanic pairs) |
| JointType | Text | | Joint type code (e.g. `flanged_joint`) |
| EnvironmentClass | Text | ✅ | ISO 9223 / EN ISO 15329 class |
| SystemType | Text | | MEP system code (`CHW`, `HWS`, `LTHW` etc.) |
| GalvanicScore | Decimal | ✅ | 0.0000–1.0000 |
| CreviceScore | Decimal | ✅ | 0.0000–1.0000 |
| CombinedScore | Decimal | ✅ | 0.0000–1.0000 |
| DominantMechanism | Text | ✅ | `Galvanic` or `Crevice` |
| X | Decimal | | IFC world coordinate X (metres) |
| Y | Decimal | | IFC world coordinate Y (metres) |
| Z | Decimal | | IFC world coordinate Z (metres) |
| CostImpactGBP | Decimal | ✅ | Estimated remediation cost in GBP |
| DelayDays | Integer | ✅ | Programme delay in working days |
| Mitigation | Text | | Recommended mitigation action |
| Notes | Text | | Free-text notes |
| CreatedDate | Date (ISO 8601) | ✅ | Date issue was raised |
| ClosedDate | Date (ISO 8601) | | Null if still open |
| RunID | Text | ✅ | Compliance run identifier |
| IsOpen | Boolean | ✅ | True if status is Open/In Progress/In Review |
| IsCriticalOrHigh | Boolean | ✅ | True if SeverityID is SEV-CRIT or SEV-HIGH |
| IsComplianceFailure | Boolean | ✅ | True if CombinedScore ≥ 0.35 |

---

## Bridge table: `issue_status_history.csv`

One row per status change event. Many-to-one relationship to `issues` on IssueID.

| Column | Type | Required | Notes |
|---|---|---|---|
| HistoryID | Text | ✅ | Format: `HIST-{10 char hex}` |
| IssueID | Text | ✅ | FK → issues |
| FromStatusID | Text | | Empty string for creation event |
| ToStatusID | Text | ✅ | FK → dim_status |
| ChangedDate | DateTime (ISO 8601) | ✅ | UTC datetime |
| ChangedBy | Text | ✅ | Name or system identifier |
| Comment | Text | | Reason for status change |
| EventType | Text | ✅ | `Created`, `StatusChange`, `Closed`, `Voided` |

---

## Dimension tables

### `dim_projects.csv`
| Column | Type | Required |
|---|---|---|
| ProjectID | Text | ✅ |
| ProjectName | Text | ✅ |
| ProjectCode | Text | |
| Client | Text | |
| Sector | Text | |
| Country | Text | |
| Currency | Text | ✅ |
| BaselineDate | Date | |
| IsActive | Boolean | ✅ |
| CreatedDate | Date | ✅ |

### `dim_models.csv`
| Column | Type | Required |
|---|---|---|
| ModelID | Text | ✅ |
| ProjectID | Text | ✅ |
| ModelName | Text | ✅ |
| IFCPath | Text | ✅ |
| IFCSchema | Text | ✅ (`IFC4`, `IFC2X3`) |
| Discipline | Text | ✅ |
| AuthoringTool | Text | |
| ExportDate | Date | ✅ |
| ElementCount | Integer | ✅ |

### `dim_rules.csv`
| Column | Type | Required |
|---|---|---|
| RuleID | Text | ✅ |
| RuleCode | Text | ✅ |
| RuleName | Text | ✅ |
| MechanismID | Text | ✅ |
| Standard | Text | ✅ |
| Version | Text | ✅ |
| IsActive | Boolean | ✅ |
| Description | Text | |

### `dim_locations.csv`
| Column | Type | Required |
|---|---|---|
| LocationID | Text | ✅ |
| ProjectID | Text | ✅ |
| Floor | Text | ✅ |
| Zone | Text | ✅ |
| Level | Integer | ✅ |
| Building | Text | |
| Wing | Text | |
| Description | Text | |

### `dim_assignments.csv`
| Column | Type | Required |
|---|---|---|
| AssigneeID | Text | ✅ |
| Name | Text | ✅ |
| Discipline | Text | |
| Role | Text | |
| Email | Text | |
| IsActive | Boolean | ✅ |
| ProjectID | Text | ✅ |

### `dim_severity.csv`
| Column | Type | Required |
|---|---|---|
| SeverityID | Text | ✅ |
| SeverityName | Text | ✅ |
| SeverityCode | Text | ✅ |
| RiskBand | Text | ✅ |
| ScoreMin | Decimal | ✅ |
| ScoreMax | Decimal | ✅ |
| Colour | Text | ✅ (hex) |
| BCFPriority | Integer | ✅ |
| SortOrder | Integer | ✅ |

### `dim_status.csv`
| Column | Type | Required |
|---|---|---|
| StatusID | Text | ✅ |
| StatusName | Text | ✅ |
| StatusCode | Text | ✅ |
| IsActive | Boolean | ✅ |
| IsTerminal | Boolean | ✅ |
| SortOrder | Integer | ✅ |

---

## Manifest: `export_manifest.json`

| Field | Type | Notes |
|---|---|---|
| schema_version | String | Must match this document's version |
| run_id | String | Unique per compliance run |
| project_id | String | |
| project_name | String | |
| export_timestamp_utc | ISO DateTime | |
| exported_by | String | |
| ifc_path | String | |
| ifc_schema | String | |
| row_counts | Object | Keys per table above |
| severity_summary | Object | `{"SEV-LOW": N, ...}` |
| cost_impact_total_gbp | Decimal | |
| total_delay_days | Integer | |
| open_issues | Integer | |
| critical_or_high_issues | Integer | |
| compliance_failures | Integer | |

---

## Schema change process

1. Update this document and bump `schema_version`
2. Update `analytics_export.py` to produce the new columns
3. Update `data/samples/*.csv` to include example values
4. Open a `feat/model-*` branch and update `model.bim` to reflect new columns
5. PR to `dev`, verify CI passes, then PR to `main`

**Do not rename or remove existing columns without a major version bump (1.x.x → 2.0.0).**  
Power BI relationships and DAX measures reference column names by string — silent renames break the model.
