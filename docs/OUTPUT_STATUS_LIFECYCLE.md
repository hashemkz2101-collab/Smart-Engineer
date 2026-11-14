# Output status lifecycle

The six output states below reproduce the master specification's Section 1
vocabulary. They describe the maturity/review state of an output, not whether a
feature or phase is implemented. A language model or automated calculation may
never grant a human review or professional approval state.

## States and proposed transition controls

| State | Meaning | Who may set/authorize it | Watermark / user-facing treatment |
|---|---|---|---|
| **Conceptual** | Exploratory design or output not yet treated as a measured/validated professional deliverable. | The system may label generated exploratory output Conceptual. An authorized user may label a manually created exploratory artifact Conceptual. This is classification, not approval. | Show “Conceptual” prominently; do not imply construction use or regulatory compliance. |
| **Initial** | A first persisted draft/model/calculation result that has not been submitted to formal review. | System may assign Initial when saving a new artifact/version; authorized editor may create a new Initial version. | Show “Initial” (or “Draft” only as a display synonym explicitly mapped to Initial). |
| **Under Review** | An Initial version formally submitted to an assigned reviewer; review is pending. | Authorized project contributor submits the immutable version to the assigned review workflow. Submission does not authorize or certify its contents. | Show “Under Review”; identify submitted version and review state. |
| **Reviewed** | A qualified, assigned discipline reviewer has completed and recorded a review within the reviewer's scope. This is not equivalent to Approved or construction authorization. | Assigned qualified reviewer records identity, discipline/scope, decision, time, findings, and reviewed version. Qualification/authority must follow DEC-007/028/033. | Show “Reviewed” only with the review record; never substitute this for Approved. |
| **Approved** | An authorized professional approver has explicitly accepted the specified version under a legally and organizationally authorized approval process. Client stage acceptance is a separate event and does not by itself constitute professional approval. | Only a professional approver whose authority is established by DEC-007/008/028/033 may authorize this transition. Until those decisions are resolved, disable Approved transitions. | Show “Approved” only with approver identity, scope, timestamp, evidence/signature where required, and exact version. It must not be described as construction-authorized unless that legal status is separately established. |
| **Rejected** | The submitted version was not accepted for the requested review/approval purpose; a reason and required follow-up are recorded. | Assigned qualified reviewer or authorized approver rejects within their scope, with reason, identity, and timestamp. Authority is subject to DEC-007/028/033. | Show “Rejected” and reason; retain the rejected version and audit history. |

## Allowed transitions

The following is a conservative proposed workflow. It is not a new legal
decision; unresolved authorization is gated by DEC-033.

```text
Conceptual ──authorized editor creates a formal version──> Initial
Initial ──authorized contributor submits immutable version──> Under Review
Under Review ──qualified reviewer records completed review──> Reviewed
Under Review ──authorized reviewer rejects with reason──────> Rejected
Reviewed ──authorized professional approver accepts─────────> Approved
Reviewed ──authorized professional approver rejects─────────> Rejected
Rejected ──authorized editor creates a new version─────────> Initial
Approved ──change requested────────────────────────────────> new Initial version
```

No direct transition from Conceptual/Initial to Reviewed or Approved is
permitted. Reopening or rescinding an Approved artifact must not rewrite its
history: issue a superseding version and retain the prior approval/revision
record. Automated rule/solver/AI output may create or update an Initial result
and may create findings, but cannot set Reviewed, Approved, or Rejected.

## Watermarks and decisions

- The master specification's Section 10 lists PDF watermarks as
  draft/conceptual/reviewed/approved. The display mapping above makes “Draft”
  a synonym for Initial only; it does not add a seventh lifecycle state.
- Under Review and Rejected watermarks should be shown for those states so a
  document cannot appear more mature than it is. This is a safe proposed
  display extension, not a change to the six master states.
- Reviewer qualification, professional sign-off, digital-signature
  requirements, client-vs-professional authority, and legal meaning of
  “Approved” remain unresolved under DEC-007, DEC-008, DEC-028, and DEC-033.
  Until resolved, the system must not grant an Approved state or claim legal
  authorization.
- Every transition records source version, actor/automation identity, prior
  and new state, time, reason/evidence, and applicable review/approval scope.
