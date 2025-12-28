import streamlit as st
import pandas as pd
import json
import os
import time

# Page Config
st.set_page_config(
    page_title="Live AI Triage Dashboard",
    page_icon="🏥",
    layout="wide"
)

# Title & Description
st.title("🏥 Live AI Healthcare Triage Agent")
st.markdown("""
**Status:** 🟢 Online  |  **Mode:** Agentic (Autonomous)
This dashboard monitors the real-time decisions made by the AI Triage Agent.
""")

# Sidebar for controls
with st.sidebar:
    st.header("Control Panel")
    auto_refresh = st.checkbox("Auto-Refresh (Real-time)", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 1, 10, 2)
    st.divider()
    st.info("The Agent is running in the background, processing 'patients.jsonl'.")

# Metric Placeholders (Top)
col1, col2, col3, col4 = st.columns(4)
metric_total = col1.empty()
metric_critical = col2.empty()
metric_icu = col3.empty()
metric_fallback = col4.empty()

OUTPUT_FILE = "./output/triage_decisions.jsonl"
RESOURCES_FILE = "./data/resources.jsonl"

def load_resources():
    if not os.path.exists(RESOURCES_FILE):
        return {}
    last_line = None
    with open(RESOURCES_FILE, "r") as f:
        for line in f:
            if line.strip():
                last_line = line
    if last_line:
        return json.loads(last_line)
    return {}

def load_data():
    if not os.path.exists(OUTPUT_FILE):
        return []
    data = []
    with open(OUTPUT_FILE, "r") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except:
                    pass
    return data

def process_data(data):
    if not data:
        return pd.DataFrame()
    processed = []
    for entry in data:
        if "error" in entry:
            continue
        p = entry.get("Patient Summary", {})
        t = entry.get("Triage Decision", {})
        r = entry.get("Resource Decision", {})
        processed.append({
            "Time": time.strftime("%H:%M:%S"), 
            "ID": p.get("ID"),
            "Name": p.get("Name"),
            "Priority": t.get("Priority Level"),
            "ICU Decision": r.get("ICU Required") + " -> " + r.get("ICU Assigned"),
            "Reasoning": t.get("Reasoning"),
            "Alert": entry.get("Alerts", {}).get("Alert Message")
        })
    return pd.DataFrame(processed)

# --- Main Logic (Linear Execution) ---
raw_data = load_data()
resources = load_resources()

# 1. Update Sidebar
if resources:
    with st.sidebar:
        st.divider()
        st.subheader("🏥 Hospital Status")
        col_a, col_b = st.columns(2)
        col_a.metric("ICU Beds", f"{resources.get('icu_beds_available', 0)} / {resources.get('icu_beds_total', 0)}")
        col_b.metric("General Wards", f"{resources.get('general_wards_available', 0)} / {resources.get('general_wards_total', 0)}")
        st.metric("Nurses Active", resources.get("nurses_available", 0))
        st.write("**Doctors On Call:**")
        
        # Handle dict (Specialists) or list (Simple)
        docs = resources.get("doctors_on_call", {})
        if isinstance(docs, dict):
            for specialty, names in docs.items():
                with st.expander(f"{specialty} ({len(names)})"):
                    for name in names:
                        st.caption(f"👨‍⚕️ {name}")
        elif isinstance(docs, list):
            for doc in docs:
                st.caption(f"👨‍⚕️ {doc}")

# 2. Process Data
df = process_data(raw_data)

if not df.empty:
    # Update Top Metrics
    metric_total.metric("Total Patients", len(df))
    crit_count = len(df[df["Priority"] == "Critical"])
    metric_critical.metric("Critical Cases", crit_count)
    fallback_count = df["Reasoning"].str.contains("Fallback", na=False).sum()
    metric_fallback.metric("Fallback Actions", fallback_count, delta_color="inverse")

    # Styling
    def highlight_critical(row):
        if row["Priority"] == "Critical":
            return ['background-color: #ffcccc'] * len(row)
        elif row["Priority"] == "High":
            return ['background-color: #ffeebb'] * len(row)
        return [''] * len(row)

    # Display Table
    st.dataframe(
        df.style.apply(highlight_critical, axis=1),
        use_container_width=True,
        height=400
    )
else:
    st.warning("Waiting for Agent to produce data...")

# 3. Chat Interface
st.divider()
st.subheader("💬 Supervisor Chat")
st.caption("Ask questions about the current patient status (e.g., 'How many critical patients?', 'Show me John Doe')")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask the Agent...", key="chat_input_unique"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Simple Logic Engine
    response = "I couldn't find that information."
    prompt_lower = prompt.lower()
    
    if "how many" in prompt_lower and "critical" in prompt_lower:
        crit_count = len(df[df["Priority"] == "Critical"]) if not df.empty else 0
        response = f"There are currently **{crit_count}** Critical patients requiring immediate attention."
    elif "how many" in prompt_lower and "total" in prompt_lower:
        response = f"I have processed a total of **{len(df)}** patients so far."
    elif "doctor" in prompt_lower:
        docs = resources.get("doctors_on_call", {})
        if isinstance(docs, dict):
            # Flatten for chat response
            all_docs = []
            for spec, names in docs.items():
                all_docs.append(f"**{spec}**: {', '.join(names)}")
            response = "Doctors on call:\n\n" + "\n\n".join(all_docs)
        else:
             response = f"Doctors currently on call: **{', '.join(docs)}**."
    elif "john doe" in prompt_lower:
        if not df.empty:
            patient = df[df["Name"].str.contains("John Doe", case=False)]
            if not patient.empty:
                status = patient.iloc[-1]['Priority']
                response = f"John Doe is marked as **{status}**. ({patient.iloc[-1]['Reasoning']})"
            else:
                response = "I haven't seen a patient named John Doe yet."
        else:
            response = "No data available yet."
    else:
        response = "I am monitoring the stream. Ask me about 'Critical' counts, 'Total' patients, or 'Doctors'."

    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

# 4. Auto-Refresh Logic
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
