# Current State objects: one vector per recorded state

This is the current representation requested by the user: **26,820 recorded states,
26,820 separately stored vector rows, grouped under 256 theorem identities**.
Each record keeps its own ID, full recorded text, proof, trace and position.
There is no deduplication of states or vector rows. Identical coordinates are
stored repeatedly as independent rows in uncompressed float64 NPY files.

Open [explore.html](explore.html) locally. Every displayed state gets a marker;
coincident markers can be inspected individually through the state-record list.
The common 2D projection was fitted to all 26,820 rows, with repetitions retained.
It is illustrative; original-space certificates classify the objects.

- `states.jsonl`: one full state record per line, with its physical `vector_row`.
- `vectors-*.npy`: 26,820 physical rows, 1,472 float64 coordinates per row,
  315,832,320 numerical bytes. Fourteen uncompressed chunks, each under 24 MB.
- `vector-manifest.json`: chunk row ranges, checksums and fixed encoder provenance.
- `objects.json`: every theorem's complete list of recorded states and vector rows.
- `verification.json`: every row and association checked against the original corpus.
- `analysis.json`, `pair-results.jsonl`: all 32,640 saved geometric certificates
  independently checked against every current physical row. The saved planes and
  witnesses are reused as proposed certificates; each is tested on the full arrays.
- `projection-*.npy`, `projection.json`: projection fitted to all recorded rows.
- `summary.json`, `SHA256SUMS`: counts and durable integrity checks.

The migration copies each state's already computed coordinates into its own row.
It does **not** claim a new encoder run or perturb equal coordinates to make them
look different. No GPU was needed. The current encoder script also schedules and
checkpoints by individual record ID, so future encoding does not collapse equal
texts into a shared vector file.

The original corpus and source proofs remain in `../state-object-v1/`, preserved
unchanged. Twenty-four inventoried proof records still have trace gaps; one theorem
has no validated recorded states, so 255 objects are nonempty. The input-identity
[audit](../../docs/state-input-identity-audit-v1.md) still applies: these inputs are
printed local-goal displays, and missing internal mathematical context has not
been restored merely by storing separate vector rows.

Verify and analyze from the repository root:

```sh
python scripts/verify-state-record-vectors.py --records results/state-object-records-v1
OPENBLAS_NUM_THREADS=1 python scripts/analyze-state-record-objects.py \
  --records results/state-object-records-v1
```

To encode a newly assembled corpus with a compatible GPU and fixed model:

```sh
python scripts/encode-state-object-states.py --corpus path/to/corpus.json.gz \
  --model path/to/reprover --output outputs/encoding-records
```

The encoder's output cache is keyed by individual record identity; an old shared
text cache is rejected. The `materialize-state-record-vectors.py` migration script
is specifically for recovering all individual rows from the already saved run.
