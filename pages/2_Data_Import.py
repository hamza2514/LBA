import streamlit as st
import pandas as pd

from core.state import init_state, ensure_lines_registered, extra_taxonomy_list, record_taxonomy_extra_bulk, save_ob, list_obs, get_ob
from core.importers import read_any, column_mapper, apply_mapping, wide_skill_matrix_to_long, long_skill_file_to_pairs
from core.matching import get_or_create_skill_group
import core.db as db

st.set_page_config(page_title="Data Import", page_icon="📥", layout="wide")
init_state()
st.title("📥 Data Import")
st.caption("Everything you load here is saved permanently — it will still be here next time you open the app.")

tab_ob, tab_emp, tab_skill = st.tabs(["Operation Breakdown", "Employees", "Skill Matrix"])

# ---------------- Operation Breakdown ----------------
with tab_ob:
    st.subheader("Operation Breakdown")
    st.caption(
        "Upload Operation, Machine Type, and SAM/SMV. Skill Group, Shift Target, Manpower, and "
        "Head Allocated are derived automatically. Line is NOT set here — you'll pick which line(s) "
        "to run this OB on when you go to Layout Balancing or Absentee Balancing."
    )
    file = st.file_uploader("Upload Operation Breakdown (.xlsx, .csv, or .pdf)", type=["xlsx", "csv", "pdf"], key="ob_upload")

    if file:
        try:
            raw = read_any(file)
        except ValueError as e:
            st.error(str(e))
            raw = None

        if raw is not None:
            st.write("Preview:")
            st.dataframe(raw.head(10), width='stretch')

            mapping = column_mapper(
                raw,
                required_fields={
                    "operation": "Operation Description",
                    "machine_type": "Machine Type",
                    "sam": "SAM / SMV",
                },
                key_prefix="ob",
            )

            st.divider()
            st.caption("These three are used to calculate the OB table. You'll be asked again (possibly with different values) during Layout Balancing.")
            c1, c2, c3 = st.columns(3)
            with c1:
                shift_time = st.number_input("Shift Time (minutes)", min_value=1.0, value=480.0, key="ob_shift_time")
            with c2:
                target = st.number_input("Target (units/shift)", min_value=1.0, value=1200.0, key="ob_target")
            with c3:
                plan_efficiency = st.number_input("Plan Efficiency", min_value=0.01, max_value=1.0, value=0.85, key="ob_eff")

            ob_name = st.text_input("Name this Operation Breakdown (so you can pick it later)", placeholder="e.g. Style ABC123 - Basic 5-Pocket")

            if st.button("Confirm & Save Operation Breakdown", type="primary", disabled=not ob_name):
                mapped = apply_mapping(raw, mapping)
                mapped["sam"] = pd.to_numeric(mapped["sam"], errors="coerce").astype(float)
                bad_sam = mapped["sam"].isna().sum()
                mapped = mapped.dropna(subset=["sam"])
                zero_sam = (mapped["sam"] <= 0).sum()
                mapped = mapped[mapped["sam"] > 0]
                bad_sam += zero_sam

                extra_taxonomy = extra_taxonomy_list()
                rows = []
                newly_created = []  # batched to ONE db write at the end, not one per new group
                progress = st.progress(0.0, text="Matching operations to skill groups...")
                total = len(mapped)
                for i, (_, r) in enumerate(mapped.iterrows()):
                    sg, created, new_row, score = get_or_create_skill_group(
                        r["operation"], r["machine_type"], r["sam"], extra_taxonomy
                    )
                    if created:
                        extra_taxonomy.append(new_row)
                        newly_created.append({
                            "skill_group_id": new_row["skill_group_id"],
                            "operation_description": new_row["operation_description"],
                            "machine_type": new_row["machine_type"],
                            "sam": new_row["sam"],
                        })
                    rows.append({"operation": r["operation"], "machine_type": r["machine_type"], "sam": r["sam"], "skill_group": sg})
                    progress.progress((i + 1) / total if total else 1.0, text=f"Matching operations... {i+1}/{total}")
                progress.empty()

                record_taxonomy_extra_bulk(newly_created)
                save_ob(ob_name, shift_time, target, plan_efficiency, rows)
                msg = f"Saved '{ob_name}' — {len(rows)} operations."
                if bad_sam:
                    msg += f" {bad_sam} row(s) had a non-numeric or zero SAM and were skipped."
                if newly_created:
                    msg += f" {len(newly_created)} operation(s) didn't match the reference taxonomy, so new Skill Group IDs were created for them."
                st.success(msg)

    saved_obs = list_obs()
    if saved_obs:
        st.divider()
        st.caption("Saved Operation Breakdowns:")
        for name in saved_obs:
            ob = get_ob(name)
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{name}** — {len(ob['rows'])} operations, shift={ob['shift_time']}, target={ob['target']}, eff={ob['plan_efficiency']}")
            if c2.button("Delete", key=f"delete_ob_{name}"):
                db.delete_ob(name)
                st.rerun()

# ---------------- Employees ----------------
with tab_emp:
    st.subheader("Employee List")
    st.caption("Active employees, each with the Line they belong to. New uploads ADD/UPDATE — existing employee codes get refreshed, not duplicated.")
    file = st.file_uploader("Upload Employee List (.xlsx or .csv)", type=["xlsx", "csv"], key="emp_upload")
    if file:
        raw = read_any(file)
        st.write("Preview:")
        st.dataframe(raw.head(10), width='stretch')

        mapping = column_mapper(
            raw,
            required_fields={"employee_id": "Employee No.", "employee_name": "Employee Name", "line": "Line"},
            key_prefix="emp",
        )
        if st.button("Confirm & Save Employees", type="primary"):
            mapped = apply_mapping(raw, mapping)
            mapped["employee_id"] = mapped["employee_id"].astype(str)
            mapped["line"] = mapped["line"].astype(str)
            ensure_lines_registered(mapped["line"].unique().tolist())
            dup_count = db.upsert_employees(mapped)
            msg = f"Saved {len(mapped) - dup_count} employees across {mapped['line'].nunique()} line(s)."
            if dup_count:
                msg += f" {dup_count} duplicate employee ID row(s) in this file were collapsed (kept the last one)."
            st.success(msg)

    current = db.list_employees()
    if current is not None:
        st.divider()
        st.caption(f"Currently saved: {len(current)} employees.")
        st.dataframe(current, width='stretch')

# ---------------- Skill Matrix ----------------
with tab_skill:
    st.subheader("Skill Matrix")
    st.caption(
        "Two formats supported. Operation/skill names are matched against the same reference "
        "taxonomy as your Operation Breakdown — so skill names don't need to match OB wording exactly. "
        "If you can provide Machine Type alongside each skill, matching is far more accurate."
    )
    file = st.file_uploader("Upload Skill Matrix (.xlsx or .csv)", type=["xlsx", "csv"], key="skill_upload")
    if file:
        raw = read_any(file)
        st.write("Preview:")
        st.dataframe(raw.head(10), width='stretch')

        file_format = st.radio(
            "Which format is this file?",
            options=["wide", "long"],
            format_func=lambda f: {
                "wide": "Wide — one row per employee, one column per operation (tick marks / ratings)",
                "long": "Long — one row per employee-skill pair (employee code repeats for each skill)",
            }[f],
            key="skill_format",
        )

        pairs = None
        if file_format == "wide":
            c1, c2 = st.columns(2)
            with c1:
                emp_col = st.selectbox("Which column is the Employee ID?", options=list(raw.columns), key="skill_emp_col")
            with c2:
                other_cols = [c for c in raw.columns if c != emp_col]
                non_skill_hints = ("name", "count", "total", "department", "designation", "line", "zone")
                exclude_cols = st.multiselect(
                    "Any other columns to EXCLUDE (e.g. Employee Name, a trailing count/total column) — everything else is treated as a skill/operation column",
                    options=other_cols,
                    default=[c for c in other_cols if any(h in str(c).lower() for h in non_skill_hints)],
                    key="skill_exclude_cols",
                )
            if st.button("Preview conversion", key="skill_wide_preview"):
                pairs = wide_skill_matrix_to_long(raw, emp_col, exclude_cols)
                pairs["machine_type"] = None
                st.session_state["skill_pairs_preview"] = pairs
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                emp_col = st.selectbox("Which column is the Employee ID?", options=list(raw.columns), key="skill_emp_col_long")
            with c2:
                skill_col = st.selectbox("Which column is the Skill/Operation name?", options=[c for c in raw.columns if c != emp_col], key="skill_skill_col_long")
            with c3:
                mt_options = ["(none)"] + [c for c in raw.columns if c not in (emp_col, skill_col)]
                mt_col = st.selectbox("Which column is Machine Type? (optional, but improves matching a lot)", options=mt_options, key="skill_mt_col_long")
            if st.button("Preview conversion", key="skill_long_preview"):
                pairs = long_skill_file_to_pairs(raw, emp_col, skill_col)
                if mt_col != "(none)":
                    pairs["machine_type"] = raw.loc[pairs.index, mt_col] if mt_col in raw.columns else None
                else:
                    pairs["machine_type"] = None
                st.session_state["skill_pairs_preview"] = pairs

        pairs = st.session_state.get("skill_pairs_preview")
        if pairs is not None:
            st.caption(f"{len(pairs)} employee-skill pairs found, {pairs['skill_text'].nunique()} distinct skill names. Matching these against the taxonomy:")
            if st.button("Confirm & Save Skill Matrix", type="primary"):
                extra_taxonomy = extra_taxonomy_list()
                cache: dict = {}
                newly_created = []  # batched to ONE db write at the end
                resolved_sg = []
                progress = st.progress(0.0, text="Matching skill names to skill groups...")
                total = len(pairs)
                for i, (_, r) in enumerate(pairs.iterrows()):
                    text = r["skill_text"]
                    mt = r.get("machine_type")
                    cache_key = (text, mt)
                    if cache_key not in cache:
                        sg, created, new_row, score = get_or_create_skill_group(text, mt, None, extra_taxonomy)
                        if created:
                            extra_taxonomy.append(new_row)
                            newly_created.append({
                                "skill_group_id": new_row["skill_group_id"],
                                "operation_description": new_row["operation_description"],
                                "machine_type": new_row["machine_type"],
                                "sam": new_row["sam"],
                            })
                        cache[cache_key] = sg
                    resolved_sg.append(cache[cache_key])
                    if i % 25 == 0 or i == total - 1:
                        progress.progress((i + 1) / total if total else 1.0, text=f"Matching... {i+1}/{total}")
                progress.empty()

                record_taxonomy_extra_bulk(newly_created)
                new_count = len(newly_created)

                pairs = pairs.copy()
                pairs["skill_group"] = resolved_sg
                pairs["employee"] = pairs["employee"].astype(str)
                with st.spinner(f"Saving {len(pairs)} pairs to the database..."):
                    dup_count = db.add_skill_pairs(pairs)

                msg = (
                    f"Saved {len(pairs) - dup_count} employee-skill pairs from this file "
                    f"({pairs['employee'].nunique()} employees, {pairs['skill_text'].nunique()} distinct skill names). "
                    "Merged with whatever was already saved — new uploads add, they don't replace."
                )
                if dup_count:
                    msg += f" {dup_count} duplicate (employee, skill) row(s) in this file were collapsed (kept the last one) — worth checking your source file for repeated entries."
                if new_count:
                    msg += f" {new_count} skill name(s) didn't match the reference taxonomy, so new Skill Group IDs were created for them."
                st.success(msg)
                st.session_state["skill_pairs_preview"] = None

    current = db.list_skill_pairs()
    if current is not None:
        st.divider()
        c1, c2 = st.columns([5, 1])
        with c1:
            st.caption(f"Currently saved — {len(current)} pairs, {current['employee'].nunique()} employees. New uploads ADD to this; they don't replace it.")
        with c2:
            if st.button("Clear all", key="clear_skill_matrix"):
                db.clear_skill_matrix()
                st.rerun()
        st.dataframe(current, width='stretch')
