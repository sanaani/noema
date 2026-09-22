# The theorem globe

`index.html` flattens the unseeded corpus's 11,489 centroids — unit vectors in
1,472 dimensions — onto an ordinary sphere two ways, and says on the page how
much each flattening lies.

Open `index.html` in a browser. The data is embedded in `data.js`, so the page
works from a plain file; the only network fetch is Three.js from a CDN and the
fonts.

Rebuild the data from the committed centroids (about three minutes):

```bash
.venv/bin/python scripts/project-centroids-sphere.py       # writes viewer/data.js
```

Two globes:

* **Global axes** — PCA. Centre the cloud, keep its three principal axes,
  push every point back out to unit length. Deterministic; the three axes carry
  10.9% of the variance and almost no neighbourhood structure (of each
  theorem's ten true nearest neighbours, 0.03 on average are still nearest).
* **Neighbourhood layout** — from the PCA globe, 1,000 rounds pulling each
  theorem along the sphere toward its ten true nearest neighbours and pushing
  it from random others (the UMAP/LargeVis objective, in plain numpy, seed 0).
  Keeps about 2.2 of the 10 neighbours; where a cluster lands means nothing.

Both figures, plus a Spearman rank agreement between true and globe angles
over 300,000 random pairs, are printed by the script and shown on the page.
Click a point to see its five true nearest neighbours drawn on whichever globe
is showing: on the first they scatter, on the second they gather, and neither
is the truth.
