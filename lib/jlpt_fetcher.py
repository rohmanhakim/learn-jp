"""Fetch JLPT vocabulary from open-source repositories."""

import json
import re
import time
import requests
from pathlib import Path
from typing import List, Dict


class JLPTFetcher:
    """Fetch JLPT vocabulary lists from GitHub repositories."""
    
    # GitHub repository with JLPT vocabulary lists
    BASE_URL = "https://raw.githubusercontent.com/wkei/jlpt-vocab-api/main/data-source/tabs"
    
    # Vocabulary files for each level (kanji + english meaning)
    FILES = {
        "n5": "n5-vocab-kanji-eng.anki.html",
        "n4": "n4-vocab-kanji-eng.anki.html",
        "n3": "n3-vocab-kanji-eng.anki.html",
        "n2": "n2-vocab-kanji-eng.anki.html",
        "n1": "n1-vocab-kanji-eng.anki.html",
    }
    
    DATA_DIR = Path(__file__).parent.parent / "data" / "jlpt"
    
    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def fetch_level(self, level: str) -> List[Dict]:
        """
        Fetch vocabulary for a specific JLPT level.
        
        Args:
            level: JLPT level (n5, n4, n3, n2, n1)
            
        Returns:
            List of dicts with 'word' and 'meaning' keys
        """
        if level not in self.FILES:
            raise ValueError(f"Invalid level: {level}. Must be n5-n1.")
        
        url = f"{self.BASE_URL}/{self.FILES[level]}"
        print(f"Fetching {level} vocabulary from: {url}")
        
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch {level} vocabulary: HTTP {response.status_code}")
        
        # Parse the HTML content
        words = self._parse_vocabulary(response.text)
        
        # Save to file
        output_file = self.DATA_DIR / f"{level}_vocab.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(words)} words to {output_file}")
        return words
    
    def _parse_vocabulary(self, html: str) -> List[Dict]:
        """
        Parse vocabulary from HTML content.
        
        Format: tab-separated with HTML span tags
        question\tanswer
        <span class="...">日本語</span>\t<span class="...">English</span>
        """
        words = []
        
        # Split by lines and skip header
        lines = html.strip().split('\n')
        
        for line in lines[1:]:  # Skip header row
            if not line.strip():
                continue
            
            # Split by tab
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            
            # Extract text from HTML spans
            word = self._extract_text(parts[0])
            meaning = self._extract_text(parts[1])
            
            if word and meaning:
                words.append({
                    "word": word,
                    "meaning": meaning
                })
        
        return words
    
    def _extract_text(self, html: str) -> str:
        """Extract text content from HTML span tags."""
        # Remove HTML tags and extract text
        text = re.sub(r'<[^>]+>', '', html)
        return text.strip()
    
    def fetch_all(self) -> Dict[str, int]:
        """
        Fetch vocabulary for all JLPT levels.
        
        Returns:
            Dict mapping level to word count
        """
        results = {}
        
        for level in ["n5", "n4", "n3", "n2", "n1"]:
            try:
                words = self.fetch_level(level)
                results[level] = len(words)
                print(f"Fetched {level}: {len(words)} words")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"Error fetching {level}: {e}")
                results[level] = 0
        
        return results
    
    def load_cached(self, level: str) -> List[Dict]:
        """
        Load cached vocabulary for a level.
        
        Args:
            level: JLPT level (n5, n4, n3, n2, n1)
            
        Returns:
            List of vocab dicts, or empty list if not cached
        """
        cache_file = self.DATA_DIR / f"{level}_vocab.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []
    
    def get_all_cached(self) -> Dict[str, List[Dict]]:
        """Load all cached vocabulary levels."""
        results = {}
        for level in ["n5", "n4", "n3", "n2", "n1"]:
            results[level] = self.load_cached(level)
        return results


def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch JLPT vocabulary")
    parser.add_argument("--level", choices=["n5", "n4", "n3", "n2", "n1"],
                        help="JLPT level to fetch")
    parser.add_argument("--all", action="store_true",
                        help="Fetch all levels")
    parser.add_argument("--list", action="store_true",
                        help="List cached vocabulary")
    
    args = parser.parse_args()
    
    fetcher = JLPTFetcher()
    
    if args.list:
        # List cached vocabulary
        for level in ["n5", "n4", "n3", "n2", "n1"]:
            words = fetcher.load_cached(level)
            if words:
                print(f"{level.upper()}: {len(words)} words")
            else:
                print(f"{level.upper()}: not cached")
    elif args.all:
        results = fetcher.fetch_all()
        print("\nSummary:")
        for level, count in results.items():
            print(f"  {level.upper()}: {count} words")
    elif args.level:
        words = fetcher.fetch_level(args.level)
        print(f"\nFetched {len(words)} words for {args.level.upper()}")
        print("\nSample (first 5):")
        for w in words[:5]:
            print(f"  {w['word']}: {w['meaning']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
