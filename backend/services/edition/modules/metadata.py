from typing import Any, Dict, Optional
from services.edition.modules.base import BaseEditionModule

class ContentRatingModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        return item_metadata.get("contentRating")

class DurationModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        duration_ms = item_metadata.get("duration")
        if not duration_ms:
            return None
        
        minutes = int(duration_ms) // 60000
        hours = minutes // 60
        mins = minutes % 60
        
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

class RatingModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        rating = item_metadata.get("rating")
        if not rating:
            return None
        return f"{rating:.1f}"

class DirectorModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        directors = item_metadata.get("Director", [])
        if directors:
            return directors[0].get("tag")
        return None

class WriterModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        writers = item_metadata.get("Writer", [])
        if writers:
            return writers[0].get("tag")
        return None

class GenreModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        genres = item_metadata.get("Genre", [])
        if genres:
            return genres[0].get("tag")
        return None

class CountryModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        countries = item_metadata.get("Country", [])
        if countries:
            return countries[0].get("tag")
        return None

class StudioModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        return item_metadata.get("studio")

class LanguageModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        # Check audio streams
        part = self._get_main_part(item_metadata)
        if not part:
            return None
            
        streams = part.get("Stream", [])
        # Find selected audio or first audio
        audio = next((s for s in streams if s.get("streamType") == 2 and s.get("selected", False)), None)
        if not audio:
            audio = next((s for s in streams if s.get("streamType") == 2), None)
            
        if audio:
            lang_code = audio.get("languageCode") # eng, jpn
            lang_title = audio.get("language") # English, Japanese
            
            # Filter if needed (e.g. skip English if configured)
            # Access self.config
            excluded = self.config.get("excluded_languages", ["English"])
            if lang_title in excluded:
                return None
                
            return lang_title
        return None

class SizeModule(BaseEditionModule):
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        part = self._get_main_part(item_metadata)
        if part:
            size_bytes = int(part.get("size", 0))
            gb = size_bytes / (1024**3)
            return f"{gb:.1f} GB"
        return None
