# Prospective GPU execution check

The user explicitly approved one temporary g5.xlarge in Ohio, a USD 5 budget,
and termination within two hours on 2026-09-14. The existing 512-triplet CPU
confirmation remains the registered primary experiment and continues unchanged.

A label-blind benchmark selected 128 development input texts by SHA256 order.
After adding the required device-to-host storage copy, the A10G processed them
at 168.34 texts/second with the same pinned weights, CTranslate2 4.8.2,
int8_float32, singleton batches, tokenization and original NumPy pooling.
Vectors were repeatable on the GPU but differed from the CPU reference: mean
L2 difference .06160, maximum .08962, minimum cosine .99598. These differences
exceed rounding noise. No task labels or prediction scores were used in this
benchmark. The first attempt failed on the CUDA storage interface before
producing benchmark vectors; its log is preserved.

Before encoding or scoring the nine-leaf confirmation on GPU, freeze this
supplement. Encode every one of its 8,500 unique texts on the same GPU backend;
do not mix CPU and GPU ReProver vectors. Keep the original syntax and MiniLM
vectors, all assignments, sampled proofs, tie bits, metrics and analysis
functions unchanged. GPU acquisition receives input strings and provenance,
not relation labels. Record a separate device manifest and source hashes.

Apply the existing headroom calculation before cloud scoring. Reproduce the
nine-control comparisons and original-plan supplemental controls descriptively
on this complete GPU arm. Compare with the CPU outcomes once those are complete.
Report vector differences and prediction agreement, including disagreements.
This checks hardware sensitivity; it is not an independent statistical
replication, a replacement primary test, or an alternative route to a positive
claim. Do not change the CPU sample size, stop its acquisition based on GPU
outcomes, or select whichever backend gives the preferred result.

Retrieve and verify all GPU artifacts, then terminate the instance promptly and
remove its temporary security group and SSH key registration. The guest timer
and independent local cleanup watchdog remain active as lifetime safeguards.
