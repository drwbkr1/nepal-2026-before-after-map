# M2 offline product verification

## Purpose and boundary

This packet defines what must be checked after an authorized download and before any product is admitted to pixel-level QA. It does not activate M2, access an account, create the external custody root, request network data, extract archives, or establish scientific fitness.

The contract covers the eight exact M1-approved products:

- six Sentinel-1 IW GRD dual-polarization archives;
- two Sentinel-2 Level-2A tile 45RUM archives.

The structure requirements follow the official [Sentinel SAFE format](https://sentiwiki.copernicus.eu/web/safe-format), [Sentinel-1 product structure](https://sentiwiki.copernicus.eu/web/s1-products), and [Sentinel-2 Level-2A product description](https://sentiwiki.copernicus.eu/web/s2-products). These references establish expected product organization and band availability; they do not prove the contents or usability of any local archive.

## Container checks

For each exact archive, `scripts/prepare_m2_verification.py` will:

1. require the exact custody path and SAFE root product identity;
2. compare local byte length with provider catalog metadata;
3. compute local SHA-256 as the custody identity;
4. compare local MD5 with the provider-declared MD5 while retaining BLAKE3 as unverified metadata;
5. reject encrypted entries, symbolic links, path traversal, case-insensitive duplicate names, excess members, and implausible expansion sizes;
6. require nonempty analysis-critical SAFE members;
7. run a full ZIP CRC test only after preflight structure and safety checks pass;
8. preserve pass, block, and defer outcomes without extracting or changing the source archive.

The Sentinel-1 profile requires VV and VH measurements plus matching product, calibration, and noise XML. The Sentinel-2 profile requires the Level-2A metadata, 10 m B02/B03/B04/B08 imagery, 20 m B05/B06/B07/B8A/B11/B12 imagery, the 20 m Scene Classification Layer, and quality data.

## What a container pass does not prove

`pass_container_only` means that the exact archive identity, provider MD5, ZIP integrity, and required member inventory passed. It does not prove:

- that JP2 or TIFF rasters open correctly or contain the expected internal metadata;
- correct Sentinel-2 processing-baseline, quantification-value, BOA-offset, or reflectance scaling;
- usable coverage or valid-pixel fractions over an approved AOI;
- acceptable clouds, shadow, snow, saturation, nodata, radar layover, radar shadow, border noise, or speckle;
- compatible orbit geometry, grids, resolution, or before/after co-registration;
- a defensible baseline, observable landscape change, interpretation, or attribution.

Those are explicit post-container gates in the contract and must be recorded separately.

## Current readiness decision

The dataset-readiness audit is **DEFER**. All nine required non-count gates remain unresolved: source terms, custody, schema and quality, coverage, uncertainty and exclusions, pair fitness, reproducibility, evaluation design, and M2 human authorization. The count of eight approved products passes, but a count cannot establish readiness or create authority.

See:

- `contracts/m2-offline-verification-candidate.json`;
- `records/readiness/m2-readiness-audit-input.json`;
- `records/readiness/m2-readiness-decision.json`.

## Static verification

This command is safe before M2 activation. It performs no custody-root access:

```powershell
python scripts/prepare_m2_verification.py --created-at 2026-09-03T16:43:33Z --verify-only
python -m unittest tests.test_m2_verification -v
```

The tests use synthetic ZIP files in temporary directories. They do not substitute fixture content for real evidence.

## Later scan command

Run only after the exact M2 activation is locked, the fresh preflight passes, the external custody root is created under that authority, and an output directory already exists:

```powershell
python scripts/prepare_m2_verification.py `
  --created-at 2026-09-03T16:43:33Z `
  --verify-only `
  --scan-custody-root "C:\Projects\Active\nepal-2026-before-after-map-data\custody" `
  --scan-output "C:\Projects\Active\nepal-2026-before-after-map-data\receipts\m2-container-verification-ATTEMPT.json" `
  --scanned-at-utc YYYY-MM-DDTHH:MM:SSZ
```

The scanner refuses a missing custody root, refuses to create the receipt parent, and refuses to replace an existing receipt.
