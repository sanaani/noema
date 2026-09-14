# Label-blind GPU benchmark

The user approved one temporary AWS g5.xlarge (A10G) in Ohio. A deterministic
sample of 128 cached eight-leaf development input texts was selected solely by
SHA256 text order. No task labels or relation scores entered the benchmark.

`selection.json` fixes the source cache, sample and code checksums. `reference.npz`
contains the CPU reference; `gpu-vectors.npz` contains the CUDA outputs, with
runtime, timing and numerical differences in `gpu-report.json`. The encoder
weights, int8_float32 compute type, singleton batches, byte tokenization and
NumPy pooling are unchanged. The GPU adapter only copies output storage to CPU.

The successful run took 0.76035 seconds for 128 texts after warm-up (168.34/sec).
The short reference-host CPU comparison measured about 0.667/sec, using grouped
checkpoints over 120 seconds; the approximately 250-fold comparison is a runtime
estimate, not a controlled multi-repetition hardware benchmark.

GPU vectors were repeatable for the repeated first input but not equal to CPU:
mean L2 difference 0.06160, maximum 0.08962, minimum cosine 0.99598. These exceed
rounding noise. The first attempt failed before producing measured vectors
because CUDA StorageView output required an explicit transfer to host memory.
Its failure log is preserved. No primary experiment cache was modified.

The complete nine-leaf hardware check is archived separately at
`../gpu-execution-check-v1/`. The registered CPU confirmation remains primary.
