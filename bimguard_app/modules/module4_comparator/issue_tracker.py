"""
BIMGUARD AI — Issue History Tracker
modules/issue_tracker.py

Tracks when issues were raised, updated, and closed across compliance runs.
Persists history to a JSON file in the working directory.
Provides the data source for the BCF issue history field.

Usage in Streamlit:
  from modules.issue_tracker import IssueTracker
  tracker = IssueTracker()
  tracker.record_run(results)
  history = tracker.get_history(global_id)
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

HISTORY_FILE = "bimguard_issue_history.json"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _now() -> str:
    return datetime.utcnow().strftime(ISO_FMT)


@dataclass
class IssueEvent:
    """A single event in an issue's history."""

    event_id: str
    timestamp: str
    event_type: str  # raised | updated | resolved | reopened | note
    risk_band: str
    composite_score: float
    author: str
    comment: str = ""


@dataclass
class IssueRecord:
    """Full history record for one element GlobalID."""

    global_id: str
    element_type: str
    system_type: str
    material: str
    first_seen: str
    last_seen: str
    current_status: str  # open | resolved | monitoring
    current_band: str
    events: list = field(default_factory=list)


class IssueTracker:
    """
    Persistent issue history tracker for BIMGUARD AI compliance runs.
    Stores history in a local JSON file between Streamlit sessions.
    """

    def __init__(self, history_path: str = HISTORY_FILE):
        self.history_path = history_path
        self._records: dict[str, IssueRecord] = {}
        self._load()

    def _load(self):
        """Load existing history from JSON file."""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for gid, data in raw.items():
                    events = [IssueEvent(**e) for e in data.get("events", [])]
                    data["events"] = events
                    self._records[gid] = IssueRecord(**data)
            except Exception:
                self._records = {}

    def _save(self):
        """Persist current history to JSON file."""
        try:
            serialisable = {}
            for gid, record in self._records.items():
                d = asdict(record)
                serialisable[gid] = d
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(serialisable, f, indent=2)
        except Exception:
            pass

    def record_run(
        self,
        results: list,
        author: str = "BIMGUARD AI",
        run_comment: str = "",
    ) -> dict:
        """
        Record a complete compliance run into the history.
        New issues are created; existing issues are updated.
        Returns summary dict of changes.
        """
        now = _now()
        summary = {"new": 0, "updated": 0, "unchanged": 0, "resolved": 0}

        seen_gids = set()

        for r in results:
            # Normalise result to dict
            if hasattr(r, "__dict__"):
                d = r.__dict__
            elif isinstance(r, dict):
                d = r
            else:
                continue

            gid = d.get("global_id", d.get("GlobalID", ""))
            if not gid:
                continue
            seen_gids.add(gid)

            band = d.get("risk_band", "Low")
            score = float(d.get("composite_score", d.get("GC001_score", 0.0)))
            etype = d.get("element_type", "IfcPipeSegment")
            stype = d.get("system_type", d.get("service_type", "Unknown"))
            mat = d.get("material_label", d.get("material", "Unknown"))

            event = IssueEvent(
                event_id=str(uuid.uuid4())[:8],
                timestamp=now,
                event_type="updated" if gid in self._records else "raised",
                risk_band=band,
                composite_score=score,
                author=author,
                comment=run_comment,
            )

            if gid not in self._records:
                # New issue
                self._records[gid] = IssueRecord(
                    global_id=gid,
                    element_type=etype,
                    system_type=stype,
                    material=mat,
                    first_seen=now,
                    last_seen=now,
                    current_status="open" if band != "Low" else "monitoring",
                    current_band=band,
                    events=[event],
                )
                summary["new"] += 1
            else:
                rec = self._records[gid]
                rec.last_seen = now

                if rec.current_band != band:
                    event.comment = (
                        f"Risk band changed: {rec.current_band} → {band}. " + run_comment
                    ).strip()
                    rec.current_band = band
                    rec.current_status = "open" if band != "Low" else "monitoring"
                    rec.events.append(event)
                    summary["updated"] += 1
                else:
                    summary["unchanged"] += 1

        # Check for elements that no longer appear (potentially resolved)
        for gid, rec in self._records.items():
            if gid not in seen_gids and rec.current_status == "open":
                rec.current_status = "resolved"
                rec.events.append(
                    IssueEvent(
                        event_id=str(uuid.uuid4())[:8],
                        timestamp=now,
                        event_type="resolved",
                        risk_band=rec.current_band,
                        composite_score=0.0,
                        author=author,
                        comment="Element no longer flagged in compliance run — marked resolved",
                    )
                )
                summary["resolved"] += 1

        self._save()
        return summary

    def get_history(self, global_id: str) -> Optional[IssueRecord]:
        """Return the full history record for a given GlobalID."""
        return self._records.get(global_id)

    def get_all_records(self) -> list[IssueRecord]:
        """Return all issue records sorted by last_seen descending."""
        return sorted(
            self._records.values(),
            key=lambda r: r.last_seen,
            reverse=True,
        )

    def get_open_issues(self) -> list[IssueRecord]:
        """Return all records with status 'open'."""
        return [r for r in self._records.values() if r.current_status == "open"]

    def add_note(
        self,
        global_id: str,
        note: str,
        author: str = "User",
    ) -> bool:
        """
        Add a manual note to an issue's history.
        Returns True if the issue was found and updated.
        """
        if global_id not in self._records:
            return False
        rec = self._records[global_id]
        rec.events.append(
            IssueEvent(
                event_id=str(uuid.uuid4())[:8],
                timestamp=_now(),
                event_type="note",
                risk_band=rec.current_band,
                composite_score=0.0,
                author=author,
                comment=note,
            )
        )
        self._save()
        return True

    def mark_resolved(
        self,
        global_id: str,
        author: str = "User",
        comment: str = "",
    ) -> bool:
        """Manually mark an issue as resolved."""
        if global_id not in self._records:
            return False
        rec = self._records[global_id]
        rec.current_status = "resolved"
        rec.events.append(
            IssueEvent(
                event_id=str(uuid.uuid4())[:8],
                timestamp=_now(),
                event_type="resolved",
                risk_band=rec.current_band,
                composite_score=0.0,
                author=author,
                comment=comment or "Manually resolved",
            )
        )
        self._save()
        return True

    def get_statistics(self) -> dict:
        """Return summary statistics across all tracked issues."""
        all_records = list(self._records.values())
        return {
            "total_tracked": len(all_records),
            "open": sum(1 for r in all_records if r.current_status == "open"),
            "resolved": sum(1 for r in all_records if r.current_status == "resolved"),
            "monitoring": sum(1 for r in all_records if r.current_status == "monitoring"),
            "by_band": {
                "Critical": sum(1 for r in all_records if r.current_band == "Critical"),
                "High": sum(1 for r in all_records if r.current_band == "High"),
                "Medium": sum(1 for r in all_records if r.current_band == "Medium"),
                "Low": sum(1 for r in all_records if r.current_band == "Low"),
            },
        }

    def clear(self):
        """Clear all history (for testing / reset)."""
        self._records = {}
        if os.path.exists(self.history_path):
            os.remove(self.history_path)


# ── STREAMLIT INTEGRATION SNIPPET ────────────────────────────────────────────
STREAMLIT_SNIPPET = """
# Add to Streamlit app — BCF Issue Manager page
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
from modules.issue_tracker import IssueTracker
import pandas as pd

# Initialise tracker (persists across reruns via session state)
if "issue_tracker" not in st.session_state:
    st.session_state.issue_tracker = IssueTracker()

tracker = st.session_state.issue_tracker

# After a compliance run, record results
if st.session_state.get("compliance_results"):
    run_note = st.text_input("Run note (optional)", placeholder="e.g. IFC rev P03 issued")
    if st.button("Record this run to history"):
        summary = tracker.record_run(
            st.session_state.compliance_results,
            run_comment=run_note
        )
        st.success(
            f"History updated — {summary['new']} new, "
            f"{summary['updated']} changed, "
            f"{summary['resolved']} resolved."
        )

# Display issue history table
st.subheader("Issue history")
stats = tracker.get_statistics()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total tracked", stats["total_tracked"])
c2.metric("Open",     stats["open"])
c3.metric("Resolved", stats["resolved"])
c4.metric("Monitoring", stats["monitoring"])

records = tracker.get_all_records()
if records:
    rows = []
    for r in records:
        rows.append({
            "GlobalID":      r.global_id[:12],
            "Element":       r.element_type,
            "System":        r.system_type,
            "Band":          r.current_band,
            "Status":        r.current_status,
            "First seen":    r.first_seen[:10],
            "Last seen":     r.last_seen[:10],
            "Event count":   len(r.events),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detail expander for selected issue
    selected_gid = st.selectbox("View issue timeline", [r.global_id for r in records])
    if selected_gid:
        rec = tracker.get_history(selected_gid)
        with st.expander(f"Timeline — {selected_gid[:16]}", expanded=True):
            for event in reversed(rec.events):
                st.markdown(
                    f"**{event.timestamp[:16]}**  |  `{event.event_type.upper()}`  "
                    f"|  Band: **{event.risk_band}**  |  Score: {event.composite_score:.3f}  "
                    f"|  {event.author}"
                    + (f"\\n\\n_{event.comment}_" if event.comment else "")
                )

        # Add manual note
        note = st.text_area("Add note to this issue")
        if st.button("Save note") and note:
            tracker.add_note(selected_gid, note, author="User")
            st.success("Note saved.")

        if st.button("Mark resolved"):
            tracker.mark_resolved(selected_gid, author="User")
            st.success("Issue marked resolved.")
"""
