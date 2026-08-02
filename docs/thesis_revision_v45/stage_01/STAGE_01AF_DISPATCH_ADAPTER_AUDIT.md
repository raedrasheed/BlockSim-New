# Stage 1AF — Dispatch Adapter Audit (correction AF2)

This audit verifies that `PROCEDURE BuildHandlerInvocation` — the named ordinary-dispatch
adapter introduced by correction AF2 — binds the EXACT named handler arguments for every
queued event type, entirely from the authoritative `event_descriptor` set (§0.7g-schema, AF1),
the trusted stored record, and the runtime context. The protocol under revision is **PoCol**;
the mechanism examined here is part of the event-dispatch machinery of PoCol operating under
the idle policy within PoCol; this correction is documentation-only and preserves the A1
continuous-control energy baseline of `8.420833333 kWh` unchanged (no executable source,
configuration, or experiment was touched).

Scope: the adapter procedure at `STAGE_01_PROTOCOL_PSEUDOCODE.md` `PROCEDURE
BuildHandlerInvocation` (lines 191–231), the two §0.7g-schema binding tables — the descriptor
core table (lines 942–963) and the "Descriptor binding (categories 1/2)" table (lines
965–990) — and the `ProcessEventTime` dispatch site that calls the adapter and invokes the
returned handler (lines 288–289). Handler signatures were cross-checked against each
`INPUTS:` line to confirm the produced argument set equals the declared parameter set.

**All line anchors below are into `STAGE_01_PROTOCOL_PSEUDOCODE.md`.**

## Findings

### Item 1 — Returns `handler_invocation(procedure, args)`; args are the exact declared arguments

`BuildHandlerInvocation` builds `args` as "the EXACT named argument set `d.handler_procedure`
declares" (lines 199–205), then returns `handler_invocation(procedure = d.handler_procedure,
args = args)` (line 223), with the `RETURNS:` shape declared as `handler_invocation(procedure,
args)` (line 224). The dispatch site consumes exactly this contract: `SET inv <- CALL
BuildHandlerInvocation(...)` (line 288) followed by `CALL inv.procedure WITH inv.args` (line
289). Spot-checked handler signatures confirm the produced argument set equals the declared
`INPUTS:` in each case — e.g. `WakeCompleteEvent` (line 1988), `HashWorkEvent` (line 3127),
`CertificateArrival` (line 5435), `BlockAcceptancePoint` (line 5460), `LeaseExpiry` (line
4958), `ActiveHashRateUpdate` (line 3358), `SetupRetryEvent` (line 2662). **PASS.**

### Item 2 — Payload binding through `d.payload_to_param_map`, including the version resolver

The payload loop iterates `FOR EACH map_entry IN d.payload_to_param_map` (line 207). The
version resolver branch resolves `(AssignmentID, assignment_version) -> P` as
`version(record.immutable_payload.AssignmentID, record.immutable_payload.assignment_version)`
(lines 208–209); the ELSE branch performs a direct 1:1 bind
`args[handler_param] <- record.immutable_payload[payload_key]` (lines 210–212). The binding
table applies this exactly: `WakeCompleteEvent` binds `(AssignmentID, assignment_version) ->
target_assignment via version(...)` (line 981) — matching the handler input `target_assignment`
(line 1988); `LeaseExpiry` binds `(AssignmentID, assignment_version) -> assignment via
version(...)` (line 983) — matching handler input `assignment` (line 4958). Direct 1:1 binds
including renames are present: `from_cursor -> cursor` for `HashWorkEvent` (line 977, handler
input `cursor` at line 3127) and `recipient -> r` for `CertificateArrival` (line 978, handler
input `r` at line 5435). **PASS.**

### Item 3 — Runtime injection is descriptor-driven

The runtime loop iterates `FOR EACH (runtime_source -> handler_param) IN d.runtime_injected`
(line 214) and switches on the source: `RoundContext` (line 216); `RunContext` — annotated
"RoundInitialiseEvent only" (line 217), and the binding table confirms `RunContext ->
RunContext` appears on that row alone (line 971, wrapper INPUTS at line 1025); `dispatch_envelope`
gated "IFF `d.recv_env` = yes" (line 218); `dispatched_event_ref` gated "IFF `d.recv_ref` =
yes — currently ONLY SetupRetryEvent" (line 219). Runtime injection is therefore driven
entirely by the descriptor, never from ambient state (line 213). **PASS.**

### Item 4 — `ReserveActivateEvent` gets `dispatch_envelope`; the wrapper (not the adapter) builds `scheduling_context`

The descriptor core row marks `ReserveActivateEvent` `recv env = yes (wrapper receives
dispatch_envelope)` and states "the wrapper builds `scheduling_context =
ORDINARY_DISPATCH(dispatch_envelope)` for the ReserveActivate call" (line 948). The binding
row injects `dispatch_envelope -> dispatch_envelope` and states "the wrapper then builds
`scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` ... AF2: never a bare envelope
reaches ReserveActivate" (line 975). The adapter's `NOTE` reiterates the same (lines 226–228).
The wrapper procedure `ReserveActivateEvent` receives `dispatch_envelope` (INPUTS, line 1066)
and issues `CALL ReserveActivate(RoundContext, deficit = deficit, scheduling_context =
ORDINARY_DISPATCH(dispatch_envelope))` (lines 1074–1075) — so `ReserveActivate` receives the
`SchedulingSourceContext` wrapper, never the bare envelope (comment, lines 1071–1073). The
construction of `scheduling_context` occurs in the wrapper body, not in `BuildHandlerInvocation`
(which only injects the raw `dispatch_envelope`). **PASS.**

### Item 5 — `BlockAcceptancePoint` / `ActiveHashRateUpdate` receive no env and no ref; `SetupRetryEvent` receives both

`BlockAcceptancePoint`: core row `recv env = no, recv ref = no` (line 952); binding row
`RoundContext -> RoundContext (AF2: NO dispatch_envelope, NO dispatched_event_ref)` (line 979);
handler INPUTS omit both (line 5460). `ActiveHashRateUpdate`: core row `recv env = no, recv ref
= no` (line 958); binding row `RoundContext -> RoundContext (no envelope)` (line 985); handler
INPUTS are `RoundContext, time t` only (line 3358). `SetupRetryEvent`: core row `recv env =
yes, recv ref = yes` (line 963); binding row injects `dispatch_envelope -> dispatch_envelope`
AND `dispatched_event_ref <- ctx.dispatched_event_ref (recv ref = yes)` (line 990); handler
INPUTS declare both `dispatch_envelope, dispatched_event_ref` (line 2662). The confirming prose
states `SetupRetryEvent` is the ONLY `recv ref = yes` descriptor and `BlockAcceptancePoint` /
`ActiveHashRateUpdate` are the ONLY `recv env = no` descriptors (lines 1006–1009). **PASS.**

### Item 6 — Defensive ASSERTs enforce env/ref agreement

Immediately after the runtime loop the adapter asserts
`ASSERT (dispatch_envelope in args) = (d.recv_env = yes)` (line 221) and
`ASSERT (dispatched_event_ref in args) = (d.recv_ref = yes)` (line 222). The inline annotations
give the concrete truth values — `BlockAcceptancePoint` / `ActiveHashRateUpdate` FALSE on both
sides of the env assertion; `SetupRetryEvent` TRUE on both sides, all others FALSE, for the ref
assertion — so an envelope or ref can never be injected for a handler that omits it, and can
never be omitted for a handler that declares it. **PASS.**

### Item 7 — No handler receives an undeclared argument, an unresolved alias, or a derived output in place of a declared input

The adapter's own contract states the guarantee: "NO undeclared argument, NO unresolved alias,
NO derived output substituted for an input" (lines 199–201), restated in the `NOTE` (lines
230–231) and in the binding-table preamble (lines 966–967). This holds mechanically because
`args` is populated only from `d.payload_to_param_map` (with declared resolvers) and
`d.runtime_injected` (lines 205–219), and the env/ref ASSERTs (lines 221–222) bound the runtime
set. Cross-checking each handler's declared `INPUTS:` against the union of its
`payload_to_param_map` targets and `runtime_injected` targets yields an exact match for every
row, with aliases resolved by the adapter before dispatch (`from_cursor`→`cursor`,
`recipient`→`r`) and version-resolved assignments delivered as the declared inputs
`target_assignment` / `assignment` rather than as raw payload keys. **PASS.**

## Per-item verdict table

| # | Claim | Verdict | Line anchors (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) |
|---|-------|:------:|--------------------------------------------------|
| 1 | Returns `handler_invocation(procedure, args)`; args = exact declared arguments | **PASS** | Adapter 199–205, 223–224; dispatch site 288–289; signatures 1988, 3127, 5435, 5460, 4958, 3358, 2662 |
| 2 | Payload binds via `d.payload_to_param_map` incl. version resolver; direct 1:1 otherwise | **PASS** | Loop 207–212; version 208–209; WakeComplete 981; LeaseExpiry 983; `from_cursor`→`cursor` 977; `recipient`→`r` 978 |
| 3 | Runtime injection descriptor-driven: RoundContext, RunContext (RoundInitialise only), env IFF recv_env, ref IFF recv_ref | **PASS** | Loop 213–219; RoundContext 216; RunContext 217 + 971; env 218; ref 219 |
| 4 | ReserveActivate gets `dispatch_envelope`; wrapper (not adapter) builds `scheduling_context = ORDINARY_DISPATCH(...)`; no bare envelope reaches ReserveActivate | **PASS** | Core 948; binding 975; NOTE 226–228; wrapper 1066, 1071–1075 |
| 5 | BlockAcceptancePoint & ActiveHashRateUpdate: no env, no ref; SetupRetryEvent: both | **PASS** | 952 & 979 & 5460; 958 & 985 & 3358; 963 & 990 & 2662; prose 1006–1009 |
| 6 | ASSERT (env in args)=(recv_env=yes); ASSERT (ref in args)=(recv_ref=yes) | **PASS** | 221; 222 |
| 7 | No undeclared argument, unresolved alias, or handler-derived output in place of a declared input | **PASS** | Contract 199–201, 230–231, 966–967; mechanism 205–222 |

## Reading notes (confirmations, not defects)

- **Version resolver dual-listing is intentional.** For `WakeCompleteEvent` / `LeaseExpiry` the
  version-resolved value is listed both under the descriptor core column "Derived by handler"
  (lines 954, 956) and under `payload_to_param_map` via the `version(...)` resolver (lines 981,
  983). These are two views of the same construct: the resolver is a declared member of
  `payload_to_param_map`, applied by the adapter (lines 208–209) so the handler receives its
  declared input (`target_assignment` / `assignment`) already resolved — consistent with, not
  contradictory to, Item 7.
- **AF4 driver-wrapper staleness/tie-key keys bind 1:1.** For the AF4 wrappers
  (`PrepareParticipantsEvent`, `ReserveActivateEvent`, `FullRangeExhaustEvent`) the binding rows
  annotate `RoundID_at_seat` / `TemplateID_at_seat` / `activation_seq` as "staleness / tie-key
  context" (lines 973, 975, 976). These identically-named payload keys bind through the adapter's
  direct 1:1 ELSE branch (lines 210–212) to the wrapper's identically-named parameters, which the
  wrappers declare and use (e.g. `ReserveActivateEvent` INPUTS line 1066, staleness check line
  1069), consistent with the wrapper contract "receives its declared runtime context, calls the
  domain procedure with the EXACT named arguments" (lines 1092–1096). The wrapper therefore still
  receives exactly its declared inputs (Item 1).

## Overall verdict

**PASS (7 of 7).** `BuildHandlerInvocation` is a faithful, descriptor-driven dispatch adapter:
it returns `handler_invocation(procedure, args)` with the exact declared argument set, binds all
payload arguments through `d.payload_to_param_map` (including the `version(...)` resolver and
direct 1:1 renames), injects runtime context strictly per the descriptor's `runtime_injected` /
`recv_env` / `recv_ref` fields, routes `dispatch_envelope` to the `ReserveActivateEvent` wrapper
which alone builds `scheduling_context = ORDINARY_DISPATCH(...)`, withholds both envelope and ref
from `BlockAcceptancePoint` and `ActiveHashRateUpdate` while supplying both to `SetupRetryEvent`,
and enforces env/ref agreement with two defensive ASSERTs. No handler receives an undeclared
argument, an unresolved alias, or a handler-derived output in place of a declared input. The AF2
correction is verified against the FINAL normative tree.
