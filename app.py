"""
================================================================================
GLOBAL TRADE ROUTE DISRUPTION MONITOR
Institutional Economic & Geopolitical Scenario Intelligence Dashboard
Focus: Maritime Supply Chains, Global Chokepoints, and Impact on India
Theme: Black / Blue / Orange
================================================================================
Run:  pip install dash dash-bootstrap-components plotly pandas numpy networkx
      python trade_route_monitor.py
"""

import dash
from dash import dcc, html, Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

try:
    import requests
except ImportError:
    requests = None
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import networkx as nx
import textwrap
import json
import os
import time
from datetime import datetime, timedelta, timezone

# ==============================================================================
# 0. THEME (BLACK / BLUE / ORANGE)
# ==============================================================================

TERMINAL_STYLE = {
    "bg_dark": "#000000",
    "card_bg": "#0A0F1C",
    "card_border": "#14213D",
    "panel_alt": "#0D1526",
    "accent_blue": "#2F8CFF",
    "accent_green": "#2F8CFF",    # healthy / open state uses blue
    "accent_red": "#FF7A00",      # closed / at-risk state uses orange
    "accent_yellow": "#FFB066",   # light orange for warnings
    "accent_alt": "#9CC9FF",      # light blue for detour arcs
    "text_main": "#F8FAFC",
    "text_muted": "#94A3B8"
}

# ==============================================================================
# 1. DATASET: MAJOR MARITIME CHOKEPOINTS & SHIPPING CORRIDORS
# ==============================================================================

ROUTES_DATA = {
    "suez": {
        "name": "Suez Canal Corridor",
        "type": "Canal Chokepoint",
        "region": "Red Sea / Mediterranean",
        "importance": "Handles ~12-15% of global trade and ~30% of global container volume.",
        "india_relevance": "Carries ~35% of India's total merchandise trade ($200B+ annually), including engineering goods, textiles, and chemicals to Europe/US.",
        "weight_to_india": 26.0,
        "default_state": "OPEN",
        "waypoints": [
            (51.92, 4.47),    # Rotterdam
            (49.5, -0.1),     # English Channel
            (36.14, -5.35),   # Gibraltar
            (37.5, 11.5),     # Central Med
            (31.25, 32.3),    # Port Said (Suez North)
            (29.97, 32.55),   # Suez South
            (22.0, 38.0),     # Red Sea
            (12.58, 43.33),   # Bab-el-Mandeb
            (12.0, 50.0),     # Gulf of Aden
            (15.0, 62.0),     # Arabian Sea
            (18.95, 72.82)    # Mumbai (Nhava Sheva)
        ],
        "chokepoint_coord": (30.58, 32.26),
        "primary_alternative": "cape_good_hope",
        "network_edge": ("Mediterranean", "Red_Sea")
    },
    "hormuz": {
        "name": "Strait of Hormuz",
        "type": "Maritime Strait",
        "region": "Persian Gulf / Arabian Sea",
        "importance": "World's most critical energy artery. Approximately 20 million barrels/day (~20% of global petroleum liquids consumption, EIA 2024).",
        "india_relevance": "Critical vulnerability: roughly 40-50% of India's crude imports, ~90% of its LPG imports, and around half or more of its LNG imports transit this 21-mile strait (Kpler, ORF and industry estimates).",
        "weight_to_india": 38.0,
        "default_state": "OPEN",
        "waypoints": [
            (27.0, 50.0),     # Persian Gulf (Ras Tanura)
            (26.56, 56.25),   # Strait of Hormuz
            (24.5, 58.5),     # Gulf of Oman
            (22.0, 65.0),     # North Arabian Sea
            (22.75, 69.7)     # Mundra / Kandla Port
        ],
        "chokepoint_coord": (26.56, 56.25),
        "primary_alternative": "east_west_pipeline_gulf",
        "network_edge": ("Persian_Gulf", "Arabian_Sea")
    },
    "malacca": {
        "name": "Strait of Malacca",
        "type": "Maritime Strait",
        "region": "Southeast Asia / Indo-Pacific",
        "importance": "Primary conduit connecting the Indian Ocean with the Pacific. ~85,000 vessels per year; 25% of all traded goods.",
        "india_relevance": "Connects India to East Asian manufacturing giants (China, Japan, South Korea, Taiwan). Vital for electronics, APIs, and critical metals.",
        "weight_to_india": 22.0,
        "default_state": "OPEN",
        "waypoints": [
            (13.08, 80.27),   # Chennai Port
            (6.0, 94.0),      # Great Channel / Andaman Sea
            (3.0, 100.5),     # Strait of Malacca
            (1.35, 103.82),   # Singapore
            (10.0, 110.0),    # South China Sea
            (22.3, 114.17),   # Hong Kong
            (31.23, 121.47)   # Shanghai
        ],
        "chokepoint_coord": (2.5, 101.5),
        "primary_alternative": "sunda_lombok",
        "network_edge": ("Bay_of_Bengal", "South_China_Sea")
    },
    "bab_el_mandeb": {
        "name": "Bab-el-Mandeb Strait",
        "type": "Maritime Strait",
        "region": "Horn of Africa / Red Sea",
        "importance": "Gatekeeper to the southern entrance of the Red Sea; critical bridge between Indian Ocean and Suez Canal.",
        "india_relevance": "Key bottleneck for bilateral trade with Europe and North Africa. Vulnerable to maritime terrorism, asymmetric strikes, and war-risk premiums.",
        "weight_to_india": 24.0,
        "default_state": "OPEN",
        "waypoints": [
            (18.95, 72.82),   # Mumbai
            (13.5, 48.0),     # Gulf of Aden
            (12.58, 43.33),   # Bab-el-Mandeb
            (18.0, 40.0),     # Southern Red Sea
            (27.0, 35.0)      # Northern Red Sea
        ],
        "chokepoint_coord": (12.58, 43.33),
        "primary_alternative": "cape_good_hope",
        "network_edge": ("Gulf_of_Aden", "Red_Sea")
    },
    "cape_good_hope": {
        "name": "Cape of Good Hope Route",
        "type": "Oceanic Bypass Corridor",
        "region": "Southern Africa / South Atlantic",
        "importance": "The historical primary maritime detour circumventing both Suez and Bab-el-Mandeb.",
        "india_relevance": "Serves as the only viable megavessel fallback when the Red Sea is shuttered. Adds 10-15 transit days and 3,500 nautical miles.",
        "weight_to_india": 12.0,
        "default_state": "OPEN",
        "waypoints": [
            (51.92, 4.47),    # Rotterdam
            (28.0, -16.0),    # Canary Islands
            (4.0, -10.0),     # Gulf of Guinea Offshore
            (-15.0, 5.0),     # South Atlantic Ocean
            (-34.35, 18.47),  # Cape of Good Hope
            (-30.0, 35.0),    # East Coast South Africa
            (-10.0, 52.0),    # Western Indian Ocean
            (9.93, 76.26),    # Kochi Port
            (18.95, 72.82)    # Mumbai
        ],
        "chokepoint_coord": (-34.35, 18.47),
        "primary_alternative": "suez",
        "network_edge": ("Atlantic_Hub", "Indian_Ocean_South")
    },
    "panama": {
        "name": "Panama Canal",
        "type": "Interoceanic Canal",
        "region": "Central America",
        "importance": "Links Atlantic and Pacific Oceans; handles ~5% of global trade and 40% of US containerized goods.",
        "india_relevance": "Moderate direct relevance. Affects indirect imports of US crude/LPG, agricultural grains, and machinery routed via the Pacific.",
        "weight_to_india": 8.0,
        "default_state": "OPEN",
        "waypoints": [
            (40.71, -74.0),   # New York
            (25.0, -75.0),    # Bahamas Passage
            (9.10, -79.69),   # Panama Canal
            (5.0, -90.0),     # Eastern Pacific
            (15.0, -120.0),   # Central Pacific
            (35.67, 139.65)   # Tokyo
        ],
        "chokepoint_coord": (9.10, -79.69),
        "primary_alternative": "cape_horn",
        "network_edge": ("Atlantic_North", "Pacific_Central")
    },
    "sunda_lombok": {
        "name": "Sunda & Lombok Straits",
        "type": "Deepwater Archipelagic Straits",
        "region": "Indonesian Archipelago",
        "importance": "Deep-draft alternative corridors to Malacca. Accommodates giant Capesize and VLCC bulkers that cannot clear Malacca's shallow draft.",
        "india_relevance": "Crucial bypass when Malacca experiences naval blockades or severe piracy. Adds 3-5 steaming days from Australian and Pacific ports.",
        "weight_to_india": 10.0,
        "default_state": "OPEN",
        "waypoints": [
            (13.08, 80.27),   # Chennai
            (0.0, 90.0),      # Equatorial Indian Ocean
            (-6.0, 105.0),    # Sunda Strait
            (-8.5, 115.7),    # Lombok Strait
            (0.0, 120.0),     # Makassar Strait
            (20.0, 125.0),    # Philippine Sea
            (31.23, 121.47)   # Shanghai
        ],
        "chokepoint_coord": (-8.5, 115.7),
        "primary_alternative": "malacca",
        "network_edge": ("Indian_Ocean_East", "Philippine_Sea")
    },
    "northern_sea_route": {
        "name": "Northern Sea Route (Arctic)",
        "type": "Polar Maritime Corridor",
        "region": "Arctic Ocean / Siberian Coast",
        "importance": "Shaves ~40% off the distance between European and East Asian ports during ice-free summer windows.",
        "india_relevance": "Strategic corridor for discounted Russian Arctic crude (Novy Port, Prirazlomnoye) and LNG from the Yamal peninsula heading to India/Asia.",
        "weight_to_india": 6.0,
        "default_state": "OPEN",
        "waypoints": [
            (51.92, 4.47),    # Rotterdam
            (68.0, 14.0),     # Norwegian Sea
            (72.0, 35.0),     # Barents Sea (Murmansk)
            (76.0, 80.0),     # Kara Sea
            (75.0, 135.0),    # Laptev Sea
            (65.0, -170.0),   # Bering Strait
            (45.0, 150.0),    # Sea of Okhotsk
            (35.67, 139.65)   # Tokyo
        ],
        "chokepoint_coord": (72.0, 60.0),
        "primary_alternative": "suez",
        "network_edge": ("Atlantic_Arctic", "Pacific_North")
    },
    "english_channel": {
        "name": "English Channel & North Sea",
        "type": "Maritime Bottleneck",
        "region": "Northwest Europe",
        "importance": "Busiest shipping lane globally with over 500 vessel transits per day serving Rotterdam, Antwerp, and Hamburg.",
        "india_relevance": "Terminal gateway for Indian engineering, chemical, and apparel consignments entering mainland northern Europe.",
        "weight_to_india": 7.0,
        "default_state": "OPEN",
        "waypoints": [
            (50.5, -1.0),     # English Channel
            (51.2, 2.0),      # Dover Strait
            (53.0, 4.0)       # North Sea Approaches
        ],
        "chokepoint_coord": (51.2, 2.0),
        "primary_alternative": "round_scotland_bypass",
        "network_edge": ("Atlantic_North", "North_Sea")
    },
    "trans_pacific": {
        "name": "Trans-Pacific Shipping Corridor",
        "type": "Oceanic Container Corridor",
        "region": "Pacific Basin",
        "importance": "Backbone of modern consumer electronics and goods trade between East Asia and North American western ports.",
        "india_relevance": "Indirect impact on global container fleet equilibrium; delays tie up blank sailings and spike global spot freight rates.",
        "weight_to_india": 9.0,
        "default_state": "OPEN",
        "waypoints": [
            (31.23, 121.47),  # Shanghai
            (35.0, 150.0),    # North Pacific Basin
            (37.8, -122.4),   # San Francisco / Long Beach
            (33.74, -118.27)
        ],
        "chokepoint_coord": (38.0, -160.0),
        "primary_alternative": "trans_pacific_polar",
        "network_edge": ("East_Asia_Hub", "US_West_Coast")
    }
}

# ==============================================================================
# 2. DATASET: MAJOR PORTS (INDIAN & GLOBAL)
# ==============================================================================

PORTS_DATA = {
    "Mumbai_Nhava_Sheva": {"lat": 18.95, "lon": 72.95, "country": "India", "type": "Indian Major Port", "desc": "India's premier container hub (JNPA)."},
    "Mundra": {"lat": 22.75, "lon": 69.70, "country": "India", "type": "Indian Major Port", "desc": "Largest commercial and container gateway in India."},
    "Kandla_Deendayal": {"lat": 23.01, "lon": 70.22, "country": "India", "type": "Indian Major Port", "desc": "Critical crude oil, POL and dry bulk terminal."},
    "Kochi": {"lat": 9.93, "lon": 76.26, "country": "India", "type": "Indian Major Port", "desc": "Southern transshipment terminal (Vallarpadam)."},
    "Chennai": {"lat": 13.08, "lon": 80.27, "country": "India", "type": "Indian Major Port", "desc": "Primary manufacturing & automotive export corridor."},
    "Visakhapatnam": {"lat": 17.68, "lon": 83.21, "country": "India", "type": "Indian Major Port", "desc": "Eastern industrial gateway for steel, petroleum, and coal."},
    "Kolkata_Haldia": {"lat": 22.03, "lon": 88.08, "country": "India", "type": "Indian Major Port", "desc": "Riverine terminal serving landlocked states & eastern hinterlands."},
    "Tuticorin_VOC": {"lat": 8.76, "lon": 78.13, "country": "India", "type": "Indian Major Port", "desc": "Major deep-sea port handling textiles and agricultural goods."},
    "Rotterdam": {"lat": 51.92, "lon": 4.47, "country": "Netherlands", "type": "Global Port", "desc": "Largest seaport in Europe."},
    "Singapore": {"lat": 1.35, "lon": 103.82, "country": "Singapore", "type": "Global Port", "desc": "World's largest bunkering & transshipment hub."},
    "Shanghai": {"lat": 31.23, "lon": 121.47, "country": "China", "type": "Global Port", "desc": "World's highest volume container port."},
    "Ras_Tanura": {"lat": 26.65, "lon": 50.16, "country": "Saudi Arabia", "type": "Global Port", "desc": "World's largest offshore crude oil loading terminal."}
}

# ==============================================================================
# 3. ALTERNATIVE ROUTE DYNAMICS & GRAPH TOPOLOGY
# ==============================================================================

ALTERNATIVE_SPECS = {
    "suez_via_cape": {
        "name": "Cape of Good Hope Oceanic Transit",
        "triggered_by": ["suez", "bab_el_mandeb"],
        "required_open": ["cape_good_hope"],
        "origin_destination": "Europe / US East Coast ⟷ Indian Subcontinent & Asia",
        "additional_distance_nm": "+3,500 – 4,200 nautical miles",
        "additional_transit_days": "+10 to 14 days",
        "bunker_cost_delta": "+$400,000 – $800,000 per voyage (fuel burn)",
        "key_constraints": "Severe container equipment imbalances, doubled voyage fuel, port congestion in Durban/Cape Town, heavy southern swells.",
        "waypoints": ROUTES_DATA["cape_good_hope"]["waypoints"]
    },
    "malacca_via_sunda": {
        "name": "Sunda & Lombok Deepwater Bypass",
        "triggered_by": ["malacca"],
        "required_open": ["sunda_lombok"],
        "origin_destination": "Indian Ocean ⟷ East Asia / North Pacific",
        "additional_distance_nm": "+1,200 – 1,800 nautical miles",
        "additional_transit_days": "+3 to 5 days",
        "bunker_cost_delta": "+$150,000 – $250,000 per voyage",
        "key_constraints": "Restricted vessel clearance in Sunda; severe currents in Lombok; limited bunkering infrastructure outside Singapore.",
        "waypoints": ROUTES_DATA["sunda_lombok"]["waypoints"]
    },
    "hormuz_pipeline_bypass": {
        "name": "Saudi Petroline (East-West) & Fujairah Bypass",
        "triggered_by": ["hormuz"],
        "required_open": [],  # Land-based infrastructure
        "origin_destination": "Arabian Gulf Crude Fields ⟷ Red Sea / Gulf of Oman",
        "additional_distance_nm": "Pipeline Transit (0 NM)",
        "additional_transit_days": "+2 to 4 days (tanker relocking)",
        "bunker_cost_delta": "Pipeline tariff + loading surcharges ($2-4/bbl)",
        "key_constraints": "Fixed capacity ceiling (~7 million bbl/day East-West pipeline capacity per EIA 2026, against ~20 million bbl/day normally transiting Hormuz). Cannot evacuate LNG or LPG volumes.",
        "waypoints": [
            (26.0, 50.0),   # Abqaiq
            (24.5, 46.5),   # Riyadh terminal
            (24.0, 38.0),   # Yanbu Port (Red Sea)
            (20.0, 60.0),   # Bypassed offshore tanker meetup
            (18.95, 72.82)  # Mumbai
        ]
    }
}

# ==============================================================================
# 4. ECONOMIC & INDUSTRY IMPACT TAXONOMY
# ==============================================================================

HOUSEHOLD_BASELINE = {
    "fuel": {"name": "Petrol & Diesel (Transport)", "base_status": "Low", "weight": 20},
    "lpg": {"name": "Household LPG (Cooking Gas)", "base_status": "Low", "weight": 20},
    "food": {"name": "Edible Oils, Cereals & Vegetables", "base_status": "Low", "weight": 15},
    "electronics": {"name": "Consumer Electronics & Mobiles", "base_status": "Low", "weight": 10},
    "automobiles": {"name": "Automobiles & 2-Wheelers", "base_status": "Low", "weight": 8},
    "pharma": {"name": "Essential Medicines & Healthcare", "base_status": "Low", "weight": 9},
    "consumer_goods": {"name": "Imported Goods & Packaging", "base_status": "Low", "weight": 6},
    "fertilizer": {"name": "Fertilizers & Crop Production Inputs", "base_status": "Low", "weight": 12}
}

INDUSTRIES_TAXONOMY = [
    {
        "id": "oil_gas",
        "name": "Oil & Gas Refining",
        "disrupted_by": ["hormuz", "bab_el_mandeb", "suez"],
        "dependency": "Crucial import reliance on crude oil (87% imported; ~60% from Persian Gulf).",
        "mechanism": "Force majeure from Gulf terminals triggers immediate crude feedstock shortages, forcing domestic refineries to cut throughput.",
        "exposure": "High Import Exposure (Crude) / High Export Exposure (Refined Diesel/Naphtha)",
        "alternative": "West African (WAF) or Russian Urals via Cape of Good Hope, but at substantial freight premiums."
    },
    {
        "id": "petrochem",
        "name": "Petrochemicals & Plastics",
        "disrupted_by": ["hormuz", "malacca"],
        "dependency": "Imported naphtha, ethane, and monomer feedstocks from the Middle East.",
        "mechanism": "Feedstock delivery failures force plants to operate at fractional capacity, choking packaging and polymer supply chains.",
        "exposure": "Severe Import Dependency",
        "alternative": "Spot domestic polymer blending; sourcing from alternative Southeast Asian crackers."
    },
    {
        "id": "fertilizers",
        "name": "Fertilizers & Agriculture",
        "disrupted_by": ["hormuz", "bab_el_mandeb"],
        "dependency": "Middle Eastern urea, rock phosphate from Jordan/Egypt, and ammonia from Gulf facilities.",
        "mechanism": "Interruption halts fertilizer manufacturing ahead of sowing cycles, driving domestic shortages and inflating agricultural subsidies.",
        "exposure": "Direct Import Sourcing Bottleneck",
        "alternative": "Emergency domestic gas reallocation and Canadian/Moroccan potash sourcing via extended sea lanes."
    },
    {
        "id": "electronics",
        "name": "Electronics & Hardware Assembly",
        "disrupted_by": ["malacca", "sunda_lombok"],
        "dependency": "Components, PCBs, semiconductor assemblies, and displays from Taiwan, China, and South Korea.",
        "mechanism": "Stoppage along East Asian sea lanes starves Indian EMS assembly plants, creating consumer electronics shortages within 14-21 days.",
        "exposure": "Extreme Import Dependency (~70% of BOM value)",
        "alternative": "Air freight for subassemblies, eroding manufacturing margins and swelling retail costs."
    },
    {
        "id": "automotive",
        "name": "Automobile & Auto Components",
        "disrupted_by": ["suez", "bab_el_mandeb", "malacca"],
        "dependency": "Electronic chips and subassemblies from East Asia; specialized steel and precision gearboxes from Germany/EU.",
        "mechanism": "Container equipment shortages and 15-day transit delays disrupt Just-In-Time (JIT) assembly lines across Pune, Chennai, and Manesar.",
        "exposure": "Balanced Import/Export Dependency",
        "alternative": "Buffer stocking and domestic substitute qualification, with lead-times of 3 to 6 months."
    },
    {
        "id": "pharma",
        "name": "Pharmaceuticals & Healthcare",
        "disrupted_by": ["malacca", "suez", "bab_el_mandeb"],
        "dependency": "Key Starting Materials (KSMs) and Active Pharmaceutical Ingredients (APIs) from China; generic formulation exports to Europe/US.",
        "mechanism": "Raw material arrivals stall; outbound cold-chain container consignments to Europe face extended routes and shelf-life degradation.",
        "exposure": "Import-Reliant for APIs (~65%) / High-Volume Finished Formulations Exporter",
        "alternative": "Air cargo for temperature-sensitive drugs; diversified sourcing via domestic PLI-funded API complexes."
    },
    {
        "id": "textiles",
        "name": "Textiles & Ready-Made Garments",
        "disrupted_by": ["suez", "bab_el_mandeb"],
        "dependency": "Apparel and yarn exports to European Union retail chains and high-street brands.",
        "mechanism": "Fast-fashion seasonal deadlines are missed due to delays around the Cape of Good Hope, causing order cancellations and penal discounts.",
        "exposure": "High Export Exposure",
        "alternative": "No viable maritime shortcut; air-lifting samples to preserve buyer contracts."
    },
    {
        "id": "shipping_logistics",
        "name": "Shipping & Freight Logistics",
        "disrupted_by": ["suez", "hormuz", "malacca", "bab_el_mandeb"],
        "dependency": "Unimpeded vessel circulation, bunker availability, and marine insurance underwriting.",
        "mechanism": "War-risk surcharges surge by 400-800%; container turnaround cycles stretch, trapping trade finance and working capital.",
        "exposure": "Direct Sectoral Transmission",
        "alternative": "Repositioning fleets to regional cabotage and feeder services."
    }
]

# ==============================================================================
# 4B. COUNTRY / CONTINENT EXPOSURE
#     NOTE: sensitivities are illustrative placeholders. Replace this block with
#     values derived from CMIE / UN Comtrade data when available.
#     iso3: (country, continent, {route_id: (sensitivity 0-1, how it is affected)})
# ==============================================================================

COUNTRY_EXPOSURE = {
    # ---- Asia ----
    "IND": ("India", "Asia", {
        "hormuz": (0.95, "~60% of crude and ~90% of LPG imports transit Hormuz"),
        "suez": (0.60, "Exports to Europe/US face Cape detour"),
        "bab_el_mandeb": (0.55, "Red Sea trade with Europe and N. Africa disrupted"),
        "malacca": (0.70, "Electronics and API imports from East Asia delayed")}),
    "CHN": ("China", "Asia", {
        "hormuz": (0.50, "Large Gulf crude importer"),
        "suez": (0.55, "Europe-bound container exports rerouted"),
        "malacca": (0.85, "Most energy and trade flows pass Malacca")}),
    "JPN": ("Japan", "Asia", {
        "hormuz": (0.85, "~90% of crude imports come from the Gulf"),
        "malacca": (0.65, "Energy and raw material shipping lane")}),
    "KOR": ("South Korea", "Asia", {
        "hormuz": (0.80, "Heavy Gulf crude and LNG dependence"),
        "malacca": (0.65, "Key shipping lane to the Indian Ocean")}),
    "SGP": ("Singapore", "Asia", {
        "malacca": (0.90, "Transshipment and bunkering hub sits on the strait"),
        "sunda_lombok": (0.40, "Diverted traffic shifts volumes away")}),
    "SAU": ("Saudi Arabia", "Asia", {
        "hormuz": (0.80, "Gulf export terminals blocked; Yanbu pipeline only partial")}),
    "ARE": ("UAE", "Asia", {
        "hormuz": (0.70, "Gulf-side ports blocked; Fujairah partly bypasses")}),
    "IRQ": ("Iraq", "Asia", {
        "hormuz": (0.95, "Almost all crude exports leave via the Gulf")}),
    "QAT": ("Qatar", "Asia", {
        "hormuz": (0.95, "All LNG exports transit Hormuz")}),
    "IDN": ("Indonesia", "Asia", {
        "malacca": (0.45, "Western ports lose East-West traffic"),
        "sunda_lombok": (0.50, "Archipelagic straits face rerouted volumes")}),

    # ---- Europe ----
    "DEU": ("Germany", "Europe", {
        "suez": (0.65, "Asia-Europe container flows delayed 10-14 days"),
        "bab_el_mandeb": (0.55, "Red Sea access to Asian suppliers lost"),
        "english_channel": (0.40, "North Sea gateway congestion")}),
    "NLD": ("Netherlands", "Europe", {
        "suez": (0.65, "Rotterdam receives Asian cargo late"),
        "english_channel": (0.55, "Rotterdam sits on the channel approach")}),
    "GBR": ("United Kingdom", "Europe", {
        "suez": (0.55, "Asian imports delayed"),
        "english_channel": (0.60, "Dover Strait is a core trade lane")}),
    "ITA": ("Italy", "Europe", {
        "suez": (0.75, "Mediterranean ports depend on the Suez route"),
        "bab_el_mandeb": (0.60, "Asia-Med trade rerouted")}),
    "FRA": ("France", "Europe", {
        "suez": (0.50, "Asia trade delayed"),
        "english_channel": (0.45, "Channel ports affected")}),
    "ESP": ("Spain", "Europe", {
        "suez": (0.45, "Mediterranean-Asia flows rerouted")}),

    # ---- Africa ----
    "EGY": ("Egypt", "Africa", {
        "suez": (0.90, "Loses canal transit revenue"),
        "bab_el_mandeb": (0.80, "Red Sea traffic collapses")}),
    "ZAF": ("South Africa", "Africa", {
        "cape_good_hope": (0.55, "Port congestion if the Cape route is overloaded"),
        "suez": (0.30, "Diverted traffic strains Durban and Cape Town")}),
    "KEN": ("Kenya", "Africa", {
        "bab_el_mandeb": (0.50, "East Africa-Europe trade rerouted"),
        "hormuz": (0.55, "Fuel imports from the Gulf")}),
    "NGA": ("Nigeria", "Africa", {
        "cape_good_hope": (0.30, "Longer routes raise freight costs")}),

    # ---- North America ----
    "USA": ("United States", "North America", {
        "panama": (0.55, "40% of containerised goods use the Panama route"),
        "trans_pacific": (0.65, "West Coast imports from Asia delayed"),
        "suez": (0.40, "East Coast-Asia flows rerouted")}),
    "CAN": ("Canada", "North America", {
        "trans_pacific": (0.50, "Pacific gateway congestion"),
        "panama": (0.35, "East-West shipping delays")}),
    "MEX": ("Mexico", "North America", {
        "panama": (0.45, "Pacific-Atlantic cargo rerouted"),
        "trans_pacific": (0.40, "Asian input imports delayed")}),
    "PAN": ("Panama", "North America", {
        "panama": (0.95, "Canal revenue and logistics economy")}),

    # ---- South America ----
    "BRA": ("Brazil", "South America", {
        "panama": (0.30, "Pacific-bound exports"),
        "cape_good_hope": (0.30, "Asia-bound trade freight cost")}),
    "CHL": ("Chile", "South America", {
        "trans_pacific": (0.55, "Copper exports to Asia delayed"),
        "panama": (0.40, "Atlantic-bound cargo")}),

    # ---- Oceania ----
    "AUS": ("Australia", "Oceania", {
        "malacca": (0.55, "Iron ore and LNG exports to Asia delayed"),
        "sunda_lombok": (0.50, "Key export lane to East Asia"),
        "trans_pacific": (0.35, "Pacific trade affected")}),
    "NZL": ("New Zealand", "Oceania", {
        "trans_pacific": (0.45, "Export access to Asia and the US"),
        "suez": (0.30, "Europe-bound dairy and meat shipments")}),
}


# Additional major economies so every continent has a fair set of countries.
# Placeholder sensitivities, same caveat as above.
COUNTRY_EXPOSURE.update({
    "RUS": ("Russia", "Europe", {
        "suez": (0.40, "Urals crude and cargo to India/Asia rerouted via the Cape"),
        "bab_el_mandeb": (0.35, "Red Sea leg of oil exports to Asia disrupted"),
        "northern_sea_route": (0.60, "Arctic LNG and crude corridor to Asia is shut"),
        "english_channel": (0.25, "Baltic and North Sea shipping disrupted")}),
    "POL": ("Poland", "Europe", {
        "suez": (0.40, "Asian imports delayed"),
        "english_channel": (0.40, "North Sea access for Baltic trade")}),
    "GRC": ("Greece", "Europe", {
        "suez": (0.70, "Shipping-dependent economy; Suez-Med traffic collapses"),
        "bab_el_mandeb": (0.50, "Asia-Med trade rerouted")}),
    "TUR": ("Turkey", "Asia", {
        "suez": (0.45, "Mediterranean-Asia trade rerouted"),
        "hormuz": (0.55, "Energy imports from the Gulf")}),
    "IRN": ("Iran", "Asia", {
        "hormuz": (0.95, "Oil exports and imports depend on the strait")}),
    "KWT": ("Kuwait", "Asia", {
        "hormuz": (0.95, "All crude exports leave through the Gulf")}),
    "PAK": ("Pakistan", "Asia", {
        "hormuz": (0.70, "Crude and LNG imports from the Gulf"),
        "suez": (0.40, "Textile exports to Europe delayed")}),
    "BGD": ("Bangladesh", "Asia", {
        "suez": (0.65, "Garment exports to Europe delayed"),
        "hormuz": (0.55, "LNG and fuel imports from the Gulf")}),
    "VNM": ("Vietnam", "Asia", {
        "malacca": (0.55, "Trade with the Indian Ocean and Europe delayed"),
        "suez": (0.50, "Europe-bound exports rerouted")}),
    "THA": ("Thailand", "Asia", {
        "malacca": (0.60, "Main sea lane to the Indian Ocean"),
        "hormuz": (0.50, "Crude imports from the Gulf")}),
    "MYS": ("Malaysia", "Asia", {
        "malacca": (0.80, "Port Klang and Tanjung Pelepas sit on the strait")}),
    "DJI": ("Djibouti", "Africa", {
        "bab_el_mandeb": (0.95, "Port economy sits on the strait"),
        "suez": (0.70, "Transit traffic collapses")}),
    "MAR": ("Morocco", "Africa", {
        "suez": (0.35, "Asia trade rerouted"),
        "cape_good_hope": (0.25, "Atlantic traffic increases")}),
    "ARG": ("Argentina", "South America", {
        "cape_good_hope": (0.35, "Asia-bound grain exports face longer routes"),
        "panama": (0.30, "Pacific access delayed")}),
    "COL": ("Colombia", "South America", {
        "panama": (0.55, "Atlantic-Pacific trade depends on the canal")}),
    "PER": ("Peru", "South America", {
        "trans_pacific": (0.50, "Mineral exports to Asia delayed"),
        "panama": (0.40, "Atlantic-bound cargo")}),
})


def compute_country_scores(closed_routes):
    """Impact score 0-100 per country. Each closed route removes a share of
    'resilience', so several closures compound but the score never exceeds 100."""
    results = {}
    for iso, (name, continent, links) in COUNTRY_EXPOSURE.items():
        resilience = 1.0
        drivers = []
        for r_id, (sens, note) in links.items():
            if r_id in closed_routes:
                resilience *= (1.0 - 0.85 * sens)
                drivers.append((ROUTES_DATA[r_id]["name"], note))
        results[iso] = {
            "name": name,
            "continent": continent,
            "score": round(100 * (1 - resilience), 1),
            "drivers": drivers,
        }
    return results


def compute_continent_scores(country_scores):
    grouped = {}
    for iso, c in country_scores.items():
        grouped.setdefault(c["continent"], []).append(c)
    continents = {}
    for cont, items in grouped.items():
        avg = round(sum(i["score"] for i in items) / len(items), 1)
        continents[cont] = {
            "score": avg,
            "countries": sorted(items, key=lambda x: x["score"], reverse=True),
        }
    return continents


# Every country is assigned to a continent so the globe can colour whole continents.
# (Russia is placed in Europe; Middle East and Turkey in Asia; Americas split in two.)
CONTINENT_MEMBERS = {
    "Asia": "AFG ARM AZE BHR BGD BTN BRN KHM CHN CYP GEO IND IDN IRN IRQ ISR JPN JOR KAZ KWT KGZ LAO LBN MYS MDV MNG MMR NPL PRK OMN PAK PSE PHL QAT SAU SGP KOR LKA SYR TWN TJK THA TLS TUR TKM ARE UZB VNM YEM HKG MAC",
    "Europe": "ALB AND AUT BLR BEL BIH BGR HRV CZE DNK EST FIN FRA DEU GRC HUN ISL IRL ITA LVA LIE LTU LUX MLT MDA MCO MNE NLD MKD NOR POL PRT ROU RUS SMR SRB SVK SVN ESP SWE CHE UKR GBR VAT FRO GIB IMN JEY GGY ALA",
    "Africa": "DZA AGO BEN BWA BFA BDI CMR CPV CAF TCD COM COG COD CIV DJI EGY GNQ ERI SWZ ETH GAB GMB GHA GIN GNB KEN LSO LBR LBY MDG MWI MLI MRT MUS MAR MOZ NAM NER NGA RWA STP SEN SYC SLE SOM ZAF SSD SDN TZA TGO TUN UGA ESH ZMB ZWE",
    "North America": "ATG BHS BRB BLZ CAN CRI CUB DMA DOM SLV GRD GTM HTI HND JAM MEX NIC PAN KNA LCA VCT TTO USA GRL PRI BMU",
    "South America": "ARG BOL BRA CHL COL ECU GUY PRY PER SUR URY VEN GUF FLK",
    "Oceania": "AUS FJI KIR MHL FSM NRU NZL PLW PNG WSM SLB TON TUV VUT NCL PYF",
}
CONTINENT_MEMBERS = {k: v.split() for k, v in CONTINENT_MEMBERS.items()}


def continent_hover(cont, data):
    """Hover text shown over any country inside a continent."""
    affected = [c for c in data["countries"] if c["drivers"]][:4]
    if affected:
        lines = "<br>".join(
            f"• <b>{c['name']}</b> ({c['score']}): " + ", ".join(r for r, _ in c["drivers"][:2])
            for c in affected
        )
    else:
        lines = "No major country currently affected."
    return (f"<b>{cont.upper()}</b><br>Continent impact: <b>{data['score']}/100</b>"
            f"<br><br><b>Most affected countries:</b><br>{lines}")


HEAT_COLORS = {
    "low": "#0A1F44",      # under 20%: not significantly affected (dark blue)
    "yellow": "#FFD60A",   # 20 - 40%
    "orange": "#FF7A00",   # 40 - 70%
    "red": "#E11D1D",      # above 70%
}


def score_color(score):
    """Band colour used by the heatmap and the Continent Impact tab."""
    if score < 20:
        return TERMINAL_STYLE["accent_blue"]
    if score < 40:
        return HEAT_COLORS["yellow"]
    if score < 70:
        return HEAT_COLORS["orange"]
    return HEAT_COLORS["red"]

# ==============================================================================
# 4C. LIVE DATA LAYER  (IMF PortWatch + UN Comtrade)
#     Both are free public APIs. Results are cached in ./data_cache so the
#     dashboard still works offline (for example during a presentation).
#     If a download fails, the dashboard falls back to the model values.
# ==============================================================================

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")
PORTWATCH_URL = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query"
COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
INDIA_COMTRADE_CODE = 699            # UN M49 code for India

PORTWATCH_TTL_HOURS = 24             # PortWatch refreshes weekly
TRADE_TTL_HOURS = 24 * 30
BASELINE_YEAR = datetime.now().year - 1   # normal-year benchmark (2025 when run in 2026)
LIVE_CLOSE_THRESHOLD = -50.0         # a chokepoint is treated as "closed" if transits are 50%+ below baseline

# Keywords used to match PortWatch chokepoint names to the routes in this dashboard.
# (Trans-Pacific and Northern Sea Route have no PortWatch chokepoint, so they keep model values.)
PORTWATCH_KEYWORDS = {
    "suez": ["suez"],
    "hormuz": ["hormuz"],
    "malacca": ["malacca"],
    "bab_el_mandeb": ["bab"],
    "cape_good_hope": ["cape of good hope"],
    "panama": ["panama"],
    "sunda_lombok": ["sunda", "lombok"],
    "english_channel": ["dover", "english channel"],
}

LIVE = {
    "chokepoints": {},        # route_id -> live transit status
    "pw_meta": {},
    "india_trade": None,      # India's trade by partner country (USD)
    "trade_meta": {},
    "baseline_year": BASELINE_YEAR,
}


def _cache_file(name):
    return os.path.join(CACHE_DIR, name)


def _read_cache(name):
    """Returns (data, age_in_hours) or (None, None)."""
    try:
        path = _cache_file(name)
        if not os.path.exists(path):
            return None, None
        age_h = (time.time() - os.path.getmtime(path)) / 3600.0
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), age_h
    except Exception:
        return None, None


def _write_cache(name, data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_file(name), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"  (could not write cache {name}: {e})")


# ---------------------------- IMF PortWatch ----------------------------------

def _fetch_portwatch_rows(since_date):
    like_clauses = " OR ".join(
        f"UPPER(portname) LIKE '%{kw.upper()}%'"
        for kws in PORTWATCH_KEYWORDS.values() for kw in kws
    )
    where = f"({like_clauses}) AND date >= timestamp '{since_date} 00:00:00'"
    rows, offset = [], 0
    while True:
        params = {
            "where": where, "outFields": "*", "orderByFields": "date ASC",
            "resultOffset": offset, "resultRecordCount": 1000,
            "returnGeometry": "false", "f": "json",
        }
        resp = requests.get(PORTWATCH_URL, params=params, timeout=40)
        resp.raise_for_status()
        js = resp.json()
        if "error" in js:
            raise RuntimeError(js["error"])
        feats = js.get("features", [])
        rows.extend(f["attributes"] for f in feats)
        if len(feats) < 1000 and not js.get("exceededTransferLimit"):
            break
        offset += len(feats)
        if not feats or offset > 80000:
            break
    return rows


def _row_total(attrs):
    total = attrs.get("n_total")
    if total is None:
        total = sum((attrs.get(k) or 0) for k in
                    ("n_container", "n_dry_bulk", "n_general_cargo", "n_roro", "n_tanker"))
    return total or 0


def _to_date(ts):
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).date()
    return datetime.strptime(str(ts)[:10], "%Y-%m-%d").date()


def compute_chokepoint_status(rows, baseline_year):
    """Baseline = average daily transits in the baseline year.
    Current = average of the latest 7 days of data."""
    daily, names = {}, {}
    for a in rows:
        if a.get("date") is None:
            continue
        pname = (a.get("portname") or "").lower()
        d = _to_date(a["date"])
        for r_id, kws in PORTWATCH_KEYWORDS.items():
            if any(kw in pname for kw in kws):
                daily.setdefault(r_id, {})
                daily[r_id][d] = daily[r_id].get(d, 0) + _row_total(a)
                names.setdefault(r_id, set()).add(a.get("portname"))
    status = {}
    for r_id, series in daily.items():
        base = [v for d, v in series.items() if d.year == baseline_year]
        if not base:
            continue
        last = max(series)
        recent = [v for d, v in series.items() if d > last - timedelta(days=7)]
        b, c = sum(base) / len(base), sum(recent) / len(recent)
        status[r_id] = {
            "baseline": round(b, 1),
            "current": round(c, 1),
            "change_pct": round((c / b - 1) * 100, 1) if b > 0 else None,
            "as_of": last.isoformat(),
            "names": sorted(n for n in names[r_id] if n),
        }
    return status


def load_portwatch():
    cached, age = _read_cache("portwatch_status.json")
    if cached is not None and age is not None and age < PORTWATCH_TTL_HOURS:
        return cached, "cache"
    try:
        if requests is None:
            raise RuntimeError("the 'requests' package is not installed")
        rows = _fetch_portwatch_rows(f"{BASELINE_YEAR}-01-01")
        status = compute_chokepoint_status(rows, BASELINE_YEAR)
        if not status:
            raise RuntimeError("no matching chokepoints were returned")
        payload = {"fetched_at": datetime.now().isoformat(timespec="seconds"),
                   "baseline_year": BASELINE_YEAR, "routes": status}
        _write_cache("portwatch_status.json", payload)
        return payload, "live"
    except Exception as e:
        print(f"  PortWatch download failed: {e}")
        if cached is not None:
            return cached, "older cache"
        return None, "unavailable"


# ------------------------------ UN Comtrade ----------------------------------

def _fetch_comtrade(year, flow):
    params = {
        "reporterCode": INDIA_COMTRADE_CODE, "period": year, "flowCode": flow,
        "cmdCode": "TOTAL", "partner2Code": 0, "customsCode": "C00", "motCode": 0,
    }
    resp = requests.get(COMTRADE_URL, params=params, timeout=40)
    resp.raise_for_status()
    return resp.json().get("data") or []


def build_trade_payload(year, export_rows, import_rows):
    iso_to_cont = {iso: c for c, members in CONTINENT_MEMBERS.items() for iso in members}
    partners = {}

    def add(rows, key):
        for r in rows:
            iso = r.get("partnerISO") or ""
            if iso in ("", "W00") or r.get("partnerCode") in (0, "0"):
                continue
            value = r.get("primaryValue") or r.get("fobvalue") or r.get("cifvalue") or 0
            p = partners.setdefault(iso, {
                "name": r.get("partnerDesc") or iso, "exports": 0.0, "imports": 0.0,
                "continent": iso_to_cont.get(iso)})
            p[key] += float(value)

    add(export_rows, "exports")
    add(import_rows, "imports")
    for p in partners.values():
        p["total"] = p["exports"] + p["imports"]
    return {"year": year, "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "total_trade": sum(p["total"] for p in partners.values()), "partners": partners}


def load_india_trade():
    cached, age = _read_cache("india_trade.json")
    if cached is not None and age is not None and age < TRADE_TTL_HOURS:
        return cached, "cache"
    try:
        if requests is None:
            raise RuntimeError("the 'requests' package is not installed")
        payload = None
        for year in range(datetime.now().year - 1, datetime.now().year - 5, -1):
            exports = _fetch_comtrade(year, "X")
            time.sleep(1.0)
            imports = _fetch_comtrade(year, "M")
            time.sleep(1.0)
            if exports and imports:
                payload = build_trade_payload(year, exports, imports)
                break
        if not payload or not payload["partners"]:
            raise RuntimeError("no India trade data returned by the public preview API")
        _write_cache("india_trade.json", payload)
        return payload, "live"
    except Exception as e:
        print(f"  UN Comtrade download failed: {e}")
        if cached is not None:
            return cached, "older cache"
        return None, "unavailable"


def load_live_data():
    print("Loading live data (IMF PortWatch, UN Comtrade)...")
    pw, pw_src = load_portwatch()
    if pw:
        LIVE["chokepoints"] = pw["routes"]
        LIVE["baseline_year"] = pw.get("baseline_year", BASELINE_YEAR)
        as_of = max((v["as_of"] for v in pw["routes"].values()), default="n/a")
        LIVE["pw_meta"] = {"src": pw_src, "as_of": as_of, "count": len(pw["routes"])}
        print(f"  PortWatch: {len(pw['routes'])} chokepoints matched ({pw_src}), latest data {as_of}")
        for r_id, v in pw["routes"].items():
            print(f"    {r_id:16s} -> {', '.join(v['names'])}")
    else:
        LIVE["pw_meta"] = {"src": pw_src}
        print("  PortWatch: not available, using model values")
    tr, tr_src = load_india_trade()
    if tr:
        LIVE["india_trade"] = tr
        LIVE["trade_meta"] = {"src": tr_src, "year": tr["year"], "total": tr["total_trade"]}
        print(f"  Comtrade: India trade {tr['year']}, ${tr['total_trade']/1e9:.0f}bn, "
              f"{len(tr['partners'])} partners ({tr_src})")
    else:
        LIVE["trade_meta"] = {"src": tr_src}
        print("  Comtrade: not available, using model values")


# --------------- India trade exposure (real trade values, assumed routes) -----
# Each partner country is assigned the main chokepoints its sea trade with India uses.
# The trade VALUES are real (UN Comtrade); the route ASSIGNMENT is a simplified assumption.

PARTNER_ROUTE_OVERRIDES = {}


def _assign(isos, routes):
    for iso in isos.split():
        PARTNER_ROUTE_OVERRIDES[iso] = routes


_assign("SAU ARE IRQ KWT QAT BHR IRN", ["hormuz"])
_assign("CHN JPN KOR TWN HKG MAC SGP MYS THA VNM PHL KHM LAO", ["malacca"])
_assign("IDN", ["malacca", "sunda_lombok"])
_assign("TUR ISR LBN SYR CYP EGY LBY TUN DZA MAR", ["suez", "bab_el_mandeb"])
_assign("JOR YEM SDN ERI DJI", ["bab_el_mandeb"])
_assign("ZAF AGO NGA GHA SEN CIV CMR COG COD GAB GNQ LBR SLE GIN MRT BEN TGO NAM", ["cape_good_hope"])
_assign("USA CAN", ["suez", "bab_el_mandeb"])
_assign("NLD BEL DEU GBR DNK NOR SWE FIN POL EST LVA LTU IRL", ["suez", "bab_el_mandeb", "english_channel"])
_assign("CHL PER ECU", ["trans_pacific"])
_assign("COL MEX", ["panama"])

CONTINENT_DEFAULT_ROUTES = {
    "Europe": ["suez", "bab_el_mandeb"],
    "South America": ["cape_good_hope"],
    "North America": ["panama"],
    "Oceania": ["sunda_lombok"],
    "Africa": [],
    "Asia": [],
}


def partner_routes(iso, continent):
    return PARTNER_ROUTE_OVERRIDES.get(iso) or CONTINENT_DEFAULT_ROUTES.get(continent, [])


def compute_india_trade_exposure(closed_routes):
    """Share of India's actual trade value (UN Comtrade) whose main sea route
    passes through a closed chokepoint. Returns None if trade data is not loaded."""
    td = LIVE.get("india_trade")
    if not td:
        return None
    total, exposed, continents = td["total_trade"], 0.0, {}
    for iso, p in td["partners"].items():
        cont = p.get("continent")
        hit = [r for r in partner_routes(iso, cont) if r in closed_routes]
        if cont:
            c = continents.setdefault(cont, {"trade": 0.0, "exposed": 0.0, "partners": []})
            c["trade"] += p["total"]
            if hit:
                c["exposed"] += p["total"]
                c["partners"].append({"name": p["name"], "value": p["total"],
                                      "routes": [ROUTES_DATA[r]["name"] for r in hit]})
        if hit:
            exposed += p["total"]
    for c in continents.values():
        c["score"] = round(100 * c["exposed"] / c["trade"], 1) if c["trade"] else 0.0
        c["partners"].sort(key=lambda x: -x["value"])
    return {"year": td["year"], "total": total, "exposed": exposed,
            "exposed_pct": round(100 * exposed / total, 1) if total else 0.0,
            "continents": continents}


def data_continent_hover(cont, info, year, total):
    if not info:
        return f"<b>{cont.upper()}</b><br>No India trade data for this continent."
    share = 100 * info["trade"] / total if total else 0
    lines = "<br>".join(
        f"• <b>{p['name']}</b> (${p['value']/1e9:.1f}bn): " + ", ".join(p["routes"])
        for p in info["partners"][:4]) or "No India trade currently exposed."
    return (f"<b>{cont.upper()}</b><br>India trade exposed: <b>{info['score']}%</b><br>"
            f"India's trade with {cont}: ${info['trade']/1e9:.0f}bn ({share:.0f}% of total, {year})"
            f"<br><br><b>Most exposed partners:</b><br>{lines}")


def live_hover_line(route_id):
    live = LIVE["chokepoints"].get(route_id)
    if not live or live.get("change_pct") is None:
        return ""
    return (f"<br><br><b>Live transits (IMF PortWatch, to {live['as_of']}):</b><br>"
            f"{live['current']:.0f}/day vs {live['baseline']:.0f}/day in {LIVE['baseline_year']} "
            f"(<b>{live['change_pct']:+.0f}%</b>)")


def data_sources_card():
    pw, tr = LIVE.get("pw_meta", {}), LIVE.get("trade_meta", {})
    if LIVE["chokepoints"]:
        pw_text = (f"{pw.get('count')} corridors matched; latest data {pw.get('as_of')}; "
                   f"baseline = {LIVE['baseline_year']} daily average ({pw.get('src')}).")
    else:
        pw_text = "Not loaded (offline or blocked). Showing model values only."
    if LIVE["india_trade"]:
        tr_text = (f"India's merchandise trade by partner country, {tr.get('year')}, "
                   f"${tr.get('total', 0)/1e9:.0f}bn total ({tr.get('src')}).")
    else:
        tr_text = "Not loaded (offline or blocked). Showing model values only."
    return dbc.Card([
        dbc.CardBody([
            html.H6("LIVE DATA SOURCES", className="text-info mb-2", style={"fontWeight": "700"}),
            html.Ul([
                html.Li([html.B("IMF PortWatch (daily chokepoint transits): "), pw_text], className="text-muted small mb-2"),
                html.Li([html.B("UN Comtrade public API (India trade by partner): "), tr_text], className="text-muted small mb-2"),
            ], className="ps-3 mb-2"),
            html.Small("Sources: UN Global Platform; IMF PortWatch. UN Comtrade.", className="d-block text-muted fst-italic mb-2"),
            html.Small("Still model assumptions: the country sensitivity scores, route weights in the India index, "
                       "the assignment of each trading partner to a sea route, and detour cost estimates. "
                       "Trade values and transit counts above are real data.", className="d-block text-warning")
        ], className="p-3")
    ], className="mt-3", style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": TERMINAL_STYLE["card_border"]})


load_live_data()


# ------------------------------------------------------------------------------
# India boundary (Survey of India version, includes all of Jammu & Kashmir and Ladakh)
# Plotly's built-in world map uses Natural Earth borders, which draw India differently,
# so India is drawn from this file instead. Keep india_boundary.geojson next to this script.
# ------------------------------------------------------------------------------
INDIA_GEOJSON = None
try:
    _geo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "india_boundary.geojson")
    with open(_geo_path, "r", encoding="utf-8") as _f:
        INDIA_GEOJSON = json.load(_f)
except Exception as _e:
    print(f"WARNING: india_boundary.geojson not found ({_e}). Falling back to Plotly's default India outline.")

# ==============================================================================
# 5. GRAPH ENGINE & IMPACT SIMULATION MODEL

# ==============================================================================

def build_trade_network(closed_routes):
    """
    Constructs a NetworkX graph of maritime connectivity, evaluates route reachability,
    and identifies dynamic alternative path activations.
    """
    G = nx.Graph()

    hubs = [
        "Rotterdam", "Gibraltar", "Mediterranean", "Red_Sea", "Gulf_of_Aden",
        "Persian_Gulf", "Arabian_Sea", "Bay_of_Bengal", "South_China_Sea",
        "Atlantic_Hub", "Indian_Ocean_South", "Atlantic_North", "Pacific_Central",
        "Indian_Ocean_East", "Philippine_Sea", "East_Asia_Hub", "US_West_Coast"
    ]
    for h in hubs:
        G.add_node(h)

    for r_id, r_info in ROUTES_DATA.items():
        if r_id not in closed_routes:
            u, v = r_info["network_edge"]
            G.add_edge(u, v, route_id=r_id, weight=1.0)

    active_alternatives = []

    if ("suez" in closed_routes or "bab_el_mandeb" in closed_routes) and ("cape_good_hope" not in closed_routes):
        active_alternatives.append("suez_via_cape")

    if "malacca" in closed_routes and ("sunda_lombok" not in closed_routes):
        active_alternatives.append("malacca_via_sunda")

    if "hormuz" in closed_routes:
        active_alternatives.append("hormuz_pipeline_bypass")

    return G, active_alternatives


def calculate_india_disruption_index(closed_routes, active_alternatives):
    """Calculates the normalized India Trade Disruption Index (0-100)."""
    if not closed_routes:
        return 0.0, "Minimal", "Optimal Maritime Freedom"

    raw_weight = sum(ROUTES_DATA[r]["weight_to_india"] for r in closed_routes if r in ROUTES_DATA)

    compounding_factor = 1.0 + (len(closed_routes) - 1) * 0.12

    mitigation_discount = 0.0
    if "suez_via_cape" in active_alternatives:
        mitigation_discount += 0.08
    if "malacca_via_sunda" in active_alternatives:
        mitigation_discount += 0.05
    if "hormuz_pipeline_bypass" in active_alternatives:
        mitigation_discount += 0.04

    score = raw_weight * compounding_factor * (1.0 - mitigation_discount)
    normalized_score = min(round(score, 1), 100.0)

    if normalized_score <= 20.0:
        band = "Low"
        summary = "Localized or absorbable supply chain friction."
    elif normalized_score <= 40.0:
        band = "Moderate"
        summary = "Noticeable maritime delays; freight surcharges emerging."
    elif normalized_score <= 60.0:
        band = "Elevated"
        summary = "Broad export delays, working capital friction, and initial consumer price inflation."
    elif normalized_score <= 80.0:
        band = "High"
        summary = "Critical stress on balance of trade, sovereign energy inventories, and industrial output."
    else:
        band = "Severe"
        summary = "Emergency economic crisis: acute energy rationing, manufacturing curtailments, and surging inflation."

    return normalized_score, band, summary


def evaluate_household_impacts(closed_routes):
    """Evaluates dynamic household impacts across 8 consumer-facing verticals."""
    impacts = {}
    for key, baseline in HOUSEHOLD_BASELINE.items():
        impact_level = "Low"
        rationale = "Supplies and consumer pricing remain stable under normal baseline operations."

        if key == "fuel":
            if "hormuz" in closed_routes:
                impact_level = "Severe"
                rationale = "Roughly 40-50% of crude imports face an immediate bottleneck. Domestic pump prices will face severe upward pressure."
            elif "bab_el_mandeb" in closed_routes or "suez" in closed_routes:
                impact_level = "Moderate"
                rationale = "Longer transit for Russian and Mediterranean crude adds freight and tanker charter costs."
        elif key == "lpg":
            if "hormuz" in closed_routes:
                impact_level = "Severe"
                rationale = "Immediate supply threat: ~90% of imported household cooking LPG transits Hormuz."
        elif key == "fertilizer":
            if "hormuz" in closed_routes and ("suez" in closed_routes or "bab_el_mandeb" in closed_routes):
                impact_level = "Severe"
                rationale = "Dual bottleneck: Middle Eastern ammonia and Egyptian/Jordanian rock phosphate are stranded."
            elif "hormuz" in closed_routes:
                impact_level = "High"
                rationale = "Gulf urea shipments choked. Government subsidy bill escalates; rural planting costs surge."
            elif "bab_el_mandeb" in closed_routes:
                impact_level = "Moderate"
                rationale = "Red Sea phosphate exports delayed, requiring longer journeys around southern Africa."
        elif key == "food":
            if "hormuz" in closed_routes or "suez" in closed_routes:
                impact_level = "Elevated" if ("hormuz" in closed_routes and "suez" in closed_routes) else "Moderate"
                rationale = "Indirect inflation driven by elevated tractor fuel costs, compounded by international delays in imported sunflower and palm oil."
        elif key == "electronics":
            if "malacca" in closed_routes:
                impact_level = "Severe"
                rationale = "Primary semiconductor and component pipelines from East Asia severed. Consumer phone and appliance prices surge."
        elif key == "automobiles":
            if "malacca" in closed_routes or "suez" in closed_routes:
                impact_level = "Moderate"
                rationale = "Delays in European precision subassemblies and East Asian microcontrollers stretch dealership waiting periods."
        elif key == "pharma":
            if "malacca" in closed_routes:
                impact_level = "High"
                rationale = "Over 65% of Active Pharmaceutical Ingredients (APIs) sourced from East Asia are blocked."
            elif "suez" in closed_routes or "bab_el_mandeb" in closed_routes:
                impact_level = "Moderate"
                rationale = "Outbound shipments of finished formulations to EU/US face extended voyage durations."
        elif key == "consumer_goods":
            if len(closed_routes) >= 2:
                impact_level = "High"
                rationale = "Surging ocean container freight rates are passed directly to retail consumers across imported goods."
            elif len(closed_routes) == 1:
                impact_level = "Moderate"
                rationale = "Retailers experience delayed seasonal catalog arrivals and localized stockouts."

        impacts[key] = {
            "name": baseline["name"],
            "level": impact_level,
            "rationale": rationale
        }
    return impacts

# ==============================================================================
# 6. DASHBOARD APPLICATION INSTANTIATION & LAYOUT
# ==============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True
)
app.title = "Global Maritime Chokepoint & Trade Disruption Monitor"

# Override Bootstrap's default red/yellow/green with the black-blue-orange theme
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body { background-color: #000000; }
            .bg-danger, .badge.bg-danger { background-color: #FF7A00 !important; color: #000000 !important; }
            .bg-warning, .badge.bg-warning { background-color: #FFB066 !important; color: #000000 !important; }
            .bg-success, .badge.bg-success { background-color: #2F8CFF !important; color: #000000 !important; }
            .bg-info, .badge.bg-info { background-color: #9CC9FF !important; color: #000000 !important; }
            .text-danger { color: #FF7A00 !important; }
            .text-warning { color: #FFB066 !important; }
            .text-success { color: #2F8CFF !important; }
            .text-info { color: #2F8CFF !important; }
            .border-success { border-color: #2F8CFF !important; }
            .border-danger { border-color: #FF7A00 !important; }
            .border-warning { border-color: #FFB066 !important; }
            .border-info { border-color: #9CC9FF !important; }
            .progress-bar { background-color: #2F8CFF; }
            .progress-bar.bg-danger { background-color: #FF7A00 !important; }
            .progress-bar.bg-warning { background-color: #FFB066 !important; }
            .btn-outline-info { color: #2F8CFF; border-color: #2F8CFF; }
            .btn-outline-info:hover { background-color: #2F8CFF; color: #000000; }
            .btn-outline-danger { color: #FF7A00; border-color: #FF7A00; }
            .btn-outline-danger:hover { background-color: #FF7A00; color: #000000; }
            .form-check-input:checked { background-color: #2F8CFF; border-color: #2F8CFF; }
            .nav-tabs .nav-link { color: #94A3B8; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


def create_header():
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span("⚓ GLOBAL MARITIME INTELLIGENCE", style={"color": TERMINAL_STYLE["accent_red"], "fontWeight": "700", "fontSize": "0.8rem", "letterSpacing": "1.5px"}),
                        html.H4("Trade Route Disruption & Sovereign Risk Monitor", className="mb-0 text-white", style={"fontWeight": "700", "letterSpacing": "-0.5px"}),
                        html.Small("Real-time scenario simulation: Chokepoints, Alternative Navigational Arcs & India Macro Exposure", style={"color": TERMINAL_STYLE["text_muted"]})
                    ])
                ], md=6),
                dbc.Col([
                    html.Div(id="header-stats-container", className="d-flex justify-content-md-end gap-3 align-items-center mt-2 mt-md-0")
                ], md=6)
            ], className="w-100 align-items-center")
        ], fluid=True),
        color=TERMINAL_STYLE["card_bg"],
        dark=True,
        className="border-bottom border-secondary py-2 sticky-top",
        style={"borderColor": TERMINAL_STYLE["card_border"]}
    )


def create_map_panel():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.Span("GEOSPATIAL SITUATIONAL MAP", style={"fontWeight": "700", "fontSize": "0.85rem", "color": TERMINAL_STYLE["accent_blue"], "letterSpacing": "1px"}),
                    html.Span(" — Global Chokepoints, Port Networks & Continent Impact Heatmap", className="text-muted small")
                ], md=7),
                dbc.Col([
                    html.Div([
                        html.Span("Active Lane", className="badge bg-dark text-success border border-success me-1"),
                        html.Span("Closed Lane", className="badge bg-dark text-danger border border-danger me-1"),
                        html.Span("Alternate Arc", className="badge bg-dark border me-1", style={"color": TERMINAL_STYLE["accent_alt"], "borderColor": TERMINAL_STYLE["accent_alt"]}),
                        html.Span("Indian Port", className="badge bg-dark text-info border border-info")
                    ], className="text-end small"),
                    html.Div([
                        dbc.Switch(id="heatmap-toggle", label="Impact heatmap", value=True, className="d-inline-block small"),
                        dbc.Switch(id="data-basis-toggle", label="India trade data (UN Comtrade)",
                                   value=LIVE["india_trade"] is not None,
                                   disabled=LIVE["india_trade"] is None,
                                   className="d-inline-block small"),
                    ], className="d-flex justify-content-end gap-3 mt-1")
                ], md=5)
            ], className="align-items-center")
        ], style={"backgroundColor": TERMINAL_STYLE["card_bg"], "borderBottom": f"1px solid {TERMINAL_STYLE['card_border']}"}),

        dbc.CardBody([
            dcc.Graph(
                id="world-trade-map",
                style={"height": "760px", "width": "100%"},
                responsive=True,
                config={
                    "displayModeBar": False,
                    "scrollZoom": False,
                    "doubleClick": False,
                    "displaylogo": False
                }
            )
        ], className="p-0")
    ], style={"backgroundColor": TERMINAL_STYLE["card_bg"], "borderColor": TERMINAL_STYLE["card_border"], "borderRadius": "8px"})


def create_control_panel():
    tab_style = {"color": TERMINAL_STYLE["accent_blue"], "fontWeight": "bold"}
    return dbc.Card([
        dbc.CardHeader([
            dbc.Tabs([
                dbc.Tab(label="Disruption Controls", tab_id="tab-controls", active_label_style=tab_style),
                dbc.Tab(label="Continent Impact", tab_id="tab-continent", active_label_style=tab_style),
                dbc.Tab(label="India Household Impact", tab_id="tab-household", active_label_style=tab_style),
                dbc.Tab(label="Industry Exposure", tab_id="tab-industry", active_label_style=tab_style),
                dbc.Tab(label="Model Notes", tab_id="tab-methodology", active_label_style=tab_style)
            ], id="right-panel-tabs", active_tab="tab-controls", className="border-0")
        ], style={"backgroundColor": TERMINAL_STYLE["card_bg"], "borderBottom": f"1px solid {TERMINAL_STYLE['card_border']}"}),

        dbc.CardBody([
            html.Div(id="tab-content-area", style={"height": "740px", "overflowY": "auto", "paddingRight": "8px"})
        ], className="p-3")
    ], style={"backgroundColor": TERMINAL_STYLE["card_bg"], "borderColor": TERMINAL_STYLE["card_border"], "borderRadius": "8px"})


app.layout = html.Div([
    create_header(),
    dbc.Container([
        dbc.Row([
            dbc.Col(create_map_panel(), lg=7, xl=7, className="mb-3 mb-lg-0"),
            dbc.Col(create_control_panel(), lg=5, xl=5)
        ], className="g-3 mt-1")
    ], fluid=True, className="px-3 pb-3"),

    dcc.Store(id="closed-routes-store", data=[])
], style={"backgroundColor": TERMINAL_STYLE["bg_dark"], "minHeight": "100vh", "fontFamily": "Segoe UI, Inter, Roboto, sans-serif"})

# ==============================================================================
# 7. MAP GENERATION ENGINE (ARCS, HEATMAP, GLOBE)
# ==============================================================================

def generate_arc_points(p1, p2, num_points=35):
    """Interpolates smooth curved arcs between waypoints, with date-line fix."""
    lon1, lon2 = p1[1], p2[1]

    if lon2 - lon1 > 180:
        lon1 += 360
    elif lon1 - lon2 > 180:
        lon2 += 360

    lats = np.linspace(p1[0], p2[0], num_points)
    lons = np.linspace(lon1, lon2, num_points)

    lat_delta = p2[0] - p1[0]
    lon_delta = lon2 - lon1

    curvature = 0.08 * np.sin(np.pi * np.linspace(0, 1, num_points))

    arc_lats = lats - curvature * lon_delta
    arc_lons = lons + curvature * lat_delta

    return list(arc_lats), list(arc_lons)


# Discrete bands: <20 dark blue | 20-40 yellow | 40-70 orange | >70 red
HEAT_SCALE = [
    [0.0, HEAT_COLORS["low"]],    [0.2, HEAT_COLORS["low"]],
    [0.2, HEAT_COLORS["yellow"]], [0.4, HEAT_COLORS["yellow"]],
    [0.4, HEAT_COLORS["orange"]], [0.7, HEAT_COLORS["orange"]],
    [0.7, HEAT_COLORS["red"]],    [1.0, HEAT_COLORS["red"]],
]


def add_impact_heatmap(fig, closed_routes, show_heatmap=True, basis="model"):
    """Colours each continent as one block using fixed bands.
    basis="model": model estimate of overall continent impact.
    basis="data":  share of India's actual trade (UN Comtrade) with that continent
                   whose main sea route passes through a closed chokepoint.
    India is drawn last from the Survey of India boundary, coloured as part of Asia."""
    country_scores = compute_country_scores(closed_routes)
    continents = compute_continent_scores(country_scores)
    exposure = compute_india_trade_exposure(closed_routes) if basis == "data" else None
    use_custom_india = INDIA_GEOJSON is not None

    cont_score, cont_hover = {}, {}
    for cont in CONTINENT_MEMBERS:
        if exposure is not None:
            info = exposure["continents"].get(cont)
            cont_score[cont] = info["score"] if info else 0.0
            cont_hover[cont] = data_continent_hover(cont, info, exposure["year"], exposure["total"])
        else:
            data = continents.get(cont, {"score": 0.0, "countries": []})
            cont_score[cont] = data["score"]
            cont_hover[cont] = continent_hover(cont, data)

    if show_heatmap:
        isos, zs, hovers = [], [], []
        for cont, members in CONTINENT_MEMBERS.items():
            for iso in members:
                if iso == "IND" and use_custom_india:
                    continue
                isos.append(iso)
                zs.append(cont_score[cont])
                hovers.append(cont_hover[cont])

        fig.add_trace(go.Choropleth(
            locations=isos,
            z=zs,
            zmin=0, zmax=100,
            colorscale=HEAT_SCALE,
            marker=dict(line=dict(color="#000000", width=0.3)),
            hoverinfo="text",
            hovertext=hovers,
            showscale=True,
            colorbar=dict(
                title=dict(text="India trade exposed" if exposure is not None else "Continent impact",
                           font=dict(color="#F8FAFC", size=11)),
                thickness=12, len=0.45, x=0.02,
                tickmode="array",
                tickvals=[10, 30, 55, 85],
                ticktext=["Under 20%", "20-40%", "40-70%", "Above 70%"],
                tickfont=dict(color="#CBD5E1", size=9),
                bgcolor="rgba(0,0,0,0)", outlinewidth=0
            ),
            showlegend=False
        ))

    if use_custom_india:
        if show_heatmap:
            z_val, colorscale = [cont_score["Asia"]], HEAT_SCALE
        else:
            z_val, colorscale = [0], [[0.0, "#0F1B33"], [1.0, "#0F1B33"]]
        fig.add_trace(go.Choropleth(
            geojson=INDIA_GEOJSON,
            locations=["IND"],
            featureidkey="id",
            z=z_val,
            zmin=0, zmax=100,
            colorscale=colorscale,
            marker=dict(line=dict(color="#000000", width=0.3)),
            hoverinfo="text",
            hovertext=[cont_hover["Asia"]],
            showscale=False,
            showlegend=False
        ))


def build_map_figure(closed_routes, active_alternatives, show_heatmap=True, basis="model"):
    """Constructs the master Plotly geospatial figure."""
    fig = go.Figure()

    # Layer 0: country impact heatmap (drawn first so lanes sit on top)
    add_impact_heatmap(fig, closed_routes, show_heatmap, basis)

    # Layer 1: Major maritime corridors
    for r_id, r_info in ROUTES_DATA.items():
        is_closed = r_id in closed_routes
        wps = r_info["waypoints"]

        all_lats = []
        all_lons = []
        for i in range(len(wps) - 1):
            arc_lats, arc_lons = generate_arc_points(wps[i], wps[i + 1], num_points=15)
            all_lats.extend(arc_lats)
            all_lons.extend(arc_lons)

        color = TERMINAL_STYLE["accent_red"] if is_closed else TERMINAL_STYLE["accent_blue"]
        width = 3.5 if is_closed else 2.2
        dash_style = "dash" if is_closed else "solid"
        opacity = 0.90 if is_closed else 0.75
        status_label = "CLOSED (BLOCKED)" if is_closed else "OPEN (OPERATIONAL)"

        wrapped_relevance = "<br>".join(textwrap.wrap(r_info['india_relevance'], width=60))
        wrapped_importance = "<br>".join(textwrap.wrap(r_info['importance'], width=60))

        hover_text = (
            f"<b>{r_info['name'].upper()}</b><br>"
            f"<b>Status:</b> {status_label}<br>"
            f"<b>Type:</b> {r_info['type']}<br>"
            f"<b>Geopolitical Region:</b> {r_info['region']}<br>"
            f"<b>Sovereign Relevance to India:</b><br>{wrapped_relevance}<br><br>"
            f"<b>Global Throughput Significance:</b><br>{wrapped_importance}"
            + live_hover_line(r_id)
        )

        fig.add_trace(go.Scattergeo(
            lon=all_lons,
            lat=all_lats,
            mode='lines',
            line=dict(width=width, color=color, dash=dash_style),
            opacity=opacity,
            name=r_info["name"],
            hoverinfo='text',
            hovertext=hover_text,
            showlegend=False
        ))

        cp_lat, cp_lon = r_info["chokepoint_coord"]
        marker_color = TERMINAL_STYLE["accent_red"] if is_closed else TERMINAL_STYLE["accent_blue"]
        marker_symbol = "x" if is_closed else "circle"
        marker_size = 11 if is_closed else 6

        fig.add_trace(go.Scattergeo(
            lon=[cp_lon],
            lat=[cp_lat],
            mode='markers',
            marker=dict(size=marker_size, color=marker_color, symbol=marker_symbol, line=dict(width=1.5, color="#FFFFFF")),
            hoverinfo='text',
            hovertext=f"<b>CHOKEPOINT: {r_info['name']}</b><br>Status: {status_label}" + live_hover_line(r_id),
            showlegend=False
        ))

    # Layer 2: Dynamic alternative routing arcs (light blue, dotted)
    for alt_id in active_alternatives:
        alt_data = ALTERNATIVE_SPECS.get(alt_id)
        if alt_data:
            alt_wps = alt_data["waypoints"]
            alt_lats = []
            alt_lons = []
            for i in range(len(alt_wps) - 1):
                seg_lats, seg_lons = generate_arc_points(alt_wps[i], alt_wps[i + 1], num_points=20)
                alt_lats.extend(seg_lats)
                alt_lons.extend(seg_lons)

            wrapped_constraints = "<br>".join(textwrap.wrap(alt_data['key_constraints'], width=60))

            alt_hover = (
                f"<b>ACTIVE DETOUR: {alt_data['name'].upper()}</b><br>"
                f"<b>Corridor:</b> {alt_data['origin_destination']}<br>"
                f"<b>Additional Distance:</b> {alt_data['additional_distance_nm']}<br>"
                f"<b>Transit Penalty:</b> {alt_data['additional_transit_days']}<br>"
                f"<b>Bunker Penalty:</b> {alt_data['bunker_cost_delta']}<br>"
                f"<b>Constraints:</b><br>{wrapped_constraints}"
            )

            fig.add_trace(go.Scattergeo(
                lon=alt_lons,
                lat=alt_lats,
                mode='lines',
                line=dict(width=3.8, color=TERMINAL_STYLE["accent_alt"], dash="dot"),
                opacity=0.95,
                name=f"Alt: {alt_data['name']}",
                hoverinfo='text',
                hovertext=alt_hover,
                showlegend=False
            ))

    # Layer 3: Ports
    for p_name, p_val in PORTS_DATA.items():
        is_india = p_val["country"] == "India"
        p_color = TERMINAL_STYLE["accent_blue"] if is_india else "#94A3B8"
        p_size = 8 if is_india else 5
        clean_name = p_name.replace("_", " ")

        port_hover = (
            f"<b>PORT: {clean_name}</b> ({p_val['country']})<br>"
            f"<b>Classification:</b> {p_val['type']}<br>"
            f"<b>Operations:</b> {p_val['desc']}"
        )

        fig.add_trace(go.Scattergeo(
            lon=[p_val["lon"]],
            lat=[p_val["lat"]],
            mode='markers+text',
            text=[clean_name if is_india else ""],
            textposition="top right",
            textfont=dict(size=9, color="#E2E8F0"),
            marker=dict(size=p_size, color=p_color, line=dict(width=1, color="#000000")),
            hoverinfo='text',
            hovertext=port_hover,
            showlegend=False
        ))

    # Layer 4: Globe styling.
    # No 'center' is set: only rotation controls the view, so dragging spins the
    # globe in place instead of sliding it out of the frame.
    fig.update_geos(
        projection_type="orthographic",
        showcoastlines=True,
        coastlinecolor="#1E3A8A",
        showland=True,
        landcolor="#0F1B33",
        showocean=True,
        oceancolor="#000000",
        showlakes=True,
        lakecolor="#000000",
        showcountries=True,
        countrycolor="#1E3A8A",
        countrywidth=0.8,
        bgcolor="#000000",

        projection_rotation=dict(lat=20.0, lon=65.0, roll=0),
        projection_scale=1.0,

        domain=dict(x=[0, 1], y=[0, 1]),
        fitbounds=False,
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=TERMINAL_STYLE["card_bg"],
        plot_bgcolor=TERMINAL_STYLE["card_bg"],
        hoverlabel=dict(
            bgcolor="#0D1526",
            font_size=12,
            font_color="#F8FAFC",
            font_family="Consolas, monospace"
        ),
        dragmode="pan",
        uirevision="locked"
    )

    return fig

# ==============================================================================
# 8. DASH CALLBACKS & INTERACTIVE STATE ORCHESTRATION
# ==============================================================================

@app.callback(
    Output("closed-routes-store", "data"),
    Input({"type": "route-toggle", "route_id": ALL}, "value"),
    Input("reset-all-btn", "n_clicks"),
    Input("live-sync-btn", "n_clicks"),
    State("closed-routes-store", "data"),
    prevent_initial_call=True
)
def manage_disrupted_routes(toggle_values, reset_clicks, sync_clicks, current_closed):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"]

    if "reset-all-btn" in trigger_id:
        # Only reset on a real click (a freshly re-created button reports n_clicks=None)
        if reset_clicks:
            return []
        raise PreventUpdate

    if "live-sync-btn" in trigger_id:
        # Close every chokepoint whose real transit count is far below its normal level
        if not sync_clicks or not LIVE["chokepoints"]:
            raise PreventUpdate
        return [r for r, st in LIVE["chokepoints"].items()
                if st.get("change_pct") is not None
                and st["change_pct"] <= LIVE_CLOSE_THRESHOLD and r in ROUTES_DATA]

    # The route switches only exist on the "Disruption Controls" tab. When another tab
    # is opened they are removed and Dash reports an empty list. That must NOT wipe the
    # saved scenario, so keep the current state.
    if not toggle_values:
        raise PreventUpdate

    new_closed = []
    for comp, is_open in zip(ctx.inputs_list[0], toggle_values):
        route_key = comp["id"]["route_id"]
        if not is_open:
            new_closed.append(route_key)

    # Nothing actually changed (switches were just re-drawn): skip the redundant refresh
    if sorted(new_closed) == sorted(current_closed or []):
        raise PreventUpdate

    return new_closed


@app.callback(
    Output("header-stats-container", "children"),
    Input("closed-routes-store", "data")
)
def render_header_metrics(closed_routes):
    G, active_alts = build_trade_network(closed_routes)
    score, band, _ = calculate_india_disruption_index(closed_routes, active_alts)

    score_color_val = TERMINAL_STYLE["accent_green"]
    if score > 40: score_color_val = TERMINAL_STYLE["accent_yellow"]
    if score > 60: score_color_val = "#FF9A3D"
    if score > 80: score_color_val = TERMINAL_STYLE["accent_red"]

    items = [
        html.Div([
            html.Small("ACTIVE DISRUPTIONS", className="d-block text-muted", style={"fontSize": "0.68rem"}),
            html.Span(f"{len(closed_routes)} CHOKEPOINTS", className="badge bg-danger", style={"fontSize": "0.85rem"})
        ], className="text-center px-2 border-end border-secondary"),

        html.Div([
            html.Small("ACTIVE BYPASS DETOURS", className="d-block text-muted", style={"fontSize": "0.68rem"}),
            html.Span(f"{len(active_alts)} DETOURS", className="badge bg-warning", style={"fontSize": "0.85rem"})
        ], className="text-center px-2 border-end border-secondary"),

        html.Div([
            html.Small("INDIA DISRUPTION INDEX", className="d-block text-muted", style={"fontSize": "0.68rem"}),
            html.Span(f"{score}/100 [{band.upper()}]", className="badge", style={"backgroundColor": score_color_val, "color": "#000000", "fontSize": "0.88rem"})
        ], className="text-center px-2")
    ]
    exposure = compute_india_trade_exposure(closed_routes)
    if exposure is not None:
        items.insert(2, html.Div([
            html.Small("INDIA TRADE EXPOSED", className="d-block text-muted", style={"fontSize": "0.68rem"}),
            html.Span(f"{exposure['exposed_pct']}%", className="badge bg-warning", style={"fontSize": "0.85rem"})
        ], className="text-center px-2 border-end border-secondary"))
    return items


@app.callback(
    Output("world-trade-map", "figure"),
    Input("closed-routes-store", "data"),
    Input("heatmap-toggle", "value"),
    Input("data-basis-toggle", "value")
)
def update_map(closed_routes, show_heatmap, use_data):
    G, active_alts = build_trade_network(closed_routes)
    return build_map_figure(closed_routes, active_alts, show_heatmap, "data" if use_data else "model")


@app.callback(
    Output("tab-content-area", "children"),
    Input("right-panel-tabs", "active_tab"),
    Input("closed-routes-store", "data"),
    Input("data-basis-toggle", "value")
)
def render_panel_tabs(active_tab, closed_routes, use_data):
    G, active_alts = build_trade_network(closed_routes)
    score, band, summary = calculate_india_disruption_index(closed_routes, active_alts)

    if active_tab == "tab-controls":
        exposure = compute_india_trade_exposure(closed_routes)
        exposure_el = []
        if exposure is not None:
            exposure_el = [html.Small(
                f"India trade value exposed: {exposure['exposed_pct']}% of ${exposure['total']/1e9:.0f}bn ({exposure['year']}, UN Comtrade)",
                className="d-block text-muted", style={"fontSize": "0.72rem"})]
        index_card = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Span("SOVEREIGN TRADE DISRUPTION INDEX", style={"fontSize": "0.75rem", "color": TERMINAL_STYLE["text_muted"], "fontWeight": "600"}),
                        html.H2(f"{score} / 100", className="mb-0", style={"color": TERMINAL_STYLE["accent_yellow"] if score > 30 else TERMINAL_STYLE["accent_green"], "fontWeight": "800"}),
                        html.Small(f"Severity Tier: {band}", style={"fontWeight": "600", "color": "#F8FAFC"}),
                        *exposure_el
                    ], width=7),
                    dbc.Col([
                        dbc.Progress(value=score, max=100, color="danger" if score > 60 else "warning" if score > 30 else "success", style={"height": "14px", "borderRadius": "4px"}),
                        html.Small(summary, className="d-block text-muted mt-2", style={"fontSize": "0.72rem", "lineHeight": "1.2"})
                    ], width=5)
                ], className="align-items-center")
            ], className="py-2")
        ], className="mb-3", style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": TERMINAL_STYLE["card_border"]})

        toggle_rows = []
        for r_id, r_info in ROUTES_DATA.items():
            is_open = r_id not in closed_routes
            live = LIVE["chokepoints"].get(r_id)
            live_el = []
            if live and live.get("change_pct") is not None:
                chg = live["change_pct"]
                live_color = TERMINAL_STYLE["accent_red"] if chg <= -50 else TERMINAL_STYLE["accent_yellow"] if chg <= -25 else TERMINAL_STYLE["text_muted"]
                live_el = [html.Small(f"Live: {live['current']:.0f}/day vs {live['baseline']:.0f}/day ({chg:+.0f}%) as of {live['as_of']}",
                                      className="d-block", style={"fontSize": "0.68rem", "color": live_color})]
            status_badge = dbc.Badge("OPEN", color="success", className="me-2") if is_open else dbc.Badge("CLOSED", color="danger", className="me-2")

            toggle_rows.append(
                dbc.ListGroupItem([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.B(r_info["name"], style={"fontSize": "0.85rem", "color": "#FFFFFF"}),
                                html.Small(f" — {r_info['type']} ({r_info['region']})", className="text-muted d-block", style={"fontSize": "0.72rem"}),
                                *live_el
                            ])
                        ], width=8),
                        dbc.Col([
                            html.Div([
                                status_badge,
                                dbc.Switch(
                                    id={"type": "route-toggle", "route_id": r_id},
                                    value=is_open,
                                    className="d-inline-block"
                                )
                            ], className="d-flex align-items-center justify-content-end")
                        ], width=4)
                    ], className="align-items-center")
                ], style={"backgroundColor": TERMINAL_STYLE["card_bg"], "borderColor": TERMINAL_STYLE["card_border"], "padding": "0.6rem 0.8rem"})
            )

        routes_control_card = dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col(html.Span("CHOKEPOINT OPERATIONAL STATUS", style={"fontSize": "0.8rem", "fontWeight": "700", "color": TERMINAL_STYLE["accent_blue"]})),
                    dbc.Col(
                        html.Div([
                            dbc.Button("LOAD LIVE STATUS", id="live-sync-btn", size="sm", color="outline-info", className="me-2",
                                       disabled=not LIVE["chokepoints"], style={"fontSize": "0.7rem", "fontWeight": "600"}),
                            dbc.Button("RESET ALL ROUTES", id="reset-all-btn", size="sm", color="outline-danger", style={"fontSize": "0.7rem", "fontWeight": "600"}),
                        ], className="d-flex justify-content-end"),
                        className="text-end"
                    )
                ], className="align-items-center")
            ], style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderBottom": f"1px solid {TERMINAL_STYLE['card_border']}"}),
            dbc.ListGroup(toggle_rows, flush=True)
        ], className="mb-3", style={"borderColor": TERMINAL_STYLE["card_border"]})

        alt_cards = []
        if active_alts:
            for alt_id in active_alts:
                alt = ALTERNATIVE_SPECS[alt_id]
                alt_cards.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Span("DYNAMIC BYPASS ACTIVATED", className="badge bg-warning mb-1", style={"fontSize": "0.68rem"}),
                                html.H6(alt["name"], className="text-white mb-1", style={"fontWeight": "700"}),
                                html.P(f"Transit Corridor: {alt['origin_destination']}", className="text-muted small mb-2"),
                                dbc.Row([
                                    dbc.Col([
                                        html.Small("Distance Penalty:", className="text-muted d-block"),
                                        html.B(alt["additional_distance_nm"], className="text-warning", style={"fontSize": "0.78rem"})
                                    ], width=6),
                                    dbc.Col([
                                        html.Small("Voyage Delay:", className="text-muted d-block"),
                                        html.B(alt["additional_transit_days"], className="text-warning", style={"fontSize": "0.78rem"})
                                    ], width=6)
                                ], className="mb-2"),
                                html.Small(f"Bunker Expense Delta: {alt['bunker_cost_delta']}", className="d-block text-muted mb-1", style={"fontSize": "0.72rem"}),
                                html.Small(f"Vulnerability Notes: {alt['key_constraints']}", className="d-block text-danger", style={"fontSize": "0.72rem"})
                            ])
                        ], className="p-2")
                    ], className="mb-2", style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": TERMINAL_STYLE["accent_yellow"]})
                )
        else:
            alt_cards.append(
                html.Div([
                    html.P("No active alternative bypasses required. Primary maritime corridors are operating within baseline specifications.", className="text-muted small text-center p-3")
                ])
            )

        alt_section = dbc.Card([
            dbc.CardHeader(
                html.Span("ACTIVE ALTERNATIVE ROUTING & DETOUR METRICS", style={"fontSize": "0.8rem", "fontWeight": "700", "color": TERMINAL_STYLE["accent_yellow"]}),
                style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderBottom": f"1px solid {TERMINAL_STYLE['card_border']}"}
            ),
            dbc.CardBody(alt_cards, className="p-2")
        ], style={"borderColor": TERMINAL_STYLE["card_border"]})

        return html.Div([index_card, routes_control_card, alt_section])

    elif active_tab == "tab-continent":
        if use_data:
            exp = compute_india_trade_exposure(closed_routes)
            if exp is None:
                return html.Div([html.P("India trade data (UN Comtrade) is not loaded, so the data view is unavailable. "
                                        "Check your internet connection and restart the app.", className="text-warning small")])
            d_ranked = sorted(exp["continents"].items(), key=lambda kv: kv[1]["score"], reverse=True)
            d_cards = []
            for cont, info in d_ranked:
                col = score_color(info["score"])
                share = 100 * info["trade"] / exp["total"] if exp["total"] else 0
                blocks = [html.Div([
                    html.Div([html.B(pt["name"], className="text-white", style={"fontSize": "0.78rem"}),
                              html.Span(f"  ${pt['value']/1e9:.1f}bn", style={"color": col, "fontSize": "0.74rem", "fontWeight": "600"})]),
                    html.Small(" · ".join(pt["routes"]), className="d-block text-muted", style={"fontSize": "0.70rem"})
                ], className="mb-2") for pt in info["partners"][:5]] or [
                    html.Small("No India trade currently exposed.", className="text-muted", style={"fontSize": "0.72rem"})]
                d_cards.append(dbc.Card([dbc.CardBody([
                    dbc.Row([
                        dbc.Col(html.H6(cont, className="text-white mb-0", style={"fontWeight": "700"}), width=7),
                        dbc.Col(html.Span(f"{info['score']}% exposed", style={"color": col, "fontWeight": "700"}), width=5, className="text-end"),
                    ]),
                    html.Small(f"India's trade with {cont}: ${info['trade']/1e9:.0f}bn ({share:.0f}% of total)",
                               className="d-block text-muted mb-1", style={"fontSize": "0.70rem"}),
                    html.Div(html.Div(style={"width": f"{info['score']}%", "height": "6px", "backgroundColor": col, "borderRadius": "3px"}),
                             style={"backgroundColor": TERMINAL_STYLE["card_border"], "borderRadius": "3px", "marginBottom": "10px"}),
                    html.Div(blocks)
                ], className="p-2")], className="mb-2",
                    style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": TERMINAL_STYLE["card_border"]}))
            return html.Div([
                html.H6("Continent-wise Exposure of India's Trade", className="text-white mb-1", style={"fontWeight": "700"}),
                html.P(f"Based on India's actual trade with each partner in {exp['year']} (UN Comtrade). "
                       f"{exp['exposed_pct']}% of India's trade value (${exp['exposed']/1e9:.0f}bn of ${exp['total']/1e9:.0f}bn) "
                       "goes to partners whose main sea route passes through a closed chokepoint. "
                       "The assignment of partners to routes is a simplified assumption.",
                       className="text-muted small mb-3"),
                html.Div(d_cards)
            ])
        country_scores = compute_country_scores(closed_routes)
        continents = compute_continent_scores(country_scores)
        ranked = sorted(continents.items(), key=lambda kv: kv[1]["score"], reverse=True)

        cards = []
        for cont, data in ranked:
            col = score_color(data["score"])
            affected = [c for c in data["countries"] if c["drivers"]][:5]

            country_blocks = []
            for c in affected:
                country_blocks.append(html.Div([
                    html.Div([
                        html.B(c["name"], className="text-white", style={"fontSize": "0.78rem"}),
                        html.Span(f"  {c['score']}/100", style={"color": score_color(c["score"]), "fontSize": "0.74rem", "fontWeight": "600"})
                    ]),
                    *[html.Small(f"{r}: {note}", className="d-block text-muted", style={"fontSize": "0.70rem", "lineHeight": "1.25"})
                      for r, note in c["drivers"][:3]]
                ], className="mb-2"))
            if not country_blocks:
                country_blocks = [html.Small("No major country currently affected.", className="text-muted", style={"fontSize": "0.72rem"})]

            cards.append(dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(html.H6(cont, className="text-white mb-1", style={"fontWeight": "700"}), width=8),
                        dbc.Col(html.Span(f"{data['score']}/100", style={"color": col, "fontWeight": "700"}), width=4, className="text-end"),
                    ]),
                    html.Div(
                        html.Div(style={"width": f"{data['score']}%", "height": "6px",
                                        "backgroundColor": col, "borderRadius": "3px"}),
                        style={"backgroundColor": TERMINAL_STYLE["card_border"], "borderRadius": "3px", "marginBottom": "10px"}
                    ),
                    html.Div(country_blocks)
                ], className="p-2")
            ], className="mb-2", style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": TERMINAL_STYLE["card_border"]}))

        return html.Div([
            html.H6("Continent-wise Impact", className="text-white mb-1", style={"fontWeight": "700"}),
            html.P("The globe shows how much each continent is affected overall. Below, each continent lists its most "
                   "affected major countries and the chokepoint behind the impact. Sensitivities are illustrative "
                   "placeholders pending CMIE data integration.",
                   className="text-muted small mb-3"),
            html.Div(cards)
        ])

    elif active_tab == "tab-household":
        household_data = evaluate_household_impacts(closed_routes)
        cards = []
        for k, v in household_data.items():
            lvl = v["level"]
            badge_color = "success"
            if lvl == "Moderate": badge_color = "info"
            elif lvl == "Elevated": badge_color = "warning"
            elif lvl == "High": badge_color = "danger"
            elif lvl == "Severe": badge_color = "danger"

            cards.append(
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6(v["name"], className="text-white mb-1", style={"fontSize": "0.88rem", "fontWeight": "600"}),
                                html.P(v["rationale"], className="text-muted mb-0", style={"fontSize": "0.75rem", "lineHeight": "1.3"})
                            ], width=9),
                            dbc.Col([
                                dbc.Badge(f"{lvl.upper()}", color=badge_color, className="w-100 py-1", style={"fontSize": "0.75rem"})
                            ], width=3, className="text-end")
                        ], className="align-items-center")
                    ], className="p-2")
                ], className="mb-2", style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": TERMINAL_STYLE["card_border"]})
            )

        return html.Div([
            html.Div([
                html.H6("Sovereign Household Vulnerability Matrix", className="text-white mb-1", style={"fontWeight": "700"}),
                html.P("Evaluates transmission channels from maritime chokepoints to retail prices, domestic supplies, and cost of living in India.", className="text-muted small mb-3")
            ]),
            html.Div(cards)
        ])

    elif active_tab == "tab-industry":
        industry_cards = []
        for ind in INDUSTRIES_TAXONOMY:
            relevant_closed = [r for r in ind["disrupted_by"] if r in closed_routes]
            is_affected = len(relevant_closed) > 0

            status_badge = dbc.Badge("AT RISK", color="danger") if is_affected else dbc.Badge("NORMAL", color="success")
            border_color = TERMINAL_STYLE["accent_red"] if is_affected else TERMINAL_STYLE["card_border"]

            industry_cards.append(
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Row([
                                dbc.Col(html.H6(ind["name"], className="text-white mb-1", style={"fontWeight": "700"}), width=9),
                                dbc.Col(status_badge, width=3, className="text-end")
                            ]),
                            html.Small(f"Direct Dependency: {ind['dependency']}", className="d-block text-muted mb-1", style={"fontSize": "0.75rem"}),
                            html.Small(f"Disruption Mechanism: {ind['mechanism']}", className="d-block text-warning mb-1", style={"fontSize": "0.73rem"}),
                            html.Small(f"Exposure Profile: {ind['exposure']}", className="d-block text-info mb-1", style={"fontSize": "0.72rem"}),
                            html.Small(f"Strategic Alternative: {ind['alternative']}", className="d-block text-muted", style={"fontSize": "0.72rem"})
                        ])
                    ], className="p-2")
                ], className="mb-2", style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": border_color})
            )

        return html.Div([
            html.Div([
                html.H6("Indian Industrial Exposure & Corporate Risk", className="text-white mb-1", style={"fontWeight": "700"}),
                html.P("Dynamic impact propagation across supply chain nodes, raw material feedstocks, and export commitments.", className="text-muted small mb-3")
            ]),
            html.Div(industry_cards)
        ])

    elif active_tab == "tab-methodology":
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H6("DATA & SCENARIO MODEL ASSUMPTIONS", className="text-info mb-2", style={"fontWeight": "700"}),
                    html.P(
                        "This dashboard is an analytical simulation tool designed for economic scenario testing, "
                        "risk assessments, and educational intelligence. The trade flows, route dependencies, "
                        "household impacts, and industrial exposure ratings are modeled representations. "
                        "They illustrate structural dependencies rather than definitive price forecasts.",
                        className="text-muted small mb-3"
                    ),
                    html.H6("Key Structural Formulations:", className="text-white small", style={"fontWeight": "700"}),
                    html.Ul([
                        html.Li("India Disruption Index: Calculated via route exposure weightings (w_i), multiplied by a compounding multi-chokepoint penalty factor, offset by dynamic mitigation discounts when bypass corridors remain navigable.", className="text-muted small mb-2"),
                        html.Li("Graph Representation: Formulated as a NetworkX graph with oceanic trade nodes. Disrupted edges are pruned to evaluate path availability and trigger alternative corridor visual traces.", className="text-muted small mb-2"),
                        html.Li("Country & Continent Impact: Each major country carries a sensitivity (0-1) to the chokepoints it depends on. Closed routes compound multiplicatively into a 0-100 country score; the continent score (shown on the globe) is the average of its major countries, so continents without a listed country in the path of a closure stay low. These sensitivities remain illustrative placeholders. The \"India trade data\" view instead uses real UN Comtrade trade values.", className="text-muted small mb-2"),
                        html.Li("Household & Industrial Models: Real-world empirical import/export sensitivities (e.g., 87% crude import exposure, 90% LPG Hormuz transit) establish qualitative and directional risk tiers (Low/Moderate/Elevated/High/Severe).", className="text-muted small")
                    ], className="ps-3 mb-3"),
                    html.Div([
                        html.Small("Notice: Actual real-world shipping dislocations depend on vessel inventory depth, strategic reserve drawdowns, war-risk reinsurance surcharges, bilateral government currency swaps, and diplomatic exemptions.", className="text-warning small fst-italic")
                    ])
                ], className="p-3")
            ], style={"backgroundColor": TERMINAL_STYLE["panel_alt"], "borderColor": TERMINAL_STYLE["card_border"]}),
            data_sources_card()
        ])

# ==============================================================================
# 9. EXECUTION ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)