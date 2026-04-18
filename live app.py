import streamlit as st
import pandas as pd
import re
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Voyce RTM Live Dashboard", layout="wide")

# Custom CSS for better UI and RTL support for Arabic text if needed
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stTable { background-color: white; border-radius: 10px; }
    h1 { color: #1E3A8A; font-family: 'Segoe UI', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. Parsing Function for Voyce Live Data ---
def parse_voyce_status(raw_text):
    interpreters = []
    # Regex to capture Status, ID, and Name from your provided sample
    pattern = r"(In Service|Pending|Serviced).*?Interpreter:\s(\d+)\s([\w\s]+)"
    matches = re.findall(pattern, raw_text)
    for match in matches:
        status_raw = match[0]
        # Mapping statuses based on your requirements
        current_status = "Busy" if status_raw == "In Service" else "Available"
        interpreters.append({
            "ID": str(match[1]),
            "Name": match[2].strip(),
            "LiveStatus": current_status
        })
    return pd.DataFrame(interpreters)

# --- 2. Parsing Function for the Uploaded Excel (Schedule) ---
def parse_schedule_excel(file):
    # Reading as CSV since the system processed your report.xlsx as CSV
    df = pd.read_csv(file)
    schedule_data = []
    current_agent_name = None
    current_agent_id = None
    
    for index, row in df.iterrows():
        cell_value = str(row.iloc[0])
        # Extract Agent ID and Name from "Agent: 12345 Name"
        if "Agent:" in cell_value:
            match = re.search(r"Agent:\s(\d+)\s(.*)", cell_value)
            if match:
                current_agent_id = str(match.group(1))
                current_agent_name = match.group(2).strip()
        
        # Check for date and shift times (Columns 2, 3, 4 based on your file snippet)
        try:
            # Filtering for specific date in file or any shift row
            if current_agent_name and ("4/18/26" in str(row.iloc[2])):
                start_time = str(row.iloc[3])
                end_time = str(row.iloc[4])
                if start_time != "nan" and start_time.lower() != "off":
                    schedule_data.append({
                        "ID": current_agent_id,
                        "Agent Name": current_agent_name,
                        "Shift Start": start_time,
                        "Shift End": end_time
                    })
        except:
            continue
    return pd.DataFrame(schedule_data)

# --- 3. UI Layout ---
st.title("📊 Voyce Real-Time Management Dashboard")
st.markdown("---")

tab1, tab2 = st.tabs(["📺 Live Monitoring", "📂 Update Schedule"])

# TAB 2: Uploading the Excel Report
with tab2:
    st.header("Schedule Management")
    st.info("Upload the 'Agent Schedules' report here whenever there's a change (Absence, Swaps, OT).")
    uploaded_file = st.file_uploader("Upload Excel/CSV Report", type=["xlsx", "csv"])
    
    if uploaded_file:
        df_sched = parse_schedule_excel(uploaded_file)
        if not df_sched.empty:
            st.session_state['master_schedule'] = df_sched
            st.success(f"Successfully loaded {len(df_sched)} agent schedules.")
            st.dataframe(df_sched, use_container_width=True)
        else:
            st.error("Could not find valid shift data in the file. Please check the format.")

# TAB 1: The Live View
with tab1:
    st.header("Live Queue Status")
    
    # Text area for Voyce Data
    voyce_input = st.text_area("Paste Live Data from Voyce Manager Page here:", height=200, 
                               placeholder="Example: 62554397... Interpreter: 1306865 Patricia Romo...")

    if voyce_input and 'master_schedule' in st.session_state:
        # Process Live Data
        df_live = parse_voyce_status(voyce_input)
        df_sched = st.session_state['master_schedule']
        
        # Merge Schedule with Live Status based on ID
        merged = pd.merge(df_sched, df_live, on="ID", how="left")
        
        # Logic to determine Compliance
        def get_compliance_status(row):
            if pd.isna(row['LiveStatus']):
                return "❌ OUT OF QUEUE (Offline)"
            elif row['LiveStatus'] == "Available":
                return "✅ IN QUEUE (Available)"
            else:
                return "📞 BUSY (In Call)"

        merged['Compliance Status'] = merged.apply(get_compliance_status, axis=1)
        
        # Color Coding logic for the table
        def color_rows(val):
            if "✅" in val: return 'background-color: #dcfce7; color: #166534;' # Light Green
            if "❌" in val: return 'background-color: #fee2e2; color: #991b1b;' # Light Red
            if "📞" in val: return 'background-color: #fef9c3; color: #854d0e;' # Light Yellow
            return ''

        # Display Final Dashboard
        st.subheader(f"Real-Time Analysis - {datetime.now().strftime('%H:%M:%S')}")
        display_df = merged[['ID', 'Agent Name', 'Shift Start', 'Shift End', 'Compliance Status']]
        
        st.table(display_df.style.applymap(color_rows, subset=['Compliance Status']))
        
        # Quick Stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Total in Shift", len(merged))
        col2.metric("Available", len(merged[merged['Compliance Status'].str.contains("✅")]))
        col3.metric("Out of Queue", len(merged[merged['Compliance Status'].str.contains("❌")]))
        
    elif not voyce_input:
        st.warning("Waiting for Voyce data... Please paste the current activity list.")
    elif 'master_schedule' not in st.session_state:
        st.error("No schedule found. Please go to 'Update Schedule' tab and upload the report first.")