import librosa
import vlc
import time
import math


class DeckEngine:
    def __init__(self, deck_id: str = "A"):
        self.deck_id = deck_id
        self._instance: vlc.Instance = vlc.Instance("--quiet")
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        self._eq: vlc.AudioEqualizer = vlc.AudioEqualizer()
        self._loaded = False
        self._volume = 0.75        # 0.0 – 1.0
        self._eq_low  = 0.0        # dB offset, stored so _apply_eq can reuse
        self._eq_mid  = 0.0
        self._eq_high = 0.0
        self._initial_bpm: float = 0.0
        self._current_bpm: float = 0.0

    # ------------------------------------------------------------------ loading
    def load(self, filepath: str) -> bool:
        try:
            media = self._instance.media_new(filepath)
            self._player.set_media(media)
            y, sr = librosa.load(filepath)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            self._initial_bpm = tempo[0]
            self._current_bpm = tempo[0]
            self._loaded = True
            # Pin VLC native volume to max ONCE here and never touch it again.
            # Everything after this uses the EQ preamp (per-stream) for volume.
            self._player.audio_set_volume(200)
            self._apply_eq()
            print(f"[Deck {self.deck_id}] Loaded: {filepath}")
            return True
        except Exception as e:
            print(f"[Deck {self.deck_id}] Load error: {e}")
            return False

    # ---------------------------------------------------------------- transport
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
        self._player.stop()
        self._player.set_time(0)
        print(f"[Deck {self.deck_id}] ⏹ CUE (rewound to 0:00)")

    @property
    def is_playing(self) -> bool:
        return self._player.is_playing() == 1

    # --------------------------------------------------------------- position
    def get_position(self) -> float:
        return max(0.0, float(self._player.get_position()))

    def set_position(self, fraction: float):
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
        self.set_time_ms(self.get_time_ms() + delta_ms)

    # ------------------------------------------------------------------ volume
    def set_volume(self, value: float):
        self._volume = max(0.0, min(1.0, float(value)))
        self._apply_eq()

    def get_volume(self) -> float:
        return self._volume

    # --------------------------------------------------------------------- BPM
    def set_bpm(self, bpm: float):
        speed = bpm / self._initial_bpm if self._initial_bpm > 0 else 1.0
        self._player.set_rate(speed)
        self._current_bpm = bpm

    def get_bpm(self) -> float:
        return self._current_bpm

    # ---------------------------------------------------------------------- EQ
    def set_eq(self, low: float = 0.0, mid: float = 0.0,
               high: float = 0.0, preamp: float = 0.0):
        self._eq_low  = low
        self._eq_mid  = mid
        self._eq_high = high
        self._apply_eq()
        print(f"[Deck {self.deck_id}] EQ "
              f"low={low:+.1f} mid={mid:+.1f} high={high:+.1f} dB")

    def reset_eq(self):
        self.set_eq()

    # --------------------------------------------------------- internal helper
    def _apply_eq(self):
        """Single source of truth for writing to the VLC equalizer.
        Volume is expressed as EQ preamp (per-stream, no OS bleed).
        audio_set_volume is never called here — it was fixed to 200 at load.
        """
        v = self._volume
        if v <= 0.0:
            self._eq.set_preamp(-20.0)
            for b in range(10):
                self._eq.set_amp_at_index(-20.0, b)
        else:
            vol_db = max(-20.0, 20.0 * math.log10(v))
            self._eq.set_preamp(vol_db)
            for b in range(3):
                self._eq.set_amp_at_index(max(-20.0, min(20.0, vol_db + self._eq_low)), b)
            for b in range(3, 6):
                self._eq.set_amp_at_index(max(-20.0, min(20.0, vol_db + self._eq_mid)), b)
            for b in range(6, 10):
                self._eq.set_amp_at_index(max(-20.0, min(20.0, vol_db + self._eq_high)), b)
        self._player.set_equalizer(self._eq)

    # ----------------------------------------------------------------- cleanup
    def release(self):
        self._player.stop()
        self._player.release()
        self._instance.release()
        print(f"[Deck {self.deck_id}] Released.")


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------
def create_decks() -> tuple[DeckEngine, DeckEngine]:
    """Return (deck_a, deck_b), each with its own isolated VLC instance."""
    return DeckEngine("A"), DeckEngine("B")


# Standalone smoke-test: python audio_engine.py track_a.mp3 track_b.mp3
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
    db.set_volume(0.4)
    time.sleep(3)
    print("--- CUE Deck A ---")
    da.cue()
    time.sleep(1)
    db.release()
    da.release()
    print("Done.")