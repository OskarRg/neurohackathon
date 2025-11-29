import time
import threading
import numpy as np
import mne
from brainaccess.utils import acquisition
from brainaccess.core.eeg_manager import EEGManager

from source.neuro_reader.utils import MINI_CAP_CHANNELS, EEGDataDict, StatusEnum

mne.set_log_level("WARNING")


class EEGService:
    def __init__(self, device_name="BA MINI 052", window_duration=4.0):
        """
        Initialize EEG service.

        :param device_name: Bluetooth device name.
        :param window_duration: Window length (in seconds). 4.0s proves to be a stable value.
        """
        self.device_name: str = device_name
        self.window_duration: float = window_duration
        self.sfreq: int = 250

        self.cap: dict[int, str] = MINI_CAP_CHANNELS

        self.running: bool = False
        self.thread: threading.Thread = None

        self.eeg: acquisition.EEG = acquisition.EEG()
        self.mgr: EEGManager | None = None

        self.latest_data: EEGDataDict = {
            "stress_index": 0.0,
            "alpha_rel": 0.0,
            "beta_rel": 0.0,
            "status": StatusEnum.DISCONNECTED.value,
            "connected": False,
            "is_ready": False,
        }

    def start(self):
        """
        Starts the EEG process in the background
        """
        if self.running:
            print("[EEG Service] Is already working.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print(f"[EEG Service] New thread is running for device: {self.device_name}")

    def stop(self):
        """
        Safely stops the thread.
        """
        print("[EEG Service] Stopping")
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)  # Wait max 5 seconds for closing
        print("[EEG Service] Stopped.")

    def get_data(self):
        """
        Pipeline method used in `__main__.py`.
        Returns a copy of the dictionary.
        """
        return self.latest_data.copy()

    def _worker_loop(self):
        """
        Main data getter loop.
        """
        try:
            with EEGManager() as mgr:
                self.mgr = mgr
                print("[EEG Worker] Connecting...")
                self.latest_data["status"] = StatusEnum.CONNECTED.value

                self.eeg.setup(
                    mgr, device_name=self.device_name, cap=self.cap, sfreq=self.sfreq
                )
                self.eeg.start_acquisition()

                print(f"[EEG Worker] Bufforing {self.window_duration}s of data...")
                self.latest_data["connected"] = True
                self.latest_data["status"] = StatusEnum.BUFFERING.value

                time.sleep(self.window_duration)
                self.latest_data["is_ready"] = True

                while self.running:
                    mne_raw = self.eeg.get_mne()

                    if mne_raw.n_times < self.sfreq * self.window_duration:
                        time.sleep(0.1)
                        continue

                    # 2. Get latest Window (X seconds)
                    current_end = mne_raw.times[-1]
                    tmin: float = max(0, current_end - self.window_duration)
                    mne_window = mne_raw.copy().crop(tmin=tmin)

                    mne_window.filter(4, 40, verbose=False)

                    # Computing PSD (Power Spectral Density)
                    n_fft: int = min(256, len(mne_window.times))
                    spectrum = mne_window.compute_psd(
                        method="welch", fmin=4, fmax=40, n_fft=n_fft, verbose=False
                    )
                    psds, freqs = spectrum.get_data(return_freqs=True)

                    avg_psd = np.mean(psds, axis=0)

                    alpha_mask = (freqs >= 8) & (freqs <= 13)
                    beta_mask = (freqs >= 13) & (freqs <= 30)
                    total_mask = (freqs >= 4) & (freqs <= 40)

                    power_alpha = np.sum(avg_psd[alpha_mask])
                    power_beta = np.sum(avg_psd[beta_mask])
                    power_total = np.sum(avg_psd[total_mask])

                    if power_total == 0:
                        power_total = 1e-9

                    ratio = power_beta / power_alpha if power_alpha > 0 else 0.0

                    mood_text: str = "RELAX"
                    if ratio > 1.5:
                        mood_text = "HIGH STRESS"
                    elif ratio > 1.0:
                        mood_text = "FOCUS"

                    # 6. Aktualizacja zmiennej publicznej
                    self.latest_data.update(
                        {
                            "stress_index": ratio,
                            "alpha_rel": power_alpha / power_total,
                            "beta_rel": power_beta / power_total,
                            "status": StatusEnum.COMPUTED.value,
                            "mood": mood_text,
                            "connected": True,
                            "is_ready": True,
                        }
                    )

                    time.sleep(0.2)

        except Exception as e:
            print(f"[EEG Worker] Critical error: {e}")
            self.latest_data["status"] = StatusEnum.ERROR.value
            self.latest_data["connected"] = False
            self.latest_data["is_ready"] = False
        finally:
            print("[EEG Worker] Closing connection...")
            try:
                self.eeg.stop_acquisition()
                self.eeg.close()
                if self.mgr:
                    self.mgr.disconnect()
            except Exception:
                pass
            self.latest_data["connected"] = False
