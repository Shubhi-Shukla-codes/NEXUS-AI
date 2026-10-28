"""
NEXUS Evaluation Benchmark Dataset & Seed Corpus
Contains structured ground-truth Q&A test cases, difficulty classifications,
and curated seed technical documents across all 6 institutional knowledge pillars.
"""

from typing import List, Dict, Any

# Curated seed documents spanning all 6 domain pillars
SEED_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "filename": "diesel_generator_maint_sop.txt",
        "title": "Tactical Diesel Generator Preventive Maintenance SOP",
        "domain": "technical_maintenance",
        "content": (
            "SECTION 1: OVERVIEW AND RATINGS\n"
            "The model DG-5000 tactical diesel generator delivers 45kW continuous output at 2400 RPM.\n"
            "Pre-operation inspection requires checking circuit breaker B-12 on alternator assembly.\n"
            "Normal lubricating oil pressure must register between 45 and 65 PSI during steady-state load.\n"
            "If oil pressure drops below 30 PSI, the automated emergency shutdown trip triggers in 5 seconds.\n\n"
            "SECTION 2: HYDRAULIC GOVERNOR AND FUEL LINES\n"
            "The hydraulic fuel governor maintains operating pressure between 2500 and 3000 PSI.\n"
            "Inspect the high-pressure relief valve weekly for seal wear and residue.\n"
            "Coolant temperature threshold: Maximum permissible operating temperature is 98 degrees Celsius.\n"
            "Fuel injector nozzle calibration must occur every 500 operating hours or semi-annually."
        )
    },
    {
        "filename": "field_engineering_curriculum.txt",
        "title": "Field Engineering Qualification Curriculum and Rubric",
        "domain": "training_education",
        "content": (
            "MODULE 1: QUALIFICATION PREREQUISITES\n"
            "Trainees must complete Level 1 Electrical Safety Certification prior to practical generator maintenance.\n"
            "The standard training course duration is 40 instructional hours comprising 16 lecture hours and 24 practical lab hours.\n"
            "Passing threshold for theoretical assessment is 80%, while practical component assembly requires 100% compliance with safety checklist.\n\n"
            "MODULE 2: OBJECTIVES AND EVALUATION\n"
            "Primary learning objective: Trainee demonstrates circuit isolation, multimeter diagnostic calibration, and lockout-tagout within 12 minutes.\n"
            "Multimeter model MM-400 requires calibration verification every 90 days against standard reference voltage."
        )
    },
    {
        "filename": "chemical_exposure_safety_sds.txt",
        "title": "Emergency Chemical Exposure & Hazard Response Guide",
        "domain": "safety_emergency",
        "content": (
            "SECTION 1: TOXIC AMMONIA PROTOCOL\n"
            "Anhydrous ammonia vapor exposure requires immediate evacuation upwind.\n"
            "Response personnel must don Level B PPE with self-contained breathing apparatus (SCBA) before entering containment perimeter.\n"
            "In case of ocular or dermal contact, immediately flush the affected area at an eye-wash station with clean potable water for a minimum of 15 minutes.\n"
            "Administer humidified oxygen if inhalation symptoms occur and transport immediately to advanced medical facility.\n\n"
            "SECTION 2: CORROSIVE ACID SPLASH\n"
            "Sulphuric acid splashes require rapid removal of contaminated apparel.\n"
            "Flush skin with copious amounts of water. Do not apply dry sodium bicarbonate directly to open dermal wounds."
        )
    },
    {
        "filename": "airgap_workstation_hardening.txt",
        "title": "Air-Gapped Workstation Defensive Hardening Standard",
        "domain": "defensive_cybersecurity",
        "content": (
            "POLICY 101: AIR-GAP NETWORK ISOLATION\n"
            "All intelligence terminals operating in classified or isolated enclaves must maintain strict physical air-gap separation.\n"
            "Wireless communication controllers, Bluetooth interfaces, and camera hardware must be physically removed or hardware-disabled at BIOS level.\n"
            "Cryptographic root keys and operational certificates must undergo rotation every 90 days using verified hardware tokens.\n\n"
            "POLICY 102: REMOVABLE MEDIA AND PORT CONTROLS\n"
            "USB mass storage devices must be read-only sanitized before ingestion into enclave systems.\n"
            "Defensive monitoring requires local syslog retention for a minimum of 365 days in write-once append-only storage.\n"
            "Supervisory control system port 502 (Modbus TCP) must be strictly blocked on host firewalls."
        )
    },
    {
        "filename": "field_hospital_geospatial_directory.txt",
        "title": "Humanitarian Field Hospital & Logistics Route Directory",
        "domain": "humanitarian_geospatial",
        "content": (
            "SECTOR 4 MEDICAL INFRASTRUCTURE\n"
            "Field Hospital Alpha-4 is situated at coordinates 34.2045 N, 71.3912 E, elevation 420 meters.\n"
            "Total inpatient bed capacity is 60 beds with an integrated surgical theater rated for Level 3 emergency trauma.\n"
            "Potable water supply requires 3,500 liters daily, supplied via primary convoy Route Blue from reservoir depot 2.\n\n"
            "SECTOR 4 LOGISTICS ROUTES\n"
            "Route Blue is all-weather paved, accommodating vehicles up to 20 metric tons.\n"
            "Emergency secondary route Green passes through mountain pass elevation 880 meters and is restricted to high-clearance 4x4 vehicles."
        )
    },
    {
        "filename": "hazardous_material_containment_guide.txt",
        "title": "Hazardous Material Containment & Environmental Spill SOP",
        "domain": "hazard_environmental",
        "content": (
            "SECTION 1: UN NUMBERS AND CLASSIFICATION\n"
            "Anhydrous ammonia is classified under UN number UN 1005 (Class 2.3 Toxic Gas, subsidiary 8 Corrosive).\n"
            "Sulphuric acid solution is classified under UN number UN 1830 (Class 8 Corrosive Substance).\n"
            "Class 3 flammable liquids must be stored in spark-proof secondary containment vessels at temperatures below 38 degrees Celsius.\n\n"
            "SECTION 2: SPILL NEUTRALIZATION AND RUNOFF\n"
            "For sulphuric acid spills up to 50 liters, deploy calcium carbonate (limestone slurry) or hydrated lime as neutralizer agent.\n"
            "Deploy polyurethane runoff containment barriers at all drainage inlets within a 100-meter radius before initiating wash-down."
        )
    }
]

# Structured Benchmark Test Cases (30 questions spanning 6 domains + out-of-domain abstentions)
BENCHMARK_CASES: List[Dict[str, Any]] = [
    # Technical Maintenance
    {
        "id": "BENCH-001",
        "domain": "technical_maintenance",
        "difficulty": "direct_factual",
        "query": "What is the normal operating oil pressure for the DG-5000 diesel generator?",
        "expected_document": "diesel_generator_maint_sop.txt",
        "relevant_keywords": ["45 and 65 psi", "steady-state"],
        "ground_truth_answer": "Normal lubricating oil pressure is between 45 and 65 PSI during steady-state load.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-002",
        "domain": "technical_maintenance",
        "difficulty": "technical_code",
        "query": "Which circuit breaker must be checked on the alternator assembly before operating the generator?",
        "expected_document": "diesel_generator_maint_sop.txt",
        "relevant_keywords": ["b-12", "circuit breaker", "alternator"],
        "ground_truth_answer": "Circuit breaker B-12 on the alternator assembly must be checked before starting.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-003",
        "domain": "technical_maintenance",
        "difficulty": "direct_factual",
        "query": "What is the pressure operating range for the hydraulic governor?",
        "expected_document": "diesel_generator_maint_sop.txt",
        "relevant_keywords": ["2500 and 3000 psi", "governor"],
        "ground_truth_answer": "The hydraulic fuel governor maintains operating pressure between 2500 and 3000 PSI.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-004",
        "domain": "technical_maintenance",
        "difficulty": "direct_factual",
        "query": "What is the maximum permissible coolant temperature for the generator?",
        "expected_document": "diesel_generator_maint_sop.txt",
        "relevant_keywords": ["98 degrees celsius", "coolant"],
        "ground_truth_answer": "The maximum permissible operating coolant temperature is 98 degrees Celsius.",
        "is_abstention_case": False
    },

    # Training & Education
    {
        "id": "BENCH-005",
        "domain": "training_education",
        "difficulty": "direct_factual",
        "query": "What is the prerequisite certification required before practical generator maintenance training?",
        "expected_document": "field_engineering_curriculum.txt",
        "relevant_keywords": ["level 1 electrical safety", "prerequisite"],
        "ground_truth_answer": "Trainees must complete Level 1 Electrical Safety Certification prior to practical maintenance.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-006",
        "domain": "training_education",
        "difficulty": "direct_factual",
        "query": "How many total instructional hours make up the field engineering course?",
        "expected_document": "field_engineering_curriculum.txt",
        "relevant_keywords": ["40 instructional hours", "16 lecture", "24 practical"],
        "ground_truth_answer": "The course is 40 instructional hours comprising 16 lecture hours and 24 practical lab hours.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-007",
        "domain": "training_education",
        "difficulty": "technical_code",
        "query": "What is the calibration interval for multimeter model MM-400?",
        "expected_document": "field_engineering_curriculum.txt",
        "relevant_keywords": ["mm-400", "90 days", "calibration"],
        "ground_truth_answer": "Multimeter model MM-400 requires calibration verification every 90 days.",
        "is_abstention_case": False
    },

    # Safety & Emergency Response
    {
        "id": "BENCH-008",
        "domain": "safety_emergency",
        "difficulty": "direct_factual",
        "query": "What level of PPE is required for toxic ammonia vapor exposure?",
        "expected_document": "chemical_exposure_safety_sds.txt",
        "relevant_keywords": ["level b", "scba", "ppe"],
        "ground_truth_answer": "Response personnel must don Level B PPE with self-contained breathing apparatus (SCBA).",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-009",
        "domain": "safety_emergency",
        "difficulty": "direct_factual",
        "query": "How long must an affected area be flushed with water following ocular ammonia contact?",
        "expected_document": "chemical_exposure_safety_sds.txt",
        "relevant_keywords": ["15 minutes", "flush", "water"],
        "ground_truth_answer": "Flush the affected area at an eye-wash station with potable water for a minimum of 15 minutes.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-010",
        "domain": "safety_emergency",
        "difficulty": "direct_factual",
        "query": "What is the emergency protocol for a sulphuric acid splash on the skin?",
        "expected_document": "chemical_exposure_safety_sds.txt",
        "relevant_keywords": ["rapid removal", "copious", "water", "do not apply dry sodium bicarbonate"],
        "ground_truth_answer": "Rapidly remove contaminated apparel and flush skin with copious amounts of water without applying dry sodium bicarbonate.",
        "is_abstention_case": False
    },

    # Defensive Cybersecurity
    {
        "id": "BENCH-011",
        "domain": "defensive_cybersecurity",
        "difficulty": "direct_factual",
        "query": "How often must cryptographic root keys be rotated on air-gapped workstations?",
        "expected_document": "airgap_workstation_hardening.txt",
        "relevant_keywords": ["every 90 days", "cryptographic root keys", "rotation"],
        "ground_truth_answer": "Cryptographic root keys must undergo rotation every 90 days using verified hardware tokens.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-012",
        "domain": "defensive_cybersecurity",
        "difficulty": "direct_factual",
        "query": "What is the minimum retention period for local syslog logs in isolated enclaves?",
        "expected_document": "airgap_workstation_hardening.txt",
        "relevant_keywords": ["365 days", "syslog", "retention"],
        "ground_truth_answer": "Local syslog logs must be retained for a minimum of 365 days in write-once append-only storage.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-013",
        "domain": "defensive_cybersecurity",
        "difficulty": "technical_code",
        "query": "Which supervisory control port must be blocked on host firewalls?",
        "expected_document": "airgap_workstation_hardening.txt",
        "relevant_keywords": ["port 502", "modbus tcp", "blocked"],
        "ground_truth_answer": "Supervisory control system port 502 (Modbus TCP) must be strictly blocked on host firewalls.",
        "is_abstention_case": False
    },

    # Humanitarian & Geospatial
    {
        "id": "BENCH-014",
        "domain": "humanitarian_geospatial",
        "difficulty": "direct_factual",
        "query": "What are the geographic coordinates and elevation of Field Hospital Alpha-4?",
        "expected_document": "field_hospital_geospatial_directory.txt",
        "relevant_keywords": ["34.2045 n", "71.3912 e", "420 meters"],
        "ground_truth_answer": "Field Hospital Alpha-4 is located at coordinates 34.2045 N, 71.3912 E at an elevation of 420 meters.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-015",
        "domain": "humanitarian_geospatial",
        "difficulty": "direct_factual",
        "query": "What is the daily potable water requirement for Sector 4 Medical Infrastructure?",
        "expected_document": "field_hospital_geospatial_directory.txt",
        "relevant_keywords": ["3,500 liters daily", "route blue"],
        "ground_truth_answer": "Potable water supply requires 3,500 liters daily via convoy Route Blue.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-016",
        "domain": "humanitarian_geospatial",
        "difficulty": "direct_factual",
        "query": "What is the vehicle weight limit for convoy Route Blue?",
        "expected_document": "field_hospital_geospatial_directory.txt",
        "relevant_keywords": ["20 metric tons", "route blue"],
        "ground_truth_answer": "Convoy Route Blue accommodates vehicles weighing up to 20 metric tons.",
        "is_abstention_case": False
    },

    # Hazardous Material & Environmental
    {
        "id": "BENCH-017",
        "domain": "hazard_environmental",
        "difficulty": "technical_code",
        "query": "What is the UN classification number for anhydrous ammonia?",
        "expected_document": "hazardous_material_containment_guide.txt",
        "relevant_keywords": ["un 1005", "class 2.3", "subsidiary 8"],
        "ground_truth_answer": "Anhydrous ammonia is classified under UN number UN 1005 (Class 2.3 Toxic Gas, subsidiary 8 Corrosive).",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-018",
        "domain": "hazard_environmental",
        "difficulty": "technical_code",
        "query": "What is the UN number for sulphuric acid solution?",
        "expected_document": "hazardous_material_containment_guide.txt",
        "relevant_keywords": ["un 1830", "class 8 corrosive"],
        "ground_truth_answer": "Sulphuric acid solution is classified under UN number UN 1830 (Class 8 Corrosive Substance).",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-019",
        "domain": "hazard_environmental",
        "difficulty": "direct_factual",
        "query": "What neutralizer agent should be deployed for sulphuric acid spills up to 50 liters?",
        "expected_document": "hazardous_material_containment_guide.txt",
        "relevant_keywords": ["calcium carbonate", "limestone slurry", "hydrated lime"],
        "ground_truth_answer": "Deploy calcium carbonate (limestone slurry) or hydrated lime as the neutralizer agent.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-020",
        "domain": "hazard_environmental",
        "difficulty": "direct_factual",
        "query": "What is the maximum permissible storage temperature for Class 3 flammable liquids?",
        "expected_document": "hazardous_material_containment_guide.txt",
        "relevant_keywords": ["38 degrees celsius", "spark-proof"],
        "ground_truth_answer": "Class 3 flammable liquids must be stored at temperatures below 38 degrees Celsius in secondary containment.",
        "is_abstention_case": False
    },

    # Multi-Hop / Compound Inquiries
    {
        "id": "BENCH-021",
        "domain": "technical_maintenance",
        "difficulty": "multi_hop",
        "query": "If DG-5000 oil pressure drops below 30 PSI, what happens and what should be inspected weekly on the governor?",
        "expected_document": "diesel_generator_maint_sop.txt",
        "relevant_keywords": ["emergency shutdown in 5 seconds", "relief valve weekly", "2500 and 3000 psi"],
        "ground_truth_answer": "The automated emergency shutdown trip triggers in 5 seconds, and the high-pressure relief valve on the governor must be inspected weekly.",
        "is_abstention_case": False
    },
    {
        "id": "BENCH-022",
        "domain": "defensive_cybersecurity",
        "difficulty": "multi_hop",
        "query": "What physical hardware modifications are required on air-gapped terminals and which industrial port is blocked?",
        "expected_document": "airgap_workstation_hardening.txt",
        "relevant_keywords": ["wireless", "bluetooth", "camera", "port 502"],
        "ground_truth_answer": "Wireless controllers, Bluetooth interfaces, and cameras must be physically removed or BIOS-disabled, and Modbus port 502 must be blocked.",
        "is_abstention_case": False
    },

    # Out-of-Domain Abstention Cases (NEXUS MUST Abstain)
    {
        "id": "BENCH-023",
        "domain": "all",
        "difficulty": "out_of_domain",
        "query": "What is the authentic recipe for baking chocolate chip cookies?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    },
    {
        "id": "BENCH-024",
        "domain": "all",
        "difficulty": "out_of_domain",
        "query": "Which country won the 1994 football world cup?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    },
    {
        "id": "BENCH-025",
        "domain": "all",
        "difficulty": "out_of_domain",
        "query": "How do I invest in stock market options contracts?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    },
    {
        "id": "BENCH-026",
        "domain": "all",
        "difficulty": "out_of_domain",
        "query": "What is the plot summary of the latest Hollywood blockbuster movie?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    },
    {
        "id": "BENCH-027",
        "domain": "all",
        "difficulty": "out_of_domain",
        "query": "What are the tourist visa requirements for traveling to Australia?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    },
    {
        "id": "BENCH-028",
        "domain": "safety_emergency",
        "difficulty": "out_of_domain",
        "query": "What are the safe handling procedures for enriched weapons-grade uranium?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    },
    {
        "id": "BENCH-029",
        "domain": "training_education",
        "difficulty": "out_of_domain",
        "query": "What is the syllabus for kindergarten finger painting class?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    },
    {
        "id": "BENCH-030",
        "domain": "defensive_cybersecurity",
        "difficulty": "out_of_domain",
        "query": "How can I launch a distributed denial of service attack on a banking web server?",
        "expected_document": None,
        "relevant_keywords": [],
        "ground_truth_answer": "The authorized repository does not contain sufficient verified information to answer this inquiry.",
        "is_abstention_case": True
    }
]


def get_benchmark_cases() -> List[Dict[str, Any]]:
    """Retrieve full suite of 30 benchmark evaluation cases."""
    return BENCHMARK_CASES


def get_seed_documents() -> List[Dict[str, Any]]:
    """Retrieve all 6 curated seed documents."""
    return SEED_DOCUMENTS
