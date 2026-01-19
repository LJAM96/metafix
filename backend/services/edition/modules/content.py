import re
from typing import Any, Dict, Optional
from services.edition.modules.base import BaseEditionModule

class CutModule(BaseEditionModule):
    """Detects special cut versions from filename or title."""
    
    CUT_PATTERNS = {
        r"theatrical[.\s_-]*cut": "Theatrical Cut",
        r"director'?s?[.\s_-]*cut": "Director's Cut",
        r"producer'?s?[.\s_-]*cut": "Producer's Cut",
        r"extended[.\s_-]*(cut|edition)?": "Extended",
        r"unrated[.\s_-]*(cut|edition)?": "Unrated",
        r"final[.\s_-]*cut": "Final Cut",
        r"television[.\s_-]*cut": "Television Cut",
        r"international[.\s_-]*cut": "International Cut",
        r"redux": "Redux",
        r"criterion": "Criterion", # Could be Release too
        r"remastered": "Remastered",
        r"restored": "Restored",
    }
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        # Check filename first (usually most reliable)
        part = self._get_main_part(item_metadata)
        if part:
            filename = part.get("file", "")
            for pattern, label in self.CUT_PATTERNS.items():
                if re.search(pattern, filename, re.IGNORECASE):
                    return label
        
        # Check title
        title = item_metadata.get("title", "")
        for pattern, label in self.CUT_PATTERNS.items():
            if re.search(pattern, title, re.IGNORECASE):
                return label
                
        return None


class ReleaseModule(BaseEditionModule):
    """Detects special release types."""
    
    PATTERNS = {
        r"criterion": "Criterion",
        r"anniversary": "Anniversary Edition",
        r"collector'?s?[.\s_-]*edition": "Collector's Edition",
        r"special[.\s_-]*edition": "Special Edition",
        r"diamond[.\s_-]*edition": "Diamond Edition",
        r"platinum[.\s_-]*edition": "Platinum Edition",
        r"signature[.\s_-]*edition": "Signature Edition",
        r"imax": "IMAX",
        r"open[.\s_-]*matte": "Open Matte",
    }
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        part = self._get_main_part(item_metadata)
        filename = part.get("file", "") if part else ""
        title = item_metadata.get("title", "")
        
        for pattern, label in self.PATTERNS.items():
            if re.search(pattern, filename, re.IGNORECASE) or \
               re.search(pattern, title, re.IGNORECASE):
                return label
        return None


class SourceModule(BaseEditionModule):
    """Detects media source from filename."""
    
    SOURCE_PATTERNS = {
        r"\bremux\b": "REMUX",
        r"\bblu-?ray\b|\bbd\b": "BluRay",
        r"\bbdrip\b": "BDRip",
        r"\bweb-?dl\b": "WEB-DL",
        r"\bwebrip\b": "WEBRip",
        r"\bhdtv\b": "HDTV",
        r"\bdvd\b": "DVD",
        r"\bdvdrip\b": "DVDRip",
        r"\bvhs\b": "VHS",
        r"\blaserdisc\b": "LaserDisc",
    }
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        part = self._get_main_part(item_metadata)
        if not part:
            return None
            
        filename = part.get("file", "")
        for pattern, label in self.SOURCE_PATTERNS.items():
            if re.search(pattern, filename, re.IGNORECASE):
                return label
        return None


class ShortFilmModule(BaseEditionModule):
    """Detects if it's a short film (e.g. < 40 mins)."""
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        duration_ms = item_metadata.get("duration")
        if not duration_ms:
            return None
            
        minutes = int(duration_ms) / 60000
        if minutes < 40:
            return "Short Film"
        return None


class SpecialFeaturesModule(BaseEditionModule):
    """Detects if it has extras."""
    # This might require checking 'Extras' metadata or checking local files if scanning locally
    # Plex metadata has 'Extras' key often? Or separate endpoint.
    # For now, simplistic check if 'Extras' key exists and is populated
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        if item_metadata.get("Extras"):
            return "Extras"
        return None
