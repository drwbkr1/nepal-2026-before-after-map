window.NEPAL_VIEWER = Object.freeze({
  "wkid": 32645,
  "bounds": [
    325165.27224028925,
    3108005.4275006475,
    366663.00523626537,
    3141766.295022798
  ],
  "range_db": [
    -30,
    0
  ],
  "source_posting_m": 10,
  "render_pixel_size_m": 11.722523445191,
  "registration_verified": false,
  "credits": "ASF DAAC HyP3 2026. Contains modified Copernicus Sentinel data 2026, processed by ESA.",
  "before": {
    "file": "renders/before.png",
    "source_id": "M1-SRC-002",
    "date": "2026-08-16",
    "size": [
      3540,
      2880
    ],
    "sha256": "04450b6809e9c4e27efdaf4d27522b65607f6968dc5831b3c92ebce8f8e7b6cd"
  },
  "after": {
    "file": "renders/after.png",
    "source_id": "M1-SRC-005",
    "date": "2026-08-28",
    "size": [
      3540,
      2880
    ],
    "sha256": "af4b053d9e15d4474b35cd54114bd70f652c44e929727b8bf03f1b44dd5ee27e"
  },
  "difference": {
    "file": "renders/difference.png",
    "source_ids": [
      "M1-SRC-002",
      "M1-SRC-005"
    ],
    "dates": [
      "2026-08-16",
      "2026-08-28"
    ],
    "size": [
      3540,
      2880
    ],
    "sha256": "cb711301a264892c69bd2ec697281b379637b206e5be6efaa8034be5451b51c0",
    "display_range_db": [
      -6,
      6
    ],
    "formula": "after_vv_db - before_vv_db",
    "unverified": true
  }
});
