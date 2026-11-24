# Export Neighbours

[Explore export destinations on CoolCode](https://coolcode.ca/exportneighbours/)

<!-- coolcode:guide -->
Choose a province, product and month to see where its domestic exports went. Compare a single month or January through the selected month with the same period one year earlier. Follow one destination’s share across months, inspect the CAD values behind the chart, or download every destination in your comparison. The Nova Scotia preset covers live, fresh or chilled lobster. The British Columbia preset covers five softwood lumber codes.
<!-- /coolcode:guide -->

## What goes into a share

The source is Statistics Canada’s [Canadian International Merchandise Trade domestic exports files](https://open.canada.ca/data/en/dataset/2909a648-5753-4924-878a-b069392d9cde), using customs-basis values in current Canadian dollars. The province or territory of origin identifies where the goods were produced. The destination is the last country known when the goods were exported. Re-exports are excluded. A destination share describes trade value. Prices and quantities can both change.

Each period sums monthly export values to every destination for the same origin and product, including smaller destinations hidden in the initial eight-row view. A destination without a reported row contributes no recorded dollars. A share is available only when its denominator is positive. January through September is compared with January through September a year earlier, including when later months of that prior year are available. The first year has no prior-period comparison. A change from 40% to 45% is a five-percentage-point gain. Revisions in the annual source archives replace previous values.

| Product | Included HS codes |
| --- | --- |
| Live, fresh or chilled lobster | 030632 |
| Frozen lobster | 030612 |
| Prepared or preserved lobster | 160530 |
| Softwood lumber | 440711, 440712, 440713, 440714, 440719 |
| Wheat and meslin | 1001, all HS6 descendants |
| Crude petroleum oils | 2709, all HS6 descendants |
| Fish, crustaceans and other aquatic invertebrates | 03 |
| Wood, wood articles and wood charcoal | 44 |
| All merchandise | All HS2 chapters |

Each row is a separate selection. Broad chapters overlap the more specific selections. The lobster presets exclude rock lobster and crawfish. All merchandise and the two chapter selections use the HS2 file. Other selections use the HS6 file. US state rows are summed to the United States. We never sum the HS2, HS6 and HS8 files together.

## Data and reuse

The checked edition starts in January 2023. [Edition metadata](https://coolcode.ca/exportneighbours/data/edition.json) includes every covered month, ISO-style source destination codes, product definitions, retrieval date and source archive links. The [full gzip-compressed CSV](https://coolcode.ca/exportneighbours/data/exports.csv.gz) has columns for month (YYYYMM), province code, destination code, product key and nominal domestic export CAD. Files retain only reported rows. The destination and product dictionaries are in the edition metadata. A weekly refresh checks for Statistics Canada’s monthly updates and revisions. A failed or regressing refresh leaves the previous release online.

Contains information adapted from Statistics Canada and used under the [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/reference/licence). The processing and presentation are CoolCode’s. Visitors load saved trade files from CoolCode. Filters and downloads are calculated in the browser. The site’s standard visit counter and issue reporting are linked on the page.

## Build

Use Python 3.12 and Node.js 22+. Run `python3 scripts/refresh.py` to retrieve and validate the official archives, or use the committed edition for an offline build. Run `node --test tests/*.test.mjs`, `python3 -m unittest discover -s tests -v`, then `python3 scripts/build.py`. Serve `dist/` locally. For the browser checks install the Playwright dependency from `tests/browser-requirements.txt` and Chromium, then run `python3 tests/browser_smoke.py`. You can set `CHROMIUM_PATH` to a local Chromium executable. The published HTML includes static Dataset structured data pointing to the compressed CSV.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
