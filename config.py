from typing import Final, TypedDict


CONVERSATION_STARTER: Final[str] = "I sense deep distress in you, young padawan."


class AppStateDict(TypedDict):
    stoic_mode_activated: bool
    conversation_locked: bool
