import re
import sqlite3
import pandas as pd
import streamlit as st

# Admin credentials
admin_username = "admin957316&7k/."
admin_password = "5tgdcjyu.w4&GF%$"

# Function to reset and re-create the table
def csv_to_sqlite(csv_file, db_file):
    try:
        # Read the CSV file into a DataFrame
        print(f"Reading CSV file: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8-sig')

        # Connect to the SQLite database (or create it)
        print(f"Connecting to database: {db_file}")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Drop the old table if it exists
        print("Dropping the existing 'energy_data' table if it exists")
        cursor.execute("DROP TABLE IF EXISTS energy_data")

        # Create the new table with group_id, criteria, energy_method, direction, and paragraph fields
        print("Creating the table 'energy_data' with direction")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                criteria TEXT,
                energy_method TEXT,
                direction TEXT,  -- Store Increase/Decrease here
                paragraph TEXT
            )
        ''')

        # Insert CSV data into SQLite, splitting paragraphs
        group_id = 1
        criteria_col = df.columns[0]  # Assuming the first column is 'criteria'
        
        # Group columns based on "Increase" and "Decrease"
        increase_cols = [col for col in df.columns if col.endswith('Increase')]
        reduction_cols = [col for col in df.columns if col.endswith('Decrease')]
        
        for _, row in df.iterrows():
            criteria = row[criteria_col]
            # Insert for each increase column
            for method in increase_cols:
                text_content = row[method]
                paragraphs = split_into_paragraphs(text_content)
                base_method = method.replace('Increase', '').strip()
                
                for paragraph in paragraphs:
                    cursor.execute('''
                        INSERT INTO energy_data (group_id, criteria, energy_method, direction, paragraph)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (group_id, criteria, base_method, 'Increase', paragraph))

            # Insert for each reduction column
            for method in reduction_cols:
                text_content = row[method]
                paragraphs = split_into_paragraphs(text_content)
                base_method = method.replace('Decrease', '').strip()
                
                for paragraph in paragraphs:
                    cursor.execute('''
                        INSERT INTO energy_data (group_id, criteria, energy_method, direction, paragraph)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (group_id, criteria, base_method, 'Decrease', paragraph))

            group_id += 1

        # Commit and close the connection
        conn.commit()
        print("Data inserted successfully")
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

# Function to split a cell's content into paragraphs
def split_into_paragraphs(text: str) -> list:
    paragraphs = [para.strip() for para in str(text).split('\n\n') if para.strip()]
    return paragraphs

# Run this function once to reset and create the database
#csv_to_sqlite('Full_References_009.csv', 'my_database.db')

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
        st.session_state.selected_direction = None
        st.rerun()  # Trigger a rerun on successful login
    else:
        st.warning("Incorrect username or password")

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]  # Clear all session states on logout
    st.rerun()

# Placeholder for dynamic tabs
placeholder = st.empty()

if st.session_state.logged_in:
    tab0, tab1, tab2 = placeholder.tabs(["Home", "Search", f"Logged in as {st.session_state.current_user}"])
else:
    tab0, tab1, tab2 = placeholder.tabs(["Home", "Search", "Login"])

# Login Tab
with tab0:
    st.title("Welcome to MacroBuild Energy")
    welcome_html = ("""<b>Aim:</b> This tool is developed from an extensive literature review of <b>200 studies</b> on macro-scale building energy consumption across neighborhood, urban, state, regional, national, and global levels. The tool identifies more than <b>100 determinants</b> that influence macro-scale building energy and clearly shows the direction of their relationship (whether increasing or decreasing) with various macro-scale energy outputs. By revealing how various factors influence energy outputs, the tool offers essential insights for urban planners and policymakers to develop effective energy reduction strategies.<br><b>Use:</b> Select the determinant you wish to explore, then choose the related energy output(s) from the 200 reviewed studies (such as total energy consumption, energy use intensity, or heating consumption).<br>Next, indicate the direction of the relationship you're interested in, and the tool will display the relevant study or studies, if available.<br><b>Future development:</b> To further expand this database, users can log in and contribute by adding references they are familiar with or their own studies, clearly specifying the determinants, energy outputs, and the direction of the relationship. After review and approval, these contributions will be added to enhance the database's comprehensiveness.<br>In future updates, two additional features—climate and scale (urban vs. national)—will be incorporated to capture the nuanced effects of these determinants on various energy outputs. With these options, the tool will provide even more precise recommendations for developers, planners, and policymakers. We encourage you to start contributing to this database and support efforts toward reducing macro-scale building energy consumption."""
    )
    st.markdown(welcome_html, unsafe_allow_html=True)

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
    #st.write("""This tool, developed through a systematic literature review, provides insights into how various determinants influence macro-scale building energy consumption, with references covering studies at neighborhood, urban, state, regional, national, and international levels."""
    #         )

    # Criteria Dropdown with Counts and Placeholder
    criteria_counts = query_criteria_counts(conn)
    criteria_list = ["Select a determinant"] + [f"{row[0]} [{row[1]}]" for row in criteria_counts]

    selected_criteria_with_count = st.selectbox(
        "Determinant",
        criteria_list,
        index=0 if st.session_state.selected_criteria is None else criteria_list.index(f"{st.session_state.selected_criteria} [{[count for crit, count in criteria_counts if crit == st.session_state.selected_criteria][0]}]"),
        format_func=lambda x: x if x == "Select a determinant" else x
    )

    if selected_criteria_with_count != "Select a determinant":
        new_criteria = selected_criteria_with_count.split(" [")[0]
        if new_criteria != st.session_state.selected_criteria:
            st.session_state.selected_criteria = new_criteria
            st.session_state.selected_method = None  # Reset method on new criteria selection
            st.rerun()  # Trigger rerun to apply selection changes

        # Energy Method Dropdown with Counts and Placeholder
        energy_method_counts = query_energy_method_counts(conn, st.session_state.selected_criteria)
        method_list = ["Select an output"] + [f"{row[0]} [{row[1]}]" for row in energy_method_counts]

        selected_method_with_count = st.selectbox(
            "Energy Output(s)",
            method_list,
            index=0 if st.session_state.selected_method is None else method_list.index(f"{st.session_state.selected_method} [{[count for meth, count in energy_method_counts if meth == st.session_state.selected_method][0]}]"),
            format_func=lambda x: x if x == "Select an output" else x
        )

        if selected_method_with_count != "Select an output":
            st.session_state.selected_method = selected_method_with_count.split(" [")[0]

            # Initialize selected_direction in session state if not already set
            if 'selected_direction' not in st.session_state:
                st.session_state.selected_direction = None
            
            # Query function to get the count for each direction
            def query_direction_counts(conn, selected_criteria, selected_method):
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT direction, COUNT(paragraph) as count
                    FROM energy_data
                    WHERE criteria = ? AND energy_method = ? AND paragraph IS NOT NULL AND paragraph != '' AND paragraph != '0' AND paragraph != '0.0'
                    GROUP BY direction
                ''', (selected_criteria, selected_method))
                return dict(cursor.fetchall())


            # Reset selected_direction when criteria or method changes
            new_criteria = selected_criteria_with_count.split(" [")[0] if selected_criteria_with_count != "Select a determinant" else None
            new_method = selected_method_with_count.split(" [")[0] if selected_method_with_count != "Select an output" else None

            # Reset selected_direction and rerun if criteria or method has changed
            if new_criteria != st.session_state.get("selected_criteria"):
                st.session_state.selected_criteria = new_criteria
                st.session_state.selected_method = None  # Reset method
                #st.session_state.selected_direction = None  # Reset direction
                st.rerun()
            elif new_method != st.session_state.get("selected_method"):
                st.session_state.selected_method = new_method
                #st.session_state.selected_direction = None  # Reset direction
                st.rerun()

            # Ensure criteria and method are selected before showing the direction choice
            if st.session_state.selected_method:
                # Fetch counts for each direction
                direction_counts = query_direction_counts(conn, st.session_state.selected_criteria, st.session_state.selected_method)
                increase_count = direction_counts.get("Increase", 0)
                decrease_count = direction_counts.get("Decrease", 0)

                # Display radio buttons with counts, without default selection
                selected_direction = st.radio(
                    "Please select the direction of the relationship",
                    [f"Increase [{increase_count}]", f"Decrease [{decrease_count}]"],
                    index= None,  # No preselection
                    key="selected_direction"
                )

                # Proceed only if a direction is selected
                if selected_direction:
                    # Remove count from selected direction (e.g., 'Increase' instead of 'Increase [5]')
                    direction_choice = selected_direction.split(" ")[0]

                # Continue with other functionality only if a direction is chosen
                #if st.session_state.get("selected_direction"):
                    paragraphs = query_paragraphs(conn, st.session_state.selected_criteria, st.session_state.selected_method, direction_choice)
                    
                    
                    # Display results or warning #The following study (or studies) shows that an increase ...
                    if paragraphs:
                        # Retrieve the count for the selected direction directly from the dictionary
                        selected_direction_count = st.session_state.selected_direction.split(" ")[1]

                        if selected_direction_count == "[1]":
                            st.markdown(f"<p><b>The following study shows that an increase (or presence) in {st.session_state.selected_criteria} leads to <i>{'higher' if st.session_state.selected_direction == 'Increase' else 'lower'}</i> {st.session_state.selected_method}.</b></p>", unsafe_allow_html=True)

                        else:
                            st.markdown(f"<p><b>The following studies show that an increase (or presence) in {st.session_state.selected_criteria} leads to <i>{'higher' if st.session_state.selected_direction == 'Increase' else 'lower'}</i> {st.session_state.selected_method}.</b></p>", unsafe_allow_html=True)


                        for para_id, para_text in paragraphs:
                            # Admin options for logged in users
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
                        st.warning(f"No studies have been reported for an increase (or presence) in {st.session_state.selected_criteria} leading to {'higher' if st.session_state.selected_direction == 'Increase' else 'lower'} {st.session_state.selected_method}.")
            
                    # Add New Record Section
                    if st.session_state.logged_in and direction_choice != None:
                        # Only show "Add New Record" button if the form is not currently active
                        if not st.session_state.get("show_new_record_form", False):
                            if st.button("Add New Record", key="add_new_record"):
                                st.session_state.show_new_record_form = True  # Show form once button is clicked

                        # Display the form only when 'show_new_record_form' is True
                        if st.session_state.get("show_new_record_form", False):
                            new_paragraph = st.text_area(
                                f"Add new record for {st.session_state.selected_criteria} and {st.session_state.selected_method} ({direction_choice})",
                                key="new_paragraph"
                            )
                            
                            # Show "Save" button within the form
                            if st.button("Save", key="save_new_record"):
                                # Save record only if text and direction are provided
                                if new_paragraph.strip() and direction_choice:
                                    cursor = conn.cursor()
                                    cursor.execute('''
                                        INSERT INTO energy_data (criteria, energy_method, direction, paragraph)
                                        VALUES (?, ?, ?, ?)
                                    ''', (st.session_state.selected_criteria, st.session_state.selected_method, direction_choice, new_paragraph))
                                    conn.commit()
                                    st.success("New record added successfully.")
                                    
                                    # Hide the form and refresh to show the new record
                                    st.session_state.show_new_record_form = False  # Reset form state
                                    st.rerun()  # Refresh to display the new record immediately
                                else:
                                    st.warning("Please select a direction and ensure the record is not empty before saving.")



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
#st.markdown(footer_html, unsafe_allow_html=True)

