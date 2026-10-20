# Pradhan seat links between consecutive elections

| File | Row |
| --- | --- |
| `gp_2008_2014.parquet` | A 2008 pradhan seat paired with its 2014 seat |
| `gp_2014_2019.parquet` | A 2014 pradhan seat paired with its 2019 seat |

Each side carries its source key (`district`, `block`, `gram_panchayat`, as
printed and trimmed), suffixed with its year, with the folded name used for
matching. `name_score` is the match score, and `shared_candidate_name` says
whether any candidate name appears in both elections. A link states that two GP
names agree inside one block. It is not an official identifier or proof of
unchanged boundaries.

All 89 block names agree across 2008, 2014 and 2019, so pairs are formed only
inside the same district and block. Names are folded to absorb Devanagari
spelling variants: nukta, chandrabindu, a nasal before a consonant written as
anusvara, long and short vowels, श/ष/स, ण/न, व/ब. 2014's list serials
("103-अजोलीमल्ली") are removed. Place qualifiers veto a pair whose counterpart
states a different one: position (मल्ला/म0 upper, बिचला middle, तल्ला/त0
lower), twin villages (खुर्द, कलां) and part numbers (नं0-2). preclink makes the
optimal one-to-one assignment among pairs scoring at least 0.80.

A name printed twice in one block, or printed once with two reservations, is
two GPs that the file cannot tell apart. Neither is linked.

## Checks

The check shares nothing with the GP name: whether any candidate name recurs
across the two elections. Common names (सुनीता देवी) recur by chance, so the
benchmark is random pairs inside the same block.

| Pair | GPs (earlier / later) | Linked | Fuzzy links | Shared candidate, identical names | Shared candidate, fuzzy names | Shared candidate, random pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2008→2014 | 6,354 / 6,607 | 5,403 | 892 | 8.3% | 7.6% | 3.1% |
| 2014→2019 | 6,607 / 5,840 | 5,042 | 684 | 5.0% | 5.3% | 1.8% |

Fuzzy links share a candidate as often as exact-name links do, which is what
correct fuzzy links would show. Exact matching alone links 3,691 GPs in
2008→2014. `MANIFEST.json` records input and output hashes, the threshold and
these checks.

```sh
uv run python -m local_elections_uttarakhand.linkage.gp_links
```
