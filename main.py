import os
import json
import time
from openai import OpenAI

# Configuration
DATA_DIR = "./data"
OUTPUT_DIR = "./output"
PATIENTS_FILE = os.path.join(DATA_DIR, "patients.jsonl")
RESOURCES_FILE = os.path.join(DATA_DIR, "resources.jsonl")
GUIDELINES_FILE = os.path.join(DATA_DIR, "guidelines.md")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "triage_decisions.jsonl")

def get_latest_resources():
    """Reads the last line of resources file to get the latest state."""
    last_line = None
    if os.path.exists(RESOURCES_FILE):
        with open(RESOURCES_FILE, "r") as f:
            for line in f:
                if line.strip():
                    last_line = line
    if last_line:
        return json.loads(last_line)
    return {}

def get_guidelines():
    if os.path.exists(GUIDELINES_FILE):
        with open(GUIDELINES_FILE, "r") as f:
            return f.read()
    return ""

def triage_patient(patient_data, guidelines_text, resources):
    prompt = f"""
    You are a Live AI Healthcare Triage Agent.
    
    GUIDELINES:
    {guidelines_text}
    
    CURRENT RESOURCES:
    ICU Beds Available: {resources.get('icu_beds_available', 'Unknown')}
    Doctors: {resources.get('doctors_on_call', [])}
    Nurses: {resources.get('nurses_available', 'Unknown')}
    
    PATIENT:
    ID: {patient_data.get('patient_id')}
    Name: {patient_data.get('name')}
    Symptoms: {patient_data.get('symptoms')}
    Vitals: {patient_data.get('vitals')}
    Labs: {patient_data.get('labs')}
    
    TASK:
    Perform triage, resource allocation, and alerting based on the guidelines and resources.
    
    OUTPUT FORMAT (Strict JSON):
    {{
        "Patient Summary": {{ ... }},
        "Triage Decision": {{ "Priority Level": "...", "Reasoning": "..." }},
        "Resource Decision": {{ "ICU Required": "...", "ICU Assigned": "...", "Doctor Assigned": "...", "Nurse Assigned": "..." }},
        "Alerts": {{ "Alert Level": "...", "Alert Message": "..." }}
    }}
    """
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set", "patient_id": patient_data.get("patient_id")}

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful medical triage assistant. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        error_msg = str(e)
        print(f"LLM Error for {patient_data.get('patient_id')}: {error_msg}")
        
        # FALLBACK LOGIC (Rule-based)
        # If LLM fails (quota, network, etc.), we apply basic keywords to keep the system running.
        symptoms = patient_data.get('symptoms', '').lower()
        priority = "Low"
        reasoning = "Fallback: Minor symptoms detected."
        icu_req = "No"
        
        if "chest pain" in symptoms or "severe" in symptoms or "difficulty breathing" in symptoms:
            priority = "Critical"
            reasoning = "Fallback: Critical keywords detected in symptoms."
            icu_req = "Yes"
        elif "broken" in symptoms or "fracture" in symptoms:
            priority = "Medium"
            reasoning = "Fallback: Potential fracture detected."
            
        return {
            "Patient Summary": {
                "ID": patient_data.get('patient_id'),
                "Name": patient_data.get('name')
            },
            "Triage Decision": {
                "Priority Level": priority,
                "Reasoning": reasoning + f" (Auto-generated due to LLM Error: {error_msg[:50]}...)"
            },
            "Resource Decision": {
                "ICU Required": icu_req,
                "ICU Assigned": "Pending Check",
                "Doctor Assigned": "On Call",
                "Nurse Assigned": "Next Available"
            },
            "Alerts": {
                "Alert Level": "Urgent" if priority == "Critical" else "Normal",
                "Alert Message": f"System Alert: Fallback mode used for {patient_data.get('name')}"
            }
        }

def run():
    print("Starting Live AI Healthcare Triage Agent (Windows Compatibility Mode)...")
    print(f"Monitoring {PATIENTS_FILE} for new patients...")

    # Create output directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Open patients file and seek to end (or start if you want to process history)
    # We will process all lines for now to emulate the stream from start
    if not os.path.exists(PATIENTS_FILE):
        print(f"Waiting for {PATIENTS_FILE} to be created...")
        while not os.path.exists(PATIENTS_FILE):
            time.sleep(1)

    with open(PATIENTS_FILE, "r") as f:
        # Seek to end to only process NEW patients? 
        # Or process existing? expected behavior is usually existing + new for "start".
        # Let's process everything for the demo.
        f.seek(0, 0) 
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(1) # Wait for new data
                continue
            
            if not line.strip():
                continue

            try:
                patient = json.loads(line)
                print(f"Processing Patient {patient.get('patient_id')}...")
                
                guidelines = get_guidelines()
                resources = get_latest_resources()
                
                decision = triage_patient(patient, guidelines, resources)
                
                # Write to output
                with open(OUTPUT_FILE, "a") as outfile:
                    outfile.write(json.dumps(decision) + "\n")
                
                print(f"Decision logged for {patient.get('patient_id')}")
                
            except json.JSONDecodeError:
                print("Skipping invalid JSON line")

if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.strip() == "sk-..." or not api_key.startswith("sk-"):
        print("\n" + "="*50)
        print("CRITICAL ERROR: Invalid OpenAI API Key detected!")
        print("You are currently using a placeholder or missing key.")
        print("Please set your ACTUAL OpenAI API Key in the terminal:")
        print("  $env:OPENAI_API_KEY='sk-your-actual-key-from-openai-dashboard'")
        print("="*50 + "\n")
        # We don't exit to allow them to set it and restart, but we warn heavily.
        # actually, better to exit or pause so they see it.
        exit(1)
        
    run()
