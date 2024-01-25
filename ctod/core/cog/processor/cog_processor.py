from abc import ABC, abstractmethod


class CogProcessor(ABC):
    """Abstract base class for CogProcessors."""
    
    @abstractmethod
    def process(self, cog_request):
        pass