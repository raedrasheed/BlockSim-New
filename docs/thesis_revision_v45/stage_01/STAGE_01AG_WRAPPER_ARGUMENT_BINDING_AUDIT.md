# Stage 1AG — Wrapper Argument-Binding Audit (correction AG1)

This is a documentation-only audit of correction **AG1** in the after-final, frozen source of truth
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only). The algorithm is **PoCol**; the mechanism exercised here is the idle
policy within PoCol. AG1 closes the residual dispatch-adapter binding gap: every AF4 wrapper payload field now has an
EXPLICIT `payload_to_param_map` entry (no unwritten same-name copy), `BuildHandlerInvocation` (AF2) binds ONLY what the
descriptor map declares and then VERIFIES the produced argument key set against the handler's ground-truth INPUTS
(`d.handler_inputs`) as a STRUCTURED result rather than a raw assertion, and `ProcessEventTime` consumes that structured
result — calling the handler only on success. This audit reads the FINAL normative tree and edits nothing. The A1
baseline (`8.420833333 kWh`) is preserved — nothing in AG1 touches the energy model, only the ordinary-dispatch argument
adapter. Every claim is grounded with `file:line` anchors into `STAGE_01_PROTOCOL_PSEUDOCODE.md` (abbreviated **PC**),
quoting the operative current lines.

---

## 0. What AG1 declares (the authoritative addenda read)

- `PROCEDURE BuildHandlerInvocation` — the sole ordinary-dispatch argument adapter (**PC:199–250**).
- `PROCEDURE ProcessEventTime` — the caller that consumes the adapter's structured result (**PC:252–343**, dispatch
  region **PC:322–336**).
- `STRUCTURE event_descriptor`, `handler_inputs` field definition (**PC:960–990**, specifically **PC:964–968**).
- §0.7g "Descriptor binding (categories 1/2)" table — `payload_to_param_map` + `runtime_injected` per event
  (**PC:1029–1058**).
- "Handler INPUTS ground truth (AG1 — `d.handler_inputs`)" table (**PC:1060–1074**).
- Descriptor core table — the EXACT closed `allowed_payload_keys` per event (**PC:1006–1027**).
- The six AF4 wrapper procedures (**PC:1108–1189**).

---

## 1. Every AF4 wrapper's `payload_to_param_map` has an EXPLICIT entry for EVERY required payload field

The descriptor-binding narrative states the rule directly: `BuildHandlerInvocation` "binds ONLY what the map declares —
there is NO unwritten same-name fallback (AG1), so EVERY handler-input parameter must be produced by an explicit
`payload_to_param_map` entry or a `runtime_injected` entry" (**PC:1030–1033**). Each wrapper's binding row (**PC:1039–1044**)
is checked against the EXACT closed `allowed_payload_keys` for that event (descriptor core, **PC:1008–1013**):

| Wrapper | Required payload fields (`allowed_payload_keys`) | Explicit `payload_to_param_map` entries | PASS/FAIL | Anchors |
|---------|--------------------------------------------------|-----------------------------------------|:---------:|---------|
| `RoundInitialiseEvent` | `round_setup_seq` | `round_setup_seq -> round_setup_seq` (AG1: explicit) | **PASS** | keys PC:1008; map PC:1039 |
| `TemplateCommitEvent` | `RoundID_at_seat`, `candidate_template` | `RoundID_at_seat -> RoundID_at_seat`; `candidate_template -> candidate_template` (AG1: both explicit) | **PASS** | keys PC:1009; map PC:1040 |
| `PrepareParticipantsEvent` | `RoundID_at_seat`, `TemplateID_at_seat` | `RoundID_at_seat -> RoundID_at_seat`; `TemplateID_at_seat -> TemplateID_at_seat` (AG1: both explicit) | **PASS** | keys PC:1010; map PC:1041 |
| `MinerRegisterEvent` | `join_request` | `join_request -> join_request` | **PASS** | keys PC:1011; map PC:1042 |
| `ReserveActivateEvent` | `RoundID_at_seat`, `deficit`, `activation_seq` | `RoundID_at_seat -> RoundID_at_seat`; `deficit -> deficit`; `activation_seq -> activation_seq` (AG1: all three explicit) | **PASS** | keys PC:1012; map PC:1043 |
| `FullRangeExhaustEvent` | `RoundID_at_seat`, `TemplateID_at_seat` | `RoundID_at_seat -> RoundID_at_seat`; `TemplateID_at_seat -> TemplateID_at_seat` (AG1: both explicit) | **PASS** | keys PC:1013; map PC:1044 |

For all six wrappers the set of payload keys with a map entry equals the closed `allowed_payload_keys` set exactly — no
payload field is left unbound. No `(none)` binding and no prose-only ("the wrapper resolves …") binding remains in any of
the six rows; a document-wide check finds no `(none)` binding anywhere in the descriptor tables. (The `runtime_injected`
side-note on the `RoundInitialiseEvent` row, "wrapper resolves `config <- RunContext.config` …" at **PC:1039**, describes
resolution the wrapper performs from the injected `RunContext` inside its body at **PC:1115–1116**; it is not a payload
binding and does not substitute for one.) **Item 1: PASS.**

---

## 2. `BuildHandlerInvocation` binds ONLY the declared map, VERIFIES against `d.handler_inputs`, and does NOT raw-assert

**Binds only what the map declares (no same-name fallback).** The payload-binding loop iterates `FOR EACH map_entry IN
d.payload_to_param_map` and assigns `args[handler_param] <- record.immutable_payload[payload_key]` (**PC:218–223**). The
governing comment is explicit: "AG1: EVERY wrapper payload field has an EXPLICIT map entry — BuildHandlerInvocation binds
ONLY what the map declares; it NEVER falls back to a same-name copy. A payload field with no map entry is therefore
simply not bound (and the AG1 verification below catches the resulting missing argument)" (**PC:215–217**). Runtime
arguments are likewise injected only from `d.runtime_injected` (**PC:224–230**).

**Verifies `keys(args) == d.handler_inputs` via `missing_args` + `extra_args`.** After both injection passes:
`SET missing_args <- members of d.handler_inputs NOT present in keys(args)` (**PC:235**) and `SET extra_args <- members of
keys(args) NOT present in d.handler_inputs` (**PC:236**). `IF missing_args is non-empty OR extra_args is non-empty` it
`RETURN handler_invocation_binding_failed(d.event_type, missing_args, extra_args)` (**PC:237–239**); otherwise it
`RETURN handler_invocation_built(procedure = d.handler_procedure, args = args)` (**PC:240**). The `RETURNS` line declares
exactly this disjunction: `handler_invocation_built(procedure, args) | handler_invocation_binding_failed(event_type,
missing_args, extra_args)` (**PC:241**).

**No raw assertion; the recv_env/recv_ref ASSERTs are gone/replaced.** The verification is a STRUCTURED failure: "A
binding inconsistency … is a STRUCTURED failure, NEVER a raw assertion. This subsumes the AF2 recv_env/recv_ref checks:
an envelope/ref injected for a handler that omits it appears as an extra_arg; an omitted one as a missing_arg"
(**PC:231–234**), reinforced by the closing NOTE "a mismatch is the structured handler_invocation_binding_failed, never a
raw assertion — AG1" (**PC:242–245**). The procedure body (**PC:206–240**) contains no `ASSERT` statement, and
`recv_env`/`recv_ref` now appear only in explanatory comments (**PC:209, 229–230, 233**), not as executable assertions —
the former AF2 recv_env/recv_ref raw asserts have been replaced by the `missing_args`/`extra_args` check. **Item 2: PASS.**

| Sub-claim | PASS/FAIL | Anchors |
|-----------|:---------:|---------|
| Binds only `payload_to_param_map` entries; no same-name fallback | **PASS** | PC:215–223 |
| Runtime args injected only from `d.runtime_injected` | **PASS** | PC:224–230 |
| Verifies `keys(args) == d.handler_inputs` (`missing_args` + `extra_args`) | **PASS** | PC:235–236 |
| Returns `handler_invocation_binding_failed(event_type, missing_args, extra_args)` on mismatch | **PASS** | PC:237–239, 241 |
| Returns `handler_invocation_built(procedure, args)` on success | **PASS** | PC:240–241 |
| Structured failure, NOT a raw assertion; recv_env/recv_ref asserts subsumed/removed | **PASS** | PC:231–234, 242–245 |

---

## 3. `d.handler_inputs` is the ground-truth INPUTS of `handler_procedure` and equals map targets ∪ runtime_injected targets

The `event_descriptor` structure defines `handler_inputs` as "the GROUND-TRUTH set of parameter names declared on
handler_procedure's INPUTS line (AG1). It is the authority BuildHandlerInvocation VERIFIES the produced argument key set
against — NOT a copy of the map. Every handler_inputs member MUST be produced by exactly one of payload_to_param_map
(category 1) or runtime_injected (category 2); none may rely on an unwritten same-name fallback (AG1)" (**PC:964–968**).
The ground-truth table (**PC:1064–1071**) is cross-checked against each wrapper's declared INPUTS line and against the
union of its map targets (**PC:1039–1044**) plus its `runtime_injected` targets (same rows):

| Wrapper | `d.handler_inputs` (table) | Wrapper INPUTS line | Map targets ∪ runtime targets | PASS/FAIL | Anchors |
|---------|----------------------------|---------------------|-------------------------------|:---------:|---------|
| `RoundInitialiseEvent` | `{ RunContext, round_setup_seq }` | `RunContext, round_setup_seq` | `{round_setup_seq}` ∪ `{RunContext}` | **PASS** | table PC:1066; INPUTS PC:1109; map/rt PC:1039 |
| `TemplateCommitEvent` | `{ RoundContext, RoundID_at_seat, candidate_template }` | `RoundContext, RoundID_at_seat, candidate_template` | `{RoundID_at_seat, candidate_template}` ∪ `{RoundContext}` | **PASS** | table PC:1067; INPUTS PC:1126; map/rt PC:1040 |
| `MinerRegisterEvent` | `{ RoundContext, join_request, dispatch_envelope }` | `RoundContext, join_request, dispatch_envelope` | `{join_request}` ∪ `{RoundContext, dispatch_envelope}` | **PASS** | table PC:1068; INPUTS PC:1139; map/rt PC:1042 |
| `PrepareParticipantsEvent` | `{ RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope }` | `RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` | `{RoundID_at_seat, TemplateID_at_seat}` ∪ `{RoundContext, dispatch_envelope}` | **PASS** | table PC:1069; INPUTS PC:1147; map/rt PC:1041 |
| `ReserveActivateEvent` | `{ RoundContext, RoundID_at_seat, deficit, activation_seq, dispatch_envelope }` | `RoundContext, RoundID_at_seat, deficit, activation_seq, dispatch_envelope` | `{RoundID_at_seat, deficit, activation_seq}` ∪ `{RoundContext, dispatch_envelope}` | **PASS** | table PC:1070; INPUTS PC:1159; map/rt PC:1043 |
| `FullRangeExhaustEvent` | `{ RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope }` | `RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` | `{RoundID_at_seat, TemplateID_at_seat}` ∪ `{RoundContext, dispatch_envelope}` | **PASS** | table PC:1071; INPUTS PC:1175; map/rt PC:1044 |

For every wrapper the ground-truth INPUTS set equals the union of the map targets and the runtime-injected targets, with
no member left over on either side. `ReserveActivateEvent` is consistent under scrutiny: the wrapper's declared INPUT is
`dispatch_envelope` (injected, **PC:1043, 1159**), and `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` is
built INSIDE the wrapper body for the domain `ReserveActivate` call (**PC:1167–1168**) — it is not a wrapper INPUT, so it
does not appear in `handler_inputs`, and the union still matches exactly. **Item 3: PASS.**

---

## 4. `ProcessEventTime` consumes the structured result correctly

`ProcessEventTime` obtains the result with `SET inv <- CALL BuildHandlerInvocation(d, record, dispatch_round_context,
RunContext, ctx)` (**PC:324**), then branches:

- **On `handler_invocation_binding_failed`** — `IF inv = handler_invocation_binding_failed(event_type, missing_args,
  extra_args)` it `RECORD dispatch_binding_failed(event_type, missing_args, extra_args)` with the comment "AG1:
  structured; handler NEVER called" (**PC:325–326**), then ATOMICALLY sets `queue_status <- CONSUMED` and CLEARs all
  `EQ.current_*` context, then `CONTINUE` (**PC:327–330**). The handler is not called on this path. **PASS.**
- **On `handler_invocation_built`** — falling through to `CALL inv.procedure WITH inv.args` (**PC:331–332**, comment
  "AG1: inv = handler_invocation_built(procedure, args) — the produced args EQUAL the handler's declared INPUTS"),
  followed by the ATOMIC `DISPATCHING -> CONSUMED` + CLEAR lifecycle after the handler returns (**PC:334–336**). **PASS.**

| Sub-claim | PASS/FAIL | Anchors |
|-----------|:---------:|---------|
| Consumes `inv` from `BuildHandlerInvocation` | **PASS** | PC:324 |
| On binding_failed: records `dispatch_binding_failed`, does NOT call handler, CONSUMEs + CLEARs, CONTINUE | **PASS** | PC:325–330 |
| On built: `CALL inv.procedure WITH inv.args` | **PASS** | PC:331–332 |
| Post-handler lifecycle `DISPATCHING -> CONSUMED` + CLEAR | **PASS** | PC:334–336 |

**Item 4: PASS.**

---

## 5. Overall verdict

| Item | Claim | Verdict |
|:----:|-------|:-------:|
| 1 | Every AF4 wrapper's `payload_to_param_map` has an explicit entry for every required payload field; no `(none)`/prose bindings remain | **PASS** |
| 2 | `BuildHandlerInvocation` binds only the declared map (no same-name fallback), verifies `keys(args) == d.handler_inputs`, returns `handler_invocation_built` / `handler_invocation_binding_failed`, and does not raw-assert (recv_env/recv_ref asserts subsumed/removed) | **PASS** |
| 3 | `d.handler_inputs` is the ground-truth INPUTS of `handler_procedure` and equals map targets ∪ runtime_injected targets for each wrapper | **PASS** |
| 4 | `ProcessEventTime` consumes the structured result — records `dispatch_binding_failed` and skips the handler on failure; calls `inv.procedure WITH inv.args` on success | **PASS** |

**OVERALL: PASS.** Correction AG1 is implemented consistently across `BuildHandlerInvocation`, the §0.7g descriptor
binding and handler-INPUTS ground-truth tables, the six AF4 wrapper procedures, and `ProcessEventTime`. No defect was
found. The audit is documentation-only; the algorithm remains PoCol with the idle policy within PoCol, and the A1
baseline (`8.420833333 kWh`) is preserved.
