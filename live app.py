import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Voyce RTM Dashboard", layout="wide")

# دالة ذكية لسحب البيانات من Voyce
def parse_voyce_status(raw_text):
    interpreters = []
    # نمط البحث عن الحالة والـ ID والاسم
    pattern = r"(In Service|Pending|Serviced).*?Interpreter:\s(\d+)\s([\w\s,]+)"
    matches = re.findall(pattern, raw_text)
    for match in matches:
        status_raw = match[0]
        current_status = "Busy" if status_raw == "In Service" else "Available"
        interpreters.append({
            "ID": str(match[1]).strip(),
            "LiveStatus": current_status
        })
    return pd.DataFrame(interpreters)

# دالة مُحسنة لقراءة ملف الإكسيل الخاص بك
def parse_schedule_excel(file):
    try:
        df = pd.read_csv(file)
        schedule_data = []
        current_agent_id = None
        current_agent_name = None
        
        for index, row in df.iterrows():
            cell_v = str(row.iloc[0])
            # سحب الـ ID والاسم من سطر "Agent:"
            if "Agent:" in cell_v:
                match = re.search(r"Agent:\s(\d+)\s(.*)", cell_v)
                if match:
                    current_agent_id = str(match.group(1)).strip()
                    current_agent_name = match.group(2).strip()
            
            # سحب أوقات العمل (بندور على أي سطر فيه توقيت في العمود الرابع)
            start_t = str(row.iloc[3])
            end_t = str(row.iloc[4])
            if current_agent_id and ":" in start_t and "AM" in start_t.upper() or "PM" in start_t.upper():
                schedule_data.append({
                    "ID": current_agent_id,
                    "Agent Name": current_agent_name,
                    "Shift Start": start_t,
                    "Shift End": end_t
                })
        
        final_df = pd.DataFrame(schedule_data).drop_duplicates(subset=['ID'])
        return final_df
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()

st.title("📊 Voyce RTM - Final Fix")

tab1, tab2 = st.tabs(["📺 Live View", "📂 Upload Schedule"])

with tab2:
    st.header("1. Upload Schedule")
    uploaded_file = st.file_uploader("Upload your report (4).xlsx here", type=["csv", "xlsx"])
    if uploaded_file:
        df_sched = parse_schedule_excel(uploaded_file)
        if not df_sched.empty:
            st.session_state['master_schedule'] = df_sched
            st.success(f"Done! Loaded {len(df_sched)} Agents.")
            st.dataframe(df_sched)

with tab1:
    st.header("2. Live Status")
    voyce_input = st.text_area("Paste Voyce Data Here:")
    
    if voyce_input and 'master_schedule' in st.session_state:
        df_live = parse_voyce_status(voyce_input)
        df_sched = st.session_state['master_schedule']
        
        # الربط (Merging)
        merged = pd.merge(df_sched, df_live, on="ID", how="left")
        
        def get_status(row):
            if pd.isna(row['LiveStatus']): return "❌ Offline / Not in Queue"
            if row['LiveStatus'] == "Available": return "✅ Available (In Queue)"
            return "📞 Busy (In Call)"
            
        merged['Status'] = merged.apply(get_status, axis=1)
        
        # نظام ألوان احترافي
        def style_df(v):
            if "✅" in v: return 'background-color: #dcfce7'
            if "❌" in v: return 'background-color: #fee2e2'
            return 'background-color: #fef9c3'

        st.table(merged[['ID', 'Agent Name', 'Shift Start', 'Shift End', 'Status']].style.applymap(style_df, subset=['Status']))
    else:
        st.info("Please Upload Schedule first, then paste Voyce data.")