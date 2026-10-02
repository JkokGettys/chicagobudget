# Aviation: FAA carryover awards and airport capital program tables

Built by `scripts/aviation_awards_build.py` into `data/splits/city/aviation_awards.json` (5 splits, all applied, 0 skipped).
Companion to `scripts/aviation_build.py` (aviation.json, first pass). Files apply in name order, so aviation.json goes first.

## What was added

| Target | Result |
|---|---|
| O'Hare AIP reserve residual (925F-2810-909A, was $311,668,831.67) | One new named piece: Extend/expand taxiway, FAA grant 31700221962024 (3-17-0022-196-2024), $29,481,263. Residual now $282,187,568.67. |
| Midway AIP reserve residual (925F-2805-909A, $99,801,318.74) | Side info only. No further Midway award qualifies. |
| O'Hare 2026B interest line (0740-2005-0902) | Side info: capital program cost and funding tables, project list, 2026B sources and uses. |
| O'Hare 2026B principal line (0740-2005-0912) | Side info: project fund deposit. |
| Midway 2023A line | Side info: 2023 Airport Projects, 2023 to 2027 Midway capital program by cost and by funding. |

## The rule for carryover awards

Summary G of the 2026 Budget Recommendations says carryover is "calculated at a point in time: August 1 of the prior budget fiscal year"
(PDF p.612). So the right test for the $411.8M and $123.9M reserves is each FAA award's unspent money on 2025-08-01,
not today's balance. The first pass used today's unspent balance, which misses grants that were paid out after August 2025.

USASpending's award funding history (`/api/v2/awards/funding/`, cached in `raw/aviation/faa_award_funding.json`, one record per Treasury
reporting period) gives obligations and cumulative gross outlays by month. Unspent on the carryover date = obligations minus the latest
cumulative outlay per account line, through federal fiscal year 2025 period 10 (July 2025, the last report before Aug 1).

Result, unspent on 2025-08-01 on City ALN 20.106 and 20.116 awards (all vs the reserve):

- O'Hare: $146,095,270 on 8 awards (reserve $411,790,000). Five were already named and two (31700221682018 and 31700221802021) had grant periods that ended before 2026. Only award 31700221962024 ($29,481,263, grant period to 2028-09-09, FAA grant 3-17-0022-196-2024) was not named, because Treasury shows it fully paid by now (a $22.4M catch-up outlay posted in September 2026). It is added as a piece. It fits inside the residual, so the box never exceeds its line.
- Midway: $65,690,740 on 8 awards: four already named and four with grant periods that ended before 2026 ( 31700250932017, 31700250942017, 31700250952018 and 31700251012021, ARPA/AIP, periods ended 2021 to 2025). The four expired ones are not treated as 2026 carryover and are listed in the side facts.
- So at most about 36% (O'Hare) and 53% (Midway) of the reserves can be tied to federal awards. The rest is unexplained by any public record.

Also checked and found not to qualify:
- Awards made after 2025-08-01 (2025-09-22 awards, all FY2026 awards, all IIJA 20.117 awards) cannot be carryover as of Aug 1 2025. Summary G has a separate line, 925F-2827 "O'Hare (BIL)" with $90M anticipated and no carryover, with no ordinance row, so IIJA 2026 awards are NOT placed in any box (O'Hare 20.117 total $83,314,240, Midway $21,410,235). They are mentioned in side info.
- Older awards (before FY2021) are fully paid.
- Award 31700221802021 (ARPA/AIP, $9.1M) showed $5.7M unspent on 2025-08-01 but its grant period ended 2025-08-03, so it is not open in 2026.
- Award 31700221682018 (2018, period ended 2023-09-06) the same.
- Funding history problems: for some awards Treasury's reports stop before the final payment (e.g. Midway 31700251012021 history ends 2023 at $26.0M outlay while USASpending reports $62.8M outlay in total, ARPA). The script uses the reporting-period data only for the Aug 2025 snapshot, so these older rows can look more unspent than they were. That is why only open-in-2026 awards become boxes.

## Other FAA records checked

- USASpending by place of performance (ZIP 60666 and 60638) gave the same City awards as the first pass plus IDOT-recipient awards (state block grants for third-party work) and Gary/Chicago Airport awards. None is a City award. Not used.
- FAA AIP grant histories FY2021 to FY2025 (raw/aviation/*.xlsx) list the same City awards, plus three COVID concessions and runway grants (31700251002021, 31700221812021, 31700221782021) recorded under IDOT as the recipient in USASpending. Paid out and expired 2025. Not used.
- FY2026 AIP grant history: the FAA has not published it (the page cached in raw/aviation/aip_hist_2026.html has no file, the XLSX URL returns 404). FY2026 awards come from USASpending only.
- ALN API JSON files in raw/aviation/aln_*.json are empty (the download failed). Not used.
- ALN 20.117 (Airport Infrastructure Grants from FY2026, created August 2025) is a new listing. FY2024 and 2025 IIJA AIG obligations still sit under 20.106.
- ALN 20.314/20.930/20.931: no City airport awards, except 20.931 award 3170022TDP2025 ($1,000,000, EV infrastructure master plan, O'Hare). It is not AIP and not in this tree.

## Side facts from the airport official statements (all printed, none computed by us)

O'Hare 2026C and 2026D Official Statement, Appendix E, Report of the Airport Consultant (Aug 21 2026). PDF page = pagenumber in the text file, E-pages in brackets.
URL: https://bondlink-cdn.com/1348/ILChicago07a-FIN.1Lay3BJv8.pdf (local raw/bonds/ohare_2026CD_OS.pdf)
- Table S-1 (PDF p.184, E-20) and Table 2-2 (PDF p.210, E-46): capital program cost and funding sources. Total $14,627,114K; previously funded $5,537,774K (includes about $290.1M of executed grants), 2026B bonds $1,004,658K, future bonds $7,484,681K, other $600,000K (airline fees).
- Table 2-1 (PDF p.207, E-43): AULA funding approval, 2018 dollars: the 12 TAP Phase 1 elements (Exhibit L total $6,111,826K), Exhibit N, Exhibit O, with completion years.
- PDF p.215 (E-51): significant ongoing CIP projects with costs (Taxiway N $59.9M, Taxiway V $91.1M, Grade Separated Roads $282.3M, ElevateT3 $305.7M, and more).
- PDF p.71 and p.301 (E-137): IIJA AIG allocations $73.7M, $73.4M, $69.6M, $63.9M, $66.0M (FFY22 to FFY26, $346.6M through August 2026), ATP $110.0M ($50M, $40M, $20M).
- PDF p.300 (E-136) and p.190 (E-26): FAA LOI AGL-10-01, $625M, $605M received by July 2026, final $20M FFY2026 payment pledged to Series 2016E debt service.

O'Hare 2026B Official Statement, Table 1-2 (PDF p.184, E-30): sources and uses of the new money component: project fund $1,004.4M, capitalized interest $134.9M, reserve $63.5M, issuance cost $9.5M.
URL: https://bondlink-cdn.com/1348/ILChicago06a-FIN.MLCK3FoI1.pdf

Midway 2025A/B Official Statement (local raw/bonds/midway_2025AB_OS.pdf, URL https://bondlink-cdn.com/1351/Official-Statement.02duRik1H.pdf):
- Table 2-1 (PDF p.212, E-34): 2023 Airport Projects, $92,590K total, $59,672K paid by Series 2023 bonds.
- Table 2-2 (PDF p.213, E-35): 2023 to 2027 CIP $514.3M by category. Table 2-3 (PDF p.214, E-36): by funding source.
- PDF p.159: IIJA AIG $80.8M and AIP entitlement $19.0M allocated FFY2022 to FFY2025, applied to Runway 13C-31C ($28.2M AIG and $9.6M AIP).
Note: the Midway tables come from the October 2023 consultant report, so they are plans from 2023 (the 2025 letter updates grants and debt only).

## Why capital costs are side info, not boxes

The O'Hare capital program ($14.6B) is paid by airport revenue bond proceeds, grants and airline fees under the airline agreement,
not appropriated line by line. The ordinance has bond debt service lines (interest 0902, principal 0912) and one tiny capital line
(0740-2005-9047, $2.0M). No official statement splits 2026 debt service by project. Putting program costs under the bond lines as boxes
would add up to far more than the lines. The tables are therefore attached to the 2026B bond interest and principal lines and the Midway 2023A line, because those
bond issues' new money pays for the program, and shown as facts only.

## Gaps

- No project-level list ties the unexplained $282.2M (O'Hare) and $99.8M (Midway) of the AIP carryover to anything. Likely explanations the data cannot prove: Budget Book carryover is an estimate of unexpended multi-year grant balance including future-year entitlement not yet awarded.
- FAA FY2026 AIP grant history not published. Awards from 2026-08 onward come from USASpending only.
- The O'Hare 21 program management and construction manager payments belong to item 2 (aviation.json and paid_to_date.json, squid).
- Treasury reporting lag makes the snapshot an upper bound for old awards.
