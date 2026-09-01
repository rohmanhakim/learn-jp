# Phase 0: Refactor Story Generator

## Goal

Refactor `/home/arif/Projects/japanese-story-generator` into an importable package that can be used by the learn-jp system.

## Current State

The story generator works but has issues:
- Hardcoded file reading
- Commented-out code
- Not modular for import
- Uses Claude API directly (needs OpenRouter)

## Tasks

### Task 1: Restructure Project

**Current structure:**
```
japanese-story-generator/
├── japanese_story_gen.py    # Main script (messy)
├── demo.py
└── ...
```

**New structure:**
```
japanese-story-generator/
├── japanese_story_generator/
│   ├── __init__.py
│   ├── anki_parser.py       # AnkiVocabParser class
│   ├── story_generator.py   # Story generation functions
│   ├── openrouter.py        # OpenRouter API client
│   └── verifier.py          # Conjugation verification
├── scripts/
│   └── generate.py          # CLI entry point
├── tests/
├── pyproject.toml
└── README.md
```

---

### Task 2: Extract AnkiVocabParser

**File:** `japanese_story_generator/anki_parser.py`

```python
"""Parse Anki exported vocabulary."""

import re
from typing import List


class AnkiVocabParser:
    """Parse Anki exported vocabulary - extract only the words."""
    
    def __init__(self, filepath: str = None):
        self.filepath = filepath
        
    def parse(self, filepath: str = None) -> List[str]:
        """Extract just the vocabulary words (kanji only)."""
        filepath = filepath or self.filepath
        if not filepath:
            raise ValueError("No filepath provided")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern: word TAB "HTML content"
        pattern = r'^([^\t\n]+)\t"(.+?)"$'
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        return [kanji for kanji, _ in matches]
    
    def parse_with_readings(self, filepath: str = None) -> List[dict]:
        """Extract words with readings."""
        filepath = filepath or self.filepath
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = r'^([^\t\n]+)\t"(.+?)"$'
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        results = []
        for kanji, html in matches:
            # Extract reading from HTML
            furigana_match = re.search(
                r'<div class=""furigana-text"">([^<]+)</div>',
                html
            )
            reading = furigana_match.group(1).strip() if furigana_match else ""
            results.append({"kanji": kanji, "reading": reading})
        
        return results
```

---

### Task 3: Create OpenRouter Client

**File:** `japanese_story_generator/openrouter.py`

```python
"""OpenRouter API client for story generation."""

from typing import List, Optional
from openai import OpenAI


class OpenRouterClient:
    """Client for OpenRouter API."""
    
    def __init__(self, api_key: str, model: str = "google/gemma-4-31b-it:free"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = model
    
    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.8) -> str:
        """Generate text from prompt."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
```

---

### Task 4: Refactor Story Generator

**File:** `japanese_story_generator/story_generator.py`

```python
"""Story generation using vocabulary-constrained prompting."""

from typing import List, Optional
from .openrouter import OpenRouterClient


class StoryGenerator:
    """Generate Japanese stories using known vocabulary."""
    
    def __init__(self, api_key: str, model: str = "google/gemma-4-31b-it:free"):
        self.client = OpenRouterClient(api_key, model)
    
    def generate(
        self,
        vocab_words: List[str],
        theme: Optional[str] = None,
        max_length: int = 500,
        strict_vocab: bool = True
    ) -> str:
        """Generate a story using only the provided vocabulary."""
        
        word_list = ", ".join(vocab_words)
        
        if strict_vocab:
            constraints = f"""1. Use ONLY words from this list: {word_list}
2. You may use basic particles (は、が、を、に、で、と、の)
3. You may conjugate verbs and adjectives freely
4. Do NOT introduce any new vocabulary"""
        else:
            constraints = f"""1. PRIMARY vocabulary to use: {word_list}
2. You may use basic particles
3. You may conjugate verbs and adjectives freely
4. Aim to use 90%+ of words from the provided list"""
        
        prompt = f"""Write a short Japanese story (maximum {max_length} characters).

【Constraints】
{constraints}

{"【Theme】" + theme if theme else ""}

Write the story in Japanese only:"""
        
        return self.client.generate(prompt, max_tokens=1000)
    
    def generate_with_questions(
        self,
        vocab_words: List[str],
        level: str = "n5",
        theme: Optional[str] = None,
        max_length: int = 500
    ) -> dict:
        """Generate story with comprehension questions."""
        
        word_list = ", ".join(vocab_words)
        
        if level in ["n5", "n4"]:
            question_format = """Questions (in English, multiple choice):
1. [Question]?
   A) [Option]
   B) [Option]
   C) [Option]
   
Answer: [Letter]"""
        else:
            question_format = """Questions:
1. [Question in Japanese]?
   Answer: [Answer in English]"""
        
        prompt = f"""Write a short Japanese story using ONLY these words: {word_list}

【Output Format】
Story:
[The story in Japanese]

Comprehension Questions:
{question_format}"""
        
        response = self.client.generate(prompt, max_tokens=1500)
        
        # Parse response
        story, questions = self._parse_response(response)
        
        return {
            "story": story,
            "questions": questions,
            "vocab_used": vocab_words
        }
    
    def _parse_response(self, response: str) -> tuple:
        """Parse story and questions from response."""
        # Simple parsing - can be improved
        parts = response.split("Comprehension Questions:")
        story = parts[0].replace("Story:", "").strip()
        questions = parts[1].strip() if len(parts) > 1 else ""
        
        return story, questions
```

---

### Task 5: Update CLI Script

**File:** `scripts/generate.py`

```python
#!/usr/bin/env python3
"""CLI for story generation."""

import argparse
import os
from pathlib import Path

from japanese_story_generator import AnkiVocabParser, StoryGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate Japanese stories")
    parser.add_argument("anki_file", help="Anki export file (.txt)")
    parser.add_argument("--theme", help="Story theme")
    parser.add_argument("--api-key", help="OpenRouter API key")
    parser.add_argument("--output", default="story.txt", help="Output file")
    parser.add_argument("--strict", action="store_true", help="Strict vocabulary mode")
    parser.add_argument("--max-length", type=int, default=500, help="Max story length")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: API key required. Use --api-key or set OPENROUTER_API_KEY")
        return 1
    
    # Parse vocabulary
    vocab_parser = AnkiVocabParser(args.anki_file)
    vocab_words = vocab_parser.parse()
    print(f"Found {len(vocab_words)} words")
    
    # Generate story
    generator = StoryGenerator(api_key)
    story = generator.generate(
        vocab_words,
        theme=args.theme,
        max_length=args.max_length,
        strict_vocab=args.strict
    )
    
    # Display and save
    print(f"\n{'='*50}")
    print(f"Story ({len(story)} characters):")
    print(f"{'='*50}")
    print(story)
    print(f"{'='*50}")
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(story)
    
    print(f"\nSaved to: {args.output}")
    return 0


if __name__ == "__main__":
    exit(main())
```

---

### Task 6: Update pyproject.toml

```toml
[project]
name = "japanese-story-generator"
version = "0.2.0"
description = "Generate Japanese stories from vocabulary"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "openai>=1.0.0",
    "requests>=2.28.0",
]

[project.scripts]
jp-story = "scripts.generate:main"
```

---

### Task 7: Add __init__.py

**File:** `japanese_story_generator/__init__.py`

```python
"""Japanese story generator package."""

from .anki_parser import AnkiVocabParser
from .story_generator import StoryGenerator
from .openrouter import OpenRouterClient

__version__ = "0.2.0"
__all__ = ["AnkiVocabParser", "StoryGenerator", "OpenRouterClient"]
```

---

## Task 8: Fix ConjugationVerifier

The current verifier shows 0 conjugations and many violations. Issues:

1. **Vocabulary matching** - MeCab may return different base forms than the vocabulary list
2. **Reading format** - Vocabulary may be in kanji but MeCab returns readings
3. **Dictionary forms** - Need to ensure vocabulary list uses dictionary forms

### Debug Steps
```python
import MeCab
import unidic_lite

tagger = MeCab.Tagger(f"-r /dev/null -d {unidic_lite.DICDIR}")
result = tagger.parseToNode("私は学校に行きます")

while result:
    print(f"surface={result.surface}, features={result.feature.split(',')[:7]}")
    result = result.next
```

### Fix
- Compare MeCab lemma output with vocabulary list format
- Add debug mode to show matching details
- Consider normalizing vocabulary forms

---

## Testing

### Test Story Generation
```bash
# Set API key
export OPENROUTER_API_KEY="sk-or-v1-..."

# Generate story
python scripts/generate.py My_Japanese_Vocabulary.txt --theme "daily life"
```

### Test Import
```python
from japanese_story_generator import StoryGenerator, AnkiVocabParser

# Use in other projects
gen = StoryGenerator(api_key)
story = gen.generate(["食べる", "飲む", "水"])
```

### Test Conjugation Verification
```python
from japanese_story_generator import ConjugationVerifier

verifier = ConjugationVerifier()
result = verifier.verify("私は学校に行きます", ["行く", "学校"])

# Should show: 行きます matches 行く
print(result)
```

---

## Checklist

- [x] Restructure project into package
- [x] Extract AnkiVocabParser class
- [x] Create OpenRouterClient class
- [x] Refactor StoryGenerator class
- [x] Update CLI script
- [x] Update pyproject.toml
- [x] Add __init__.py
- [x] Test story generation
- [x] Test import from learn-jp
- [x] Remove old commented-out code (deleted japanese_story_gen.py)
- [x] Update README.md
- [x] Fix ConjugationVerifier (switched to fugashi, now working)
- [x] Add graceful rate limit error handling

---

## Dependencies Status

### Removed ✅
- `anthropic` (no longer using Claude API)
- `torch` (not using local models)
- `transformers` (not using local models)
- `accelerate` (not using local models)
- `mecab-python3` (replaced by fugashi)

### Added ✅
- `openai` (for OpenRouter API)
- `fugashi` (MeCab wrapper, better API)
- `unidic-lite` (dictionary for fugashi)
