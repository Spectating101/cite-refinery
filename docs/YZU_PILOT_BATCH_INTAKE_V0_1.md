# YZU Pilot Batch Intake V0.1

Status: **pre-contact operational package**

The first pilot should not require YZU to integrate software or author Problem Commons JSON. A program office can export or paste a small batch of existing needs into a CSV using:

`pilot/intake/yzu-center-batch-template.v0.1.csv`

## Minimum fields

Only four columns are structurally required per row:

- `title`
- `owner_org`
- `owner_statement`
- `geography`

All other columns may be blank and remain unresolved rather than inferred.

Useful optional fields include source URL/reference, current schedule, affected actors, available resources, requested support, constraints, uncertainties, safeguarding notes and data-access notes.

List-valued cells use `|` as the separator, for example:

`students|families|community volunteers`

## Provenance and confirmation

If `source_ref` is blank, the importer creates an internal row reference such as `batch:<filename>#row=<n>`. This is provenance for the intake event, not independent evidence of the underlying condition.

`owner_confirmation` defaults to `not-contacted`. A Center-supplied spreadsheet therefore does **not** automatically become owner-confirmed merely because an institutional office supplied it. Use `confirmed` or `reframed` only when a corresponding confirmation reference and timestamp exist.

## Batch command

```bash
problem-intake batch-csv needs.csv \
  --steward pilot-curator \
  --out-dir /tmp/problem-commons-intake
```

For every valid row the command writes:

- a restricted candidate Problem Packet;
- a minimum-necessary owner-review pack;
- one batch manifest describing valid/invalid rows and warnings.

Rows are processed independently. Invalid rows remain visible in the manifest rather than being silently dropped.

## Deliberately absent behavior

The batch importer does not:

- publish a Problem;
- treat a Center record as problem-owner approval;
- open solver work;
- invent candidate Project Briefs when none were supplied/curated;
- infer funding, compensation or volunteer availability;
- grant data access or intervention authority.

The intended first-cycle flow is:

`existing YZU sheet/database → CSV export → restricted candidates → owner review → curation → solver-ready work`

This is specifically designed to test whether Problem Commons improves YZU's existing field-matching process without asking the institution to change its upstream system first.
