"""spaCy blank English pipeline + EntityRuler/Matcher helpers (patterns for degrees, certs, dates)."""

from __future__ import annotations

import spacy
from spacy.matcher import Matcher
from spacy.pipeline import EntityRuler

_nlp_singleton = None


def get_v2_nlp():
    """Process-wide singleton: spacy.blank('en') with ruler + matcher patterns."""
    global _nlp_singleton
    if _nlp_singleton is None:
        nlp = spacy.blank("en")
        ruler = nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})
        ruler.add_patterns(
            [
                {"label": "DEG", "pattern": [{"LOWER": "bachelor"}]},
                {"label": "DEG", "pattern": [{"LOWER": "masters"}, {"LOWER": "degree"}]},
                {"label": "DEG", "pattern": [{"LOWER": "master"}, {"TEXT": "of"}]},
                {"label": "DEG", "pattern": [{"LOWER": "mba"}]},
                {"label": "DEG", "pattern": [{"LOWER": "phd"}]},
                {"label": "DEG", "pattern": [{"LOWER": "m.sc"}]},
                {"label": "DEG", "pattern": [{"LOWER": "b.sc"}]},
                {"label": "CERT", "pattern": [{"LOWER": "aws"}, {"LOWER": "certified"}]},
                {"label": "CERT", "pattern": [{"LOWER": "pmp"}]},
                {"label": "CERT", "pattern": [{"TEXT": {"REGEX": r"(?i)certified"}}]},
            ]
        )
        _nlp_singleton = nlp
    return _nlp_singleton


def make_date_matcher() -> Matcher:
    nlp = get_v2_nlp()
    m = Matcher(nlp.vocab)
    # Jan 2020 – Mar 2021 / Present
    m.add(
        "DATE_RANGE",
        [
            [
                {"IS_ALPHA": True, "LENGTH": {">": 2}},
                {"TEXT": {"IN": ["-", "–", "—", "to", "&"]}},
                {"TEXT": {"REGEX": r"(?i)(present|\d{4})"}},
            ]
        ],
    )
    m.add("MON_YEAR", [[{"TEXT": {"REGEX": r"(?i)^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"}}, {"TEXT": {"REGEX": r"\d{4}"}}]])
    m.add("SLASH_YEAR", [[{"TEXT": {"REGEX": r"\d{1,2}/\d{4}"}}]])
    return m
