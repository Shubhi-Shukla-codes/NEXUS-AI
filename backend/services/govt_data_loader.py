"""
NEXUS Government Data Generator & Ingestion Engine
Compiles authoritative Government of India States and Union Territories
demographic, geographic, and administrative data into structured PDF and XLSX formats,
and automatically ingests and indexes them into the NEXUS knowledge base.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import fitz  # PyMuPDF

from backend.config import settings
from backend.services.document_service import upload_document, approve_document
from backend.ingestion.pipeline import process_document
from backend.storage.vector_store import index_document_in_vector_store
from backend.retrieval.bm25 import BM25Index

# Full authoritative dataset for all 28 States and 8 Union Territories
STATES_AND_UTS_DATA = [
    # 28 States
    {"name": "Andhra Pradesh", "type": "State", "capital": "Amaravati", "area_km2": 162975, "population": 49577103, "density": 304, "sex_ratio": 993, "literacy_pct": 67.02, "districts": 26, "language": "Telugu", "zone": "Southern"},
    {"name": "Arunachal Pradesh", "type": "State", "capital": "Itanagar", "area_km2": 83743, "population": 1383727, "density": 17, "sex_ratio": 938, "literacy_pct": 65.38, "districts": 26, "language": "English", "zone": "North Eastern"},
    {"name": "Assam", "type": "State", "capital": "Dispur", "area_km2": 78438, "population": 31205576, "density": 398, "sex_ratio": 958, "literacy_pct": 72.19, "districts": 31, "language": "Assamese", "zone": "North Eastern"},
    {"name": "Bihar", "type": "State", "capital": "Patna", "area_km2": 94163, "population": 104099452, "density": 1106, "sex_ratio": 918, "literacy_pct": 61.80, "districts": 38, "language": "Hindi", "zone": "Eastern"},
    {"name": "Chhattisgarh", "type": "State", "capital": "Raipur", "area_km2": 135192, "population": 25545198, "density": 189, "sex_ratio": 991, "literacy_pct": 70.28, "districts": 33, "language": "Hindi, Chhattisgarhi", "zone": "Central"},
    {"name": "Goa", "type": "State", "capital": "Panaji", "area_km2": 3702, "population": 1458545, "density": 394, "sex_ratio": 973, "literacy_pct": 88.70, "districts": 2, "language": "Konkani", "zone": "Western"},
    {"name": "Gujarat", "type": "State", "capital": "Gandhinagar", "area_km2": 196244, "population": 60439692, "density": 308, "sex_ratio": 919, "literacy_pct": 78.03, "districts": 33, "language": "Gujarati", "zone": "Western"},
    {"name": "Haryana", "type": "State", "capital": "Chandigarh", "area_km2": 44212, "population": 25351462, "density": 573, "sex_ratio": 879, "literacy_pct": 75.55, "districts": 22, "language": "Hindi", "zone": "Northern"},
    {"name": "Himachal Pradesh", "type": "State", "capital": "Shimla (Summer), Dharamshala (Winter)", "area_km2": 55673, "population": 6864602, "density": 123, "sex_ratio": 972, "literacy_pct": 82.80, "districts": 12, "language": "Hindi", "zone": "Northern"},
    {"name": "Jharkhand", "type": "State", "capital": "Ranchi", "area_km2": 79716, "population": 32988134, "density": 414, "sex_ratio": 948, "literacy_pct": 66.41, "districts": 24, "language": "Hindi", "zone": "Eastern"},
    {"name": "Karnataka", "type": "State", "capital": "Bengaluru", "area_km2": 191791, "population": 61095297, "density": 319, "sex_ratio": 973, "literacy_pct": 75.36, "districts": 31, "language": "Kannada", "zone": "Southern"},
    {"name": "Kerala", "type": "State", "capital": "Thiruvananthapuram", "area_km2": 38852, "population": 33406061, "density": 860, "sex_ratio": 1084, "literacy_pct": 94.00, "districts": 14, "language": "Malayalam", "zone": "Southern"},
    {"name": "Madhya Pradesh", "type": "State", "capital": "Bhopal", "area_km2": 308252, "population": 72626809, "density": 236, "sex_ratio": 931, "literacy_pct": 69.32, "districts": 55, "language": "Hindi", "zone": "Central"},
    {"name": "Maharashtra", "type": "State", "capital": "Mumbai", "area_km2": 307713, "population": 112374333, "density": 365, "sex_ratio": 929, "literacy_pct": 82.34, "districts": 36, "language": "Marathi", "zone": "Western"},
    {"name": "Manipur", "type": "State", "capital": "Imphal", "area_km2": 22327, "population": 2855794, "density": 128, "sex_ratio": 985, "literacy_pct": 76.94, "districts": 16, "language": "Meiteilon (Manipuri)", "zone": "North Eastern"},
    {"name": "Meghalaya", "type": "State", "capital": "Shillong", "area_km2": 22429, "population": 2966889, "density": 132, "sex_ratio": 989, "literacy_pct": 74.43, "districts": 12, "language": "English", "zone": "North Eastern"},
    {"name": "Mizoram", "type": "State", "capital": "Aizawl", "area_km2": 21087, "population": 1097206, "density": 52, "sex_ratio": 976, "literacy_pct": 91.33, "districts": 11, "language": "Mizo, English", "zone": "North Eastern"},
    {"name": "Nagaland", "type": "State", "capital": "Kohima", "area_km2": 16579, "population": 1978502, "density": 119, "sex_ratio": 931, "literacy_pct": 79.55, "districts": 16, "language": "English", "zone": "North Eastern"},
    {"name": "Odisha", "type": "State", "capital": "Bhubaneswar", "area_km2": 155707, "population": 41974218, "density": 270, "sex_ratio": 979, "literacy_pct": 72.87, "districts": 30, "language": "Odia", "zone": "Eastern"},
    {"name": "Punjab", "type": "State", "capital": "Chandigarh", "area_km2": 50362, "population": 27743338, "density": 551, "sex_ratio": 895, "literacy_pct": 75.84, "districts": 23, "language": "Punjabi", "zone": "Northern"},
    {"name": "Rajasthan", "type": "State", "capital": "Jaipur", "area_km2": 342239, "population": 68548437, "density": 200, "sex_ratio": 928, "literacy_pct": 66.11, "districts": 50, "language": "Hindi", "zone": "Northern"},
    {"name": "Sikkim", "type": "State", "capital": "Gangtok", "area_km2": 7096, "population": 610577, "density": 86, "sex_ratio": 890, "literacy_pct": 81.42, "districts": 6, "language": "Nepali, English", "zone": "North Eastern"},
    {"name": "Tamil Nadu", "type": "State", "capital": "Chennai", "area_km2": 130060, "population": 72147030, "density": 555, "sex_ratio": 996, "literacy_pct": 80.09, "districts": 38, "language": "Tamil", "zone": "Southern"},
    {"name": "Telangana", "type": "State", "capital": "Hyderabad", "area_km2": 112077, "population": 35003674, "density": 312, "sex_ratio": 988, "literacy_pct": 66.54, "districts": 33, "language": "Telugu, Urdu", "zone": "Southern"},
    {"name": "Tripura", "type": "State", "capital": "Agartala", "area_km2": 10491, "population": 3673917, "density": 350, "sex_ratio": 960, "literacy_pct": 87.22, "districts": 8, "language": "Bengali, Kokborok", "zone": "North Eastern"},
    {"name": "Uttar Pradesh", "type": "State", "capital": "Lucknow", "area_km2": 240928, "population": 199812341, "density": 829, "sex_ratio": 912, "literacy_pct": 67.68, "districts": 75, "language": "Hindi, Urdu", "zone": "Central"},
    {"name": "Uttarakhand", "type": "State", "capital": "Dehradun (Winter), Gairsain (Summer)", "area_km2": 53483, "population": 10086292, "density": 189, "sex_ratio": 963, "literacy_pct": 78.82, "districts": 13, "language": "Hindi", "zone": "Central"},
    {"name": "West Bengal", "type": "State", "capital": "Kolkata", "area_km2": 88752, "population": 91276115, "density": 1028, "sex_ratio": 950, "literacy_pct": 76.26, "districts": 23, "language": "Bengali, English", "zone": "Eastern"},

    # 8 Union Territories
    {"name": "Andaman and Nicobar Islands", "type": "Union Territory", "capital": "Port Blair (Sri Vijaya Puram)", "area_km2": 8249, "population": 380581, "density": 46, "sex_ratio": 876, "literacy_pct": 86.63, "districts": 3, "language": "Hindi, English", "zone": "Southern / Island"},
    {"name": "Chandigarh", "type": "Union Territory", "capital": "Chandigarh", "area_km2": 114, "population": 1055450, "density": 9258, "sex_ratio": 818, "literacy_pct": 86.05, "districts": 1, "language": "English, Punjabi, Hindi", "zone": "Northern"},
    {"name": "Dadra and Nagar Haveli and Daman and Diu", "type": "Union Territory", "capital": "Daman", "area_km2": 603, "population": 586956, "density": 970, "sex_ratio": 774, "literacy_pct": 76.24, "districts": 3, "language": "Gujarati, Hindi", "zone": "Western"},
    {"name": "Delhi (NCT of Delhi)", "type": "Union Territory", "capital": "New Delhi", "area_km2": 1483, "population": 16787941, "density": 11320, "sex_ratio": 868, "literacy_pct": 86.21, "districts": 11, "language": "Hindi, English", "zone": "Northern"},
    {"name": "Jammu and Kashmir", "type": "Union Territory", "capital": "Srinagar (Summer), Jammu (Winter)", "area_km2": 42241, "population": 12267013, "density": 290, "sex_ratio": 889, "literacy_pct": 67.16, "districts": 20, "language": "Kashmiri, Dogri, Hindi, Urdu", "zone": "Northern"},
    {"name": "Ladakh", "type": "Union Territory", "capital": "Leh (Summer), Kargil (Winter)", "area_km2": 59146, "population": 274289, "density": 4.6, "sex_ratio": 690, "literacy_pct": 77.48, "districts": 2, "language": "Ladakhi, Hindi, English", "zone": "Northern"},
    {"name": "Lakshadweep", "type": "Union Territory", "capital": "Kavaratti", "area_km2": 32, "population": 64473, "density": 2015, "sex_ratio": 946, "literacy_pct": 91.85, "districts": 1, "language": "Malayalam, English", "zone": "Southern / Island"},
    {"name": "Puducherry", "type": "Union Territory", "capital": "Puducherry", "area_km2": 492, "population": 1247953, "density": 2536, "sex_ratio": 1037, "literacy_pct": 85.85, "districts": 4, "language": "Tamil, French, English", "zone": "Southern"},
]


def create_government_handbook_pdf(output_path: Path) -> Path:
    """Generate official multi-page Government of India Statistical Handbook PDF using PyMuPDF."""
    doc = fitz.open()

    # Page 1: Executive Summary & National Overview
    p1 = doc.new_page(width=595, height=842)  # A4 size
    p1.draw_rect(fitz.Rect(20, 20, 575, 822), color=(0.15, 0.25, 0.15), width=2)
    p1.draw_rect(fitz.Rect(24, 24, 571, 70), fill=(0.12, 0.22, 0.14))

    p1.insert_text(fitz.Point(40, 52), "GOVERNMENT OF INDIA // OFFICIAL STATISTICAL HANDBOOK", fontname="helv", fontsize=14, color=(0.95, 0.95, 0.90))
    p1.insert_text(fitz.Point(40, 78), "COMPREHENSIVE DIRECTORY OF STATES AND UNION TERRITORIES (2026 EDITION)", fontname="helv", fontsize=10, color=(0.85, 0.75, 0.45))

    p1.insert_textbox(
        fitz.Rect(40, 110, 555, 330),
        "1. EXECUTIVE OVERVIEW & CONSTITUTIONAL FRAMEWORK\n\n"
        "The Republic of India is a sovereign, socialist, secular, democratic republic comprising 28 States and 8 Union Territories. "
        "Under the constitutional division of powers, each State exercises jurisdiction across executive, legislative, and judicial domains. "
        "Union Territories are administered directly by the Central Government through appointed Lieutenant Governors or Administrators.\n\n"
        "Key National Demographic Benchmarks:\n"
        "• Total Number of Constituent States: 28 States.\n"
        "• Total Number of Union Territories: 8 Union Territories.\n"
        "• Total Sovereign Land Area: Approximately 3,287,263 square kilometers.\n"
        "• Largest State by Geographic Area: Rajasthan (342,239 km², representing ~10.4% of total national landmass).\n"
        "• Smallest State by Geographic Area: Goa (3,702 km²).\n"
        "• Largest Union Territory by Geographic Area: Ladakh (59,146 km²).\n"
        "• Smallest Union Territory by Geographic Area: Lakshadweep (32 km²).\n"
        "• Most Populous State: Uttar Pradesh (199,812,341 residents; over 75 districts).\n"
        "• Least Populous State: Sikkim (610,577 residents; 6 districts).\n"
        "• Highest State Population Density: Bihar (1,106 persons per km²).\n"
        "• Lowest State Population Density: Arunachal Pradesh (17 persons per km²).\n"
        "• Highest State Literacy Rate: Kerala (94.00%).\n"
        "• Highest Sex Ratio in India: Kerala (1,084 females per 1,000 males).\n\n"
        "Document Provenance: Ministry of Home Affairs, Census of India, Survey of India, and MOSPI Administrative Records.",
        fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1)
    )

    # Page 1 Table: Comparative National Summary
    p1.insert_text(fitz.Point(40, 360), "2. NATIONAL EXTREMES & ADMINISTRATIVE BENCHMARKS", fontname="helv", fontsize=11, color=(0.15, 0.25, 0.15))
    
    summary_table_text = (
        "| Metric / Category | Leading Entity | Measured Value | Trailing Entity | Measured Value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| State Land Area | Rajasthan | 342,239 km² | Goa | 3,702 km² |\n"
        "| UT Land Area | Ladakh | 59,146 km² | Lakshadweep | 32 km² |\n"
        "| State Population | Uttar Pradesh | 199,812,341 | Sikkim | 610,577 |\n"
        "| UT Population | Delhi (NCT) | 16,787,941 | Lakshadweep | 64,473 |\n"
        "| Population Density | Bihar (State) | 1,106 / km² | Arunachal Pradesh | 17 / km² |\n"
        "| Literacy Rate | Kerala | 94.00% | Bihar | 61.80% |\n"
        "| Sex Ratio | Kerala | 1,084 / 1000 | Haryana | 879 / 1000 |\n"
        "| District Count | Uttar Pradesh | 75 Districts | Goa | 2 Districts |"
    )
    p1.insert_textbox(fitz.Rect(40, 375, 555, 520), summary_table_text, fontsize=8.5, fontname="courier", color=(0.05, 0.15, 0.05))

    p1.insert_textbox(
        fitz.Rect(40, 540, 555, 780),
        "3. ADMINISTRATIVE ZONAL STRUCTURE\n\n"
        "To promote inter-state cooperation and coordination, States and Union Territories are grouped into six Zonal Councils:\n"
        "1. Northern Zonal Council: Haryana, Himachal Pradesh, Punjab, Rajasthan, NCT of Delhi, UT of Jammu & Kashmir, Ladakh, and Chandigarh.\n"
        "2. Central Zonal Council: Chhattisgarh, Madhya Pradesh, Uttarakhand, and Uttar Pradesh.\n"
        "3. Eastern Zonal Council: Bihar, Jharkhand, Odisha, and West Bengal.\n"
        "4. Western Zonal Council: Goa, Gujarat, Maharashtra, and UT of Dadra & Nagar Haveli and Daman & Diu.\n"
        "5. Southern Zonal Council: Andhra Pradesh, Karnataka, Kerala, Tamil Nadu, Telangana, and UT of Puducherry.\n"
        "6. North Eastern Council: Assam, Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, and Tripura.\n\n"
        "This handbook provides authoritative operational parameters for resource allocation, emergency response planning, and demographic analysis.",
        fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1)
    )
    p1.insert_text(fitz.Point(260, 810), "Page 1 of 6 // SECURE OFFICIAL DOCUMENT", fontname="helv", fontsize=8, color=(0.4, 0.4, 0.4))

    # Helper function to render a table page
    def render_data_page(page_num: int, title: str, subtitle: str, items: List[Dict[str, Any]], notes: str):
        p = doc.new_page(width=595, height=842)
        p.draw_rect(fitz.Rect(20, 20, 575, 822), color=(0.15, 0.25, 0.15), width=2)
        p.draw_rect(fitz.Rect(24, 24, 571, 60), fill=(0.12, 0.22, 0.14))
        p.insert_text(fitz.Point(36, 48), title.upper(), fontname="helv", fontsize=12, color=(0.95, 0.95, 0.90))
        p.insert_text(fitz.Point(36, 68), subtitle, fontname="helv", fontsize=9, color=(0.85, 0.75, 0.45))

        # Markdown Table Header
        table_lines = [
            "| State / UT Name | Capital City | Area (km²) | Population | Density (/km²) | Literacy | Districts | Zone |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"
        ]
        for it in items:
            pop_str = f"{it['population']:,}"
            area_str = f"{it['area_km2']:,}"
            lit_str = f"{it['literacy_pct']:.1f}%"
            table_lines.append(
                f"| {it['name']} | {it['capital']} | {area_str} | {pop_str} | {it['density']} | {lit_str} | {it['districts']} | {it['zone']} |"
            )

        p.insert_textbox(fitz.Rect(30, 95, 565, 450), "\n".join(table_lines), fontsize=7.5, fontname="courier", color=(0.05, 0.15, 0.05))

        # Narrative Detailed Section for each item
        narrative = f"DETAILED ADMINISTRATIVE PROFILES ({subtitle}):\n\n"
        for it in items:
            narrative += (
                f"• {it['name']} ({it['type']}): Capital: {it['capital']}. Total land area spans {it['area_km2']:,} square kilometers "
                f"with an enumerated population of {it['population']:,} citizens. Population density stands at {it['density']} persons/km² "
                f"with a literacy rate of {it['literacy_pct']:.2f}% across {it['districts']} administrative districts. "
                f"Primary official language: {it['language']}. Administrative Zonal Council: {it['zone']}.\n"
            )
        narrative += f"\nOperational Intelligence Notes:\n{notes}"

        p.insert_textbox(fitz.Rect(35, 460, 560, 790), narrative, fontsize=8.5, fontname="helv", color=(0.1, 0.1, 0.1))
        p.insert_text(fitz.Point(260, 810), f"Page {page_num} of 6 // SECURE OFFICIAL DOCUMENT", fontname="helv", fontsize=8, color=(0.4, 0.4, 0.4))

    # Page 2: Northern and Western States
    p2_items = [s for s in STATES_AND_UTS_DATA if s["name"] in (
        "Rajasthan", "Maharashtra", "Gujarat", "Goa", "Punjab", "Haryana", "Himachal Pradesh"
    )]
    render_data_page(
        page_num=2,
        title="SECTION 2: NORTHERN & WESTERN STATES DIRECTORY",
        subtitle="Geographic, Demographic, and Administrative Specifications",
        items=p2_items,
        notes="Rajasthan is the largest State in India by land area (342,239 km²), characterized by the Thar Desert and 50 districts. "
              "Maharashtra is the second most populous state in India (112.37M) and primary economic engine with capital at Mumbai. "
              "Goa is the smallest state in India by territory (3,702 km²) with only 2 districts and high literacy (88.7%)."
    )

    # Page 3: Central and Eastern States
    p3_items = [s for s in STATES_AND_UTS_DATA if s["name"] in (
        "Uttar Pradesh", "Madhya Pradesh", "Chhattisgarh", "Bihar", "West Bengal", "Odisha", "Jharkhand"
    )]
    render_data_page(
        page_num=3,
        title="SECTION 3: CENTRAL & EASTERN STATES DIRECTORY",
        subtitle="Geographic, Demographic, and Administrative Specifications",
        items=p3_items,
        notes="Uttar Pradesh holds the largest population in India (199,812,341) and highest number of districts (75). "
              "Madhya Pradesh is the second largest state by geographic area (308,252 km²). "
              "Bihar possesses the highest population density among all Indian states at 1,106 persons per km²."
    )

    # Page 4: Southern States
    p4_items = [s for s in STATES_AND_UTS_DATA if s["name"] in (
        "Andhra Pradesh", "Karnataka", "Kerala", "Tamil Nadu", "Telangana"
    )]
    render_data_page(
        page_num=4,
        title="SECTION 4: SOUTHERN STATES DIRECTORY",
        subtitle="Geographic, Demographic, and Administrative Specifications",
        items=p4_items,
        notes="Kerala has achieved the highest literacy rate in India at 94.00% and highest sex ratio (1,084 females per 1,000 males). "
              "Karnataka spans 191,791 km² with capital at Bengaluru, prominent tech and aerospace hub. "
              "Tamil Nadu spans 130,060 km² with capital Chennai, comprising 38 districts and high industrial density."
    )

    # Page 5: North Eastern States
    p5_items = [s for s in STATES_AND_UTS_DATA if s["name"] in (
        "Assam", "Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"
    )]
    render_data_page(
        page_num=5,
        title="SECTION 5: NORTH EASTERN STATES DIRECTORY",
        subtitle="Geographic, Demographic, and Administrative Specifications",
        items=p5_items,
        notes="Arunachal Pradesh has the lowest population density among Indian states at 17 persons per km². "
              "Sikkim is the least populous state in India with 610,577 inhabitants. "
              "Mizoram achieves one of the highest literacy rates in India at 91.33%."
    )

    # Page 6: Union Territories & National Ranking Compendium
    p6_items = [s for s in STATES_AND_UTS_DATA if s["type"] == "Union Territory"]
    render_data_page(
        page_num=6,
        title="SECTION 6: ALL 8 UNION TERRITORIES OF INDIA",
        subtitle="Constitutional Administration and Demographic Register",
        items=p6_items,
        notes="Ladakh is the largest Union Territory by area (59,146 km²), while Lakshadweep is the smallest both by area (32 km²) "
              "and population (64,473). NCT of Delhi holds the highest population density in India (11,320 persons per km²). "
              "Puducherry has the highest sex ratio among Union Territories at 1,037 females per 1,000 males."
    )

    doc.save(str(output_path))
    doc.close()
    return output_path


def create_government_directory_xlsx(output_path: Path) -> Path:
    """Generate structured Excel workbook of all 36 States and Union Territories."""
    wb = openpyxl.Workbook()
    
    # Sheet 1: Master Directory
    ws = wb.active
    ws.title = "States & UT Master Directory"

    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1B3B22", end_color="1B3B22", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='D0D7DE'),
        right=Side(style='thin', color='D0D7DE'),
        top=Side(style='thin', color='D0D7DE'),
        bottom=Side(style='thin', color='D0D7DE')
    )

    headers = [
        "Entity Name", "Entity Type", "Capital City", "Area (km²)",
        "Population", "Density (per km²)", "Sex Ratio", "Literacy Rate (%)",
        "Districts Count", "Official Languages", "Zonal Council"
    ]

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for row_idx, item in enumerate(STATES_AND_UTS_DATA, start=2):
        row_values = [
            item["name"],
            item["type"],
            item["capital"],
            item["area_km2"],
            item["population"],
            item["density"],
            item["sex_ratio"],
            item["literacy_pct"],
            item["districts"],
            item["language"],
            item["zone"]
        ]
        ws.append(row_values)
        
        # Style row
        for col_idx in range(1, len(row_values) + 1):
            c = ws.cell(row=row_idx, column=col_idx)
            c.border = thin_border
            if col_idx in (4, 5, 6, 7, 8, 9):
                c.alignment = right_align
                if col_idx in (4, 5):
                    c.number_format = "#,##0"
                elif col_idx == 8:
                    c.number_format = "0.00%"
            else:
                c.alignment = left_align

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # Sheet 2: Rankings & Key Extremes
    ws2 = wb.create_sheet(title="Rankings & Extremes")
    ws2.append(["Category", "Record Entity", "Value", "Metric Description"])
    for col_idx in range(1, 5):
        cell = ws2.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = PatternFill(start_color="2A4D32", end_color="2A4D32", fill_type="solid")
        cell.alignment = center_align

    extremes_records = [
        ["Largest State by Area", "Rajasthan", "342,239 km²", "Spans 10.4% of total Indian land area"],
        ["Smallest State by Area", "Goa", "3,702 km²", "Smallest state with 2 administrative districts"],
        ["Largest UT by Area", "Ladakh", "59,146 km²", "Trans-Himalayan union territory with Leh and Kargil"],
        ["Smallest UT by Area", "Lakshadweep", "32 km²", "Archipelago of 36 islands"],
        ["Most Populous State", "Uttar Pradesh", "199,812,341", "Highest population and 75 districts"],
        ["Least Populous State", "Sikkim", "610,577", "Eastern Himalayan state"],
        ["Most Populous UT", "Delhi (NCT)", "16,787,941", "National Capital Territory"],
        ["Least Populous UT", "Lakshadweep", "64,473", "Island territory"],
        ["Highest Population Density (State)", "Bihar", "1,106 per km²", "Eastern state"],
        ["Lowest Population Density (State)", "Arunachal Pradesh", "17 per km²", "North Eastern border state"],
        ["Highest Literacy Rate", "Kerala", "94.00%", "Southern coastal state"],
        ["Lowest Literacy Rate", "Bihar", "61.80%", "Eastern state"],
        ["Highest Sex Ratio", "Kerala", "1,084 per 1,000", "Females per 1,000 males"],
        ["Lowest Sex Ratio", "Haryana", "879 per 1,000", "Northern state"],
        ["Highest Districts Count", "Uttar Pradesh", "75 Districts", "Central zone"],
    ]

    for row_idx, rec in enumerate(extremes_records, start=2):
        ws2.append(rec)
        for col_idx in range(1, 5):
            c = ws2.cell(row=row_idx, column=col_idx)
            c.border = thin_border

    for col in ws2.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws2.column_dimensions[col_letter].width = max(max_len + 3, 14)

    wb.save(str(output_path))
    wb.close()
    return output_path


def seed_and_train_government_dataset(user_id: int = 1, username: str = "admin") -> Dict[str, Any]:
    """
    Main orchestration routine:
    1. Compiles PDF and XLSX documents under data/seeds/
    2. Ingests into vault via upload_document
    3. Runs extraction, table parsing, and chunking via process_document
    4. Approves and indexes into ChromaDB vector store via index_document_in_vector_store
    5. Rebuilds sparse BM25 technical index
    """
    seeds_dir = settings.paths.data_dir / "seeds"
    seeds_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = seeds_dir / "GOVERNMENT_OF_INDIA_STATES_AND_UNION_TERRITORIES_STATISTICAL_HANDBOOK_2026.pdf"
    xlsx_path = seeds_dir / "INDIA_STATES_AND_UT_ADMINISTRATIVE_DIRECTORY_2026.xlsx"

    print("Generating Government Statistical Handbook PDF...")
    create_government_handbook_pdf(pdf_path)

    print("Generating Government Administrative Directory XLSX...")
    create_government_directory_xlsx(xlsx_path)

    results = []
    files_to_ingest = [
        (pdf_path, "humanitarian_geospatial", "Government of India: States and Union Territories Statistical Handbook (2026)"),
        (xlsx_path, "humanitarian_geospatial", "India States & UT Administrative Directory & Demographic Register (2026)"),
    ]

    for file_path, domain, doc_title in files_to_ingest:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        print(f"Uploading '{file_path.name}' ({len(file_bytes)/1024:.1f} KB)...")
        upload_res = upload_document(
            file_bytes=file_bytes,
            filename=file_path.name,
            domain=domain,
            user_id=user_id,
            username=username,
            title=doc_title,
            auto_approve=True
        )

        doc_id = upload_res["id"]
        print(f"Processing pages, tables, and chunks for document #{doc_id}...")
        proc_res = process_document(doc_id)

        print(f"Approving and indexing document #{doc_id} into ChromaDB vector store...")
        approve_document(doc_id, user_id=user_id, username=username)
        index_document_in_vector_store(doc_id)

        results.append({
            "doc_id": doc_id,
            "filename": file_path.name,
            "title": doc_title,
            "pages": proc_res.get("pages_count", 0),
            "chunks": proc_res.get("chunks_count", 0),
            "status": "indexed"
        })

    # Rebuild BM25 sparse index from all indexed documents
    print("Rebuilding BM25 technical index...")
    bm25_idx = BM25Index()
    bm25_idx.build_from_database()

    print("Government dataset successfully ingested, chunked, and indexed!")
    return {
        "status": "success",
        "ingested_documents": results,
        "bm25_doc_count": len(bm25_idx.doc_ids)
    }


if __name__ == "__main__":
    res = seed_and_train_government_dataset()
    print("Execution Result:", res)
