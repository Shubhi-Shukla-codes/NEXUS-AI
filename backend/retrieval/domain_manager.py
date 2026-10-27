"""
NEXUS Domain Modules & Taxonomy Engine
Defines specialized metadata schemas, taxonomy dictionaries, and query scoping
for the 6 core institutional knowledge pillars.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainProfile:
    """Specification of an institutional domain pillar."""
    id: str
    display_name: str
    description: str
    badge_color: str
    taxonomy_keywords: tuple
    metadata_fields: tuple


DOMAIN_PROFILES: Dict[str, DomainProfile] = {
    "technical_maintenance": DomainProfile(
        id="technical_maintenance",
        display_name="Technical & Equipment Maintenance",
        description="Preventive maintenance, component repair, schematic interpretation, and diagnostics.",
        badge_color="#4E6B50",
        taxonomy_keywords=(
            "schematic", "circuit", "valve", "hydraulic", "pressure", "torque",
            "wiring", "lubricant", "turbine", "alternator", "breaker", "multimeter",
            "calibration", "tolerance", "overhaul", "b-12", "diesel", "generator"
        ),
        metadata_fields=("equipment_type", "model_number", "maintenance_level", "criticality")
    ),
    "training_education": DomainProfile(
        id="training_education",
        display_name="Training & Education",
        description="Standard operating procedures, course curricula, practical drills, and technical qualifications.",
        badge_color="#3E5C76",
        taxonomy_keywords=(
            "curriculum", "syllabus", "module", "lesson", "objective", "prerequisite",
            "assessment", "rubric", "practical", "certification", "qualification",
            "instructor", "trainee", "evaluation", "standard-operating-procedure"
        ),
        metadata_fields=("target_audience", "skill_level", "estimated_hours")
    ),
    "safety_emergency": DomainProfile(
        id="safety_emergency",
        display_name="Safety & Emergency Response",
        description="Hazard avoidance, chemical exposure, PPE guidelines, triage, and evacuation protocols.",
        badge_color="#C05621",
        taxonomy_keywords=(
            "evacuation", "hazard", "fire", "extinguisher", "ppe", "sds", "chemical",
            "spill", "first-aid", "triage", "decontamination", "toxic", "antidote",
            "respirator", "eye-wash", "exposure", "burn-treatment", "emergency"
        ),
        metadata_fields=("hazard_class", "ppe_rating", "response_level")
    ),
    "defensive_cybersecurity": DomainProfile(
        id="defensive_cybersecurity",
        display_name="Defensive Cybersecurity",
        description="Secure system configuration, vulnerability mitigation, defensive monitoring, and incident containment.",
        badge_color="#2B6CB0",
        taxonomy_keywords=(
            "firewall", "encryption", "intrusion", "zero-trust", "vulnerability",
            "patch", "audit", "hash", "cipher", "endpoint", "access-control",
            "isolation", "syslog", "air-gap", "incident-response", "hardening"
        ),
        metadata_fields=("framework", "security_tier", "asset_category")
    ),
    "humanitarian_geospatial": DomainProfile(
        id="humanitarian_geospatial",
        display_name="Humanitarian & Geospatial",
        description="Disaster preparedness, logistics supply chains, shelter management, and field coordination.",
        badge_color="#2C7A7B",
        taxonomy_keywords=(
            "shelter", "logistics", "water-supply", "relief", "ration", "hospital",
            "coordinates", "elevation", "waypoint", "convoy", "clinic", "dispensary",
            "displaced-persons", "supply-route", "aid-distribution"
        ),
        metadata_fields=("geographic_region", "logistics_status", "resource_type")
    ),
    "hazard_environmental": DomainProfile(
        id="hazard_environmental",
        display_name="Hazardous Material & Environment",
        description="Safe containment, SDS technical interpretation, environmental spill response, and neutralization.",
        badge_color="#7B341E",
        taxonomy_keywords=(
            "un-number", "containment", "absorption", "disposal", "neutralizer",
            "runoff", "biodegradable", "barrier", "toxic-release", "corrosive",
            "flammable", "oxidizer", "neutralization", "secondary-containment"
        ),
        metadata_fields=("un_number", "storage_temperature", "neutralizer_agent")
    )
}


def get_domain_profile(domain_id: str) -> Optional[DomainProfile]:
    """Retrieve the domain profile by its canonical identifier."""
    return DOMAIN_PROFILES.get(domain_id)


def list_domain_profiles() -> List[DomainProfile]:
    """Return all active institutional domain profiles."""
    return list(DOMAIN_PROFILES.values())


def match_domain_by_query(query: str) -> Optional[str]:
    """
    Heuristically identify the most relevant domain based on query terms
    matching domain taxonomy keywords.
    """
    clean_query = query.lower()
    best_domain = None
    max_hits = 0

    for domain_id, profile in DOMAIN_PROFILES.items():
        hits = sum(1 for kw in profile.taxonomy_keywords if kw in clean_query)
        if hits > max_hits:
            max_hits = hits
            best_domain = domain_id

    return best_domain if max_hits > 0 else None
