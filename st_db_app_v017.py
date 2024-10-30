import sqlite3
import streamlit as st

# Admin credentials
admin_username = "admin957316&7k/."
admin_password = "5tgdcjyu.w4&GF%$"

# Initialize session state variables
if 'login_status' not in st.session_state:
    st.session_state.login_status = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'selected_criteria' not in st.session_state:
    st.session_state.selected_criteria = None
if 'selected_method' not in st.session_state:
    st.session_state.selected_method = None
if 'show_new_record_form' not in st.session_state:
    st.session_state.show_new_record_form = False

# Database connection
db_file = 'my_database.db'
conn = sqlite3.connect(db_file)

# Query functions
def query_criteria_counts(conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT criteria, COUNT(paragraph) as count
        FROM energy_data
        WHERE paragraph IS NOT NULL AND paragraph != '' AND paragraph != '0' AND paragraph != '0.0'
        GROUP BY criteria
    ''')
    return cursor.fetchall()

def query_energy_method_counts(conn, selected_criteria):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT energy_method, COUNT(paragraph) as count
        FROM energy_data
        WHERE criteria = ? AND (paragraph IS NOT NULL AND paragraph != '' AND paragraph != '0' AND paragraph != '0.0')
        GROUP BY energy_method
    ''', (selected_criteria,))
    return cursor.fetchall()

def query_paragraphs(conn, criteria, energy_method, direction):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, paragraph FROM energy_data
        WHERE criteria = ? AND energy_method = ? AND direction = ?
    ''', (criteria, energy_method, direction))
    paragraphs = cursor.fetchall()
    return [(id, para) for id, para in paragraphs if para not in ['0', '0.0', '', None]]

def admin_actions(conn, paragraph_id, new_text=None, delete=False):
    cursor = conn.cursor()
    if delete:
        cursor.execute("DELETE FROM energy_data WHERE id = ?", (paragraph_id,))
        conn.commit()
        st.success(f"Record {paragraph_id} deleted.")
    elif new_text:
        cursor.execute("UPDATE energy_data SET paragraph = ? WHERE id = ?", (new_text, paragraph_id))
        conn.commit()
        st.success(f"Record {paragraph_id} updated.")


# Login and Logout functions
def login(username, password):
    if username == admin_username and password == admin_password:
        st.session_state.logged_in = True
        st.session_state.current_user = username
        st.session_state.login_status = "Logged in successfully!"
        st.rerun()  # Trigger a rerun on successful login
    else:
        st.session_state.login_status = "Incorrect username or password"

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]  # Clear all session states on logout
    st.rerun()

# Placeholder for dynamic tabs
placeholder = st.empty()

if st.session_state.logged_in:
    tab1, tab2 = placeholder.tabs(["Search", f"Logged in as {st.session_state.current_user}"])
else:
    tab1, tab2 = placeholder.tabs(["Search", "Login"])

# Login Tab
with tab2:
    if st.session_state.logged_in:
        if st.button("Logout"):
            logout()
    else:
        st.header("Login")
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        if st.button("Submit"):
            login(username, password)

# Search Tab with Criteria Dropdown and Simplified Direction Selection
with tab1:
    st.title("Determinants of Macro Scale Building Energy Consumption")


    st.write(
    """This tool, developed through a systematic literature review, provides insights into how various determinants influence macro-scale building energy consumption, with references covering studies at neighborhood, urban, state, regional, national, and international levels."""
    )
    # Criteria Dropdown with Counts and Placeholder
    criteria_counts = query_criteria_counts(conn)
    criteria_list = ["Select a determinant"] + [f"{row[0]} ({row[1]})" for row in criteria_counts]

    selected_criteria_with_count = st.selectbox(
        "Determinant",
        criteria_list,
        index=0 if st.session_state.selected_criteria is None else criteria_list.index(f"{st.session_state.selected_criteria} ({[count for crit, count in criteria_counts if crit == st.session_state.selected_criteria][0]})"),
        format_func=lambda x: x if x == "Select a determinant" else x
    )

    if selected_criteria_with_count != "Select a determinant":
        new_criteria = selected_criteria_with_count.split(" (")[0]
        if new_criteria != st.session_state.selected_criteria:
            st.session_state.selected_criteria = new_criteria
            st.session_state.selected_method = None  # Reset method on new criteria selection
            st.rerun()  # Trigger rerun to apply selection changes

        # Energy Method Dropdown with Counts and Placeholder
        energy_method_counts = query_energy_method_counts(conn, st.session_state.selected_criteria)
        method_list = ["Select an output"] + [f"{row[0]} ({row[1]})" for row in energy_method_counts]

        selected_method_with_count = st.selectbox(
            "Energy Output(s)",
            method_list,
            index=0 if st.session_state.selected_method is None else method_list.index(f"{st.session_state.selected_method} ({[count for meth, count in energy_method_counts if meth == st.session_state.selected_method][0]})"),
            format_func=lambda x: x if x == "Select an output" else x
        )

        if selected_method_with_count != "Select an output":
            st.session_state.selected_method = selected_method_with_count.split(" (")[0]

            # Directly use radio button without session state
            selected_direction = st.radio(
                "Relationship Direction",
                ["Increase", "Decrease"],
                index=0 if "Increase" else 1
            )

            # Query paragraphs based on the selected filters
            paragraphs = query_paragraphs(conn, st.session_state.selected_criteria, st.session_state.selected_method, selected_direction)
            
            if paragraphs:
                st.markdown(f"<p><b>An increase (or presence) in {st.session_state.selected_criteria} leads to <i>{'higher' if selected_direction == 'Increase' else 'lower'}</i> {st.session_state.selected_method}.</b></p>", unsafe_allow_html=True)
                for para_id, para_text in paragraphs:
                    if st.session_state.logged_in:
                        new_text = st.text_area(f"Edit text for record {para_id}", value=para_text, key=f"edit_{para_id}")
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            if st.button("Save changes", key=f"save_btn_{para_id}"):
                                admin_actions(conn, para_id, new_text=new_text)
                                st.rerun()
                        with col2:
                            if st.session_state.get(f"confirm_delete_{para_id}", False):
                                st.warning(f"Are you sure you want to delete record {para_id}?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("Yes", key=f"confirm_yes_{para_id}"):
                                        admin_actions(conn, para_id, delete=True)
                                        st.session_state[f"confirm_delete_{para_id}"] = False
                                        st.rerun()
                                with col_no:
                                    if st.button("Cancel", key=f"confirm_no_{para_id}"):
                                        st.session_state[f"confirm_delete_{para_id}"] = False
                                        st.rerun()
                            else:
                                if st.button("Delete", key=f"delete_btn_{para_id}"):
                                    st.session_state[f"confirm_delete_{para_id}"] = True
                                    st.rerun()
                    else:
                        st.write(para_text)
            else:
                st.warning(f"No references have been reported for an increase (or presence) in {st.session_state.selected_criteria} leading to {'higher' if selected_direction == 'Increase' else 'lower'} {st.session_state.selected_method}.")

            # Add a new record if logged in
            if st.session_state.logged_in and st.button("Add New Record", key="add_new_record"):
                st.session_state.show_new_record_form = True
            if st.session_state.show_new_record_form:
                new_paragraph = st.text_area(f"Add new record for {st.session_state.selected_criteria} and {st.session_state.selected_method} ({selected_direction})", key="new_paragraph")
                if st.button("Save", key="save_new_record"):
                    if new_paragraph.strip():
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO energy_data (criteria, energy_method, direction, paragraph)
                            VALUES (?, ?, ?, ?)
                        ''', (st.session_state.selected_criteria, st.session_state.selected_method, selected_direction, new_paragraph))
                        conn.commit()
                        st.success("New record added successfully.")
                        st.session_state.show_new_record_form = False
                        st.rerun()
                    else:
                        st.warning("Record cannot be empty.")

conn.close()

# Footer with fixed positioning
footer_html = """
    <style>
    .custom_footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #010101;
        color: grey;
        text-align: center;
        padding: 5px;
    }
    </style>
    <div class="custom_footer">
        <p style='font-size:12px;'>If your study, or a study you are aware of, suggests any of these relationships are currently missing from the database, please email the study to ssk5573@psu.edu.<br> Your contribution will help further develop and improve this tool.</p>
    </div>
"""
st.markdown(footer_html, unsafe_allow_html=True)