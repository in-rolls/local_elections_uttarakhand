# Inferred values

Nothing in this folder is a source value. Each file states how it was inferred,
keeps its inputs beside the result, and is never written back into `data/fin/`.

| File | Row | What is inferred |
| --- | --- | --- |
| `winner_female_probability_{year}.parquet` | An elected pradhan (2008, 2010, 2014, 2015, 2019; 2010 and 2015 are Haridwar) | `winner_female_probability_from_name` |

## Winner sex

The results portal records no sex. `infer/winner_sex.py` infers a probability
from the printed name, following the `name-sex-inference` recipe:

- a character n-gram logistic regression on the Devanagari name;
- naampy's first-name score on the name romanized by indicate's offline model;
- fixed last-word markers (devi, debi, dei, kaur, ... versus singh, lall,
  kumar, ...), written in the spellings indicate produces.

A logistic regression combines them. The labels are recorded candidate sex from
Uttar Pradesh's 2021 pradhan candidates (`local_elections_up`) and Bihar's 2016
and 2021 candidates (`local_elections_bihar`), read at pinned commits and
checked by hash. Uttarakhand was part of Uttar Pradesh until 2000 and prints
names in the same script.

Uttarakhand is a third state, so the model is scored the same way: on names from
one labelled state that the other state's model never saw.

| Test (4,000 unseen names each) | naampy alone | Character model | Combined |
| --- | --- | --- | --- |
| Bihar model on UP names | AUC 0.922 | AUC 0.949 | AUC 0.965, 87.2% correct |
| UP model on Bihar names | AUC 0.927 | AUC 0.978 | AUC 0.987, 93.6% correct |

On Uttarakhand, winners of women's seats must be women:

| Year | Winners scored | Women's-seat winners, mean probability | Women's-seat winners below 0.5 | Open-seat winners, mean probability |
| --- | ---: | ---: | ---: | ---: |
| 2008 | 6,370 | 0.969 | 55 | 0.077 |
| 2014 | 6,621 | 0.974 | 46 | 0.090 |
| 2019 | 5,847 | 0.960 | 62 | 0.154 |

Some of the women's-seat winners below 0.5 carry plainly male names (विनोद,
MANOJ KUMAR) and are source errors. Others are women's names the model misreads
(भागीरथी). 232 winners in 2019 are printed in Latin script. They are scored
without the character model, and their rows say so in
`winner_female_probability_method`.

Use these probabilities as an outcome in aggregate analyses, for example as the
expected share of women, rather than as a label for any person. `MANIFEST.json`
records the input hashes, package versions, the combiner's coefficients,
calibration bands and these checks.

```sh
uv sync --group infer
uv run python -m local_elections_uttarakhand.infer.winner_sex
```
