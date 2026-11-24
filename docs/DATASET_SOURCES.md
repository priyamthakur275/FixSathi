# Dataset sources: evaluation, licences and attribution

Evaluated 20 Nov 2026. "Imported" means records are present in `data/processed/repair_records.jsonl` from this run.

| Source | Reachable | What it is | Fit for FixSaathi | Licence | Status |
|---|---|---|---|---|---|
| ApplianceDB (free developer sample) | Yes (git clone, commit `ac368a0`) | 438 error codes with meanings, components, severity and per-row source URLs; 288 ranked repair procedures; 20 OEM parts. US and UK markets; 13 brands (LG, Samsung, GE, Whirlpool, Maytag, Bosch, Frigidaire, Hotpoint, Indesit, Beko, Miele, Candy, Hoover). Categories: washer, dryer, dishwasher, refrigerator, oven. | Good for washer and fridge error codes. **No AC or fan data. Not Indian-market codes**: models sold in India can use different code sets. | **ODbL-1.0** (data), CC BY 4.0 (docs). Commercial use allowed with attribution **and share-alike**; embedding without share-alike needs their paid licence. | **Imported**: 280 records (250 washer, 30 refrigerator). 158 rows skipped as out of scope (dishwasher 73, oven 45, dryer 40). 0 rejected. |
| Open Repair Alliance (ORDS v0.3) | Page yes; **data behind a request form** | ~416k EEE + ~204k non-EEE community repair attempts: product category, brand, free-text problem, outcome (Fixed / Repairable / End of life). | Real-world symptom wording and outcomes. Washing machines and fridges sit inside a mixed "Large home electrical" bucket, and ACs are mixed with dehumidifiers. No error codes or steps. | **CC BY-SA 4.0** | **Importer built and tested on a fixture; not imported.** Download the CSV via the form, put it in `data/raw/openrepair/`, and run the pipeline. |
| LBNL HVAC fault detection data | Page yes; files not fetched | Labelled time-series sensor data (20 to 100+ points) for commercial rooftop units, AHUs, VAV boxes, fan coils, chillers and boilers; mostly simulated. | **Not a fit** for repair records: these are building-scale systems, not residential split ACs, and the data is sensor streams rather than symptom-to-fix records. | Not stated on the page; would need confirmation (afdd@lbl.gov). | **Not imported.** |
| MIMII (Hitachi, Zenodo 3384388) | Page yes; ~100 GB not fetched | Normal and anomalous sounds of industrial valves, pumps, fans and slide rails; 8-channel, 16 kHz. | Industrial machines, not household appliances. Possibly useful later for audio anomaly research. | **CC BY-SA 4.0**; cite Purohit et al., arXiv:1909.09347. | **Not imported.** The `dataset_media` table can register clips later. |
| Manufacturer documentation (summarised by FixSaathi) | Yes (fetched 20 Nov 2026) | 21 public troubleshooting pages and user manuals: LG (AC error codes, fridge noises), Daikin India (split AC), Samsung (AC, fridge, microwave), Crompton and Orient (ceiling fans), Kent and Eureka Forbes Aquaguard (purifier manuals). Full list: `docs/SOURCE_ATTRIBUTION.md`. | Fills the AC, fan, fridge, microwave and purifier gaps with Indian-market brands. | Facts paraphrased with attribution; no source text redistributed. Manufacturers keep their rights. | **Imported**: 85 records (split AC 26, ceiling fan 16, microwave 16, water purifier 18, refrigerator 9). 0 rejected. Manuals hosted by a retailer or manual archive are `unverified`. |
| FixSaathi curated guidance | Local | 12 generic, safety-first entries across all six appliance types (`backend/app/knowledge/faults.json`). | Fills gaps (split AC, ceiling fan, MCB, solar). | Project-owned. | Migrated (12/12), status **unverified** (not technician-reviewed). |

## Attribution required in the product

- "Contains data from ApplianceDB (https://github.com/ApplianceDB/ApplianceDB-public), licensed under ODbL v1.0." Each record also keeps its own upstream `source_url` (manufacturer or repair-reference page).
- If Open Repair data is imported: "Contains data from the Open Repair Alliance, CC BY-SA 4.0."

## Licence consequence to decide on (not legal advice)

ODbL and CC BY-SA are share-alike. Publicly using a database derived from ApplianceDB means offering that derived database under ODbL. ApplianceDB says embedding without share-alike needs their commercial licence. Before FixSaathi is sold, choose one of these:
- publish the derived knowledge base under ODbL;
- buy ApplianceDB's licence;
- drop those records.

The pipeline keeps the licence on every record, so filtering by licence is one query.
