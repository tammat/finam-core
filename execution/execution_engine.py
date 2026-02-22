from abc import ABC, abstractmethod

class BaseExecutionEngine(ABC):
    @abstractmethod
    def execute(self, order):
        pass