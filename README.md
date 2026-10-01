# Line Balancing

Upload an Operation Breakdown, an Employee list (with Line), and a Skill
Matrix — the app matches operations to a shared skill-group taxonomy,
calculates manpower using the confirmed formula set, pools under-utilized
and overflow work into merged assignments where the rules allow, and
assigns present/active operators to operations (line-aware).

## Structure

```
app.py                         Home / dashboard
pages/
  1_Lines.py                   Add/manage line names
  2_Data_Import.py             Upload OB (with Line), Employees (with Line), Skill Matrix
  3_Operation_Breakdown.py     Module 1: formula table only, no merging
  4_Employees.py               Browse/search the loaded employee list
  5_Skill_Matrix.py            Coverage per employee and per skill group
  6_Layout_Balancing.py        Module 2 (single line) + Module 3 (multiple lines)
  7_Absentee_Balancing.py      Module 4: multi-line, present employees only
core/
  formulas.py                  The confirmed OB formula set (Shift Target, Manpower, Head Allocated, Work Minutes)
  matching.py                  Fuzzy-matches operations against data/skill_taxonomy.csv; auto-creates new
                                Skill Group IDs (SG-AUTO-####) for anything that doesn't match, session-wide
  pooling.py                   The 50%-under-utilized / overflow merge logic, same-line and cross-line
  assignment.py                Turns pooling bins into actual named, line-aware employee assignments
  orchestrate.py                Ties the above into one balancing run
  render.py                    Color-codes merged operations for display
  importers.py                 Generic file reading + column-mapping UI
  state.py                     Central session-state shape
data/
  skill_taxonomy.csv           Reference taxonomy built from real operation databases across two companies
```

## The formulas (confirmed against formula_references.xlsx)

Given Shift Time, Target, and Plan Efficiency:

| Column | Formula |
|---|---|
| Shift Target @100% | Shift Time ÷ SAM |
| Shift Target @Plan Eff | Shift Target@100% × Plan Efficiency |
| Manpower @100% | Target ÷ Shift Target@100% |
| Manpower @Plan Eff | Target ÷ Shift Target@Plan Eff |
| Head Allocated | 1 if Manpower@PlanEff < 1; else round up if remainder > 0.3, else round down |
| Work Minutes (internal only) | Target × SAM |

## The merge/pooling rule

An operation with Head Allocated = 1 and Work Minutes ≤ 50% of shift time
leaves its person under-utilized. An operation whose Work Minutes exceed
what its allocated heads can cover creates an overflow chunk. Both are
pooled into one person's day (target ~85% of shift time, hard cap = shift
time), preferring same Skill Group, falling back to same Machine Type,
never merged if neither matches. In multi-line mode, the same operation
(same Skill Group) with spare capacity in a *different* line takes priority
over same-line pooling — one person works it across both lines.

## Testing performed

All core formulas were checked against the exact worked examples in
formula_references.xlsx and the chat (the 220/200 and 220/600 pooling
examples reproduce exactly: 420 and 340 minutes). All 8 pages were run
through Streamlit's own `AppTest` framework (not just `py_compile`) —
Operation Breakdown, Layout Balancing (single- and multi-line), and
Absentee Balancing were driven through real button clicks with sample data
and produced correct, exception-free results, including cross-line pooling
and present-employee-only restriction.

## What's still simplified (said plainly, not hidden)

- **No persistence** — everything lives in `st.session_state` for the
  browser session. OBs, Lines, auto-created skill groups all reset on
  reload. The loss-time tracker's Postgres pattern is the natural next step.
- **No login/multi-factory separation** — single-session prototype.
- **Pooling is a greedy heuristic, not a guaranteed-optimal bin-pack** — it
  processes the largest chunks first and takes the first compatible bin it
  finds. For most real OBs this will be good, not necessarily perfect.
- **Tie-breaking between equally-qualified candidates is alphabetical** —
  no seniority, fairness-rotation, or workload-history weighting yet.
- **Auto-created skill groups (`SG-AUTO-####`) aren't fed back into
  `data/skill_taxonomy.csv`** — they live only in the session. Worth a
  periodic manual review-and-merge into the real taxonomy file, the same
  way the last several rounds of chat did for the two real companies.
- **Shift Time / Target / Plan Efficiency are one shared set per balancing
  run** — multi-line mode doesn't yet support different targets per line in
  a single run; re-run per line-group if they genuinely differ.

## Running locally / deploying

```
pip install -r requirements.txt
streamlit run app.py
```

Push to a GitHub repo and connect on Streamlit Community Cloud — same
workflow as the other apps.
