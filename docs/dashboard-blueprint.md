# BIMGUARD AI — Power BI Dashboard Blueprint

## Page 1: Executive Overview
**Purpose:** Single-screen health check for project director or client.

| Element | Visual type | Measure / Field |
|---|---|---|
| KPI — Total Issues | Card | `Total Issues` |
| KPI — Open Issues | Card | `Open Issues` |
| KPI — Critical or High | Card | `Critical or High Issues` |
| KPI — Compliance Score | Card | `Compliance Score %` |
| Monthly trend | Line chart | DimDate[YearMonth] × `Total Issues`, `Open Issues` |
| Matrix heatmap | Matrix | Rows: Floor; Cols: Zone; Values: `Total Issues` (conditional format) |
| Status breakdown | Donut | dim_status[StatusName] × `Total Issues` |
| Slicers | Slicer | Project, Date range, Severity |

**Conditional formatting thresholds (matrix):**
- 0 → White
- 1–3 → #FFF3CD
- 4–9 → #F5A623
- 10–19 → #D9534F
- 20+ → #8B0000

---

## Page 2: Rule / Compliance
**Purpose:** Which rules are firing and where compliance score is degrading.

| Element | Visual type | Measure / Field |
|---|---|---|
| Compliance gauge | Gauge | `Compliance Score %` (target: 95%) |
| Rule failures by rule | Horizontal bar | dim_rules[RuleName] × `Compliance Failures` |
| Failures over time | Line | DimDate[YearMonth] × `Compliance Failures` |
| By mechanism | Column | issues[DominantMechanism] × `Compliance Failures` |
| Issue summary table | Table | RuleName, `Total Issues`, `Critical Issues`, `Compliance Score %` |
| Slicers | Slicer | Rule, Model, Project, Date |

---

## Page 3: Spatial / Location
**Purpose:** Where in the building are issues concentrated.

| Element | Visual type | Measure / Field |
|---|---|---|
| Issue density heatmap | Matrix | Rows: Floor; Cols: Zone; Values: `Total Issues` |
| Severity heatmap | Matrix | Rows: Floor; Cols: Zone; Values: `Critical or High Issues` |
| Companion export table | Table | Floor, Zone, `Total Issues`, `Critical Issues`, `High Issues`, `Compliance Score %` |
| Optional spatial plot | Scatter | X/Y from issues[X], issues[Y]; Size: `Total Issues`; Color: SeverityID |
| Slicers | Slicer | System type, Project, Date range |

---

## Page 4: Workflow / History
**Purpose:** Are issues being resolved, or aging and stalling?

| Element | Visual type | Measure / Field |
|---|---|---|
| Avg issue age | KPI card | `Avg Issue Age Days` |
| Overdue issues | KPI card | `Overdue Issues` |
| Resolution rate | KPI card | `Resolution Rate %` |
| Status transitions | Table | issue_status_history — IssueID, FromStatus, ToStatus, ChangedDate, ChangedBy |
| Age distribution | Column | Age band (derived) × Open Issues |
| Slicers | Slicer | Assignee, Severity, Project |

---

## DAX measure library — quick reference

```
Volume:      Total Issues, Open Issues, Closed Issues, Approved Issues
Severity:    Critical Issues, High Issues, Medium Issues, Low Issues, Critical or High Issues
Compliance:  Compliance Failures, Compliance Score %, Failure Rate %
Programme:   Total Cost Impact GBP, Total Delay Days
Assignment:  Assigned Issues, Unassigned Issues, Assigned Rate %
Mechanism:   Galvanic Issues, Crevice Issues, Avg Galvanic Score, Avg Crevice Score
Time:        Issues This Month, Issues Previous Month, Issues MoM Change, Issues MoM Change %
Workflow:    Resolution Rate %, Avg Issue Age Days, Overdue Issues
```
