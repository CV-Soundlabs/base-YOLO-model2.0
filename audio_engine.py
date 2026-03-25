import os

import vlc
import time

_vlc_instance = vlc.Instance("--quiet")

class DeckEngine:
    def __init__(self, deck_id: str = "A"):
        self.deck_id = deck_id
        self._player: vlc.MediaPlayer = _vlc_instance.media_player_new()
        self._eq:     vlc.AudioEqualizer | None = None
        self._loaded  = False
        self._volume  = 1.0

# Loading
    def load(self, filepath: str) -> bool:
        """Load any audio file VLC supports (MP3, WAV, FLAC, AAC…)."""
        try:
            media = _vlc_instance.media_new(filepath)
            self._player.set_media(media)
            self._loaded = True
            print(f"[Deck {self.deck_id}] Loaded: {filepath}")
            return True
        except Exception as e:
            print(f"[Deck {self.deck_id}] Load error: {e}")
            return False
        

#Transport
    def play(self):
        if not self._loaded:
            print(f"[Deck {self.deck_id}] No track loaded.")
            return
        self._player.play()
        print(f"[Deck {self.deck_id}] ▶ PLAY")

    def pause(self):
        self._player.pause()
        print(f"[Deck {self.deck_id}] ⏸ PAUSE")

    def toggle_play_pause(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def cue(self):
        """Stop playback and explicitly seek back to 0:00."""
        self._player.stop()
        self._player.set_time(0)
        print(f"[Deck {self.deck_id}] ⏹ CUE  (rewound to 0:00)")

    @property
    def is_playing(self) -> bool:
        return self._player.is_playing() == 1


#Position / jog wheel
    def get_position(self) -> float:
        """Playback position as fraction 0.0 – 1.0."""
        return max(0.0, float(self._player.get_position()))

    def set_position(self, fraction: float):
        """Seek to a fraction of the track."""
        self._player.set_position(max(0.0, min(1.0, float(fraction))))

    def get_time_ms(self) -> int:
        return max(0, self._player.get_time())

    def set_time_ms(self, ms: int):
        duration = self.get_duration_ms()
        if duration > 0:
            self._player.set_time(max(0, min(ms, duration)))

    def get_duration_ms(self) -> int:
        return self._player.get_length()

    def jog(self, delta_ms: int):
        """
        Nudge forward (positive) or backward (negative) by delta_ms.

        Wire to JOG_WHEEL angle delta in on_mouse():
            dx = current_angle - previous_angle   # degrees
            deck_a.jog(int(dx * 50))              # 50 ms per degree, tune to taste
        """
        self.set_time_ms(self.get_time_ms() + delta_ms)



# Volume
    def set_volume(self, value: float):
        """
        value : float  0.0 (silent) – 1.0 (full)

        Wire to VOLUME_SLIDER in on_mouse():
            deck_a.set_volume(VOLUME_SLIDER['value'] / 100.0)
        """
        value = max(0.0, min(1.0, float(value)))
        self._volume = value
        self._player.audio_set_volume(int(value * 100))

    def get_volume(self) -> float:
        return self._volume

    
# EQ  
    def set_eq(self,
               low:    float = 0.0,
               mid:    float = 0.0,
               high:   float = 0.0,
               preamp: float = 0.0):
    
        if self._eq is None:
            self._eq = vlc.AudioEqualizer()

        self._eq.set_preamp(preamp)

        # Map our 3 bands onto VLC's 10 bands:
        # LOW  → bands 0-2  (~60, 170, 310 Hz)
        for b in range(3):
            self._eq.set_amp_at_index(low, b)
        # MID  → bands 3-5  (~600 Hz, 1k, 3k)
        for b in range(3, 6):
            self._eq.set_amp_at_index(mid, b)
        # HIGH → bands 6-9  (~6k, 12k, 14k, 18k)
        for b in range(6, 10):
            self._eq.set_amp_at_index(high, b)

        self._player.set_equalizer(self._eq)
        print(f"[Deck {self.deck_id}] EQ  "
              f"low={low:+.1f}  mid={mid:+.1f}  high={high:+.1f}  preamp={preamp:+.1f} dB")

    def reset_eq(self):
        """Flat EQ — all bands 0 dB."""
        self.set_eq()


#Cleanup
    def release(self):
        self._player.stop()
        self._player.release()
        print(f"[Deck {self.deck_id}] Released.")


#Factory
def create_decks() -> tuple[DeckEngine, DeckEngine]:
    """Return (deck_a, deck_b) ready to use."""
    return DeckEngine("A"), DeckEngine("B")



#Standalone smoke-test:  python audio_engine.py track_a.mp3 track_b.mp3
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python audio_engine.py track_a.mp3 track_b.mp3")
        sys.exit(1)

    da, db = create_decks()
    da.load(sys.argv[1])
    db.load(sys.argv[2])

    print("\n--- Deck A play 3s ---")
    da.play()
    da.set_volume(0.9)
    time.sleep(3)

    print("--- Jog forward 5 s ---")
    da.jog(5000)
    time.sleep(3)

    print("--- Deck B play alongside ---")
    db.play()
    db.set_volume(0.7)
    time.sleep(3)

    print("--- CUE Deck A ---")
    da.cue()
    time.sleep(1)

    db.release()
    da.release()
    print("Done.")
