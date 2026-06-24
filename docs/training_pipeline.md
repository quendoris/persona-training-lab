# Training pipeline

Цель вкладки **Обучение** — запустить локальный fine-tune и получить воспроизводимый artifact модели.

## Поток данных

```text
profile + dataset + base_model + hyperparameters
→ TrainingService
→ LocalFullFineTuneBackend
→ artifacts/full_finetune/<run_id>/model
→ model version / snapshot
```

## Что подключено

- создание training run;
- проверка локальной модели;
- full fine-tune backend;
- логирование запуска и завершения;
- сохранение artifact path;
- проверка ответа локальной модели.

## Что проверять в UI

- кнопка запуска не блокирует интерфейс надолго;
- статус run меняется с ready/running на завершённый;
- живые логи показывают запуск, training step и путь artifact;
- после завершения можно проверить модель и перейти к тестам.

## Типовые признаки проблемы

- нет строки загрузки весов — не дошли до backend inference/training;
- UI зависает — тяжёлая операция попала в главный поток;
- artifact отсутствует — обучение завершилось не полностью;
- pytest красный — сначала чинить контракт, потом запускать UI.
