from typing import Any, Dict, Optional
from services.edition.modules.base import BaseEditionModule

class ResolutionModule(BaseEditionModule):
    """Extracts video resolution."""
    
    RESOLUTION_MAP = {
        (7680, 4320): "8K",
        (3840, 2160): "4K",
        (2560, 1440): "2K",
        (1920, 1080): "1080p",
        (1280, 720): "720p",
        (720, 576): "576p",
        (720, 480): "480p",
    }
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        media = self._get_main_media(item_metadata)
        if not media or not media.get("videoResolution"):
            return None
        
        width = int(media.get("width", 0))
        height = int(media.get("height", 0))
        
        if width == 0 or height == 0:
            # Fallback to string label
            res_label = media.get("videoResolution")
            if res_label == "4k": return "4K"
            if res_label == "1080": return "1080p"
            if res_label == "720": return "720p"
            if res_label == "sd": return "SD"
            return res_label.upper()

        # Find closest match
        for (w, h), label in self.RESOLUTION_MAP.items():
            # Allow some tolerance (e.g. cropped black bars)
            if width >= w * 0.85 or height >= h * 0.85:
                return label
        
        return "SD"


class DynamicRangeModule(BaseEditionModule):
    """Extracts HDR/Dolby Vision information."""
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        media = self._get_main_media(item_metadata)
        if not media:
            return None
        
        parts = []
        part_obj = self._get_main_part(item_metadata)
        
        # Check streams for DOVI/HDR
        if part_obj:
            streams = part_obj.get("Stream", [])
            video_stream = next((s for s in streams if s.get("streamType") == 1), None)
            
            if video_stream:
                dovi_profile = video_stream.get("DOVIProfile")
                if dovi_profile:
                    parts.append(f"DV P{dovi_profile}")
                elif "dovi" in str(video_stream.get("DOVIPresent", "")).lower():
                    parts.append("Dolby Vision")
                
                hdr_type = str(video_stream.get("displayTitle", "")).upper()
                # Or use 'colorPrimaries', 'colorTrc', 'colorSpace' if needed
                # Plex typically exposes videoHDRType in Media sometimes? No, usually in Stream.
        
        # Some Plex versions put it in Media
        # Only add HDR/HDR10+ if not DOVI (or combined?)
        # Let's check typical structure.
        
        return " . ".join(parts) if parts else None


class VideoCodecModule(BaseEditionModule):
    """Extracts video codec."""
    
    CODEC_MAP = {
        "h264": "H.264",
        "h265": "H.265",
        "hevc": "H.265",
        "mpeg4": "MPEG-4",
        "mpeg2video": "MPEG-2",
        "av1": "AV1",
        "vp9": "VP9",
    }

    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        media = self._get_main_media(item_metadata)
        if not media:
            return None
        
        codec = media.get("videoCodec", "").lower()
        return self.CODEC_MAP.get(codec, codec.upper())


class BitrateModule(BaseEditionModule):
    """Extracts video bitrate."""
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        media = self._get_main_media(item_metadata)
        if not media:
            return None
        
        bitrate = media.get("bitrate") # in kbps
        if not bitrate:
            return None
            
        mbps = int(bitrate) / 1000
        return f"{mbps:.1f} Mbps"


class FrameRateModule(BaseEditionModule):
    """Extracts frame rate."""
    
    def extract(self, item_metadata: Dict[str, Any]) -> Optional[str]:
        media = self._get_main_media(item_metadata)
        if not media:
            return None
        
        # check Video Stream first for precise frameRate
        part = self._get_main_part(item_metadata)
        if part:
            streams = part.get("Stream", [])
            video = next((s for s in streams if s.get("streamType") == 1), None)
            if video and video.get("frameRate"):
                fr = video.get("frameRate")
                # Round logic
                try:
                    fr_float = float(fr)
                    if 23.9 < fr_float < 24.1: return "24fps"
                    if 29.9 < fr_float < 30.1: return "30fps"
                    if 59.9 < fr_float < 60.1: return "60fps"
                    return f"{int(fr_float)}fps"
                except:
                    pass
        
        # Fallback to Media.videoFrameRate (string usually like "24p")
        return media.get("videoFrameRate")
