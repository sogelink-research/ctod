from abc import ABC, abstractmethod

class CogProcessor(ABC):

    @abstractmethod
    def process(self, cog_request):
        pass