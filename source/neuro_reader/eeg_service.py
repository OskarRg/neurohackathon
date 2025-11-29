import time
import threading
import numpy as np
import mne
from brainaccess.utils import acquisition
from brainaccess.core.eeg_manager import EEGManager

# Wyłączamy logi MNE, żeby nie śmieciły w konsoli
mne.set_log_level('WARNING')

class EEGService:
    def __init__(self, device_name="BA MINI 052", window_duration=4.0):
        """
        Inicjalizacja serwisu EEG.
        :param device_name: Nazwa urządzenia Bluetooth
        :param window_duration: Długość okna analizy (w sekundach). 4.0s jest stabilne.
        """
        self.device_name = device_name
        self.window_duration = window_duration
        self.sfreq = 250
        
        # Konfiguracja elektrod (BrainAccess MINI)
        self.cap = {
            0: "F3", 1: "F4", 2: "C3", 3: "C4",
            4: "P3", 5: "P4", 6: "O1", 7: "O2",
        }
        
        # Zmienne sterujące wątkiem
        self.running = False
        self.thread = None
        
        # Obiekty biblioteki BrainAccess
        self.eeg = acquisition.EEG()
        self.mgr = None
        
        # DANE WYNIKOWE (Bezpieczne do odczytu przez aplikację główną)
        # To jest "interfejs" wymiany danych
        self.latest_data = {
            "stress_index": 0.0,    # Wskaźnik Beta/Alpha ratio
            "alpha_rel": 0.0,       # Względna moc Alpha (0.0 - 1.0)
            "beta_rel": 0.0,        # Względna moc Beta (0.0 - 1.0)
            "status": "DISCONNECTED", # Status tekstowy
            "connected": False,     # Czy urządzenie jest połączone
            "is_ready": False       # Czy bufor jest pełny i dane są wiarygodne
        }

    def start(self):
        """Uruchamia proces EEG w tle."""
        if self.running:
            print("[EEG Service] Już działa.")
            return

        self.running = True
        # daemon=True oznacza, że wątek zamknie się sam, jeśli padnie główny program
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print(f"[EEG Service] Uruchomiono wątek dla urządzenia: {self.device_name}")

    def stop(self):
        """Zatrzymuje proces bezpiecznie."""
        print("[EEG Service] Zatrzymywanie...")
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0) # Czekamy max 5 sekund na zamknięcie
        print("[EEG Service] Zatrzymano.")

    def get_data(self):
        """
        Główna metoda dla Twojej aplikacji.
        Zwraca kopię słownika z najnowszymi wynikami.
        """
        return self.latest_data.copy()

    def _worker_loop(self):
        """Wewnętrzna pętla wątku (Logika biznesowa)."""
        try:
            with EEGManager() as mgr:
                self.mgr = mgr
                print("[EEG Worker] Próba połączenia...")
                self.latest_data["status"] = "CONNECTING"
                
                # Konfiguracja i start
                self.eeg.setup(mgr, device_name=self.device_name, cap=self.cap, sfreq=self.sfreq)
                self.eeg.start_acquisition()
                
                print(f"[EEG Worker] Połączono. Buforowanie {self.window_duration}s danych...")
                self.latest_data["connected"] = True
                self.latest_data["status"] = "BUFFERING"
                
                # Czekamy na napełnienie bufora, żeby filtry nie wariowały
                time.sleep(self.window_duration)
                self.latest_data["is_ready"] = True

                while self.running:
                    # 1. Pobranie danych surowych
                    mne_raw = self.eeg.get_mne()
                    
                    # Sprawdzenie czy jest dość próbek
                    if mne_raw.n_times < self.sfreq * self.window_duration:
                        time.sleep(0.1)
                        continue

                    # 2. Wycięcie okna (ostatnie X sekund)
                    current_end = mne_raw.times[-1]
                    tmin = max(0, current_end - self.window_duration)
                    mne_window = mne_raw.copy().crop(tmin=tmin)

                    # 3. Przetwarzanie
                    # UWAGA: Używamy 4-40Hz, aby uniknąć błędów na krótkich oknach
                    mne_window.filter(4, 40, verbose=False)
                    
                    # Obliczenie PSD (Gęstość Widmowa Mocy)
                    n_fft = min(256, len(mne_window.times))
                    spectrum = mne_window.compute_psd(method='welch', fmin=4, fmax=40, n_fft=n_fft, verbose=False)
                    psds, freqs = spectrum.get_data(return_freqs=True)
                    
                    # Uśredniamy wszystkie kanały
                    avg_psd = np.mean(psds, axis=0)

                    # 4. Wyciągnięcie pasm
                    alpha_mask = (freqs >= 8) & (freqs <= 13)
                    beta_mask = (freqs >= 13) & (freqs <= 30)
                    total_mask = (freqs >= 4) & (freqs <= 40)

                    power_alpha = np.sum(avg_psd[alpha_mask])
                    power_beta  = np.sum(avg_psd[beta_mask])
                    power_total = np.sum(avg_psd[total_mask])

                    if power_total == 0: power_total = 1e-9

                    # 5. Obliczenie wskaźników
                    ratio = power_beta / power_alpha if power_alpha > 0 else 0.0
                    
                    # Logika Statusu
                    status_text = "RELAX"
                    if ratio > 1.5:
                        status_text = "HIGH STRESS"
                    elif ratio > 1.0:
                        status_text = "FOCUS"

                    # 6. Aktualizacja zmiennej publicznej
                    self.latest_data.update({
                        "stress_index": ratio,
                        "alpha_rel": power_alpha / power_total,
                        "beta_rel": power_beta / power_total,
                        "status": status_text,
                        "connected": True,
                        "is_ready": True
                    })
                    
                    # Odciążenie procesora (5Hz refresh rate wystarczy)
                    time.sleep(0.2)

        except Exception as e:
            print(f"[EEG Worker] BŁĄD KRYTYCZNY: {e}")
            self.latest_data["status"] = "ERROR"
            self.latest_data["connected"] = False
            self.latest_data["is_ready"] = False
        finally:
            print("[EEG Worker] Zamykanie połączenia...")
            try:
                self.eeg.stop_acquisition()
                self.eeg.close()
                if self.mgr: self.mgr.disconnect()
            except:
                pass
            self.latest_data["connected"] = False