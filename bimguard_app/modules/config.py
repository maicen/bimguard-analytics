"""
app/modules/config.py
----------------------
Shared constants for Module 1 and Module 3 pipeline components.
Imported by rule_generator.py, rule_converter.py, and obc_seed_rules.py.
"""

import os

from app.services.persistence import PersistenceService

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = PersistenceService.DB_PATH
# Runtime backend is selected via BIM_GUARD_DB_BACKEND (sqlite or supabase).

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
# ── Source document labels ────────────────────────────────────────────────────
SOURCE_DOC_PDF = "OBC_Part9_PDF"
SOURCE_DOC_SEED = "OBC_Part9_Seed"

# ── Operators ─────────────────────────────────────────────────────────────────
VALID_OPERATORS = [
    ">=",
    "<=",
    "==",
    "!=",  # numeric comparisons
    "between",  # numeric range (uses value_min / value_max)
    "exists",  # property must be present
    "not_exists",  # property must be absent (prohibition)
    "matches",  # regex / pattern match
    "conforms_to",  # must conform to a referenced standard
]

# ── Rule types ────────────────────────────────────────────────────────────────
# All 8 types. Validation requirements differ per type — see rule_generator.py.
VALID_RULE_TYPES = [
    "numeric_comparison",  # single threshold  e.g. Width >= 860 mm
    "numeric_range",  # band check        e.g. RiserHeight between 125–200 mm
    "prohibition",  # must NOT be used  e.g. glass blocks as loadbearing
    "standard_conformance",  # must conform to   e.g. ASTM C62 for masonry
    "deemed_to_comply",  # alternative path  e.g. sprinklers in lieu of separation
    "table_lookup",  # value from table  e.g. Table 9.8.4.1 tread depths
    "spatial_clearance",  # clearance check   e.g. headroom >= 1950 mm
    "tiered",  # context-dependent e.g. different widths per occupancy
]

# ── IFC class → plain-language keyword mapping ────────────────────────────────
# Used by _enrich_target() to auto-correct free-text entity names.
OBC_TO_IFC_MAP = {
    # Stairs
    "stair": "IfcStairFlight",
    "step": "IfcStairFlight",
    "flight": "IfcStairFlight",
    "riser": "IfcStairFlight",
    "tread": "IfcStairFlight",
    "nosing": "IfcStairFlight",
    "winder": "IfcStairFlight",
    # Doors
    "door": "IfcDoor",
    "exit": "IfcDoor",
    "egress": "IfcDoor",
    "doorway": "IfcDoor",
    # Windows
    "window": "IfcWindow",
    "glazing": "IfcWindow",
    "skylight": "IfcWindow",
    # Ramps
    "ramp": "IfcRamp",
    "slope": "IfcRamp",
    # Guards & handrails
    "guard": "IfcRailing",
    "handrail": "IfcRailing",
    "railing": "IfcRailing",
    "balustrade": "IfcRailing",
    # Walls
    "wall": "IfcWall",
    "partition": "IfcWall",
    "firewall": "IfcWall",
    "separation": "IfcWall",
    # Slabs / landings
    "slab": "IfcSlab",
    "landing": "IfcSlab",
    "floor": "IfcSlab",
    "platform": "IfcSlab",
    # Spaces / rooms
    "space": "IfcSpace",
    "room": "IfcSpace",
    "corridor": "IfcSpace",
    "zone": "IfcZone",
    # Structure
    "column": "IfcColumn",
    "footing": "IfcFooting",
    "foundation": "IfcFooting",
    "beam": "IfcBeam",
    # MEP
    "pipe": "IfcPipeSegment",
    "duct": "IfcDuctSegment",
}

# ── IFC class → default Pset mapping ─────────────────────────────────────────
# Used by _enrich_property_set() to populate property_set when the LLM omits it.
IFC_PROPERTY_SET_MAP = {
    "IfcStairFlight": "Pset_StairFlightCommon",
    "IfcDoor": "Pset_DoorCommon",
    "IfcWindow": "Pset_WindowCommon",
    "IfcRailing": "Pset_RailingCommon",
    "IfcRamp": "Pset_RampCommon",
    "IfcRampFlight": "Pset_RampFlightCommon",
    "IfcSlab": "Pset_SlabCommon",
    "IfcWall": "Pset_WallCommon",
    "IfcSpace": "Pset_SpaceCommon",
    "IfcColumn": "Pset_ColumnCommon",
    "IfcBeam": "Pset_BeamCommon",
    "IfcFooting": "Pset_FootingCommon",
}

# ── Rule type → minimum required fields ──────────────────────────────────────
# Validation in rule_generator.py is driven by this map.
RULE_TYPE_REQUIRED_FIELDS = {
    "numeric_comparison": ["target", "property_name", "operator", "check_value"],
    "numeric_range": ["target", "property_name", "value_min", "value_max"],
    "prohibition": ["target", "desc"],
    "standard_conformance": ["target", "desc"],
    "deemed_to_comply": ["target", "desc"],
    "table_lookup": ["target", "property_name"],
    "spatial_clearance": ["target", "property_name", "operator", "check_value"],
    "tiered": ["target", "desc"],
}
