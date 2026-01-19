from typing import Any, Dict, Optional
from services.edition.modules.base import BaseEditionModule

class AudioCodecModule(BaseEditionModule):
    """Extracts audio codec."""
    
    CODEC_MAP = {
        "truehd": "Dolby TrueHD",
        "eac3": "Dolby Digital Plus",
        "ac3": "Dolby Digital",
        "dts-hd ma": "DTS-HD MA",
        "dts": "DTS",
        "flac": "FLAC",
        "aac": "AAC",
        "mp3": "MP3",
        "opus": "Opus",
    }

    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        media = self._get_main_media(item_metadata)
        if not media:
            return None
        
        # Audio codec usually in media.audioCodec
        # But we want the main audio stream details (e.g. Atmos)
        
        codec = media.get("audioCodec", "").lower()
        display = self.CODEC_MAP.get(codec, codec.upper())
        
        # Check for Atmos
        part = self._get_main_part(item_metadata)
        if part:
            streams = part.get("Stream", [])
            # Find selected or first audio stream
            # Usually we want the best one? Or just the first one.
            # Plex `Media` usually summarizes the 'best' or main.
            
            # Let's search all audio streams for Atmos if we want to highlight it
            # Or just check the main one.
            # Assuming main audio is what we care about.
            audio = next((s for s in streams if s.get("streamType") == 2 and s.get("selected", False)), None)
            if not audio:
                audio = next((s for s in streams if s.get("streamType") == 2), None)
            
            if audio:
                # Check title or displayTitle for "Atmos"
                title = (audio.get("displayTitle") or "").lower()
                if "atmos" in title:
                    display += " Atmos"
                elif "dts:x" in title:
                    display = "DTS:X"
        
        return display


class AudioChannelsModule(BaseEditionModule):
    """Extracts audio channel layout."""
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        media = self._get_main_media(item_metadata)
        if not media:
            return None
        
        channels = media.get("audioChannels")
        if not channels:
            return None
            
        # Map simple ints to x.1 format
        # 8 -> 7.1, 6 -> 5.1, 2 -> 2.0, 1 -> 1.0
        
        if channels == 8: return "7.1"
        if channels == 7: return "6.1"
        if channels == 6: return "5.1"
        if channels == 2: return "2.0"
        if channels == 1: return "1.0"
        
        return f"{channels}ch"
