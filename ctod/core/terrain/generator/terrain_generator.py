from abc import ABC, abstractmethod

class TerrainGenerator(ABC):

    @abstractmethod
    def generate(self, terrain_request):
        pass