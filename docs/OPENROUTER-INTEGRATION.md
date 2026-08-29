# OpenRouter Integration

## Overview

OpenRouter provides unified API access to multiple LLM providers, including free models. The system uses it for:
- Story generation (reading practice)
- Grammar explanations
- Writing feedback

## Setup

### 1. Get API Key

1. Go to https://openrouter.ai
2. Sign up / Log in
3. Go to **Keys** section
4. Create new API key
5. Save it securely

### 2. Store API Key

**Option A: Environment Variable**
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

**Option B: File**
```bash
echo "sk-or-v1-..." > .openrouter-api-key
```

---

## API Reference

### Base URL
```
https://openrouter.ai/api/v1
```

### Authentication
```python
headers = {
    "Authorization": "Bearer sk-or-v1-...",
    "HTTP-Referer": "https://your-app.com",
    "X-Title": "learn-jp"
}
```

### Request Format (OpenAI-compatible)
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-..."
)

response = client.chat.completions.create(
    model="google/gemma-4-31b-it:free",
    messages=[
        {"role": "user", "content": "Hello"}
    ],
    max_tokens=1000,
    temperature=0.7
)
```

---

## Available Free Models

| Model | Quality | Speed | Best For |
|-------|---------|-------|----------|
| `google/gemma-4-31b-it:free` | ⭐⭐⭐⭐⭐ | Medium | **Story generation (recommended)** |
| `google/gemma-4-26b-a4b-it:free` | ⭐⭐⭐⭐ | Fast | Quick tasks |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ⭐⭐⭐⭐⭐ | Slow | Complex reasoning |
| `nvidia/nemotron-3-super-120b-a12b:free` | ⭐⭐⭐⭐ | Medium | General use |

**Recommendation:** Use `google/gemma-4-31b-it:free` for story generation - best quality for free tier.

---

## Integration Pattern: Story Generation

### 1. Basic Story Generation

```python
def generate_story(vocab_words: list, theme: str = None) -> str:
    """Generate a story using only the provided vocabulary."""
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=get_api_key()
    )
    
    # Create word list
    word_list = ", ".join(vocab_words)
    
    # Build prompt
    prompt = f"""Write a short Japanese story (maximum 500 characters) using ONLY these vocabulary words.

【Vocabulary List】
{word_list}

【Rules】
1. Use only words from the list
2. You may conjugate verbs and adjectives freely
3. You may use basic particles (は、が、を、に、で、と、の)
4. Make the story natural and engaging

{"【Theme】" + theme if theme else ""}

Write the story in Japanese only:"""
    
    # Generate
    response = client.chat.completions.create(
        model="google/gemma-4-31b-it:free",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.8
    )
    
    return response.choices[0].message.content.strip()
```

---

### 2. Story with Comprehension Questions

```python
def generate_story_with_questions(vocab_words: list, level: str) -> dict:
    """Generate story with comprehension questions."""
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=get_api_key()
    )
    
    word_list = ", ".join(vocab_words)
    
    # Adjust question difficulty based on level
    if level in ["n5", "n4"]:
        question_format = """
Questions (in English, multiple choice):
1. [Question]?
   A) [Option]
   B) [Option]
   C) [Option]
   
Answer: [Letter]"""
    else:
        question_format = """
Questions:
1. [Question in Japanese]?
   Answer: [Answer in English]
   
2. What does [Japanese word] mean?
   Answer: [English meaning]"""
    
    prompt = f"""Write a short Japanese story (maximum 500 characters) using ONLY these vocabulary words.

【Vocabulary List】
{word_list}

【Rules】
1. Use only words from the list
2. You may conjugate verbs and adjectives freely
3. Make the story natural

【Output Format】
Story:
[The story in Japanese]

Comprehension Questions:
{question_format}"""
    
    response = client.chat.completions.create(
        model="google/gemma-4-31b-it:free",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.8
    )
    
    # Parse response
    content = response.choices[0].message.content
    story, questions = parse_story_response(content)
    
    return {
        "story": story,
        "questions": questions,
        "vocab_used": vocab_words
    }
```

---

### 3. Writing Feedback

```python
def get_writing_feedback(user_text: str, vocab_used: list) -> str:
    """Provide feedback on user's writing."""
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=get_api_key()
    )
    
    prompt = f"""You are a Japanese language teacher. Provide feedback on this student's writing.

【Student's Writing】
{user_text}

【Vocabulary They Should Use】
{', '.join(vocab_used)}

Please provide:
1. Grammar corrections (if any)
2. Vocabulary usage feedback
3. Suggestions for improvement
4. Encouraging comments

Be constructive and educational."""
    
    response = client.chat.completions.create(
        model="google/gemma-4-31b-it:free",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()
```

---

## Cost Management

### Free Tier Limits
- Rate limits apply (varies by model)
- No cost for `:free` models
- Higher priority for paid models

### Best Practices
1. Cache responses when possible
2. Use shorter prompts for simple tasks
3. Implement retry logic with backoff
4. Monitor usage in OpenRouter dashboard

---

## Error Handling

```python
from openai import OpenAI, APIError, RateLimitError

def safe_generate(prompt: str, model: str = "google/gemma-4-31b-it:free") -> str:
    """Generate text with error handling."""
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=get_api_key()
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except RateLimitError:
        print("Rate limited. Waiting 60 seconds...")
        time.sleep(60)
        return safe_generate(prompt, model)  # Retry
        
    except APIError as e:
        print(f"API error: {e}")
        return None
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

---

## Example Usage in learn-jp

```python
# In agent workflow:

# 1. Get user's known vocabulary from DB
known_vocab = db.get_mastered_vocabulary(user_id)

# 2. Generate story
story = generate_story(
    vocab_words=known_vocab[:50],  # Use up to 50 words
    theme="daily life"
)

# 3. Present to user
print("Read this story:")
print(story)

# 4. Get user's comprehension
user_answer = input("What does it mean? ")

# 5. Provide feedback
feedback = get_writing_feedback(user_answer, known_vocab[:50])
print(feedback)
```

---

## Resources

- OpenRouter Docs: https://openrouter.ai/docs
- Available Models: https://openrouter.ai/models
- API Reference: https://openrouter.ai/api
