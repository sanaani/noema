# Phase 14 judge prompt (sent verbatim to each judge subagent, with a batch path)

You are judging how a mathematics paper uses one of its references.

Read the JSON file `{BATCH}`. It is a list of items. Each item has:
- `tool`: the title of a cited work (a book or paper), with its first author and year;
- `citing_paper` and `citing_area`: the arXiv paper that cites it, and its arXiv area;
- `contexts`: up to 5 passages of the citing paper's LaTeX source around each
  citation of the tool, each with its section heading.

For each item, decide from the contexts alone:

- **used**: a result, method or construction from the tool is applied in the
  paper's own argument: a proof, computation, construction or estimate relies
  on it (for example "by Theorem 4.2 of [T]", "we follow the method of [T]",
  "using the bound in [T, Lemma 3]", "the operator defined in [T]" when the
  paper then works with it).
- **passing**: cited only as background, survey, history, related work,
  notation, a standard definition that is not then relied on, or a pointer
  for further reading.
- **unclear**: the contexts do not show which.

Judge each item on its own. Do not look at other files, do not search, and do
not guess from the titles alone; if the contexts are uninformative, say
unclear.

Write your answer as a JSON list to `{OUT}`, one object per item, in the same
order: `{"item": "<item id>", "label": "used" | "passing" | "unclear",
"reason": "<one short sentence>"}`. Then reply with only the number of items
labelled.
