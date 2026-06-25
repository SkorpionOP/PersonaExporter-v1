from abc import ABC, abstractmethod
from typing import BinaryIO
from models.domain import Conversation

class BaseParser(ABC):
    
    @abstractmethod
    def parse(self, file: BinaryIO) -> Conversation:
        """Parses a chat export file and returns a standard Conversation object."""
        pass
