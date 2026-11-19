from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterator

from .errors import DomainError


@dataclass(frozen=True)
class Period:
    """Intervalle de dates, bornes incluses."""
    start: dt.date
    end: dt.date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise DomainError("La date de fin doit être postérieure à la date de début.")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, day: dt.date) -> bool:
        return self.start <= day <= self.end

    def each_day(self) -> Iterator[dt.date]:
        for i in range(self.days):
            yield self.start + dt.timedelta(days=i)
