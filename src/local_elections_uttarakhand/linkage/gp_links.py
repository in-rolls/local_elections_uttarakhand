"""Link pradhan (gram panchayat head) seats between consecutive elections.

No GP identifier survives between elections. All 89 block names agree across
2008, 2014 and 2019, so a GP pair is a candidate only inside the same district
and block. Names are folded to absorb Devanagari spelling variants and paired
one-to-one by preclink's Hungarian assignment.

2014 prints a serial before every name ("103-अजोलीमल्ली"); it is a list position,
not part of the name, and is removed. Kumaon and Garhwal names distinguish
neighbouring villages by position (मल्ला upper, बिचला middle, तल्ला lower, often
abbreviated म0, त0), twins by खुर्द/कलां, and parts by number (नं0-2). These
are read off the name and veto a pair whose counterpart states a different one.

Names repeated within a block in one election (one name for two GPs, or one
name printed with two reservations) are left unlinked: nothing in the file tells
the two apart.

The check shares nothing with the GP name: the share of linked pairs that have a
candidate name in common across the two elections, against random pairs in the
same block.
"""

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from preclink import Pipeline
from rapidfuzz import fuzz

DATA = Path("data")
SOURCE = DATA / "fin" / "uttarakhand-panchayat-elections.parquet"
OUT = DATA / "linkage"
OFFICE = "प्रधान (ग्राम पंचायत)"
PAIRS = [(2008, 2014), (2014, 2019)]
KEY = ["district", "block", "gram_panchayat"]
NAME_THRESHOLD = 0.80

SERIAL = re.compile(r"^\s*\d+\s*[-.]\s*")
QUALIFIERS = {
    "position": {
        "upper": r"मल्ल[ाी]|म0",
        "middle": r"बिचल[ाी]|बि0",
        "lower": r"तल्ल[ाी]|त0",
    },
    "twin": {"khurd": r"खुर्द", "kalan": r"कलां|कला[ंँ]"},
}
NUMBER = re.compile(r"(?:नं?0\s*-?\s*|[-\s])([0-9]+)\s*\)?\s*$")
FOLDS = [
    (r"[‌‍़]", ""),  # joiners, nukta
    (r"ँ", "ं"),  # chandrabindu -> anusvara
    (r"[ङञणनम]्", "ं"),  # nasal + virama -> anusvara (काण्डा = कांडा)
    (r"ी", "ि"),
    (r"ू", "ु"),
    (r"ै", "े"),
    (r"ौ", "ो"),
    (r"[शष]", "स"),
    (r"ण", "न"),
    (r"व", "ब"),
    (r"[^ऀ-ॿ]", ""),  # spaces, digits, brackets, abbreviation zeros
]
MATRAS = re.compile(r"[ा-्ंः]")


def qualifiers(name):
    found = {}
    for family, members in QUALIFIERS.items():
        hits = {m for m, p in members.items() if re.search(p, name)}
        if len(hits) == 1:
            found[family] = hits.pop()
    number = NUMBER.search(name)
    if number:
        found["number"] = int(number.group(1))
    return found


def fold(name):
    text = unicodedata.normalize("NFC", SERIAL.sub("", name or ""))
    for members in QUALIFIERS.values():
        for pattern in members.values():
            text = re.sub(pattern, " ", text)
    text = NUMBER.sub(" ", text)
    for pattern, replacement in FOLDS:
        text = re.sub(pattern, replacement, text)
    return text


def similarity(a, b):
    if not a or not b:
        return 0.0
    skeleton = fuzz.ratio(MATRAS.sub("", a), MATRAS.sub("", b)) - 5
    return max(fuzz.ratio(a, b), skeleton) / 100


def conflict(qa, qb):
    return any(k in qb and qb[k] != v for k, v in qa.items())


@dataclass(frozen=True, slots=True)
class PlaceName:
    """preclink comparison on (folded name, qualifiers) pairs."""

    column: str = "name_key"
    weight: float = 1.0

    def compare(self, left, right):
        scores = [
            0.0 if conflict(qa, qb) else similarity(a, b)
            for (a, qa), (b, qb) in zip(left, right, strict=True)
        ]
        return pd.Series(scores, index=left.index)


def seats(source, year):
    d = source[(source["year"] == year) & (source["office_raw"].str.strip() == OFFICE)]
    d = d.assign(
        district=d["district_raw"].str.strip(),
        block=d["block_raw"].str.strip(),
        gram_panchayat=d["gram_panchayat_raw"].str.strip(),
    )
    candidates = d.groupby(KEY)["candidate_raw"].agg(
        lambda s: frozenset(fold(n) for n in s.dropna() if fold(n))
    )
    g = (
        d.groupby(KEY)
        .agg(
            candidates=("candidate_raw", "size"),
            reservations=("reserved_raw", "nunique"),
        )
        .join(candidates.rename("candidate_names"))
    )
    # one name printed with two reservations is two GPs the file cannot tell
    # apart (the pooled build splits them); neither is linked
    g = g[g["reservations"] <= 1]
    g = g.reset_index()
    g["base"] = g["gram_panchayat"].map(fold)
    g["qualifiers"] = g["gram_panchayat"].map(
        lambda n: json.dumps(qualifiers(n), sort_keys=True)
    )
    # one name for two GPs in a block: neither can be linked
    g = g[~g.duplicated(["district", "block", "base", "qualifiers"], keep=False)].copy()
    g["group"] = g["district"] + "|" + g["block"]
    g["name_key"] = [
        (f, json.loads(q)) for f, q in zip(g["base"], g["qualifiers"], strict=True)
    ]
    return g.reset_index(drop=True)


def link(left, right):
    pipeline = (
        Pipeline()
        .block(on="group")
        .score(comparisons=[PlaceName()])
        .filter(min_score=NAME_THRESHOLD)
        .decide(method="hungarian")
        .build()
    )
    found = []
    for group in sorted(set(left["group"]) & set(right["group"])):
        lg = left[left["group"] == group].reset_index(drop=True)
        rg = right[right["group"] == group].reset_index(drop=True)
        matches = pipeline.link(
            lg[["group", "name_key"]], rg[["group", "name_key"]]
        ).matches
        if matches.empty:
            continue
        found.append(
            pd.DataFrame(
                {
                    "left": lg["_row"].to_numpy()[matches["left_index"]],
                    "right": rg["_row"].to_numpy()[matches["right_index"]],
                    "name_score": matches["name_key_score"].to_numpy(),
                }
            )
        )
    return pd.concat(found, ignore_index=True)


def shared_candidate(a, b):
    return np.array([len(x & y) > 0 for x, y in zip(a, b, strict=True)])


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_pair(source, a, b):
    ga, gb = seats(source, a), seats(source, b)
    ga["_row"], gb["_row"] = ga.index, gb.index
    found = link(ga, gb)
    left = ga.loc[found["left"], [*KEY, "base", "candidate_names"]].reset_index(
        drop=True
    )
    right = gb.loc[found["right"], [*KEY, "base", "candidate_names"]].reset_index(
        drop=True
    )
    shared = shared_candidate(left["candidate_names"], right["candidate_names"])
    # random pairs within the same block, as the benchmark for that agreement
    rng = np.random.default_rng(1)
    shuffled = right.groupby(right["district"] + right["block"])[
        "candidate_names"
    ].transform(lambda s: s.iloc[rng.permutation(len(s))].to_numpy())
    random_shared = shared_candidate(left["candidate_names"], shuffled)
    table = pd.concat(
        [
            left[[*KEY, "base"]].add_suffix(f"_{a}"),
            right[[*KEY, "base"]].add_suffix(f"_{b}"),
            found[["name_score"]],
        ],
        axis=1,
    ).rename(columns={f"base_{a}": f"name_folded_{a}", f"base_{b}": f"name_folded_{b}"})
    table["shared_candidate_name"] = shared
    table = table.sort_values([f"district_{a}", f"block_{a}", f"gram_panchayat_{a}"])
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"gp_{a}_{b}.parquet"
    table.to_parquet(path, index=False)
    identical = (table[f"name_folded_{a}"] == table[f"name_folded_{b}"]).to_numpy()
    exact = identical.mean()
    checks = {
        f"gps_{a}": len(ga),
        f"gps_{b}": len(gb),
        "linked": len(table),
        "folded_names_identical_share": round(float(exact), 4),
        "shared_candidate_name_linked": round(float(shared.mean()), 4),
        "shared_candidate_name_random_in_block": round(float(random_shared.mean()), 4),
        "shared_candidate_name_identical_names": round(
            float(shared[identical].mean()), 4
        ),
        "shared_candidate_name_fuzzy_names": round(float(shared[~identical].mean()), 4),
        "fuzzy_links": int((~identical).sum()),
    }
    return {
        "validation": checks,
        "file": {"path": path.name, "rows": len(table), "sha256": sha(path)},
    }


def build():
    source = pd.read_parquet(SOURCE)
    manifest = {
        "purpose": (
            "Research crosswalks between pradhan seats of consecutive elections. "
            "A link states that GP names agree inside the same block, not that "
            "boundaries are unchanged."
        ),
        "matcher": {
            "preclink": version("preclink"),
            "rapidfuzz": version("rapidfuzz"),
            "name_threshold": NAME_THRESHOLD,
        },
        "inputs": {str(SOURCE): sha(SOURCE)},
        "code_sha256": sha(__file__),
        "pairs": {f"{a}_{b}": build_pair(source, a, b) for a, b in PAIRS},
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        json.dumps({k: v["validation"] for k, v in manifest["pairs"].items()}, indent=2)
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
