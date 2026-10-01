import streamlit as st
import pandas as pd

from core.state import init_state, ensure_lines_registered
from core.importers import read_any, column_mapper, apply_mapping, wide_skill_matrix_to_long
from core.matching import get_or_create_skill_group

st.set_page_config(page_title="Data Import", page_icon="📥", layout="wide")
init_state()
st.title("📥 Data Import")

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

            if st.button("Confirm & Load Operation Breakdown", type="primary", disabled=not ob_name):
                mapped = apply_mapping(raw, mapping)
                mapped["sam"] = pd.to_numeric(mapped["sam"], errors="coerce").astype(float)
                bad_sam = mapped["sam"].isna().sum()
                mapped = mapped.dropna(subset=["sam"])

                rows = []
                new_count = 0
                progress = st.progress(0.0, text="Matching operations to skill groups...")
                total = len(mapped)
                for i, (_, r) in enumerate(mapped.iterrows()):
                    sg, created, new_row, score = get_or_create_skill_group(
                        r["operation"], r["machine_type"], r["sam"], st.session_state["extra_taxonomy"]
                    )
                    if created:
                        st.session_state["extra_taxonomy"].append(new_row)
                        new_count += 1
                    rows.append(
                        {
                            "operation": r["operation"],
                            "machine_type": r["machine_type"],
                            "sam": r["sam"],
                            "skill_group": sg,
                        }
                    )
                    progress.progress((i + 1) / total if total else 1.0, text=f"Matching operations... {i+1}/{total}")
                progress.empty()

                st.session_state["obs"][ob_name] = {
                    "rows": rows,
                    "shift_time": shift_time,
                    "target": target,
                    "plan_efficiency": plan_efficiency,
                }
                msg = f"Loaded '{ob_name}' — {len(rows)} operations."
                if bad_sam:
                    msg += f" {bad_sam} row(s) had a non-numeric SAM and were skipped — worth checking the source file."
                if new_count:
                    msg += f" {new_count} operation(s) didn't match the reference taxonomy, so new Skill Group IDs were created for them."
                st.success(msg)

    if st.session_state["obs"]:
        st.divider()
        st.caption("Saved Operation Breakdowns:")
        for name, ob in st.session_state["obs"].items():
            st.write(f"**{name}** — {len(ob['rows'])} operations, shift={ob['shift_time']}, target={ob['target']}, eff={ob['plan_efficiency']}")

# ---------------- Employees ----------------
with tab_emp:
    st.subheader("Employee List")
    st.caption("Active employees, each with the Line they belong to.")
    file = st.file_uploader("Upload Employee List (.xlsx or .csv)", type=["xlsx", "csv"], key="emp_upload")
    if file:
        raw = read_any(file)
        st.write("Preview:")
        st.dataframe(raw.head(10), width='stretch')

        mapping = column_mapper(
            raw,
            required_fields={
                "employee_id": "Employee No.",
                "employee_name": "Employee Name",
                "line": "Line",
            },
            key_prefix="emp",
        )
        if st.button("Confirm & Load Employees", type="primary"):
            mapped = apply_mapping(raw, mapping)
            mapped["employee_id"] = mapped["employee_id"].astype(str)
            mapped["line"] = mapped["line"].astype(str)
            ensure_lines_registered(mapped["line"].unique().tolist())
            st.session_state["employees_df"] = mapped
            st.success(f"Loaded {len(mapped)} employees across {mapped['line'].nunique()} line(s).")

    current = st.session_state.get("employees_df")
    if current is not None:
        st.divider()
        st.caption("Currently loaded:")
        st.dataframe(current, width='stretch')

# ---------------- Skill Matrix ----------------
with tab_skill:
    st.subheader("Skill Matrix")
    st.caption(
        "Wide format expected: one row per employee, one column per operation/skill group, "
        "any non-empty cell means that employee is qualified. Columns should line up with the "
        "Skill Group IDs used in your Operation Breakdown(s) for best results."
    )
    file = st.file_uploader("Upload Skill Matrix (.xlsx or .csv)", type=["xlsx", "csv"], key="skill_upload")
    if file:
        raw = read_any(file)
        st.write("Preview:")
        st.dataframe(raw.head(10), width='stretch')

        emp_col = st.selectbox("Which column identifies the employee?", options=list(raw.columns), key="skill_emp_col")
        if st.button("Confirm & Load Skill Matrix", type="primary"):
            long_df = wide_skill_matrix_to_long(raw, emp_col)
            long_df["employee"] = long_df["employee"].astype(str)
            st.session_state["skill_matrix_long"] = long_df
            st.success(f"Loaded {len(long_df)} employee-skill pairs from {raw[emp_col].nunique()} employees.")

    current = st.session_state.get("skill_matrix_long")
    if current is not None:
        st.divider()
        st.caption("Currently loaded (long format):")
        st.dataframe(current, width='stretch')
