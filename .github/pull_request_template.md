## Summary

<!-- One sentence: what does this PR change and why? -->

## Change type

- [ ] `feat/report-*` — Report page / visual change only (no model.bim changes)
- [ ] `feat/model-*` — Semantic model change (new table, measure, or relationship)
- [ ] `feat/measures-*` — DAX measure additions or edits
- [ ] `fix/` — Bug fix
- [ ] `chore/` — Config, CI, docs, tooling

## Checklist

### All PRs
- [ ] Branch name follows convention (`feat/`, `fix/`, `chore/`)
- [ ] Commit messages are descriptive (`feat: add compliance score gauge to rule page`)
- [ ] No `.pbix` files committed (PBIP only)
- [ ] No IFC / point cloud files committed (`.ifc`, `.las`, `.laz`, `.e57`)
- [ ] No secrets or credentials in diff

### Model changes (`feat/model-*`)
- [ ] `model.bim` is valid JSON (CI check will confirm)
- [ ] New measures are in the correct measure table (not scattered across fact/dim tables)
- [ ] New relationships are single-direction (dimension → fact)
- [ ] `DimDate` remains marked as the date table
- [ ] No breaking changes to existing column names referenced by DAX measures

### Report changes (`feat/report-*`)
- [ ] No model.bim changes in this PR (model and report changes are separated)
- [ ] New visuals use measures from the DAX library, not implicit measures
- [ ] Slicers sync correctly with the affected pages
- [ ] Conditional formatting thresholds match `dim_severity` risk bands

### Data contract changes
- [ ] `data/schema/data-contract.md` updated
- [ ] `data/samples/*.csv` updated to reflect new columns
- [ ] `analytics_export.py` updated to output new columns
- [ ] Schema version bumped in `export_manifest.json`

## Screenshots (report changes)

<!-- Attach before/after screenshots of affected dashboard pages -->

## Related issues / BCF references

<!-- Link to any related GitHub Issues or BIMGUARD BCF issue IDs -->
