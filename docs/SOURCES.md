# Source register

This register distinguishes event framing, technical documentation, and exact catalog-product verification. It is not a claim that any product has usable pixels over the study area.

## Event framing

| Source | Use in this proposal | Qualification |
|---|---|---|
| [Government of Nepal Ministry of Home Affairs relief appeal](https://moha.gov.np/en/post/ha-ra-tha-ka-apa-l-11) | Confirms a major Bhote Koshi flood in Rasuwa District on 26 August 2026 and downstream impacts | Government response notice; not a geomorphic mechanism study |
| [USGS Landslide Hazards Program event page](https://www.usgs.gov/programs/landslide-hazards/science/2026-nepal-debris-avalanche-and-flash-flood) | Preliminary event type, location, source-to-corridor framing, and ongoing satellite mapping context | Marked active and subject to change |
| [WHO Nepal: 2026 Rasuwa flash floods](https://www.who.int/nepal/emergencies/2026-rasuwa-flash-floods) | Independent confirmation of affected Bhote Koshi and Trishuli river corridors | Emergency context, not remote-sensing validation |

The project uses **26 August 2026 debris avalanche and flash flood** as its working event label. Mechanism and exact source geometry remain review questions.

## Satellite data documentation

- [Copernicus Data Space Ecosystem: Sentinel-1](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1)
- [Copernicus Data Space Ecosystem: Sentinel-2](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2)
- [Sentinel-1 GRD API documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html)
- [Sentinel-2 Level-2A API documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html)
- [Copernicus Data Space OData documentation](https://documentation.dataspace.copernicus.eu/APIs/OData.html)
- [Copernicus Browser documentation](https://documentation.dataspace.copernicus.eu/Applications/Browser.html)
- [Copernicus Data Space terms and conditions](https://dataspace.copernicus.eu/terms-and-conditions)
- [Copernicus Data Space citation guidance](https://documentation.dataspace.copernicus.eu/FAQ.html)

Copernicus Sentinel data is described by CDSE as free, full, and open under the Sentinel Data Legal Notice. Public or modified outputs must use the applicable Copernicus Sentinel source notice. Portal materials outside the Sentinel data grant can have narrower noncommercial and redistribution terms, so downloaded quicklooks remain in Git-ignored scratch custody and are not redistributed from this repository.

## Exact product-name check

The ten Sentinel product names in [DATA_AND_METHODS_PLAN.md](DATA_AND_METHODS_PLAN.md) were queried against the public Copernicus Data Space OData Products catalog using exact `Name` equality with the `.SAFE` suffix. All ten returned catalog records.

The machine-readable response summary is stored at [records/source-gates/catalog-candidate-verification.json](../records/source-gates/catalog-candidate-verification.json).

This establishes catalog identity only. It does not establish:

- complete archive availability;
- successful download or checksum;
- redistribution rights for every downstream artifact;
- footprint intersection at the required precision;
- usable cloud-free or artifact-free pixels;
- correct co-registration;
- event causation.

## Retrieval date

Event and documentation pages were reviewed on 31 August 2026 local time. The exact product-name query was run on 1 September 2026 UTC.
