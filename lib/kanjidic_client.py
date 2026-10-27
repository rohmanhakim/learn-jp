"""KANJIDIC2 XML client for kanji lookup.

Reads the gzipped KANJIDIC2 XML file (data/kanji/kanjidic2.xml.gz),
builds an in-memory index keyed by kanji literal, and returns
on/kun readings, English meanings, JLPT level, grade, and stroke count.
"""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

DEFAULT_DATA_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "kanji" / "kanjidic2.xml.gz"
)


class KANJIDICClient:
    """Client for KANJIDIC kanji dictionary."""

    def __init__(self, data_file: str | Path | None = None):
        self.data_file = Path(data_file) if data_file else DEFAULT_DATA_FILE
        self._index: Optional[dict[str, dict]] = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self._index = {}
        if not self.data_file.exists():
            return
        try:
            with gzip.open(self.data_file, "rb") as f:
                tree = ET.parse(f)
        except Exception:
            return
        root = tree.getroot()
        for char_elem in root.findall("character"):
            literal = char_elem.findtext("literal")
            if not literal:
                continue
            self._index[literal] = self._parse_character(char_elem, literal)

    @staticmethod
    def _parse_character(char_elem: ET.Element, literal: str) -> dict:
        misc = char_elem.find("misc")
        grade: Optional[int] = None
        stroke_count: Optional[int] = None
        jlpt: Optional[int] = None
        if misc is not None:
            grade_text = misc.findtext("grade")
            stroke_text = misc.findtext("stroke_count")
            jlpt_text = misc.findtext("jlpt")
            grade = int(grade_text) if grade_text else None
            stroke_count = int(stroke_text) if stroke_text else None
            jlpt = int(jlpt_text) if jlpt_text else None

        on_readings: list[str] = []
        kun_readings: list[str] = []
        meanings: list[str] = []
        for rm in char_elem.findall("reading_meaning"):
            rmgroup = rm.find("rmgroup")
            if rmgroup is None:
                continue
            for reading in rmgroup.findall("reading"):
                r_type = reading.get("r_type")
                value = reading.text or ""
                if r_type == "ja_on":
                    on_readings.append(value)
                elif r_type == "ja_kun":
                    kun_readings.append(value)
            for meaning in rmgroup.findall("meaning"):
                m_lang = meaning.get("m_lang")
                if m_lang in (None, "en"):
                    value = meaning.text or ""
                    if value:
                        meanings.append(value)

        # Deduplicate while preserving order
        on_readings = list(dict.fromkeys(on_readings))
        kun_readings = list(dict.fromkeys(kun_readings))
        meanings = list(dict.fromkeys(meanings))

        return {
            "character": literal,
            "on_readings": on_readings,
            "kun_readings": kun_readings,
            "meanings": meanings,
            "jlpt": jlpt,
            "grade": grade,
            "strokes": stroke_count,
        }

    def lookup(self, kanji: str) -> Optional[dict]:
        """Look up a kanji character. Returns None if not found or data missing."""
        self._ensure_loaded()
        if self._index is None:
            return None
        return self._index.get(kanji)

    @property
    def loaded(self) -> bool:
        self._ensure_loaded()
        return self._index is not None and len(self._index) > 0