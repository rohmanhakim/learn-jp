# OpenRouter Integration

## Overview

OpenRouter provides unified API access to multiple LLM providers, including free models. The system uses it for:
- Story generation (reading practice)
- Grammar explanations
- Writing feedback

**Package:** `japanese-story-generator` (handles OpenRouter API)

---

## Setup

### 1. Get API Key

1. Go to https://openrouter.ai
2. Sign up / Log in
3. Go to **Keys** section
4. Create new API key
5. Save it securely

### 2. Store API Key

**Option A: Environment Variable (Recommended)**
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

**Option B: Pass to StoryGenerator**
```python
from japanese_story_generator import StoryGenerator

gen = StoryGenerator(api_key="sk-or-v1-...")
```

---

## Using japanese-story-generator Package

### Basic Story Generation

```python
from japanese_story_generator import StoryGenerator, AnkiVocabParser

# Parse vocabulary from Anki export
parser = AnkiVocabParser("My_Japanese_Vocabulary.txt")
vocab_words = parser.parse()

# Generate story
gen = StoryGenerator(api_key="your-key")
story = gen.generate(
    vocab_words=vocab_words,
    theme="daily life",
    max_length=500,
    strict_vocab=True
)
print(story)
```

### Story with Comprehension Questions

```python
result = gen.generate_with_questions(
    vocab_words=vocab_words,
    level="n5",
    theme="at school"
)

print(result["story"])
print(result["questions"])
```

### Direct OpenRouterClient Usage

```python
from japanese_story_generator import OpenRouterClient

client = OpenRouterClient(api_key="your-key")
response = client.generate("Write a short Japanese story about cats...")
print(response)
```

---

## Available Free Models

| Model | Quality | Speed | Best For |
|-------|---------|-------|----------|
| `google/gemma-4-26b-a4b-it:free` | ⭐⭐⭐⭐ | Fast | **Story generation (default)** |
| `google/gemma-2-9b-it:free` | ⭐⭐⭐ | Fast | Quick tasks |
| `meta-llama/llama-3.1-8b-instruct:free` | ⭐⭐⭐⭐ | Fast | General use |
| `qwen/qwen-2-7b-instruct:free` | ⭐⭐⭐ | Fast | Japanese support |

**Paid Models (Better Quality):**
| Model | Cost | Quality |
|-------|------|---------|
| `openai/gpt-4o-mini` | ~$0.001/1K tokens | ⭐⭐⭐⭐⭐ |
| `openai/gpt-4o` | ~$0.005/1K tokens | ⭐⭐⭐⭐⭐ |

---

## CLI Usage

```bash
# Basic usage
uv run jp-story My_Japanese_Vocabulary.txt

# With theme
uv run jp-story My_Japanese_Vocabulary.txt --theme "at school"

# Different model
uv run jp-story My_Japanese_Vocabulary.txt --model "openai/gpt-4o-mini"

# Verify vocabulary usage
uv run jp-story My_Japanese_Vocabulary.txt --verify
```

---

## Rate Limit Handling

The package includes graceful rate limit handling:

```
⚠️  Rate limit exceeded for model: google/gemma-4-26b-a4b-it:free

Free models have strict rate limits. Try:
  1. Wait a few minutes and retry
  2. Use a different model: --model 'openai/gpt-4o-mini'
  3. Add your own API key: https://openrouter.ai/settings/integrations
```

---

## Integration Pattern in learn-jp

```python
# In agent workflow:

from japanese_story_generator import StoryGenerator, AnkiVocabParser

# 1. Get user's known vocabulary from DB
known_vocab = db.get_mastered_vocabulary(user_id)

# 2. Generate story
gen = StoryGenerator(api_key=os.getenv("OPENROUTER_API_KEY"))
story = gen.generate(
    vocab_words=known_vocab[:50],  # Use up to 50 words
    theme="daily life"
)

# 3. Present to user
print("Read this story:")
print(story)

# 4. Verify vocabulary usage
from japanese_story_generator import ConjugationVerifier
verifier = ConjugationVerifier()
result = verifier.verify(story, known_vocab)

# 5. Log violations for progress tracking
if result["violations"]:
    print(f"Words used outside vocabulary: {len(result['violations'])}")
```

---

## Resources

- OpenRouter Docs: https://openrouter.ai/docs
- Available Models: https://openrouter.ai/models
- API Keys: https://openrouter.ai/keys
- japanese-story-generator: `/home/arif/Projects/japanese-story-generator`
