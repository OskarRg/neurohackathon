from enum import Enum
from typing import TypedDict

# BrainAccess MINI documentation
MINI_CAP_CHANNELS: dict[int, str] = {
    0: "F3",
    1: "F4",
    2: "C3",
    3: "C4",
    4: "P3",
    5: "P4",
    6: "O1",
    7: "O2",
}


class EEGDataDict(TypedDict):
    stress_index: float  # Index Beta/Alpha ratio
    alpha_rel: float  # Relative power Alpha (0.0 - 1.0)
    beta_rel: float  # Relative power Beta (0.0 - 1.0)
    status: str  # Np. "DISCONNECTED", "CONNECTED"
    connected: bool  # Is the device connected
    is_ready: bool  # Is the buffer full and trustworthy


class StatusEnum(str, Enum):
    DISCONNECTED: str = "DISCONNECTED"
    CONNECTED: str = "CONNECTING"
    BUFFERING: str = "BUFFERING"
    COMPUTED: str = "COMPUTED"
    ERROR: str = "ERROR"
