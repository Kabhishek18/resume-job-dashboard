"""Resume tailoring implementations."""

from abc import ABC, abstractmethod

from app.schemas.tailor_contract import TailorApiV1, TailorRequest


class TailoringService(ABC):
    @abstractmethod
    def tailor(self, body: TailorRequest) -> TailorApiV1:
        pass
