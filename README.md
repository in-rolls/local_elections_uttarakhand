# Uttarakhand Local Election Results

[![CI](https://github.com/in-rolls/local_elections_uttarakhand/actions/workflows/ci.yml/badge.svg)](https://github.com/in-rolls/local_elections_uttarakhand/actions/workflows/ci.yml)
[![Code license: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)

Historical candidate results from Uttarakhand's urban local-body and panchayat elections, collected from the [State Election Commission results portal](https://secresult.uk.gov.in/). The repository preserves the collected CSVs and provides typed Parquet exports, explicit column mappings, and reproducible offline checks.

## Data

| File | Elections | Candidate records |
|---|---|---:|
| [uttarakhand-local-elections.parquet](data/fin/uttarakhand-local-elections.parquet) | Urban: 2008, 2013, 2018, 2019 | 12,530 |
| [uttarakhand-panchayat-elections.parquet](data/fin/uttarakhand-panchayat-elections.parquet) | Panchayat: 2008, 2014, 2019 | 106,382 |
| [uttarakhand-panchayat-elections-haridwar.parquet](data/fin/uttarakhand-panchayat-elections-haridwar.parquet) | Haridwar panchayat: 2010, 2015 | 10,132 |

The original CSVs remain in [data/](data/). [MANIFEST.json](data/fin/MANIFEST.json) records each input and output checksum, schema, and row count. [schemas.json](schemas.json) maps every original Hindi or English header to its exported column. No dataset DOI is recorded in this repository.

| Series | Year | Records |
|---|---:|---:|
| Urban | 2008 | 3,282 |
| Urban | 2013 | 3,411 |
| Urban | 2018 | 5,585 |
| Urban | 2019 | 252 |
| Panchayat | 2008 | 40,746 |
| Panchayat | 2014 | 36,736 |
| Panchayat | 2019 | 28,900 |
| Haridwar panchayat | 2010 | 5,095 |
| Haridwar panchayat | 2015 | 5,037 |

These are counts of collected candidate records, not unique seats or verified statewide coverage. Haridwar's panchayat elections are supplied in a separate file with different election years.

## Column dictionary

`year` is int16 and `source_row` is int32. Source data cells remain strings, with empty cells represented as null. The `_raw` suffix identifies values preserved without substantive recoding. The source-row number starts at 1 after the CSV header and identifies an observation within its file. Repeated observations remain separate.

| Shared columns | Meaning |
|---|---|
| `year`, `district_raw` | Election year and source district label |
| `candidate_raw`, `candidate_votes_raw` | Candidate name and that candidate's vote cell |
| `source_row` | Logical row in the corresponding source CSV |
| `quality_flags` | List of known data concerns; list of strings |

| Urban-only columns | Meaning |
|---|---|
| `body_name_raw`, `ward_category_raw` | Listing's local-body name and combined ward/category text |
| `winner_summary_raw`, `runner_up_summary_raw` | Listing's combined name/party/symbol fields |
| `detail_body_name_raw`, `detail_ward_raw` | Body and ward labels from the detailed result page |
| `party_raw`, `symbol_raw` | Candidate party and symbol |
| `total_votes_polled_raw`, `invalid_votes_raw`, `tender_votes_raw`, `valid_votes_raw` | Contest totals repeated on candidate rows |

| Panchayat-only columns | Meaning |
|---|---|
| `office_raw` | Office: gram-panchayat head, block-panchayat member, or district-panchayat member |
| `declared_results_count_raw`, `unopposed_elected_count_raw` | Source dashboard counts for the district/office, repeated across candidate rows |
| `block_raw`, `gram_panchayat_raw`, `block_ward_raw`, `district_ward_raw` | Source location and ward labels; which fields apply depends on the office |
| `reservation_raw` | Seat-reservation cell |
| `winner_raw`, `winner_symbol_raw`, `winner_votes_raw` | Winner-level fields repeated for the contest |
| `runner_up_raw`, `runner_up_symbol_raw`, `runner_up_votes_raw`, `margin_raw` | Runner-up and reported vote-margin fields |
| `candidate_serial_raw`, `relation_name_raw`, `candidate_symbol_raw` | Detailed candidate serial, father/husband name, and symbol |

The complete mapping retains distinctions among the three Hindi `चुनाव चिन्‍ह`/`प्राप्‍त मत` pairs: winner, runner-up, and candidate. Vote text remains text because the historical scraper already serialized it; conversion does not infer numeric missing values or remove leading zeroes.

## Coverage and known gaps

**Do not sum repeated contest or dashboard totals across candidate rows.** Candidate votes and winner votes describe different units. `unopposed_elected_count_raw` is a repeated dashboard count, not a boolean describing the individual candidate. A separate, verified seat/contest key is needed before aggregating these fields.

The urban data include 43 rows containing Cyrillic characters where the source text appears misdecoded. They carry `text_encoding_suspect`. The two panchayat rows without candidate names carry `candidate_missing`. Their original cells are retained; there is no automatic encoding repair or row deletion.

The original scripts caught table-parsing errors and continued, then dropped exact duplicate rows before writing CSVs. Failures were not retained in a structured manifest, so missing contests cannot be enumerated from these files alone. The stored urban script also contains early loop exits and does not reproduce the entire committed multi-year collection as written. Coverage should therefore be assessed from the source records and independent election totals, rather than inferred from the scraper's year list.

There are no saved HTML responses or complete acquisition receipts in this repository. Exact capture times and per-record retrieval histories are unavailable. These files do not supply a validated cross-year seat panel, stable administrative codes, or a complete roster of unopposed winners.

## How collected

| Series | Historical source route | Method |
|---|---|---|
| Urban | `secresult.uk.gov.in`, urban result and candidate-detail forms | ASP.NET form submissions, combining contest summaries with detailed candidate tables |
| Panchayat | `secresult.uk.gov.in/panch_result/` | District/office dashboard links, contest tables, and candidate-detail pages |
| Haridwar panchayat | Same panchayat system, separate 2010/2015 selections | A separate collection script for Haridwar's election cycles |

The [historical implementation](https://github.com/in-rolls/local_elections_uttarakhand/tree/df9ab6f) preserves the collection scripts. The current converter reads only retained CSVs and makes no network requests. Each Parquet row can be traced to its source file and row number, and `make verify-data` checks all exported values against the declared source mapping.

## Usage

```sh
git clone https://github.com/in-rolls/local_elections_uttarakhand.git
cd local_elections_uttarakhand
uv sync --frozen --group dev
make verify-data
```

Read a file:

```python
import pyarrow.parquet as pq

table = pq.read_table("data/fin/uttarakhand-local-elections.parquet")
print(table.num_rows)
print(table.schema)
```

Rebuild the Parquet exports from the original CSVs:

```sh
make to-parquet
make verify-data
```

Conversion rejects unexpected columns, years, and malformed rows. It writes each file through a temporary path before replacing an existing export. It neither deduplicates observations nor treats unknown source cells as verified values.

## Development

```sh
make check
make ci-docker
```

The checks run Ruff, formatting, pytest, pre-commit, and exact schema/value/source-checksum verification. CI and the standard Docker target cover Python 3.12 and 3.14. Tests use synthetic records with original-script text, distinct vote fields, leading zeroes, repeated observations, and deliberate failures.

## Citation

Gaurav Sood. *Uttarakhand Local Election Results*. Include the repository URL and commit used. [CITATION.cff](CITATION.cff) provides machine-readable metadata. Contact: [contact@gsood.com](mailto:contact@gsood.com).

## License

The code is [MIT licensed](LICENSE). The underlying election results were published by the Uttarakhand State Election Commission. No separate data license is asserted in this repository.

## 🔗 Adjacent Repositories

- [in-rolls/local_elections_kerala](https://github.com/in-rolls/local_elections_kerala) — Kerala Local Government Seat Reservation Data and Winner Attributes
- [in-rolls/local_elections_up](https://github.com/in-rolls/local_elections_up) — UP Local Election Data --- GP and ULB. Seat reservation, winner, and candidates for some elections
- [in-rolls/local_elections_bihar](https://github.com/in-rolls/local_elections_bihar) — Candidate Info. + Valid Votes Won by Cands. in the 2016 Bihar Panchayat Elections
- [in-rolls/parse_unsearchable_rolls](https://github.com/in-rolls/parse_unsearchable_rolls) — Parse Unsearchable Electoral Rolls
- [in-rolls/mnrega_social](https://github.com/in-rolls/mnrega_social) — MNREGA Social Audit Data
