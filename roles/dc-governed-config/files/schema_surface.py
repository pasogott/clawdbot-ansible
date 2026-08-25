#!/usr/bin/env python3
"""Re-read every control-surface map row against the LIVE schema (TASK-225 c1).

    schema_surface.py --schema S --rows R [--effective E]

WHAT THIS CLOSES

TASK-225 built a control-surface map: for each OpenClaw subsystem, which layer
enforces it, which keys control it, and whether a PER-AGENT narrowing exists.
Most rows were verified against pinned upstream v2026.7.1 and carry
"HOST REVALIDATION REQUIRED". Criterion 1 requires every row re-read against the
live schema of the pinned build, and says plainly:

    "If the live schema differs from any row above, preserve the conflict and
     revise the row; do not reconcile by assumption."

So this file does not reconcile. It reports.

WHY NOT JUST PASTE THE SCHEMA

The schema is ~1.9MB. Pasting it satisfies the letter of "capture evidence" and
none of its purpose: nobody re-reads twelve rows against 1.9MB by eye, and the
rows most likely to be wrong are the ones nobody looks at. This file mechanically
checks the ONE claim on each row that the schema can actually adjudicate --
whether a per-agent narrowing surface is DECLARED -- and reports the rest as
captured evidence for a human.

THE ASYMMETRY, WHICH IS LOAD-BEARING

A key absent from the schema is NOT proof the control is missing. It may be
undeclared and still enforced internally. So absence is UNKNOWN, never FAIL.
subagent_conformance.py holds the same rule for the same reason: a false FAIL on
an isolation control sends someone to widen a policy that was never broken.

THREE MECHANISMS OF PER-AGENT NARROWING, AND WHY ALL THREE MUST BE CHECKED

The first version of this file recognised only one of them and produced four
confident false conflicts out of thirteen rows on the first real run. The map
does not express "per-agent narrowing" one way; it expresses it three:

  A  AGENT-SCOPED CONFIG   a key under agents.defaults.* / agents.list.*.
                           Tool policy, sandbox, heartbeat, model, memory,
                           sub-agents. Matched by `agent_markers`.

  B  ROOT ROUTING BY AGENT ID   a Gateway-root key that NAMES an agent:
                           hooks.allowedAgentIds, hooks.mappings[].agentId,
                           bindings[].agentId. The narrowing is real and the
                           key is nowhere near `agents.`. Matched by
                           `agent_ref_markers`, as EXACT declared paths.

  D  DELEGATED             the row narrows through another row's mechanism.
                           Agent-visible MCP functions narrow through tool
                           policy, so no mcp-named agent path exists and none
                           should. Declared by `narrows_via`.

Recognising only A reports B and D as OVERSTATED — a confident claim that
governance believes it can scope something it cannot, when it can. That is worse
than no check: it sends someone to weaken a correct map row.

`exclude_markers` exists because the same run also produced the opposite error.
The Gateway row carried the marker `bind`, which matched
`agents.list.sandbox.docker.binds` -- filesystem bind MOUNTS, not network binds
-- and reported UNDERSTATED against a row whose own note says sandbox belongs to
a different row. A marker is a substring match and substrings collide.

CONFLICT is reserved for the two cases where the schema genuinely contradicts a
recorded governance claim:

  OVERSTATED   the map claims a configurable per-agent narrowing, and this build
               declares no such path. Governance believes it can scope something
               it cannot. This is the SOP-manifest defect class TASK-225 was
               created to find (`memory_scope` was the first instance).

  UNDERSTATED  the map says no per-agent narrowing exists, and the schema
               declares one. A control surface nobody decided about -- the same
               shape as `heartbeat_respond`, the seven session tools, and
               `plugins.allow` auto-load. Every one of those was visible the
               whole time to a check that was never written.

UNMAPPED ROOTS

A top-level schema property covered by NO map row is reported separately. That
is the recurring defect of this workstream stated structurally: a surface nobody
enumerates is a surface nobody has decided about. Four such surfaces were found
on 2026-08-16 and three of them held something.

EXIT CODES

  0  every row adjudicated, no conflict
  1  conflicts and/or unmapped roots found -- a REPORT, not an error. The caller
     must not fail the play on this: preserving a conflict is the required
     behaviour, and a play that aborts on the first one never reaches row twelve.
  2  inputs unreadable. This IS an error: every finding below is derived from
     the schema, so without it the result is UNKNOWN rather than negative.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Paths under these prefixes are the per-agent configuration surface. `agents.list`
# is an array; the walker keeps the element path unindexed, so a key declared on
# an agent entry reads `agents.list.tools.deny` -- the spelling already used in
# the canonical TASK-225 record.
AGENT_PREFIXES = ("agents.defaults.", "agents.list.", "agents.entries.")

MAX_PATHS_PER_ROW = 60


def resolve(node: Any, root: Any, depth: int = 0) -> Any:
    """Follow a local $ref chain. Foreign refs are returned unresolved rather
    than guessed at -- an unresolvable ref must not silently become an empty
    node, because an empty node reads downstream as 'declares nothing'."""
    while isinstance(node, dict) and "$ref" in node and depth < 32:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return node
        target = root
        for seg in ref[2:].split("/"):
            seg = seg.replace("~1", "/").replace("~0", "~")
            if isinstance(target, dict) and seg in target:
                target = target[seg]
            else:
                return node
        node = target
        depth += 1
    return node


def describe(node: Any) -> dict[str, str]:
    """Type, enum, default and description -- the four things criterion 1 asks
    to be pasted back. Descriptions are frequently the ONLY place a precedence
    rule is written down, so they are captured rather than summarised away."""
    if not isinstance(node, dict):
        return {"type": "?", "desc": ""}
    t = node.get("type")
    if isinstance(t, list):
        t = "|".join(str(x) for x in t)
    elif t is None:
        for comb in ("anyOf", "oneOf", "allOf"):
            members = node.get(comb)
            if isinstance(members, list):
                seen = [m.get("type") for m in members
                        if isinstance(m, dict) and isinstance(m.get("type"), str)]
                if seen:
                    t = "|".join(dict.fromkeys(seen))
                    break
    out = {"type": str(t) if t else "?", "desc": ""}
    if isinstance(node.get("enum"), list):
        out["type"] += " enum[" + ", ".join(str(x) for x in node["enum"][:8]) + "]"
    if "const" in node:
        out["type"] += f" const={node['const']!r}"
    if "default" in node:
        out["type"] += f" default={json.dumps(node['default'])[:60]}"
    d = node.get("description")
    if isinstance(d, str):
        out["desc"] = " ".join(d.split())
    return out


def walk(node: Any, root: Any, path: str, out: dict[str, dict[str, str]],
         seen: set[tuple[int, str]]) -> None:
    node = resolve(node, root)
    if not isinstance(node, dict):
        return
    guard = (id(node), path)
    if guard in seen:
        return
    seen.add(guard)

    props = node.get("properties")
    if isinstance(props, dict):
        for k, v in props.items():
            p = f"{path}.{k}" if path else k
            v = resolve(v, root)
            out[p] = describe(v)
            walk(v, root, p, out, seen)

    for comb in ("anyOf", "oneOf", "allOf"):
        members = node.get(comb)
        if isinstance(members, list):
            for m in members:
                walk(m, root, path, out, seen)

    # Array elements keep the parent path: `agents.list` holds agent entries, and
    # `agents.list.tools` is how this workstream already writes that key.
    items = node.get("items")
    if isinstance(items, dict):
        walk(items, root, path, out, seen)

    ap = node.get("additionalProperties")
    if isinstance(ap, dict):
        walk(ap, root, f"{path}.<name>" if path else "<name>", out, seen)


def under(path: str, rootpath: str) -> bool:
    return path == rootpath or path.startswith(rootpath + ".")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--effective", default="")
    ap.add_argument("--build", default="unknown")
    args = ap.parse_args()

    try:
        schema = json.loads(Path(args.schema).read_text())
        rows = json.loads(Path(args.rows).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INSUFFICIENT EVIDENCE — inputs unreadable: {exc}", file=sys.stderr)
        return 2
    if not isinstance(rows, list) or not rows:
        print("INSUFFICIENT EVIDENCE — no map rows supplied to adjudicate.",
              file=sys.stderr)
        return 2

    effective: dict[str, str] = {}
    if args.effective:
        try:
            effective = json.loads(Path(args.effective).read_text() or "{}")
        except (OSError, json.JSONDecodeError):
            effective = {}

    declared: dict[str, dict[str, str]] = {}
    walk(schema, schema, "", declared, set())
    if len(declared) < 50:
        print(f"INSUFFICIENT EVIDENCE — the schema parsed to only {len(declared)} "
              "declared paths. A build this size declares hundreds. Reporting "
              "'not declared' from this would be an inference from a broken "
              "read, which is the exact failure this workstream keeps making.",
              file=sys.stderr)
        return 2

    out: list[str] = []
    add = out.append
    conflicts: list[str] = []

    add("=" * 78)
    add("TASK-225 CRITERION 1 — CONTROL-SURFACE MAP vs LIVE SCHEMA")
    add(f"build={args.build}   declared_paths={len(declared)}   rows={len(rows)}")
    add("=" * 78)
    add("")
    add("Every row below is adjudicated against the schema of THIS build.")
    add("Classification rules, applied without exception:")
    add("  VERIFIED HOST  this build's schema declares it.")
    add("  UNKNOWN        the schema does not declare it. NOT a finding of")
    add("                 absence -- a control may be undeclared and still")
    add("                 enforced internally.")
    add("  CONFLICT       the schema contradicts a recorded governance claim.")
    add("                 Preserved, NOT reconciled. Revising the map row is a")
    add("                 separate act by a human.")
    add("")

    covered_roots: set[str] = set()
    # Delegation (mechanism D) is resolved after every row is adjudicated, so a
    # row may point at one declared later. Two passes, not a lookahead.
    verdicts: dict[str, str] = {}
    deferred: list[tuple[dict, int]] = []

    for row in rows:
        name = row.get("subsystem", "<unnamed>")
        roots = row.get("roots", []) or []
        markers = [m.lower() for m in (row.get("agent_markers", []) or [])]
        excludes = [m.lower() for m in (row.get("exclude_markers", []) or [])]
        refs = row.get("agent_ref_markers", []) or []
        delegate = row.get("narrows_via", "")
        claim = (row.get("agent_scoped_claim", "unknown") or "unknown").lower()
        note = " ".join((row.get("map_note", "") or "").split())

        for r in roots:
            covered_roots.add(r.split(".")[0])

        add("-" * 78)
        add(f"ROW: {name}")
        add(f"  map claim (per-agent narrowing): {claim.upper()}")
        if note:
            add(f"  map note: {note}")

        present = [r for r in roots if any(under(p, r) for p in declared)]
        missing = [r for r in roots if r not in present]
        add(f"  declared roots:   {', '.join(present) if present else '(none)'}")
        if missing:
            add(f"  UNDECLARED roots: {', '.join(missing)}  [UNKNOWN — not proof of absence]")

        family = sorted(p for p in declared if any(under(p, r) for r in roots))

        # Mechanism A. The tail is the path BELOW `agents.defaults` /
        # `agents.list`, so a marker cannot match on the word "agents" itself.
        def tail(path: str) -> str:
            return path[path.index(".", path.index(".") + 1) + 1:].lower()

        agent_paths = sorted(
            p for p in declared
            if p.startswith(AGENT_PREFIXES)
            and any(m in tail(p) for m in markers)
            and not any(x in tail(p) for x in excludes)
        ) if markers else []

        # Mechanism B. EXACT declared paths, not substrings: a routing key is a
        # specific key, and matching it loosely is how `bind` matched a bind
        # mount. A ref path listed but NOT declared is reported, because a map
        # row citing a key this build does not have is itself the finding.
        ref_present = sorted(r for r in refs if r in declared)
        ref_absent = sorted(r for r in refs if r not in declared)

        if ref_absent:
            add("  MAP CITES KEYS THIS BUILD DOES NOT DECLARE:")
            for r in ref_absent:
                add(f"    [UNKNOWN] {r} — cited by the map row, not declared here.")

        if not present:
            verdict = "UNKNOWN"
            add("  VERDICT: UNKNOWN — no root of this family is declared on this")
            add("           build, so the row cannot be adjudicated from the")
            add("           schema. It is NOT falsified.")
        elif claim in ("yes", "partial"):
            if agent_paths:
                verdict = "CONFIRMED"
                add(f"  VERDICT: CONFIRMED [VERIFIED HOST] — mechanism A "
                    f"(agent-scoped config): {len(agent_paths)} per-agent path(s).")
            elif ref_present:
                verdict = "CONFIRMED"
                add("  VERDICT: CONFIRMED [VERIFIED HOST] — mechanism B (Gateway-root")
                add(f"           routing by agent id): {', '.join(ref_present)}.")
                add("           The narrowing is real and lives nowhere near `agents.`,")
                add("           which is why matching only agent-scoped paths reported")
                add("           this row as a false conflict on the first run.")
            elif delegate:
                verdict = "DEFER"
                deferred.append((row, len(out)))
                add("  VERDICT: pending — mechanism D (delegated), resolved below.")
            else:
                verdict = "CONFLICT"
                add("  VERDICT: CONFLICT — OVERSTATED. The map claims a per-agent")
                add("           narrowing, and this build declares no agent-scoped")
                add("           path, no agent-routing key, and no delegation for it.")
                add("           Governance may believe it can scope something it")
                add("           cannot configure. The `memory_scope` class.")
                add("           PRESERVED, not reconciled.")
        elif claim == "no":
            if agent_paths or ref_present:
                verdict = "CONFLICT"
                add("  VERDICT: CONFLICT — UNDERSTATED. The map says no per-agent")
                add("           narrowing exists, and the schema declares one. This")
                add("           is a control surface nobody has decided about --")
                add("           the `heartbeat_respond` shape. PRESERVED.")
            else:
                verdict = "CONFIRMED"
                add("  VERDICT: CONFIRMED [VERIFIED HOST] — no agent-scoped path and")
                add("           no agent-routing key declared, as the map records.")
        else:
            verdict = "UNKNOWN"
            add("  VERDICT: UNKNOWN — the row states no adjudicable per-agent claim.")

        verdicts[name] = verdict
        if verdict == "CONFLICT":
            kind = "UNDERSTATED" if (agent_paths or ref_present) else "OVERSTATED"
            conflicts.append(f"{name}: {kind}")

        if ref_present:
            add("  agent-routing keys declared by this build (mechanism B):")
            for r in ref_present:
                add(f"    [VERIFIED HOST] {r}  :: {declared[r]['type']}")
                if declared[r]["desc"]:
                    add(f"        {declared[r]['desc'][:220]}")

        if agent_paths:
            add("  per-agent paths declared by this build:")
            for p in agent_paths[:MAX_PATHS_PER_ROW]:
                add(f"    [VERIFIED HOST] {p}  :: {declared[p]['type']}")
                if declared[p]["desc"]:
                    add(f"        {declared[p]['desc'][:220]}")
            if len(agent_paths) > MAX_PATHS_PER_ROW:
                add(f"    ... {len(agent_paths) - MAX_PATHS_PER_ROW} further per-agent "
                    "path(s) NOT shown — cap reached, and this line exists so the "
                    "omission cannot read as completeness.")

        add(f"  family paths declared: {len(family)}")
        for p in family[:MAX_PATHS_PER_ROW]:
            line = f"    {p}  :: {declared[p]['type']}"
            add(line)
            if declared[p]["desc"]:
                add(f"        {declared[p]['desc'][:220]}")
        if len(family) > MAX_PATHS_PER_ROW:
            add(f"    ... {len(family) - MAX_PATHS_PER_ROW} further path(s) NOT shown "
                "— cap reached. The full schema artifact holds them.")

        shown = [k for k in effective if any(under(k, r) for r in roots)]
        if shown:
            add("  effective values on this host (CONFIGURED state, not runtime behaviour):")
            for k in sorted(shown):
                v = " ".join(str(effective[k]).split())[:200] or "<unset, or path not present>"
                add(f"    {k} = {v}")
        add("")

    # --- second pass: resolve delegated rows (mechanism D) --------------------
    #
    # A delegated row narrows through ANOTHER row's mechanism. MCP is the case
    # that forced this: agent-visible MCP functions are narrowed by tool policy
    # using exact tool names or server globs, so no mcp-named agent path exists
    # and none should. Adjudicating it against mcp-named paths alone reported a
    # true map row as OVERSTATED.
    #
    # The delegation is only evidence if the row it points at was itself
    # CONFIRMED. A delegate that is UNKNOWN or in conflict proves nothing, and
    # inheriting its verdict would launder an unproven claim into a confirmed
    # one -- so that case resolves to UNKNOWN, never to CONFIRMED.
    for row, idx in deferred:
        name = row.get("subsystem", "<unnamed>")
        target = row.get("narrows_via", "")
        tv = verdicts.get(target)
        if tv == "CONFIRMED":
            verdicts[name] = "CONFIRMED"
            out[idx] = (f"  VERDICT: CONFIRMED [VERIFIED HOST] — mechanism D "
                        f"(delegated to '{target}', which is CONFIRMED). No key "
                        f"named for this family exists under `agents.`, and none "
                        f"should: the narrowing is that row's mechanism.")
        elif tv is None:
            verdicts[name] = "UNKNOWN"
            out[idx] = (f"  VERDICT: UNKNOWN — this row delegates to '{target}', "
                        f"which is not among the rows supplied. A map row citing a "
                        f"delegate that does not exist is itself a map defect.")
        else:
            verdicts[name] = "UNKNOWN"
            out[idx] = (f"  VERDICT: UNKNOWN — this row delegates to '{target}', "
                        f"which resolved {tv} rather than CONFIRMED. A delegation "
                        f"is only evidence if its target is; inheriting an "
                        f"unproven verdict would launder it into a confirmed one.")

    # --- roots no row covers --------------------------------------------------
    top = sorted(p for p in declared if "." not in p)
    unmapped = [r for r in top if r not in covered_roots]
    add("-" * 78)
    add("TOP-LEVEL SCHEMA ROOTS COVERED BY NO MAP ROW")
    add("")
    add("A surface nobody enumerates is a surface nobody has decided about.")
    add("This list is not a defect list -- most entries will be irrelevant to")
    add("governance. It exists so that irrelevance is a CONCLUSION rather than")
    add("an assumption, which is the difference the four surfaces enumerated on")
    add("2026-08-16 turned on.")
    add("")
    add("COVERAGE IS JUDGED AT THE TOP-LEVEL ROOT ONLY. A row whose root is")
    add("`agents.defaults.heartbeat` marks the whole `agents` root as covered, so")
    add("an unmapped key NESTED under a covered root will not appear here. This")
    add("list is therefore a floor on what is unmapped, never a ceiling, and it")
    add("says so rather than letting the omission read as completeness.")
    add("")
    if unmapped:
        for r in unmapped[:MAX_PATHS_PER_ROW]:
            d = declared[r]["desc"][:160]
            add(f"  [UNMAPPED] {r}  :: {declared[r]['type']}")
            if d:
                add(f"      {d}")
        if len(unmapped) > MAX_PATHS_PER_ROW:
            add(f"  ... {len(unmapped) - MAX_PATHS_PER_ROW} further unmapped root(s) "
                "NOT shown — cap reached.")
    else:
        add("  (none — every declared top-level root is covered by a map row)")
    add("")

    add("=" * 78)
    add("SUMMARY")
    add("=" * 78)
    add(f"  rows adjudicated : {len(rows)}")
    add(f"  conflicts        : {len(conflicts)}")
    for c in conflicts:
        add(f"      CONFLICT — {c}")
    add(f"  unmapped roots   : {len(unmapped)}")
    add("")
    add("  Conflicts are PRESERVED. TASK-225 criterion 1 requires the conflicting")
    add("  row to be revised by a human against this evidence; reconciling by")
    add("  assumption is the prohibited move, and nothing here does it.")
    add("")
    add("  SCOPE OF THIS ARTIFACT, stated so it survives being quoted out of")
    add("  context: every finding is about what this build DECLARES and what this")
    add("  host has CONFIGURED. None of it is a behavioural observation of the")
    add("  running Gateway. A declared key is not a proven enforcement, and an")
    add("  undeclared key is not a proven absence.")

    print("\n".join(out))
    return 1 if (conflicts or unmapped) else 0


if __name__ == "__main__":
    sys.exit(main())
