import time
import os
import sys

# Importujemy naszą klasę z pliku obok
from eeg_service import EEGService

def draw_bar(value, max_val=3.0, length=30):
    """Pomocnicza funkcja do rysowania paska w konsoli"""
    norm = min(max(value, 0), max_val) / max_val
    fill = int(norm * length)
    bar = "█" * fill + "░" * (length - fill)
    return bar

def main():
    # 1. KONFIGURACJA
    # Tutaj wpisz nazwę swojego urządzenia
    DEVICE = "BA MINI 052" 
    
    print("--- Aplikacja Testowa EEG ---")
    print(f"Inicjalizacja serwisu dla: {DEVICE}")
    
    # Tworzymy instancję serwisu
    eeg = EEGService(device_name=DEVICE, window_duration=4.0)
    
    # 2. START WĄTKU (Nie blokuje programu)
    eeg.start()
    
    try:
        # 3. GŁÓWNA PĘTLA APLIKACJI
        # W prawdziwej aplikacji to będzie pętla gry, GUI, etc.
        while True:
            # Pobieramy dane z serwisu (natychmiastowy odczyt z pamięci)
            data = eeg.get_data()
            
            # Czyścimy konsolę (dla efektu animacji)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"--- PANEL KONTROLNY EEG ({DEVICE}) ---")
            
            if data['connected']:
                if data['is_ready']:
                    # Mamy poprawne dane
                    idx = data['stress_index']
                    status = data['status']
                    
                    # Kolorowanie statusu (kody ANSI)
                    color = "\033[92m" # Green
                    if status == "FOCUS": color = "\033[93m" # Yellow
                    if status == "HIGH STRESS": color = "\033[91m" # Red
                    reset = "\033[0m"
                    
                    print(f"Status: {color}{status}{reset}")
                    print(f"Index:  {idx:.2f}")
                    print(f"Wskaźnik: [{draw_bar(idx)}] {idx:.2f}")
                    print("-" * 30)
                    print(f"Moc Alpha: {data['alpha_rel']*100:.1f}%")
                    print(f"Moc Beta:  {data['beta_rel']*100:.1f}%")
                    
                    # PRZYKŁAD REAKCJI LOGICZNEJ
                    if idx > 1.2:
                        print("\n>>> ALERT: Wykryto wysokie skupienie/stres!")
                else:
                    # Połączono, ale trwa buforowanie (pierwsze 4 sekundy)
                    print(f"Status: {data['status']} (Proszę czekać...)")
            else:
                # Brak połączenia lub błąd
                print(f"Status: {data['status']}")
                print("Próba nawiązania połączenia w tle...")

            # Symulacja klatkażu aplikacji (np. 10 FPS)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika.")
    finally:
        # 4. SPRZĄTANIE
        # Bardzo ważne, żeby zwolnić Bluetooth przy wyjściu
        eeg.stop()
        print("Aplikacja zakończona.")

if __name__ == "__main__":
    main()