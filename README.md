# Line Balancing

A factory-agnostic line balancing tool with **real, permanent persistence**
(Postgres) and a **Roles layer** that lets you teach it general rules once
(e.g. "a Presser is qualified for every press-family operation") instead of
needing every individual operation spelled out for every employee.

## Setup — database (do this first)

1. Create a free [Neon](https://neon.tech) Postgres project (same service
   the loss-time tracker uses).
2. Copy its connection string (starts with `postgresql://`).
3. On Streamlit Community Cloud: app → Settings → Secrets, add:
   ```
   DATABASE_URL = "postgresql://your-connection-string-here"
   ```
4. For local development, set it as an environment variable instead:
   ```
   export DATABASE_URL="postgresql://your-connection-string-here"
   ```

The app creates all its tables automatically on first run — no manual SQL
needed. If `DATABASE_URL` isn't set, the app shows a clear error on the
home page explaining exactly what to do, instead of failing silently.

## Structure

```
app.py                         Home / dashboard
pages/
  1_Lines.py                   Add/manage line names
  2_Data_Import.py             Upload OB (Excel/CSV/PDF), Employees, Skill Matrix (wide or long, + Machine Type)
  3_Operation_Breakdown.py     Module 1: pure formula table, no merging
  4_Employees.py               Browse/search employee list
  5_Skill_Matrix.py            Coverage per employee / per skill group
  6_Layout_Balancing.py        Module 2 (single line) + Module 3 (multiple lines)
  7_Absentee_Balancing.py      Module 4: multi-line, present-employees-only
  8_Roles.py                   Define general-purpose roles and assign them to employees
core/
  db.py                        Postgres persistence layer — ALL durable state lives here now
  formulas.py                  OB formula engine
  matching.py                  Fuzzy-matches operations/skills against the taxonomy; auto-creates new
                                Skill Group IDs (SG-AUTO-####) for anything unmatched
  pooling.py                   The 50%-under-utilization / overflow merge (pooling) logic
  assignment.py                Turns pooling bins + standalone ops into named, line-aware employee assignments
  orchestrate.py               Ties formulas+pooling+assignment into one balancing run
  render.py                    Builds the color-coded results table + manual-assignment UI
  importers.py                 Generic file reading (xlsx/csv/pdf) + column-mapping UI + skill-matrix format handling
  state.py                     Thin, DB-backed data-access layer pages call into
data/
  skill_taxonomy.csv           The reviewed reference taxonomy (~11,312 rows) — static, bundled, read-only
```

## What's now permanently saved (this is the whole point of this version)

Lines, Operation Breakdowns, Employees, Skill Matrix entries, auto-created
Skill Groups, Roles, and employee-role assignments all live in Postgres.
Close the browser, redeploy the app, come back next week — it's all still
there. Only the in-progress balancing result on screen and manual-override
selections mid-form are session-only (regenerable by clicking Run again).

## The Roles layer — what it actually does

A Role (e.g. "Presser") is a name plus a list of Machine Types it covers.
An employee holding that role is automatically qualified for **every**
operation on any of those machine types in whatever OB is being balanced —
even an operation the taxonomy has never seen before, and even if that
employee has zero entries in the skill matrix. This is how a fact like
"a presser can do any press operation" gets taught **once**, on the Roles
page, and applies forever after — instead of living only in a conversation
or being baked into specific Skill Group IDs by hand.

Verified behavior: an employee tagged only with the Presser role (no
explicit skill-matrix entry at all) correctly gets qualified for both an
Auto Press and a Steam Press operation in a test OB, and correctly does
NOT get qualified for an unrelated Overlock operation — pure machine-family
matching, nothing guessed.

## Skill Matrix: Machine Type support

Long-format skill files can now optionally include a Machine Type column.
When present, it's used for matching exactly like the OB's own machine
type — this closes a real consistency gap where skill-matrix text (no
machine context) could resolve to a different Skill Group ID than the same
operation in an OB (confirmed on real data: "DORI ATTACH" without machine
context matched a different ID than "DORI ATTACH" with machine=HELPER).
Skill matrix entries are always re-resolved against the active OB's own
operations first at balancing time regardless, as a second layer of
protection against this class of bug.

## The merge/pooling rule (unchanged, still verified against real worked examples)

An operation with Head Allocated = 1 and Work Minutes ≤ 50% of shift time
leaves its person under-utilized. An operation whose Work Minutes exceed
what its allocated heads cover creates an "overflow" chunk of leftover
work. Both are pooled into one person's day, preferring same Skill Group,
falling back to same Machine Type, never merged if neither matches. In
multi-line mode, the same operation (same Skill Group) with spare capacity
in a different line takes priority over same-line pooling.

## Manual assignment for unstaffed operations

Any row the automatic engine can't staff gets a dropdown suggestion (same-
line employees listed first) so you can assign someone by hand. A merged/
cross-line bin gets ONE assignment choice applied to all its rows, not a
separate dropdown per row.

## Testing performed

Every piece of the database layer (Lines, OBs, Employees, Skill Matrix,
Roles, Taxonomy Extra) was tested against a real local Postgres instance,
not mocked. Cross-session persistence was explicitly verified: data written
in one `AppTest` session (simulating one browser session) is visible in a
completely fresh, separate session with no shared Python state — the same
guarantee a real deployment needs. The Roles feature was verified against
a realistic scenario (an employee with a role but zero explicit skills
correctly getting staffed on exactly the machine types their role covers,
and correctly NOT on unrelated ones) through actual button clicks on the
real Layout Balancing page, not just direct function calls.

## What's still simplified (said plainly, not hidden)

- No login/multi-factory separation yet — any user of the deployed app
  sees and edits the same shared data. Fine for one team; would need an
  auth layer for multiple independent factories sharing one deployment.
- Pooling is a greedy heuristic (largest chunks first, first compatible
  bin), not a guaranteed-optimal bin-pack.
- Tie-breaking between equally-qualified candidates is alphabetical — no
  seniority/fairness/workload-history weighting yet.
- Shift Time/Target/Plan Efficiency are one shared set per multi-line
  balancing run — doesn't yet support different targets per line in a
  single run.
- Roles currently grant qualification by machine type only — there's no
  per-role exclusion list yet (e.g. "Presser, but not Bottle Press") if a
  role needs a carve-out.

## Running locally

```
pip install -r requirements.txt
export DATABASE_URL="postgresql://..."
streamlit run app.py
```

## Deploying

Push to a GitHub repo, connect it on Streamlit Community Cloud, set
DATABASE_URL in Secrets — same workflow as the other internal tools.
