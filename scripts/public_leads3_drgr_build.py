"""Public leads 3, lead 1: CDBG-DR stormwater and planning lines. Writes data/splits/city/drgr_cdbgdr.json.
Sources (all public, held in raw/pl3/, not committed):
  City CDBG-DR Public Hearing Deck, May 2025 (hearing_deck.pdf), pp.11, 14-18: federal plus local funds and project counts.
    https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CDBG/cdbg-dr/CDBG-DR%20Public%20Hearing%20Deck_Website.pdf
  HUD DRGR Quarterly Performance Report B-25-MU-17-0001, Apr 1 to Jun 30 2026 (qpr_q2_2026.pdf), pp.2, 4, 6:
    https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CDBG/cdbg-dr/B-25-MU17-0001_QPR_Q2_2026.pdf
  DRGR Public Data Portal API https://drgr.hud.gov/DRGRPublicService/rest/publicService/directRecipient/197 (grant list).
The counts are the City's own 'under consideration' counts. Equal shares of each ordinance line are OUR proxy
(the deck says final projects, locations and allocations are subject to engineering), and are labelled proxy."""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), "..")
DECK = {"doc": "City of Chicago CDBG-DR Public Hearing Deck (May 2025)", "url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CDBG/cdbg-dr/CDBG-DR%20Public%20Hearing%20Deck_Website.pdf", "page": "11 and 14-18"}
QPR = {"doc": "HUD DRGR Quarterly Performance Report, grant B-25-MU-17-0001, Apr 1 to Jun 30 2026", "url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CDBG/cdbg-dr/B-25-MU17-0001_QPR_Q2_2026.pdf", "page": "2, 4, 6"}
EQ = "Our estimate: the line divided equally by the City's count. The City says final projects, locations and amounts are still subject to engineering, so real units will differ."

def line(dept, auth, acct, amt, **kw):
    d = {"target": {"by": "ordinance_line", "fund": "925D", "dept": dept, "authority": auth, "account": acct}, "expect_amount": amt}; d.update(kw); return d

splits = [
  line("88", "2821", "0540", 221342000, mode="budget_split",
       pieces=[{"name": "104 blocks of new local sewer main (equal share of each block)", "amount": 221341999.84, "basis": "proxy", "kind": "count_x_average",
                "count": 104, "unit_amount": 2128288.46, "unit_label": "blocks", "source": DECK,
                "note": EQ + " 104 x $2,128,288.46. The City's deck says CDBG-DR and local money would 'install new local sewer mains on 104 blocks' (p.14-15). Federal money for all sewer mains is $226,341,802 and local $23,068,233 (p.11).",
                "why": "The City says it wants to build new sewer pipe under 104 city blocks, but it has not published which blocks or what each one will cost."}],
       residual={"name": "Rounding (cents left over from dividing evenly)"},
       side=[{"kind": "official_plan", "label": "City deck p.11: Sewer Mains federal $226,341,802 plus local $23,068,233 = $249,410,035 (this line plus the $5,000,000 trunk sewer design line is $226,342,000 federal)", "amount": 249410035, "period": "2025 plan", "basis": "gov_estimate", "source": DECK},
             {"kind": "official_plan", "label": "HUD DRGR report: project 882821 'New Sewer Main' shows $390,277,600 budgeted for the whole Infrastructure and Mitigation program, nothing drawn yet as of June 30 2026", "amount": 390277600, "period": "to 2031", "basis": "gov_estimate", "source": QPR}]),
  line("88", "2823", "0540", 62097000, mode="budget_split",
       pieces=[{"name": "12 wing storage tanks (equal share of each)", "amount": 62097000, "basis": "proxy", "kind": "count_x_average", "count": 12, "unit_amount": 5174750, "unit_label": "tanks", "source": DECK,
                "note": EQ + " 12 x $5,174,750. Deck p.16: 'Installing 12 wing storage facilities'. Federal $62,096,736 plus local $15,524,184 = $77,620,920 (p.11).",
                "why": "The City plans 12 underground tanks that hold storm water on side streets, but it has not said where they go or what each costs."}],
       side=[{"kind": "official_plan", "label": "City deck p.11 and p.16: wing storage federal $62,096,736 plus local $15,524,184 = $77,620,920", "amount": 77620920, "period": "2025 plan", "basis": "gov_estimate", "source": DECK}]),
  line("84", "281M", "0540", 67104000, mode="budget_split",
       pieces=[{"name": "60 permeable alleys (equal share of each)", "amount": 67104000, "basis": "proxy", "kind": "count_x_average", "count": 60, "unit_amount": 1118400, "unit_label": "alleys", "source": DECK,
                "note": EQ + " 60 x $1,118,400. Deck p.14 and p.17: 'Reconstructing 60 alleyways with permeable pavements'. Federal $67,103,330 plus local $13,420,670 = $80,524,000 (p.11).",
                "why": "The City plans to rebuild 60 alleys so rain soaks into the ground, but it has not published which alleys or what each costs."}],
       side=[{"kind": "official_plan", "label": "City deck p.11 and p.17: permeable alleys federal $67,103,330 plus local $13,420,670 = $80,524,000", "amount": 80524000, "period": "2025 plan", "basis": "gov_estimate", "source": DECK}]),
  line("88", "2822", "0140", 29736000, mode="budget_split",
       pieces=[{"name": "2,100 blocks of sewer cleaning (equal share of each)", "amount": 29736000, "basis": "proxy", "kind": "count_x_average", "count": 2100, "unit_amount": 14160, "unit_label": "blocks", "source": DECK,
                "note": EQ + " 2,100 x $14,160. Deck p.14-15: 'Cleaning and debris removal for 2,100 blocks of sewer lines'. Federal $29,735,732 (p.11)."}],
       side=[{"kind": "official_plan", "label": "City deck p.11 and p.15: grid cleaning federal $29,735,732, no local money", "amount": 29735732, "period": "2025 plan", "basis": "gov_estimate", "source": DECK}]),
  line("88", "2824", "0140", 5000000, mode="side_only",
       note="Plain words: this pays to study new big trunk sewers. The City's deck says it will 'evaluate construction of new trunk sewer lines spanning 52 blocks' (p.16).",
       side=[{"kind": "official_plan", "label": "City deck p.16: DWM will evaluate 52 blocks of trunk sewers. The deck puts no separate dollar figure on it. Action Plan Table 25 (p.50) prices trunk sewer at $19,000,000 per mile", "period": "2025 plan", "basis": "gov_estimate", "source": DECK}]),
  line("54", "2897", "0140", 5000000, mode="side_only",
       note="Plain words: this pays to turn 5 or 6 empty lots into plazas that soak up rain (deck p.18, 'Permeable Outdoor Plazas', $5,000,000).",
       side=[{"kind": "official_plan", "label": "City deck p.18: 5 to 6 permeable outdoor plazas, $5,000,000 total, all federal", "amount": 5000000, "period": "2025 plan", "basis": "gov_estimate", "source": DECK}]),
  line("5", "2825", "0140", 19553758, mode="side_only",
       why="This pays outside contractors who help run the flood-recovery grant. The City's HUD report names one, Guidehouse Inc., but the budget gives only one amount for the whole line.",
       note="HUD's quarterly report lists the whole grant's administration and planning budget as $21,330,400 in two activities: City staff and costs $7,641,172, and the contractor 'Planning & Admin - Contractor' $13,689,228. These are budgets for the life of the grant (to July 2031), not for 2026, so they are not boxes here.",
       side=[{"kind": "drgr_activity", "label": "DRGR activity 02 'Planning & Admin - Contractor' (responsible organization GUIDEHOUSE INC.): total budget for the life of the grant", "amount": 13689228, "period": "to 2031", "basis": "gov_estimate", "source": QPR},
             {"kind": "drgr_activity", "label": "DRGR activity 02: paid to Guidehouse through Jun 30 2026 (cumulative, first report)", "amount": 1577819.10, "period": "to Jun 30 2026", "basis": "paid_to_date", "source": QPR},
             {"kind": "drgr_activity", "label": "DRGR activity 01 'Administration' (City of Chicago): total budget for the life of the grant", "amount": 7641172, "period": "to 2031", "basis": "gov_estimate", "source": QPR},
             {"kind": "drgr_activity", "label": "DRGR activity 01: spent by the City through Jun 30 2026 (cumulative)", "amount": 281544.33, "period": "to Jun 30 2026", "basis": "paid_to_date", "source": QPR}]),
]
out = {"meta": {"author": "public leads 3 agent", "description": "CDBG-DR stormwater and planning lines: City's published project counts (hearing deck May 2025) and HUD DRGR activity budgets (QPR Q2 2026)", "built_by": "scripts/public_leads3_drgr_build.py"}, "splits": splits}
json.dump(out, open(f"{ROOT}/data/splits/city/drgr_cdbgdr.json", "w"), indent=1)
print("wrote", len(splits), "splits")
