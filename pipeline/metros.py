"""Metro expansion config. Each metro = a core city (where we run the Maps
ingest) plus key suburbs (seeded into target_cities so suburb businesses the
core-city search returns get marked 'confirmed' rather than 'mismatch').

We ingest the CORE city only per metro to stay Apify-frugal (~$0.36/core
city vs ~$2.33 for a full 8-city sweep) — Google Maps' core-city search
already surfaces nearby-suburb businesses. If a metro underperforms the
~5-10-listing threshold after extraction, add suburb ingests for that one.

All metros chosen are OUTSIDE Reventals.com's 34-metro footprint (the funded
competitor) — same "find the uncovered gap" logic that made Charlotte viable.
"""

METROS = [
    {
        "name": "Raleigh-Durham",
        "core": ("Raleigh", "NC"),
        "suburbs": [("Durham", "NC"), ("Cary", "NC"), ("Chapel Hill", "NC"),
                    ("Apex", "NC"), ("Wake Forest", "NC"), ("Morrisville", "NC")],
    },
    {
        "name": "Greensboro-Winston-Salem",
        "core": ("Greensboro", "NC"),
        "suburbs": [("Winston-Salem", "NC"), ("High Point", "NC"),
                    ("Kernersville", "NC"), ("Burlington", "NC")],
    },
    {
        "name": "Richmond",
        "core": ("Richmond", "VA"),
        "suburbs": [("Henrico", "VA"), ("Chesterfield", "VA"),
                    ("Midlothian", "VA"), ("Glen Allen", "VA")],
    },
    {
        "name": "Columbus",
        "core": ("Columbus", "OH"),
        "suburbs": [("Dublin", "OH"), ("Westerville", "OH"),
                    ("Grove City", "OH"), ("Hilliard", "OH")],
    },
    {
        "name": "Indianapolis",
        "core": ("Indianapolis", "IN"),
        "suburbs": [("Carmel", "IN"), ("Fishers", "IN"),
                    ("Greenwood", "IN"), ("Noblesville", "IN")],
    },
    {
        "name": "Jacksonville",
        "core": ("Jacksonville", "FL"),
        "suburbs": [("Orange Park", "FL"), ("Ponte Vedra", "FL"),
                    ("St. Augustine", "FL")],
    },
    {
        "name": "Pittsburgh",
        "core": ("Pittsburgh", "PA"),
        "suburbs": [("Cranberry Township", "PA"), ("Bethel Park", "PA"),
                    ("Monroeville", "PA")],
    },
    {
        "name": "Greenville",
        "core": ("Greenville", "SC"),
        "suburbs": [("Greer", "SC"), ("Simpsonville", "SC"),
                    ("Anderson", "SC"), ("Spartanburg", "SC")],
    },
]
