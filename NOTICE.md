# Data sources and attribution

The software in this repository is MIT licensed. Source data remains attributable to its
original provider and may be subject to that provider's terms.

## P2000 Bommel

- https://p2000.bommel.net/
- Bulk CSV: https://p2000.bommel.net/cap2csv.php

Bommel explicitly describes its capcode information as freely usable and intended as a basis
for other programs. It is the mandatory baseline source for this project.

## Capcodes.eu

- https://capcodes.eu/

Capcodes.eu provides capcode, region, service and description data and states that its data is
generated from the P2000netwerk.nl system. The project operator/user has confirmed that this
data may be reused with attribution. This project identifies records from this provider as
`capcodes_eu` and keeps the source URL in provenance metadata.

## TomZulu10 Capcodes Hulpdiensten / Brandweer voertuignummers

- https://www.tomzulu10capcodes-brandweervoertuignummers.nl/

TomZulu10 publishes capcode lists per safety region and is actively maintained. The
project operator/user has confirmed that this data may be reused with attribution. This
project identifies records from this provider as `tomzulu` and keeps the source page URL in
provenance metadata.

## p2000.page

- https://p2000.page/

Not scraped by this project. Without a verified bulk endpoint, collecting the complete capcode
database would require many individual page requests. A provider can be added later if a
suitable bulk/API interface is available.

If a source changes its reuse policy, disable that provider until the policy is clarified.

## TomZulu10 abbreviation lists

The generated abbreviation artifacts may include entries obtained from the public TomZulu10
pages below. Records retain the exact page or embedded-sheet URL used during collection.

- https://www.tomzulu10capcodes-brandweervoertuignummers.nl/afkortingen-hulpdiensten-klik-hier
- https://www.tomzulu10capcodes-brandweervoertuignummers.nl/afkortingen-kustwacht-knrm-reddingsbrigade-klik-hier

The project stores these as attributed source data and does not claim copyright over the source
material. The software itself remains MIT licensed.
