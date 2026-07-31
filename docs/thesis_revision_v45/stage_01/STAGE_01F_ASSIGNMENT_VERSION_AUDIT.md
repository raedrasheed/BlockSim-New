# Stage 1F — Assignment-Version Audit (F7, I18)

Verifies immutable, atomic assignment versioning: renewal creates a new CURRENT version and
supersedes the old one without mutating identity, exactly one CURRENT version exists per lineage, and
old versions stay resolvable for discovery snapshots. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md`
§0.8, `RenewAssignment`, `CreatePendingAssignment`, `ValidateCandidate`; and I18.

## 1. Version model

An `Assignment` is an immutable versioned object with a stable `lineage_id`. Versions are created by
`CreatePendingAssignment` (ORIGINAL / REASSIGNED / RENEWED) and `RenewAssignment` (RENEWED CURRENT).
`status ∈ {PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}`.

## 2. Renewal (RenewAssignment)

`RenewAssignment(old_assignment, t)` creates version `V2` on the SAME range/holder/RoundID/TemplateID
with `assignment_version+1`, `assignment_origin = RENEWED`, `previous_assignment_reference =
AssignmentID(old)`, COPIED actual/reported/accepted frontiers and provenance, and a new lease window;
then ATOMICALLY sets `status(old) = SUPERSEDED` (`superseded_at = t`) and `status(V2) = CURRENT`.

## 3. Properties

| # | Property | Result |
|--:|----------|--------|
| 1 | Renewal creates an immutable new version, not an in-place mutation | **PASS** — `RenewAssignment` CREATEs `V2` with a fresh `AssignmentID`; the old version's fields are never rewritten (only its `status`/`superseded_at` are set as it retires) |
| 2 | Exactly one CURRENT version per lineage (I18) | **PASS** — the atomic swap sets old→SUPERSEDED and new→CURRENT together; `RenewAssignment` asserts "exactly one CURRENT in lineage" post-swap |
| 3 | Renewal preserves range, holder, coverage, provenance | **PASS** — same range/holder; frontiers and provenance copied; status stays effectively CURRENT (on `V2`); no WAKING (E5/E9/F7) |
| 4 | Old versions remain resolvable by snapshot | **PASS** — `ValidateCandidate` resolves `snapshot.(AssignmentID, assignment_version)` to the immutable version; a `v1`-discovery snapshot resolves to the SUPERSEDED `v1` and validates if `v1` was CURRENT at discovery and not revoked before `discovery_time` (E1) |
| 5 | A discovered solution stays valid across renewal | **PASS** — TV35: discovery under `v1`, renewal to `v2`, `ValidateCandidate` against the `v1` snapshot returns ok; the paused finder is not invalidated by the renewal |
| 6 | A changed range is never a renewal | **PASS** — `RenewAssignment` keeps the SAME range; a different range is a reassignment via `CreatePendingAssignment(REASSIGNED)` + `StartWake` (E5; the retired T6 self-loop cannot reappear) |
| 7 | Shared constructor sets provenance by origin | **PASS** — `CreatePendingAssignment(assignment_origin)`: ORIGINAL → custody original + null reference; REASSIGNED → custody reassigned + source reference + I9 provenance; RENEWED → custody renewed + copied lineage coverage (F4) |
| 8 | Reserve provenance distinguishes ORIGINAL vs REASSIGNED | **PASS** — `ReserveActivate` selects `origin` by whether the range is fresh or a prior unsearched suffix; a reassignable suffix is never ORIGINAL (TV31/TV32) |

## 4. Lineage invariant enforcement (I18)

`I18` is enforced at `RenewAssignment` (atomic supersede-and-publish) and read by `ValidateCandidate`
(version resolution). Because renewal is atomic, no observer ever sees two CURRENT versions or zero
CURRENT versions in a lineage.

## Result

**ASSIGNMENT-VERSION AUDIT (F7/I18): PASS.** Renewal is an atomic immutable version swap; exactly one
CURRENT version exists per lineage; old versions stay immutable and snapshot-resolvable; provenance
is set correctly by `assignment_origin`. (Exercised by TV31, TV32, TV35.)
