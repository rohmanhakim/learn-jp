# Anki Integration

## Overview

The system uses **AnkiConnect** plugin to communicate with Anki. This allows the agent to:
- Add new cards to Anki
- Query deck statistics
- Get review history
- Check which cards are due

## Setup

### 1. Install AnkiConnect Plugin

1. Open Anki
2. Go to **Tools → Add-ons**
3. Click **Get Add-ons...**
4. Enter code: `2055492159`
5. Click **OK** and restart Anki

### 2. Verify Installation

AnkiConnect runs on `http://localhost:8765`. Test with:

```bash
curl http://localhost:8765 -X POST -d '{"action":"version","version":6}'
```

Expected response: `{"result": 240701, "error": null}`

---

## API Reference

### Base URL
```
http://localhost:8765
```

### Request Format
```python
import requests

response = requests.post("http://localhost:8765", json={
    "action": "actionName",
    "version": 6,
    "params": { ... }
})
result = response.json()
```

### Response Format
```json
{
    "result": <action_result>,
    "error": null | "<error_message>"
}
```

---

## Common Actions

### 1. Add a Note (Card)

```python
def add_note(deck_name, front, back, tags=None):
    """Add a single card to Anki."""
    note = {
        "deckName": deck_name,
        "modelName": "Basic",
        "fields": {
            "Front": front,
            "Back": back
        }
    }
    if tags:
        note["tags"] = tags
    
    response = requests.post("http://localhost:8765", json={
        "action": "addNote",
        "version": 6,
        "params": {"note": note}
    })
    return response.json()
```

**Example:**
```python
add_note(
    deck_name="Japanese::N5::Vocab",
    front="食べる",
    back="たべる<br>to eat<br>verb"
)
```

---

### 2. Add Multiple Notes

```python
def add_notes(deck_name, notes):
    """Add multiple cards to Anki."""
    anki_notes = []
    for note in notes:
        anki_notes.append({
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": note["front"],
                "Back": note["back"]
            },
            "tags": note.get("tags", [])
        })
    
    response = requests.post("http://localhost:8765", json={
        "action": "addNotes",
        "version": 6,
        "params": {"notes": anki_notes}
    })
    return response.json()
```

---

### 3. Find Notes

```python
def find_notes(query):
    """Find notes matching a query."""
    response = requests.post("http://localhost:8765", json={
        "action": "findNotes",
        "version": 6,
        "params": {"query": query}
    })
    return response.json()["result"]
```

**Query Examples:**
```python
# Find all notes in a deck
find_notes("deck:Japanese::N5::Vocab")

# Find notes with specific tag
find_notes("tag:vocab_n5")

# Find notes containing a word
find_notes("食べる")

# Find notes added today
find_notes("added:1")

# Find notes reviewed in last 3 days
find_notes("rated:3")
```

---

### 4. Get Note Info

```python
def get_note_info(note_ids):
    """Get detailed info about notes."""
    response = requests.post("http://localhost:8765", json={
        "action": "notesInfo",
        "version": 6,
        "params": {"notes": note_ids}
    })
    return response.json()["result"]
```

---

### 5. Get Deck Statistics

```python
def get_deck_stats(deck_name):
    """Get statistics for a deck."""
    response = requests.post("http://localhost:8765", json={
        "action": "getDeckStats",
        "version": 6,
        "params": {"decks": [deck_name]}
    })
    return response.json()["result"]
```

**Response includes:**
- `new_count`: Cards not yet reviewed
- `learn_count`: Cards in learning
- `review_count`: Cards due for review
- `total_in_deck`: Total cards
- `review_today`: Reviews done today

---

### 6. Get Review History

```python
def get_review_history(days=30):
    """Get review history for last N days."""
    response = requests.post("http://localhost:8765", json={
        "action": "getReviews",
        "version": 6,
        "params": {"days": days}
    })
    return response.json()["result"]
```

---

### 7. Create Deck

```python
def create_deck(deck_name):
    """Create a new deck."""
    response = requests.post("http://localhost:8765", json={
        "action": "createDeck",
        "version": 6,
        "params": {"deck": deck_name}
    })
    return response.json()
```

---

### 8. Get List of Decks

```python
def get_decks():
    """Get list of all decks."""
    response = requests.post("http://localhost:8765", json={
        "action": "deckNames",
        "version": 6,
        "params": {}
    })
    return response.json()["result"]
```

---

## Integration Patterns

### Pattern 1: Seed Vocabulary

```python
def seed_vocabulary(vocab_list, level):
    """Add vocabulary to Anki and database."""
    deck = f"Japanese::{level}::Vocab"
    
    # Ensure deck exists
    create_deck(deck)
    
    # Add cards to Anki
    for word in vocab_list:
        result = add_note(
            deck_name=deck,
            front=word["content"],
            back=f"{word['reading']}<br>{word['meaning']}",
            tags=[f"vocab_{level}"]
        )
        
        # Log to database
        if result.get("result"):
            log_to_database(word, result["result"])
```

---

### Pattern 2: Get Due Cards Count

```python
def get_due_count(level):
    """Get count of cards due for review."""
    deck = f"Japanese::{level}::Vocab"
    stats = get_deck_stats(deck)
    return stats.get("result", {}).get("reviews", 0)
```

---

### Pattern 3: Sync Review Results

```python
def sync_reviews_to_db():
    """Sync Anki review results to agent database."""
    # Get recent reviews from Anki
    reviews = get_review_history(days=1)
    
    # Process and log to agent database
    for review in reviews:
        log_session(
            item_id=review["card_id"],
            severity=calculate_severity(review),
            response_time=review["time"]
        )
```

---

## Deck Structure Convention

```
Japanese (deck)
├── N5
│   ├── Vocab (cards)
│   └── Kanji (cards)
├── N4
│   ├── Vocab (cards)
│   └── Kanji (cards)
├── N3
│   ├── Vocab (cards)
│   └── Kanji (cards)
└── ...
```

**Naming Convention:**
- Deck: `Japanese::{level}::Vocab` or `Japanese::{level}::Kanji`
- Tags: `vocab_{level}`, `kanji_{level}`

---

## Card Templates

### Basic Vocabulary Card

**Front:**
```
食べる
```

**Back:**
```
たべる<br>
to eat<br>
<i>verb</i>
```

---

### Vocabulary Card with Audio

**Front:**
```
食べる
```

**Back:**
```
たべる<br>
to eat<br>
<i>verb</i><br>
[sound:Japanese_food_eateru.mp3]
```

---

### Kanji Card

**Front:**
```
人
```

**Back:**
```
ジン、ニン<br>
ひと<br>
person, people<br>
<i>JLPT N5</i>
```

---

## Error Handling

```python
def safe_add_note(deck, front, back):
    """Add note with error handling."""
    try:
        result = add_note(deck, front, back)
        if result.get("error"):
            print(f"Error adding note: {result['error']}")
            return None
        return result.get("result")
    except requests.exceptions.ConnectionError:
        print("Error: Anki is not running or AnkiConnect not installed")
        return None
```

---

## Troubleshooting

### Issue: Connection refused
- Ensure Anki is running
- Ensure AnkiConnect plugin is installed
- Check if port 8765 is blocked

### Issue: Note not added
- Check deck name exists
- Check model name is "Basic" (or your custom model)
- Check for duplicate notes

### Issue: Wrong data
- Verify field names match your note type
- Check encoding (UTF-8 for Japanese)

---

## Resources

- AnkiConnect Documentation: https://foosoft.net/projects/anki-connect/
- Anki Manual: https://docs.ankiweb.net/
- AnkiConnect GitHub: https://github.com/FooSoft/anki-connect
