# Quickstart

Persona Training Lab — локальная desktop-first лаборатория для подготовки профиля и данных, локального fine-tuning, регистрации версий модели и последующей оценки/анализа.

Этот документ — короткий маршрут для первого рабочего прогона. Полный набор текущей документации находится в `docs/README.md`; встроенный раздел **Документация** показывает только несколько явно зарегистрированных быстрых/методологических тем.

## 1. Установка и запуск

Для базового приложения нужен Python `>=3.12` и `uv`.

Из корня репозитория:

```bash
uv sync --locked
uv run --locked python -m persona_training_lab.bootstrap.app
```

Базовая установка запускает интерфейс, но не обязана содержать стек локального inference/training.

Если нужен только локальный inference/smoke generation:

```bash
uv sync --locked --extra inference
```

Если нужен локальный Training:

```bash
uv sync --locked --extra training
```

Подробности: `docs/user-guide/getting-started.md`.

## 2. Подготовьте профиль

Откройте **Профили** и создайте/выберите профиль личности, который должен участвовать в Training.

Training работает не с произвольным незаписанным текстом из интерфейса, а с сохранённым Profile. При создании Training run PTL фиксирует fingerprint выбранного профиля, поэтому последующее редактирование Profile не переписывает уже созданный run задним числом.

Подробности: `docs/user-guide/profiles.md` и `docs/user-guide/training.md`.

## 3. Подготовьте Датасеты

Откройте **Датасеты** и импортируйте поддерживаемый `.jsonl` файл.

Для типичного диалогового training-примера используются поля:

```text
prompt
response
```

Импорт сам по себе ещё не делает Dataset готовым к Training. Пройдите текущий workflow проверки и явного одобрения.

Канонический persisted/readiness status готовой версии:

```text
approved_for_training
```

Если данные изменились после одобрения или проверка больше не подтверждает ожидаемый content fingerprint, не считайте старое состояние доказательством пригодности нового содержимого.

Подробности: `docs/user-guide/datasets.md`.

## 4. Проверьте локальную модель

До создания/старта Training убедитесь, что PTL видит локальную base model.

Стандартный путь модели:

```text
<workspace>/models/qwen3.5-0.8b
```

Можно использовать и другой путь. Относительные model references разрешаются относительно стабильного PTL workspace, а не относительно случайного current working directory процесса.

Статус:

```text
found
```

означает, что shallow file probe нашёл ожидаемые model/tokenizer/config markers. Он **не** доказывает, что модель успешно загрузится в `transformers`, поместится в RAM/VRAM или выполнит generation.

Для более сильной проверки используйте smoke generation из Training/local-model flow.

Подробности: `docs/operations/local-models.md`.

## 5. Создайте Training run

Откройте **Обучение** и выберите:

- сохранённый Profile;
- Dataset version со статусом `approved_for_training`;
- локальную base model;
- нужные параметры запуска.

При создании run PTL фиксирует Profile/Dataset fingerprints и разрешённый путь base model. Полные байты директории base model в v1.0 не content-addressed, поэтому неизменность пути не гарантирует неизменность самой модели.

Перед фактическим стартом PTL снова проверяет доступность base model. Это позволяет обнаружить ситуацию, когда модель существовала при создании run, но исчезла/была перемещена до старта.

## 6. Запустите Training и дождитесь терминального состояния

Training выполняется как управляемая runtime operation. Не запускайте конкурирующие операции над теми же защищёнными runtime resources в обход PTL.

Во время работы следите за:

- статусом run;
- Activity/Issues;
- Training log/output;
- runtime-operation состоянием.

Успешный UI-переход сам по себе не является доказательством существования пригодного model artifact. Финальный Training flow валидирует publishable artifact перед регистрацией model version.

Артефакты конкретного full-fine-tune run находятся под:

```text
<workspace>/artifacts/full_finetune/<run_id>/
```

Финальная model directory:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
```

а metadata:

```text
<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json
```

При failure/interruption каталог может существовать частично. Наличие файлов в нём не означает `completed`.

Подробности: `docs/user-guide/training.md` и `docs/training_pipeline.md`.

## 7. Проверьте зарегистрированную версию модели

После успешного Training откройте **Снимки**.

В текущем v1.0 Snapshots показывает persisted model-version registry и provenance/reference на артефакт. Это не отдельное универсальное immutable artifact storage поверх filesystem.

Проверьте связь новой model version с Training run и artifact reference.

Подробности: `docs/user-guide/snapshots.md`.

## 8. Запустите Тесты и откройте Анализ

Откройте **Тесты**, выберите подходящую model version и выполните текущий evaluation workflow.

После завершения откройте **Анализ**, чтобы изучить:

- сохранённые case responses/results;
- factor KPI;
- protocol-compatible comparisons/delta между версиями.

Не интерпретируйте protocol score как клинический диагноз или прямое измерение недоступного внутреннего состояния модели. Это результат конкретного PTL evaluation protocol.

Подробности:

```text
docs/user-guide/tests-and-analysis.md
docs/reference/evaluation-contract.md
```

## 9. Что считать успешным первым прогоном

Для полного Training/evaluation маршрута минимально ожидается:

1. Profile сохранён и доступен для выбора;
2. Dataset version прошла validation/approval и имеет `approved_for_training`;
3. base model проходит ожидаемую локальную проверку и фактически доступна для нужного backend;
4. Training run достигает `completed`, а не только создаёт частичный filesystem output;
5. PTL регистрирует новую model version с ожидаемым lineage/provenance;
6. evaluation завершается с интерпретируемыми сохранёнными результатами;
7. Analysis показывает данные только в рамках совместимого protocol contract.

Если какой-либо этап завершается ошибкой, сначала сохраните диагностические данные и определите failing layer. Не начинайте recovery с удаления workspace/артефактов.

См. `docs/operations/troubleshooting.md`.

## 10. Быстрые инженерные проверки source checkout

Если вы не только используете PTL, но и разрабатываете его, отдельный минимальный набор проверок выглядит так:

```bash
uv run --locked python -m compileall -q src tests tools
uv run --locked python -m ruff check src tests tools
uv run --locked python -m pytest -q
```

Для воспроизводимого curated development gate из **чистого Git worktree**:

```bash
uv run --locked python tools/release_gate.py --quick
```

Quick gate не является полным release proof: текущий full release profile дополнительно включает, в частности, полный mypy и package build.

Подробности:

```text
docs/development/testing.md
docs/development/release-process.md
```

## 11. Куда идти дальше

Полная карта документации:

```text
docs/README.md
```

Основные пользовательские маршруты:

```text
docs/user-guide/getting-started.md
docs/user-guide/interface-tour.md
docs/user-guide/profiles.md
docs/user-guide/datasets.md
docs/user-guide/training.md
docs/user-guide/snapshots.md
docs/user-guide/tests-and-analysis.md
```

Операционные границы:

```text
docs/operations/workspace-and-storage.md
docs/operations/local-models.md
docs/operations/troubleshooting.md
docs/operations/backup-reset-recovery.md
docs/operations/security-boundaries.md
```

Если вы читаете этот файл внутри PTL, помните: текущий Documentation workspace показывает Markdown как read-only source text. Полная canonical navigation tree находится в `docs/README.md`.
