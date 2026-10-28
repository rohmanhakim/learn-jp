"""AnkiConnect API wrapper."""

import requests
from typing import List, Optional


class AnkiConnector:
    """Wrapper for AnkiConnect API."""
    
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
    
    def _request(self, action: str, **params) -> dict:
        """Make API request."""
        response = requests.post(
            self.base_url,
            json={"action": action, "version": 6, "params": params}
        )
        return response.json()
    
    def version(self) -> int:
        """Get AnkiConnect version."""
        result = self._request("version")
        return result.get("result")
    
    def create_deck(self, deck_name: str) -> dict:
        """Create a new deck."""
        return self._request("createDeck", deck=deck_name)
    
    def add_note(self, deck_name: str, front: str, back: str, 
                 model: str = "Basic", tags: List[str] = None) -> dict:
        """Add a single note to Anki."""
        note = {
            "deckName": deck_name,
            "modelName": model,
            "fields": {"Front": front, "Back": back}
        }
        if tags:
            note["tags"] = tags
        
        return self._request("addNote", note=note)
    
    def add_notes(self, deck_name: str, notes: List[dict], 
                  model: str = "Basic") -> dict:
        """Add multiple notes to Anki."""
        anki_notes = []
        for note in notes:
            anki_notes.append({
                "deckName": deck_name,
                "modelName": model,
                "fields": {
                    "Front": note["front"],
                    "Back": note["back"]
                },
                "tags": note.get("tags", [])
            })
        
        return self._request("addNotes", notes=anki_notes)
    
    def find_notes(self, query: str) -> List[int]:
        """Find notes matching query."""
        result = self._request("findNotes", query=query)
        return result.get("result", [])
    
    def notes_info(self, note_ids: List[int]) -> List[dict]:
        """Get info about notes."""
        result = self._request("notesInfo", notes=note_ids)
        return result.get("result", [])
    
    def deck_names(self) -> List[str]:
        """Get list of all deck names."""
        result = self._request("deckNames")
        return result.get("result", [])
    
    def deck_stats(self, deck_names: List[str]) -> dict:
        """Get deck statistics."""
        result = self._request("getDeckStats", decks=deck_names)
        return result.get("result", {})
    
    def cards_info(self, card_ids: List[int]) -> List[dict]:
        """Get info about cards, including the note id each card belongs to."""
        result = self._request("cardsInfo", cards=card_ids)
        return result.get("result", [])

    def get_reviews(self, days: int = 30) -> dict:
        """Get review history."""
        result = self._request("getReviews", days=days)
        return result.get("result", {})
    
    def is_available(self) -> bool:
        """Check if Anki is running and AnkiConnect is available."""
        try:
            version = self.version()
            return version is not None
        except requests.exceptions.ConnectionError:
            return False


# Singleton instance
connector = AnkiConnector()
