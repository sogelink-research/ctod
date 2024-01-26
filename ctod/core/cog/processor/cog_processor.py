from abc import ABC, abstractmethod


class CogProcessor(ABC):
    """Abstract base class for CogProcessors."""
    
    @abstractmethod
    def process(self, cog_request):
        pass
    
    
    def get_reader_kwargs(self):
        return {}