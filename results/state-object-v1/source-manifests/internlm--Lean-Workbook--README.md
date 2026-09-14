---
license: apache-2.0
language:
- en
size_categories:
- 10K<n<100K
---

# Lean Workbook
This dataset is about contest-level math problems formalized in Lean 4.

Our dataset contains 57231 problems in the split of Lean Workbook and 82893 problems in the split of Lean Workbook Plus. We provide the natural language statement, answer, formal statement, and formal proof (if available) for each problem. These data can support autoformalization model training and searching for proofs.

We open-source our [code](https://github.com/InternLM/InternLM-Math) and our [data](https://huggingface.co/datasets/InternLM/Lean-Workbook).

Our test environment is based on Lean v4.8.0-rc1 with Mathlib4 of the same version (which can be cloned by specifying the tag v4.8.0-rc1).

# Citation
```
@misc{ying2024lean,
      title={Lean Workbook: A large-scale Lean problem set formalized from natural language math problems}, 
      author={Huaiyuan Ying and Zijian Wu and Yihan Geng and Jiayu Wang and Dahua Lin and Kai Chen},
      year={2024},
      eprint={2406.03847},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```