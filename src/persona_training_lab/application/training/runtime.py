from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TrainingRunEvent:
    run_id: str
    status: str
    epoch_progress: str
    progress: float
    loss: str
    speed: str
    message: str
    finished: bool = False


class DeterministicTrainingRunner:
    def __init__(self, epochs: int = 3, steps_per_epoch: int = 5) -> None:
        self._epochs = max(1, epochs)
        self._steps_per_epoch = max(1, steps_per_epoch)
        self._state: dict[str, int] = {}

    def start(self, run_id: str) -> TrainingRunEvent:
        self._state[run_id] = 0
        return TrainingRunEvent(
            run_id=run_id,
            status="Выполняется",
            epoch_progress=f"0 / {self._epochs}",
            progress=0.0,
            loss="—",
            speed="~ 0.0 samples/s",
            message="Запуск training runner skeleton",
            finished=False,
        )

    def step(self, run_id: str) -> TrainingRunEvent:
        step = self._state.get(run_id, 0) + 1
        total_steps = self._epochs * self._steps_per_epoch
        if step > total_steps:
            step = total_steps
        self._state[run_id] = step

        epoch = min(self._epochs, (step - 1) // self._steps_per_epoch + 1)
        progress = step / total_steps
        loss = max(0.05, 1.25 - progress)
        finished = step >= total_steps
        return TrainingRunEvent(
            run_id=run_id,
            status="Завершено" if finished else "Выполняется",
            epoch_progress=f"{epoch} / {self._epochs}",
            progress=progress,
            loss=f"{loss:.4f}",
            speed=f"~ {8.0 + progress * 4.0:.1f} samples/s",
            message=("Обучение завершено" if finished else f"Эпоха {epoch}: шаг {step}/{total_steps}"),
            finished=finished,
        )
