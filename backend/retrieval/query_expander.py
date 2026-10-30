"""
NEXUS Query Expansion & Acronym Normalization Engine
Resolves common acronyms, state abbreviations, colloquial terminology,
and military/technical codes to bridge the semantic gap between operator queries
and formal document text.
"""

import re
from typing import Dict, List, Tuple

# Comprehensive dictionary of state & UT abbreviations, capitals, and administrative terms
DOMAIN_ACRONYMS: Dict[str, str] = {
    # Indian States & UT Abbreviations
    "up": "Uttar Pradesh",
    "u.p.": "Uttar Pradesh",
    "mp": "Madhya Pradesh",
    "m.p.": "Madhya Pradesh",
    "ap": "Andhra Pradesh",
    "a.p.": "Andhra Pradesh",
    "hp": "Himachal Pradesh",
    "h.p.": "Himachal Pradesh",
    "tn": "Tamil Nadu",
    "t.n.": "Tamil Nadu",
    "wb": "West Bengal",
    "w.b.": "West Bengal",
    "mh": "Maharashtra",
    "rj": "Rajasthan",
    "gj": "Gujarat",
    "ka": "Karnataka",
    "kl": "Kerala",
    "pb": "Punjab",
    "hr": "Haryana",
    "uk": "Uttarakhand",
    "ua": "Uttarakhand",
    "jk": "Jammu and Kashmir",
    "j&k": "Jammu and Kashmir",
    "j & k": "Jammu and Kashmir",
    "dl": "Delhi",
    "nct": "National Capital Territory of Delhi",
    "ch": "Chandigarh",
    "py": "Puducherry",
    "ar": "Arunachal Pradesh",
    "br": "Bihar",
    "cg": "Chhattisgarh",
    "ga": "Goa",
    "jh": "Jharkhand",
    "mn": "Manipur",
    "ml": "Meghalaya",
    "mz": "Mizoram",
    "nl": "Nagaland",
    "od": "Odisha",
    "sk": "Sikkim",
    "tg": "Telangana",
    "ts": "Telangana",
    "tr": "Tripura",
    "a&n": "Andaman and Nicobar Islands",
    "a & n": "Andaman and Nicobar Islands",
    "la": "Ladakh",
    "ld": "Lakshadweep",

    # Common Technical & Operational Acronyms
    "ut": "Union Territory",
    "uts": "Union Territories",
    "sds": "Safety Data Sheet",
    "sop": "Standard Operating Procedure",
    "ppe": "Personal Protective Equipment",
    "mil-std": "Military Standard",
    "sq km": "square kilometers",
    "km2": "square kilometers",
    "pop": "population",
}


def expand_query(query: str) -> Tuple[str, List[str]]:
    """
    Detect acronyms and colloquial terms in query and expand them.
    Returns:
      (expanded_query_string, list_of_applied_expansions)
    
    Example:
      'capital of up' -> ('capital of up (Uttar Pradesh)', ['up -> Uttar Pradesh'])
    """
    clean_q = query.strip()
    if not clean_q:
        return clean_q, []

    # Tokenize preserving word boundaries and punctuation like & or .
    words = re.findall(r'\b[a-zA-Z0-9.&]+\b', clean_q)
    applied_expansions = []
    expansions_text = []

    lower_query = f" {clean_q.lower()} "

    # Check multi-word or punctuation patterns first (e.g. 'j&k', 'u.p.')
    for acronym, expansion in DOMAIN_ACRONYMS.items():
        pattern = r'(?i)\b' + re.escape(acronym) + r'\b'
        if re.search(pattern, clean_q):
            # Only add if the full expansion is not already explicitly in query
            if expansion.lower() not in lower_query:
                applied_expansions.append(f"{acronym.upper()} -> {expansion}")
                expansions_text.append(expansion)

    if not expansions_text:
        return clean_q, []

    # Create hybrid expanded query
    expanded = f"{clean_q} ({', '.join(expansions_text)})"
    return expanded, applied_expansions
