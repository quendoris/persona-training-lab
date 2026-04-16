from typing import Protocol


class TrainingRunnerPort(Protocol):
    def start(self) -> None: ...
