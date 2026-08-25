#!/usr/bin/env python3
"""Contract tests for the TASK-225 criterion-1 schema adjudication.

    python3 tests/dc_schema_surface.py

WHY THIS FILE EXISTS

schema_surface.py decides, for each recorded control-surface row, whether this
build declares a per-agent narrowing. That decision drives a governance CONFLICT
finding, so the ways it can be quietly wrong all matter:

  * If $ref resolution breaks, most of the schema becomes invisible and EVERY
    row reports OVERSTATED -- a page of confident, false conflicts.
  * If array `items` got an index in the path, `agents.list.tools.deny` would
    read `agents.list.0.tools.deny`, no marker would match, and again every
    per-agent row reports OVERSTATED.
  * If a broken or truncated schema were adjudicated instead of refused, the
    report would be a wall of "not declared" that looks like a finding.

Each of those produces output that reads like a discovery. None is one. So the
tests below do not merely check that a good schema passes -- several BREAK the
thing a check protects and assert the check notices. A control that has never
been observed to fail has not been tested.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLE = ROOT / "roles" / "dc-governed-config"
READER = ROLE / "files" / "schema_surface.py"


def pad(n: int = 60) -> dict:
    """Filler properties. The reader refuses a schema of fewer than 50 declared
    paths, so a fixture testing anything else must clear that floor first."""
    return {f"pad{i}": {"type": "string"} for i in range(n)}


AGENT_DEF = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "tools": {"type": "object", "properties": {
            "deny": {"type": "array", "description": "denied tools"}}},
        "sandbox": {"type": "object", "properties": {"mode": {"type": "string"}}},
    },
}


def base_schema(*, use_ref: bool = True) -> dict:
    agent = {"$ref": "#/$defs/Agent"} if use_ref else json.loads(json.dumps(AGENT_DEF))
    return {
        "$defs": {"Agent": AGENT_DEF},
        "type": "object",
        "properties": dict(pad(), **{
            "plugins": {"type": "object", "properties": {"deny": {"type": "array"}}},
            "gateway": {"type": "object", "properties": {"bind": {"type": "string"}}},
            "tools": {"type": "object", "properties": {"deny": {"type": "array"}}},
            "agents": {"type": "object", "properties": {
                "defaults": agent,
                "list": {"type": "array", "items": agent},
            }},
        }),
    }


def run(schema: dict | str, rows: list) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as d:
        sp, rp = Path(d) / "s.json", Path(d) / "r.json"
        sp.write_text(schema if isinstance(schema, str) else json.dumps(schema))
        rp.write_text(json.dumps(rows))
        p = subprocess.run(
            [sys.executable, str(READER), "--schema", str(sp), "--rows", str(rp),
             "--build", "test"],
            capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout, p.stderr


ROW_TOOLS_YES = {"subsystem": "Tool policy", "roots": ["tools"],
                 "agent_markers": ["tools"], "agent_scoped_claim": "yes"}
ROW_GATEWAY_NO = {"subsystem": "Gateway", "roots": ["gateway"],
                  "agent_markers": ["gateway", "bind"], "agent_scoped_claim": "no"}


def main() -> int:
    checks: list[tuple[str, bool]] = []

    if not READER.exists():
        print(f"FAIL  reader missing at {READER}")
        return 1

    # --- 1. the happy path, so a later failure means something ---------------
    rc, out, _ = run(base_schema(), [ROW_TOOLS_YES, ROW_GATEWAY_NO])
    checks.append((
        "a well-formed schema confirms a YES row from declared agent paths",
        "ROW: Tool policy" in out and "CONFIRMED" in out.split("ROW: Gateway")[0]))
    checks.append((
        "a NO row with no agent-scoped path confirms rather than conflicts",
        "CONFLICT" not in out.split("ROW: Gateway")[1].split("TOP-LEVEL")[0]))

    # --- 2. $ref resolution: break it and confirm the break is visible -------
    # If refs stopped resolving, agents.defaults.tools would vanish and the YES
    # row would report a confident OVERSTATED conflict. This asserts the SAME
    # fixture passes with refs and that the ref-free spelling agrees -- if the
    # two ever disagree, resolution is broken.
    rc_ref, out_ref, _ = run(base_schema(use_ref=True), [ROW_TOOLS_YES])
    rc_inline, out_inline, _ = run(base_schema(use_ref=False), [ROW_TOOLS_YES])
    checks.append((
        "$ref and inlined spellings of the same schema reach the same verdict",
        ("OVERSTATED" in out_ref) == ("OVERSTATED" in out_inline)))
    checks.append((
        "$ref resolution actually finds the per-agent path",
        "agents.defaults.tools.deny" in out_ref))

    # --- 3. array items keep the parent path ---------------------------------
    # `agents.list` is an array of agent entries. An indexed path would break
    # every per-agent marker match at once.
    checks.append((
        "array elements keep the unindexed path spelling",
        "agents.list.tools.deny" in out_ref and "agents.list.0" not in out_ref))

    # --- 4. OVERSTATED fires when the claim exceeds the build ----------------
    rc, out, _ = run(base_schema(), [{
        "subsystem": "Memory", "roots": ["plugins"],
        "agent_markers": ["memoryscope"], "agent_scoped_claim": "partial"}])
    checks.append((
        "a claimed per-agent narrowing the build does not declare is OVERSTATED",
        "OVERSTATED" in out and rc == 1))

    # --- 5. UNDERSTATED fires in the other direction -------------------------
    # The dangerous direction: a narrowing exists that governance believes does
    # not. This is the `heartbeat_respond` shape.
    rc, out, _ = run(base_schema(), [{
        "subsystem": "Tool policy", "roots": ["tools"],
        "agent_markers": ["tools"], "agent_scoped_claim": "no"}])
    checks.append((
        "an undeclared-in-governance narrowing that the build declares is UNDERSTATED",
        "UNDERSTATED" in out and rc == 1))

    # --- 6. absence is UNKNOWN, never FAIL -----------------------------------
    # The asymmetry the whole design rests on: a control may be undeclared and
    # still enforced, so a missing root must not falsify a row.
    rc, out, _ = run(base_schema(), [{
        "subsystem": "Nonexistent", "roots": ["notAThing"],
        "agent_markers": ["nope"], "agent_scoped_claim": "yes"}])
    row = out.split("ROW: Nonexistent")[1].split("TOP-LEVEL")[0]
    checks.append((
        "a row whose roots are undeclared is UNKNOWN, not CONFLICT",
        "UNKNOWN" in row and "CONFLICT" not in row))
    checks.append((
        "the report says absence is not proof of absence",
        "not proof of absence" in out or "NOT a finding of" in out))

    # --- 7. the floor: a broken source is refused, not adjudicated -----------
    rc, _, err = run({"type": "object", "properties": {"a": {"type": "string"}}},
                     [ROW_TOOLS_YES])
    checks.append((
        "a schema too small to be evidence returns INSUFFICIENT EVIDENCE (rc=2)",
        rc == 2 and "INSUFFICIENT EVIDENCE" in err))
    rc, _, err = run("{not json", [ROW_TOOLS_YES])
    checks.append((
        "an unparseable schema returns rc=2 rather than an empty adjudication",
        rc == 2 and "INSUFFICIENT EVIDENCE" in err))
    rc, _, err = run(base_schema(), [])
    checks.append((
        "no rows to adjudicate is refused rather than reported as clean",
        rc == 2))

    # --- 8. rc=1 is a report, not an error, and the play must treat it so ----
    play = (ROLE / "tasks" / "schema_evidence.yml").read_text()
    checks.append((
        "the play tolerates rc=1 (conflicts found) and fails only on rc=2",
        "not in [0, 1]" in play))
    checks.append((
        "the play refuses to adjudicate a schema that did not read",
        "INSUFFICIENT EVIDENCE" in play and "dc_fail_closed" in play))
    checks.append((
        "the play states it is evidence and not acceptance",
        "NOT ACCEPTANCE" in play.upper()))

    # --- 9. zero mutation ----------------------------------------------------
    # A read-only play that acquires a write verb is the failure this whole
    # repository is arranged to prevent, so it is asserted rather than assumed.
    # Matched on MECHANISM, not on the word. The first version of this test
    # searched for "restart" and failed on the play's own comment saying it
    # restarts nothing -- a check that fires on the documentation of the
    # property it is verifying is not a check.
    for verb in ("'patch'", "'set'", "'unset'", "--fix", "notify:",
                 "flush_handlers", "ansible.builtin.systemd",
                 "ansible.builtin.service"):
        checks.append((
            f"the play never uses {verb}",
            verb not in play))

    # --- 10. the rows are well-formed governance data ------------------------
    defaults = (ROLE / "defaults" / "main.yml").read_text()
    try:
        import yaml
        rows = yaml.safe_load(defaults)["dc_schema_surface_rows"]
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  could not load dc_schema_surface_rows: {exc}")
        return 1

    checks.append(("every row names a subsystem",
                   all(r.get("subsystem") for r in rows)))
    checks.append(("every row names at least one root",
                   all(r.get("roots") for r in rows)))
    checks.append((
        "every row carries agent_markers, without which no claim is adjudicable",
        all(r.get("agent_markers") for r in rows)))
    checks.append((
        "every claim is one of yes/no/partial",
        all(r.get("agent_scoped_claim") in ("yes", "no", "partial") for r in rows)))
    checks.append((
        "the twelve mapped subsystems plus the sub-agent addition are all present",
        len(rows) >= 13))
    for wanted in ("Plugins", "Memory", "MCP", "Tool policy", "Sub-agent"):
        checks.append((
            f"a row covers {wanted}",
            any(wanted.lower() in r["subsystem"].lower() for r in rows)))

    # --- 11. REGRESSION: the four false conflicts from the first real run ----
    #
    # 2026-08-25, build 2026.7.1-2, 6990 declared paths: the first version of the
    # adjudicator produced FOUR conflicts out of thirteen rows and every one was
    # its own fault. Each is reproduced here against a fixture and asserted gone.
    # A check that has never been observed to fail has not been tested; these
    # were observed to fail, on real evidence, and this is the proof they stop.

    # B: a Gateway-root key that NAMES an agent. hooks.allowedAgentIds and
    # bindings.agentId are both declared on the real host -- the rule that only
    # looked under `agents.` called both rows OVERSTATED.
    sch = base_schema()
    sch["properties"]["hooks"] = {"type": "object", "properties": {
        "allowedAgentIds": {"type": "array", "description": "agent allowlist"}}}
    sch["properties"]["bindings"] = {"type": "array", "items": {
        "type": "object", "properties": {"agentId": {"type": "string"}}}}

    rc, out, _ = run(sch, [{
        "subsystem": "Hooks", "roots": ["hooks"], "agent_markers": ["hook"],
        "agent_ref_markers": ["hooks.allowedAgentIds"],
        "agent_scoped_claim": "yes"}])
    checks.append((
        "REGRESSION Hooks: root routing by agent id CONFIRMS, not OVERSTATED",
        "mechanism B" in out and "OVERSTATED" not in out))

    rc, out, _ = run(sch, [{
        "subsystem": "Channels", "roots": ["bindings"],
        "agent_markers": ["binding"], "agent_ref_markers": ["bindings.agentId"],
        "agent_scoped_claim": "yes"}])
    checks.append((
        "REGRESSION Channels: bindings.agentId CONFIRMS, not OVERSTATED",
        "mechanism B" in out and "OVERSTATED" not in out))

    # Mechanism B matches EXACT declared paths. A loose match is what turned
    # `bind` into a bind mount, so a ref key that is merely a prefix of a real
    # one must not count.
    rc, out, _ = run(sch, [{
        "subsystem": "Hooks", "roots": ["hooks"], "agent_markers": ["nope"],
        "agent_ref_markers": ["hooks.allowed"], "agent_scoped_claim": "yes"}])
    checks.append((
        "a ref marker that is only a PREFIX of a declared key does not match",
        "OVERSTATED" in out))
    checks.append((
        "a cited-but-undeclared ref key is reported rather than silently ignored",
        "does not declare" in out.lower() or "not declared here" in out))

    # D: MCP narrows through tool policy, so no mcp-named agent path exists and
    # none should. Delegation must confirm -- but only from a CONFIRMED target.
    rc, out, _ = run(base_schema(), [
        ROW_TOOLS_YES,
        {"subsystem": "MCP servers", "roots": ["tools"], "agent_markers": ["mcp"],
         "narrows_via": "Tool policy", "agent_scoped_claim": "partial"}])
    checks.append((
        "REGRESSION MCP: delegation to a CONFIRMED row confirms, not OVERSTATED",
        "mechanism D" in out and "OVERSTATED" not in out))

    rc, out, _ = run(base_schema(), [{
        "subsystem": "MCP servers", "roots": ["tools"], "agent_markers": ["mcp"],
        "narrows_via": "A row nobody supplied", "agent_scoped_claim": "partial"}])
    checks.append((
        "delegating to a row that does not exist is UNKNOWN, not CONFIRMED",
        "UNKNOWN" in out and "CONFIRMED [VERIFIED HOST]" not in out))

    # The laundering guard: a delegate that is itself unproven must not hand out
    # a confirmed verdict.
    rc, out, _ = run(base_schema(), [
        {"subsystem": "Ghost", "roots": ["notAThing"], "agent_markers": ["x"],
         "agent_scoped_claim": "yes"},
        {"subsystem": "MCP servers", "roots": ["tools"], "agent_markers": ["mcp"],
         "narrows_via": "Ghost", "agent_scoped_claim": "partial"}])
    checks.append((
        "delegation to an UNKNOWN row resolves UNKNOWN, never CONFIRMED",
        "launder" in out and out.count("CONFIRMED [VERIFIED HOST]") == 0))

    # A: exclude_markers. `bind` matched agents.list.sandbox.docker.binds and
    # reported the Gateway row UNDERSTATED. The exclusion must kill it.
    sch2 = base_schema()
    sch2["$defs"]["Agent"]["properties"]["sandbox"]["properties"]["binds"] = {
        "type": "array"}
    rc, out_no_excl, _ = run(sch2, [{
        "subsystem": "Gateway", "roots": ["gateway"],
        "agent_markers": ["gateway", "bind"], "agent_scoped_claim": "no"}])
    rc, out_excl, _ = run(sch2, [{
        "subsystem": "Gateway", "roots": ["gateway"],
        "agent_markers": ["gateway", "bind"], "exclude_markers": ["sandbox"],
        "agent_scoped_claim": "no"}])
    checks.append((
        "REGRESSION Gateway: a bind-mount path DOES trip a bare `bind` marker",
        "UNDERSTATED" in out_no_excl))
    checks.append((
        "REGRESSION Gateway: exclude_markers suppresses the bind-mount collision",
        "UNDERSTATED" not in out_excl))

    # The four corrected rows must carry their mechanism in the shipped defaults,
    # or the fix lives only in the reader and the real run regresses.
    by_name = {r["subsystem"]: r for r in rows}
    for nm, field in (("Hooks", "agent_ref_markers"), ("Channels", "agent_ref_markers"),
                      ("MCP", "narrows_via"), ("Gateway", "exclude_markers")):
        row = next((r for k, r in by_name.items() if nm.lower() in k.lower()), None)
        checks.append((
            f"the shipped {nm} row declares {field}",
            bool(row and row.get(field))))

    # --- 12. caps announce themselves ---------------------------------------
    # Silent truncation reads as "covered everything". Every cap in the reader
    # must print a line saying it bit.
    reader = READER.read_text()
    checks.append((
        "the reader announces its per-row cap when it bites",
        "NOT shown" in reader and "cap reached" in reader))
    checks.append((
        "the unmapped-roots list states it is a floor and not a ceiling",
        "floor on what is unmapped, never a ceiling" in reader))

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    if failed:
        print(f"\n{len(failed)} schema-surface check(s) failed.")
        return 1
    print(f"\nAll {len(checks)} schema-surface checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
