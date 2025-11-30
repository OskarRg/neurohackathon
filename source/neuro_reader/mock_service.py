import random
import time


class MockEEGService:
    def __init__(self):
        self.start_time = time.time()
        print("USING MOCK")

    def start(self):
        pass

    def stop(self):
        pass

    def get_data(self):
        """
        Simulate data
        """
        elapsed = time.time() - self.start_time

        if elapsed < 2:
            base_stress = 0.2
            mood = "RELAX"
        elif elapsed < 5:
            base_stress = 1.0
            mood = "FOCUS"
        elif elapsed > 10:
            base_stress = 0.2
            mood = "RELAX"
        else:
            base_stress = 2.5
            mood = "HIGH STRESS"

        jitter = random.uniform(-0.1, 0.1)
        fake_ratio = max(0.0, base_stress + jitter)

        return {
            "stress_index": fake_ratio,
            "alpha_rel": 0.5,
            "beta_rel": 0.5,
            "status": "SIMULATED",
            "connected": True,
            "is_ready": True,
            "mood": mood,
        }
