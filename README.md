Real-Time Adaptive Healthcare Triage Agent using Pathway
Track Selection
Track 1: Agentic AI (Applied GenAI)

Problem Statement
Emergency rooms struggle with dynamic resource allocation and prioritizing patients during surges. Static protocols fail to adapt to real-time bed availability and changing medical guidelines, leading to inefficiencies and potential patient harm.

System Design & Architecture
Our solution is a Live AI Triage Agent built on Pathway, employing a stream-processing architecture to handle healthcare data in real-time.

1. Data Ingestion Layer (The "Senses")
The agent ingests three distinct, asynchronous data streams:

Patient Stream (Live): Intake forms arriving via JSON stream (simulating HL7/FHIR feeds).
Resource Stream (Stateful): Real-time updates on ICU/ER bed capacity and staff availability.
Knowledge Stream (Context): Medical guidelines and triage protocols (Markdown/Text), which can be updated dynamically without restarting the system.
2. Processing Engine (Pathway)
We utilize Pathway’s Rust-based engine for high-throughput, low-latency processing.

pw.io.fs.read(mode="streaming"): continuously watches input sources.
Windowing & Joins: The incoming patient stream is joined with the latest known state of the hospital resources. This integration ensures the AI never assigns a bed that doesn't exist.
3. Agentic Logic (The "Brain")
The core logic utilizes an LLM (OpenAI GPT-4o/3.5) with a robust fallback mechanism.

Context Construction: For every patient, a dynamic prompt is assembled containing the specific patient's vitals, the current hospital capacity, and relevant sections of the triage guidelines.
Decision Making: The agent classifies priority (1-5), assigns resources, and justifies its reasoning.
Resilience: A rule-based fallback system activates automatically if the LLM API is unreachable (e.g., rate limits, network failure), ensuring 100% uptime for critical decisions.
4. Output Layer (Action)
Alerts: Critical cases trigger immediate alerts.
Log: Decisions are streamed to a persistent audit log (
jsonl
 sink) for downstream visualization or hospital dashboards.
Agentic Flow & "Post-Transformer" Alignment
This system moves beyond static "Chat with PDF" use cases. It represents Agentic AI because:

It Perceives: It monitors a changing environment (Resource Stream).
It Adapts: If guidelines change, the very next decision reflects the new protocol.
It Acts: It allocates actual resources (digital twin assignment) rather than just answering questions.
Why Pathway?
Pathway is critical to this design because standard Python scripts cannot easily handle the complexity of joining asynchronous live streams (Patients) with slowly changing dimension tables (Resources) in a consistent, fault-tolerant manner. Pathway’s table-based streaming model makes this complex join trivial and scalable.

