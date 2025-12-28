import pathway as pw
import os
import json

# Define schema for patients
class PatientSchema(pw.Schema):
    patient_id: str
    name: str
    symptoms: str
    vitals: dict
    labs: dict

# Define schema for resources
class ResourceSchema(pw.Schema):
    timestamp: str
    icu_beds_total: int
    icu_beds_available: int
    doctors_on_call: list
    nurses_available: int

# Configuration
DATA_DIR = "./data"
OUTPUT_DIR = "./output"

def run():
    # 1. Ingest Streams
    # Patients: Read as a stream of events
    patients = pw.io.fs.read(
        os.path.join(DATA_DIR, "patients.jsonl"),
        format="json",
        schema=PatientSchema,
        mode="streaming"
    )

    # Resources: Read as a table (we want the latest state)
    resources = pw.io.fs.read(
        os.path.join(DATA_DIR, "resources.jsonl"),
        format="json",
        schema=ResourceSchema,
        mode="streaming"
    )
    # We only care about the latest resource update, so we can reduce/take latest if needed, 
    # but for simplicity in this stream join, we'll just join on a common key or use a cross join equivalent.
    # Since Pathway joins are temporal, we'll keep it simple:
    # In a real app, resources would be a slowly changing dimension table.
    
    # Guidelines: Read as text (simplification)
    with open(os.path.join(DATA_DIR, "guidelines.md"), "r") as f:
        guidelines_text = f.read()

    # 2. Transformation with LLM
    # We define a User Defined Function (UDF) to call the LLM
    @pw.udf
    def triage_patient(
        p_id: str, 
        p_name: str, 
        p_sum: str, 
        p_vitals: dict, 
        p_labs: dict,
        r_beds: int,
        r_docs: list,
        r_nurses: int
    ) -> str:
        
        # Construct the prompt
        prompt = f"""
        You are a Live AI Healthcare Triage Agent.
        
        GUIDELINES:
        {guidelines_text}
        
        CURRENT RESOURCES:
        ICU Beds Available: {r_beds}
        Doctors: {r_docs}
        Nurses: {r_nurses}
        
        PATIENT:
        ID: {p_id}
        Name: {p_name}
        Symptoms: {p_sum}
        Vitals: {p_vitals}
        Labs: {p_labs}
        
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
        
        # Call OpenAI (Simulated here if no key, but structured for real call)
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return json.dumps({"error": "OPENAI_API_KEY not set. Cannot perform triage."})
            
        from openai import OpenAI
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
            return response.choices[0].message.content
        except Exception as e:
            return json.dumps({"error": str(e)})

    # Join Patients with latest Resources
    # This is a 'window' or 'asof' join in concept, but for this simple demo we'll just cross join 
    # assuming resources is a single row table that updates. 
    # In Pathway, we can cross join a stream with a table.
    
    # We need to make resources a table with a single 'latest' row if possible, 
    # or just join on a dummy key.
    patients_with_key = patients.select(
        *pw.this,
        join_key=pw.apply.lambda_v(lambda x: 1, patients.patient_id) # dummy key
    )
    
    resources_with_key = resources.reduce(
        join_key=1,
        icu_beds_available=pw.reducers.max(resources.icu_beds_available), # Simplified: taking max just to get a value
        doctors_on_call=pw.reducers.max(resources.doctors_on_call),
        nurses_available=pw.reducers.max(resources.nurses_available)
        # In reality, you'd want the *latest* by timestamp.
        # resources.sort_by(resources.timestamp).reduce(...)
    )

    # Join
    triage_inputs = patients_with_key.join(
        resources_with_key,
        patients_with_key.join_key == resources_with_key.join_key
    ).select(
        patients_with_key.patient_id,
        patients_with_key.name,
        patients_with_key.symptoms,
        patients_with_key.vitals,
        patients_with_key.labs,
        resources_with_key.icu_beds_available,
        resources_with_key.doctors_on_call,
        resources_with_key.nurses_available
    )

    # Apply LLM Logic
    decisions = triage_inputs.select(
        patient_id=triage_inputs.patient_id,
        decision=triage_patient(
            triage_inputs.patient_id,
            triage_inputs.name,
            triage_inputs.symptoms,
            triage_inputs.vitals,
            triage_inputs.labs,
            triage_inputs.icu_beds_available,
            triage_inputs.doctors_on_call,
            triage_inputs.nurses_available
        )
    )

    # 3. Output
    pw.io.fs.write(
        decisions,
        os.path.join(OUTPUT_DIR, "triage_decisions.jsonl"),
        format="json"
    )

    # Run the pipeline
    pw.run()

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    run()
