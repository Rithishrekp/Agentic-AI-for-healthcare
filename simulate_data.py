import time
import json
import random
import os

DATA_FILE = "./data/patients.jsonl"

patients = [
    {"patient_id": "P2001", "name": "Alice Wonderland", "symptoms": "Severe headache, slurred speech", "vitals": {"bp": "180/100", "hr": 90, "spo2": 95}, "labs": {}},
    {"patient_id": "P2002", "name": "Bob Builder", "symptoms": "Broken thumb", "vitals": {"bp": "130/80", "hr": 80, "spo2": 99}, "labs": {}},
    {"patient_id": "P2003", "name": "Charlie Brown", "symptoms": "Asthma attack, difficulty breathing", "vitals": {"bp": "140/90", "hr": 120, "spo2": 88}, "labs": {}},
]

def simulate():
    print(f"Simulating data stream to {DATA_FILE}...")
    for p in patients:
        time.sleep(5)
        with open(DATA_FILE, "a") as f:
            f.write(json.dumps(p) + "\n")
        print(f"Added patient {p['patient_id']}")

if __name__ == "__main__":
    if not os.path.exists(DATA_FILE):
        print("Data file not found!")
    else:
        simulate()
