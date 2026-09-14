---
dataset_info:
  features:
  - name: problem_id
    dtype: string
  - name: full_proof
    dtype: string
  splits:
  - name: train
    num_bytes: 42296519
    num_examples: 29750
  download_size: 16165753
  dataset_size: 42296519
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
---

This is the 29.7 solutions of Lean-workbook found by [Goedel-Prover-SFT](https://goedel-lm.github.io/).

## Citation
```latex
@misc{lin2025goedelproverfrontiermodelopensource,
      title={Goedel-Prover: A Frontier Model for Open-Source Automated Theorem Proving}, 
      author={Yong Lin and Shange Tang and Bohan Lyu and Jiayun Wu and Hongzhou Lin and Kaiyu Yang and Jia Li and Mengzhou Xia and Danqi Chen and Sanjeev Arora and Chi Jin},
      year={2025},
      eprint={2502.07640},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2502.07640}, 
}
```
