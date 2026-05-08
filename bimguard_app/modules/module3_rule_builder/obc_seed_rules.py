"""
module3_rule_builder/obc_seed_rules.py
----------------------------------------
Pre-built OBC Part 9 compliance rules.
These seed the database before any PDF is uploaded,
so rules.db always has a baseline to work from.

Run directly to seed the database:
    python -m module3_rule_builder.obc_seed_rules

Or import and call:
    from module3_rule_builder.obc_seed_rules import seed_rules
    seed_rules(store, generator)

Field names match the rich rule schema:
    ref           — OBC section reference
    desc          — plain-English description
    target        — IFC class name
    rule_type     — one of the 8 valid rule types
    operator      — one of the valid operators
    check_value   — single threshold value (None for between/exists)
    value_min     — lower bound for numeric_range / between
    value_max     — upper bound for numeric_range / between
    unit          — measurement unit string
    severity      — mandatory | recommended | informational
    property_set  — Pset name (auto-filled by RuleGenerator if omitted)
    property_name — IFC property to measure
"""

try:
    from config import DB_PATH, SOURCE_DOC_SEED
    from module3_rule_builder.rule_generator import RuleGenerator
    from module3_rule_builder.rule_store import RuleStore
except ImportError:
    from app.modules.config import DB_PATH, SOURCE_DOC_SEED
    from app.modules.module3_rule_builder.rule_generator import RuleGenerator
    from app.modules.module3_rule_builder.rule_store import RuleStore


# ── PRE-BUILT OBC PART 9 RULES ────────────────────────────────────────────────
# All rules use the rich schema field names. RuleGenerator._apply_defaults()
# fills any missing optional fields before saving.

OBC_SEED_RULES = [
    # ── STAIR WIDTH ──────────────────────────────────────────────────────────
    {
        "ref": "9.8.2.1.(2)",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Exit stair serving house/dwelling — minimum clear width 860 mm",
    },
    {
        "ref": "9.8.2.1.(4)",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "At least one stair between floor levels — minimum width 860 mm",
    },
    # ── HEADROOM ─────────────────────────────────────────────────────────────
    {
        "ref": "9.8.2.2.(3)",
        "rule_type": "spatial_clearance",
        "target": "IfcStairFlight",
        "property_name": "HeadroomClearance",
        "operator": ">=",
        "check_value": 1950,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Minimum vertical headroom over full stair width — 1950 mm",
    },
    {
        "ref": "9.8.2.2.(3)",
        "rule_type": "spatial_clearance",
        "target": "IfcSlab",
        "property_name": "HeadroomClearance",
        "operator": ">=",
        "check_value": 1950,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Minimum headroom clearance over stair landings — 1950 mm",
    },
    # ── RISER HEIGHT ─────────────────────────────────────────────────────────
    {
        "ref": "Table 9.8.4.1",
        "rule_type": "numeric_range",
        "target": "IfcStairFlight",
        "property_name": "RiserHeight",
        "operator": "between",
        "check_value": None,
        "value_min": 125,
        "value_max": 200,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Private stair riser height — min 125 mm, max 200 mm",
    },
    # ── TREAD DEPTH ──────────────────────────────────────────────────────────
    {
        "ref": "Table 9.8.4.1",
        "rule_type": "numeric_range",
        "target": "IfcStairFlight",
        "property_name": "TreadDepth",
        "operator": "between",
        "check_value": None,
        "value_min": 255,
        "value_max": 355,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Private stair tread run/depth — min 255 mm, max 355 mm",
    },
    # ── FLIGHT HEIGHT ─────────────────────────────────────────────────────────
    {
        "ref": "9.8.3.3.(1)",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "FlightHeight",
        "operator": "<=",
        "check_value": 3700,
        "unit": "mm",
        "severity": "recommended",
        "desc": "Maximum vertical height per stair flight — 3700 mm",
    },
    # ── LANDINGS ─────────────────────────────────────────────────────────────
    {
        "ref": "9.8.6.3",
        "rule_type": "numeric_comparison",
        "target": "IfcSlab",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Landing width must be at minimum equal to stair width — min 860 mm",
    },
    {
        "ref": "9.8.6.3",
        "rule_type": "numeric_comparison",
        "target": "IfcSlab",
        "property_name": "MaxSlope",
        "operator": "<=",
        "check_value": 0.02,
        "unit": "ratio",
        "severity": "recommended",
        "desc": "Landing surface slope must not exceed 1:50 (0.02)",
    },
    # ── WINDERS ──────────────────────────────────────────────────────────────
    {
        "ref": "9.8.4.5.(1)",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "WinderTurnAngle",
        "operator": "<=",
        "check_value": 90,
        "unit": "deg",
        "severity": "recommended",
        "desc": "Maximum total winder set turn angle — 90 degrees",
    },
    {
        "ref": "9.8.4.5.(2)",
        "rule_type": "numeric_range",
        "target": "IfcStairFlight",
        "property_name": "IndividualWinderAngle",
        "operator": "between",
        "check_value": None,
        "value_min": 30,
        "value_max": 45,
        "unit": "deg",
        "severity": "recommended",
        "desc": "Each winder tread angle must be between 30° and 45°",
    },
    {
        "ref": "9.8.4.5.(2)",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "WinderSetSeparation",
        "operator": ">=",
        "check_value": 1200,
        "unit": "mm",
        "severity": "recommended",
        "desc": "Minimum plan separation between winder sets — 1200 mm",
    },
    # ── EGRESS DOORS ─────────────────────────────────────────────────────────
    {
        "ref": "OBC 9.6.4",
        "rule_type": "numeric_comparison",
        "target": "IfcDoor",
        "property_name": "ClearWidth",
        "operator": ">=",
        "check_value": 800,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Egress door minimum clear opening width — 800 mm",
    },
    {
        "ref": "OBC 9.6.4",
        "rule_type": "numeric_comparison",
        "target": "IfcDoor",
        "property_name": "Height",
        "operator": ">=",
        "check_value": 1980,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Egress door minimum height — 1980 mm",
    },
    # ── GUARDS & HANDRAILS ────────────────────────────────────────────────────
    {
        "ref": "OBC 9.8.8",
        "rule_type": "numeric_comparison",
        "target": "IfcRailing",
        "property_name": "Height",
        "operator": ">=",
        "check_value": 900,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Guard minimum height at floor edges, stairs, landings, balconies — 900 mm",
    },
    {
        "ref": "OBC 9.8.7",
        "rule_type": "numeric_range",
        "target": "IfcRailing",
        "property_name": "HandrailHeight",
        "operator": "between",
        "check_value": None,
        "value_min": 865,
        "value_max": 1070,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Handrail height must be between 865 mm and 1070 mm above stair nosings",
    },
    # ── WINDOWS ──────────────────────────────────────────────────────────────
    {
        "ref": "OBC 9.7.2",
        "rule_type": "numeric_comparison",
        "target": "IfcWindow",
        "property_name": "ClearOpeningArea",
        "operator": ">=",
        "check_value": 0.35,
        "unit": "m2",
        "severity": "mandatory",
        "desc": "Bedroom egress window minimum clear opening area — 0.35 m²",
    },
    {
        "ref": "OBC 9.7.2",
        "rule_type": "numeric_comparison",
        "target": "IfcWindow",
        "property_name": "ClearOpeningHeight",
        "operator": ">=",
        "check_value": 380,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Bedroom egress window minimum clear opening height — 380 mm",
    },
    {
        "ref": "OBC 9.7.2",
        "rule_type": "numeric_comparison",
        "target": "IfcWindow",
        "property_name": "ClearOpeningWidth",
        "operator": ">=",
        "check_value": 450,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Bedroom egress window minimum clear opening width — 450 mm",
    },
    # ── GARAGE FIRE SEPARATION ────────────────────────────────────────────────
    {
        "ref": "OBC 9.35",
        "rule_type": "prohibition",
        "target": "IfcWall",
        "property_name": "FireRating",
        "operator": "exists",
        "check_value": None,
        "unit": None,
        "severity": "mandatory",
        "desc": "Garage-to-dwelling separation walls must have a FireRating property",
    },
    # ── SPATIAL SEPARATION ────────────────────────────────────────────────────
    {
        "ref": "OBC 3.2.3",
        "rule_type": "spatial_clearance",
        "target": "IfcWall",
        "property_name": "LimitingDistance",
        "operator": ">=",
        "check_value": 0,
        "unit": "m",
        "severity": "mandatory",
        "desc": "Limiting distance from exterior wall face to property line must be calculated",
    },
    # ── RAMPS ─────────────────────────────────────────────────────────────────
    {
        "ref": "OBC 3.8.3.4",
        "rule_type": "numeric_comparison",
        "target": "IfcRamp",
        "property_name": "Slope",
        "operator": "<=",
        "check_value": 0.083,
        "unit": "ratio",
        "severity": "mandatory",
        "desc": "Accessible ramp slope must not exceed 1:12 (0.083)",
    },
    {
        "ref": "OBC 3.8.3.4",
        "rule_type": "numeric_comparison",
        "target": "IfcRamp",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 1100,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Accessible ramp clear width minimum — 1100 mm",
    },
    # ── CORRIDORS ─────────────────────────────────────────────────────────────
    {
        "ref": "OBC 3.8.3.2",
        "rule_type": "numeric_comparison",
        "target": "IfcSpace",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 1100,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Accessible corridor / aisle minimum clear width — 1100 mm",
    },
    # ── CEILING HEIGHT ────────────────────────────────────────────────────────
    {
        "ref": "OBC 9.5.1.1",
        "rule_type": "numeric_comparison",
        "target": "IfcSpace",
        "property_name": "Height",
        "operator": ">=",
        "check_value": 2400,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Habitable room minimum ceiling height — 2400 mm",
    },
    {
        "ref": "OBC 9.5.1.2",
        "rule_type": "numeric_comparison",
        "target": "IfcSpace",
        "property_name": "Height",
        "operator": ">=",
        "check_value": 1950,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Bathroom / utility room minimum ceiling height — 1950 mm",
    },
    # ── FIRE RESISTANCE ───────────────────────────────────────────────────────
    {
        "ref": "OBC 9.10.9.13",
        "rule_type": "prohibition",
        "target": "IfcWall",
        "property_name": "FireRating",
        "operator": "exists",
        "check_value": None,
        "unit": None,
        "severity": "mandatory",
        "desc": "Party walls between dwelling units must have a FireRating property",
    },
    {
        "ref": "OBC 9.10.9.14",
        "rule_type": "numeric_comparison",
        "target": "IfcWall",
        "property_name": "FireRating",
        "operator": ">=",
        "check_value": 45,
        "unit": "min",
        "severity": "mandatory",
        "desc": "Fire-rated wall between dwelling units — minimum 45-minute fire resistance",
    },
    # ── MODEL QA ─────────────────────────────────────────────────────────────
    {
        "ref": "BIMGuard QA",
        "rule_type": "prohibition",
        "target": "IfcDoor",
        "property_name": "Width",
        "operator": "exists",
        "check_value": None,
        "unit": None,
        "severity": "informational",
        "desc": "All IfcDoor elements must have a Width property — flag if missing",
    },
    {
        "ref": "BIMGuard QA",
        "rule_type": "prohibition",
        "target": "IfcSpace",
        "property_name": "LongName",
        "operator": "exists",
        "check_value": None,
        "unit": None,
        "severity": "informational",
        "desc": "All rooms/spaces must have a LongName — flag if missing",
    },
    {
        "ref": "BIMGuard QA",
        "rule_type": "prohibition",
        "target": "IfcStairFlight",
        "property_name": "Name",
        "operator": "exists",
        "check_value": None,
        "unit": None,
        "severity": "informational",
        "desc": "All stair flight elements must have a Name property",
    },
]


def seed_rules(store: RuleStore, generator: RuleGenerator) -> int:
    """
    Seed the database with the pre-built OBC Part 9 rules.
    Safe to call multiple times — skips if rules already exist from this source.

    Args:
        store     (RuleStore):     target database
        generator (RuleGenerator): validator and saver

    Returns:
        int: number of rules saved
    """
    existing_count = store.count()

    if existing_count > 0:
        print(f"[SeedRules] DB already has {existing_count} rules — skipping seed")
        print("  To re-seed, call store.clear_all_rules() first")
        return 0

    print(f"[SeedRules] Seeding {len(OBC_SEED_RULES)} OBC Part 9 rules...\n")
    saved_ids = generator.save_batch(OBC_SEED_RULES, source_doc=SOURCE_DOC_SEED)
    print(f"\n[SeedRules] Done — {len(saved_ids)} rules saved to DB")
    return len(saved_ids)


# ── RUN DIRECTLY ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    store = RuleStore(DB_PATH)
    generator = RuleGenerator(store)
    seed_rules(store, generator)

    print("\nRules in DB by target:")
    summary = store.summary()
    for target, count in summary["by_entity"].items():
        print(f"  {target:<30} {count} rules")
