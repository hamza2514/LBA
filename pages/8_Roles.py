import streamlit as st

from core.state import init_state, list_roles, save_role, delete_role, employee_roles_dict, set_employee_roles, list_obs, get_ob
from core.matching import load_taxonomy
import core.db as db

st.set_page_config(page_title="Roles", page_icon="🎓", layout="wide")
init_state()
st.title("🎓 Roles")
st.caption(
    "This is how you teach the tool a general rule ONCE instead of listing every individual operation. "
    "Example: a 'Presser' is qualified for every operation on any press-family machine — define that "
    "mapping here, and any employee tagged with the Presser role gets it automatically, in every OB, "
    "even operations the taxonomy has never seen before."
)


def known_machine_types() -> list[str]:
    types = set()
    for row in load_taxonomy():
        if row.machine_type:
            types.add(row.machine_type)
    for ob_name in list_obs():
        ob = get_ob(ob_name)
        for r in ob["rows"]:
            if r.get("machine_type"):
                types.add(r["machine_type"])
    return sorted(types)


tab_define, tab_assign = st.tabs(["Define Roles", "Assign Roles to Employees"])

with tab_define:
    st.subheader("Define a Role")
    all_machine_types = known_machine_types()
    if not all_machine_types:
        st.info("No machine types seen yet — upload an Operation Breakdown first so there's something to pick from.")
    else:
        with st.form("add_role_form"):
            role_name = st.text_input("Role name", placeholder="e.g. Presser, Overlock Operator, Helper")
            machine_types = st.multiselect("Machine types this role covers — ANY operation on these machines qualifies", options=all_machine_types)
            submitted = st.form_submit_button("Save Role", type="primary")
            if submitted and role_name and machine_types:
                save_role(role_name.strip(), machine_types)
                st.success(f"Saved role '{role_name.strip()}' covering {len(machine_types)} machine type(s).")

    st.divider()
    roles = list_roles()
    if roles:
        st.subheader(f"{len(roles)} role(s) defined")
        for name, mts in roles.items():
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{name}** — {', '.join(mts)}")
            if c2.button("Delete", key=f"delete_role_{name}"):
                delete_role(name)
                st.rerun()
    else:
        st.info("No roles defined yet.")

with tab_assign:
    employees_df = db.list_employees()
    roles = list_roles()
    if employees_df is None:
        st.warning("No employees loaded yet. Go to Data Import first.")
    elif not roles:
        st.warning("No roles defined yet. Define one in the 'Define Roles' tab first.")
    else:
        emp_roles = employee_roles_dict()
        emp_options = [f"{r['employee_id']} - {r['employee_name']}" for _, r in employees_df.iterrows()]
        chosen = st.selectbox("Employee", options=emp_options)
        emp_id = chosen.split(" - ")[0]

        current_roles = emp_roles.get(emp_id, [])
        new_roles = st.multiselect("Roles this employee holds", options=list(roles.keys()), default=current_roles)

        if st.button("Save", type="primary"):
            set_employee_roles(emp_id, new_roles)
            st.success(f"Updated roles for {chosen}.")

        st.divider()
        st.caption("Current role assignments:")
        if emp_roles:
            rows = [{"Employee": e, "Roles": ", ".join(r)} for e, r in emp_roles.items()]
            st.dataframe(rows, width='stretch', hide_index=True)
        else:
            st.info("No employees have roles assigned yet.")
