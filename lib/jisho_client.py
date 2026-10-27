"""Jisho API client for word lookup."""

import requests
import time
import json
from pathlib import Path
from typing import List, Optional


class JishoClient:
    """Client for Jisho API."""
    
    BASE_URL = "https://jisho.org/api/v1/search/words"
    CACHE_FILE = Path(__file__).parent.parent / "data" / "cache" / "jisho_cache.json"
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        """Load API response cache."""
        if self.CACHE_FILE.exists():
            with open(self.CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save cache to file."""
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def lookup(self, word: str) -> Optional[dict]:
        """Look up a word on Jisho."""
        # Check cache
        if word in self.cache:
            return self.cache[word]
        
        # Rate limiting
        time.sleep(1)
        
        # API request
        response = requests.get(
            self.BASE_URL,
            params={"keyword": word},
            timeout=15,
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        results = data.get("data", [])
        
        if not results:
            return None
        
        # Parse first result
        first = results[0]
        japanese = first.get("japanese", [{}])[0]
        senses = first.get("senses", [{}])
        
        # Collect all meanings from all senses
        all_meanings = []
        for sense in senses[:3]:  # Top 3 senses
            defs = sense.get("english_definitions", [])
            all_meanings.extend(defs[:2])  # Up to 2 defs per sense
        
        pos_list = senses[0].get("parts_of_speech", []) if senses else []
        result = {
            "word": word,
            "reading": japanese.get("reading", ""),
            "meaning": "; ".join(all_meanings[:5]),  # Top 5 meanings
            "part_of_speech": pos_list[0] if pos_list else "",
            "jlpt": first.get("jlpt", []),
            "is_common": first.get("is_common", False)
        }
        
        # Cache result
        self.cache[word] = result
        self._save_cache()
        
        return result
    
    def lookup_batch(self, words: List[str]) -> List[dict]:
        """Look up multiple words."""
        results = []
        for word in words:
            result = self.lookup(word)
            if result:
                results.append(result)
        return results
