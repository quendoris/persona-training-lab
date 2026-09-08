# Experiment protocol

Этот документ задаёт практический исследовательский протокол вокруг текущих Training, model-version и Tests/Analysis контрактов PTL.

Его цель — не создать ещё один внутренний статус приложения, а не дать исследователю случайно сравнить результаты, полученные из разных входов, разных артефактов или разных evaluation protocols.

Точные machine contracts находятся в:

```text
docs/training_pipeline.md
docs/reference/evaluation-contract.md
docs/reference/statuses-and-identifiers.md
```

## 1. Что считать единицей исследовательского сравнения

Для сравнения «до/после» полезно рассматривать не один `experiment` row, а всю provenance chain:

```text
base-model identity
+ Profile Training representation/fingerprint
+ approved Dataset bytes/fingerprint
+ Training configuration
+ completed Training run
+ produced model artifact
+ registered model_version
+ evaluation battery_version
+ evaluation scoring_version
+ execution/environment evidence
```

В PTL эти элементы хранятся в разных местах и имеют разные гарантии идентичности. Не превращайте приведённую формулу в утверждение, будто существует одна атомарная запись, содержащая всё это целиком.

## 2. Что PTL фиксирует сильнее всего

### Profile

Training run сохраняет fingerprint Training-представления Profile:

```text
profile_sha256
```

Он вычисляется по реально сформированному Training instruction. Profile notes в этот fingerprint не входят.

### Dataset

Dataset approval сохраняет SHA-256 текущих внешних JSONL bytes:

```text
content_sha256
```

При создании Training run это значение pin'ится как:

```text
dataset_sha256
```

На Training boundary PTL снова читает файл и проверяет его bytes against pinned hash.

Таким образом Dataset content identity в текущем Training flow защищена сильнее, чем одна ссылка на `dataset_id`.

## 3. Что PTL не content-addresses полностью

### Base model

Training run хранит resolved path/reference base model, но v1.0 не сохраняет hash всей model directory.

Следовательно:

```text
same model path != cryptographic proof of same model bytes
```

Для исследовательской воспроизводимости отдельно фиксируйте хотя бы source/revision/checksum модели и не заменяйте weights/tokenizer/config in-place под прежним path.

### Produced model artifact

Model version и evaluation сохраняют artifact/model references, но portrait result также не содержит полного cryptographic manifest всей model artifact directory.

Сохраняйте artifact immutable либо ведите отдельный hash inventory, если byte-level identity важна для статьи/репликации.

## 4. До Training

Перед созданием run зафиксируйте:

1. **PTL source/release identity** — commit/tag/version, из которого выполняется workflow.
2. **Base model provenance** — path плюс внешний revision/checksum/source, потому что один path недостаточен.
3. **Profile** — выбранный Profile и Training-relevant содержимое.
4. **Dataset** — Dataset ID, source provenance и одобренный SHA-256 bytes.
5. **Training parameters** — как минимум `epochs`, `batch_size`, `learning_rate`.
6. **Baseline evaluation**, если исследовательский вопрос требует сравнения до/после.

Baseline должен быть связан с конкретной model version/artifact, а не просто называться «до обучения» в заметках.

## 5. Создание Training run

Создавайте новый run после intentional изменения Training-relevant Profile или после одобрения новых Dataset bytes.

Созданный run pin'ит:

```text
profile_id
profile_sha256
dataset_id
dataset_sha256
base_model path/reference
epochs
batch_size
learning_rate
```

Перед backend execution PTL повторно проверяет Profile/Dataset/model boundary. Старый run не должен молча следовать за новой версией входных данных.

## 6. После Training

После запуска не считайте появление каталога достаточным доказательством успеха.

Проверьте:

1. Training run достиг canonical terminal status `completed`;
2. финальная model directory существует;
3. `training_metadata.json` существует и соответствует run;
4. persisted artifact path указывает на ожидаемый output;
5. model version зарегистрирована с ожидаемым Training provenance;
6. runtime/log evidence не указывает на partial/failed path, ошибочно принятый за success.

Текущий full-fine-tune output:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json
```

## 7. Evaluation после Training

Для portrait evaluation используйте конкретную model version, когда сравнение относится к конкретному Training artifact.

Текущий встроенный protocol identity:

```text
battery_version = big_five_short_v1
scoring_version = big_five_score_v1
```

Но эти значения нельзя считать вечными. Всегда берите identity из фактического сохранённого run/result, а не из памяти или этого примера.

## 8. Правило сравнимости

Числовая factor delta в current Analysis допустима только когда оба run имеют известный одинаковый ключ:

```text
(battery_version, scoring_version)
```

Если battery/scoring отличаются или metadata неизвестны, результаты можно рассматривать отдельно, но numeric delta между ними не является валидным PTL protocol comparison.

Совпадение названий факторов само по себе не делает два run сравнимыми.

## 9. Что именно означает delta

Для protocol-compatible пары:

```text
delta_trait = latest_mean_trait - previous_mean_trait
```

Это арифметическая разница средних доступных валидных item scores.

Она не является автоматически:

- статистически значимым эффектом;
- effect size;
- доказательством причинности fine-tune;
- психологическим диагнозом;
- доказательством стабильной черты вне данного protocol.

## 10. Partial evaluation

Обычные per-item failures могут привести к persisted evaluation status:

```text
partial
```

Partial run может всё равно иметь factor mean по доступным валидным CASE.

Это означает, что два одинаково выглядящих KPI могут быть рассчитаны по разному coverage. При научной интерпретации сохраняйте:

```text
run status
passed/total
item errors
CASE status
VALID_SCORE
```

и не трактуйте partial factor как автоматически эквивалентный complete factor.

## 11. `VALID_SCORE` и model response status — разные признаки

В case payload:

```text
VALID_SCORE: 1
```

означает, что score token распознан.

Полный success predicate item также учитывает local-model `STATUS`.

Для аудита CASE сохраняйте оба поля. Нельзя сводить всё качество execution к одному `VALID_SCORE`.

## 12. `RAW_RESPONSE` в текущем v1.0

Поле `RAW_RESPONSE` не является lossless raw generation transcript.

Перед persistence строка очищается/схлопывается и ограничивается по длине. Она полезна как bounded diagnostic evidence для короткого `SCORE` protocol, но не как полный forensic record.

Текущий Tests/Analysis workflow не предоставляет встроенный lossless full-generation export для portrait cases. Если исследованию нужны полные generations, сохраняйте их внешним исследовательским capture-процессом либо добавляйте отдельный versioned capture/export contract; не считайте существующий `RAW_RESPONSE` таким механизмом.

## 13. Generation/environment provenance

Текущий portrait row не хранит полный self-contained generation environment manifest.

Для более строгой репликации дополнительно фиксируйте существенные параметры, например:

```text
Python version
PyTorch version
Transformers version
CUDA/driver/GPU environment
tokenizer/model hashes or immutable revisions
chat-template identity/route
generation parameters
PTL commit/release
```

Не все эти поля являются first-class persisted PTL fields в v1.0.

## 14. Battery integrity

Current evaluation result сохраняет:

```text
battery_version
scoring_version
```

но не SHA-256 bundled battery JSONL.

Значит version discipline — часть trust boundary. Если научный смысл батареи изменился, нельзя оставлять прежнюю protocol identity только потому, что приложение технически продолжает читать файл.

Изменения item wording/language, item set, factor mapping, `reverse`, scale или aggregation/scoring должны сопровождаться осмысленным version change.

## 15. Что сохранять для статьи/отчёта

Минимальный research bundle должен позволять восстановить следующую цепочку:

```text
PTL commit/release
        ↓
base model provenance
        ↓
Profile identity + Training fingerprint
        ↓
Dataset identity + approved SHA-256
        ↓
Training run + hyperparameters + metadata
        ↓
model artifact/model_version provenance
        ↓
evaluation run
        ↓
battery_version + scoring_version
        ↓
CASE coverage/status/score evidence
        ↓
factor KPI + allowed protocol-compatible delta
```

Дополнительно сохраняйте внешние hashes/environment details, которые PTL v1.0 сам не content-addresses.

## 16. Повторные прогоны

Один deterministic-looking run не доказывает устойчивость измерения во всех средах/версиях/аппаратных условиях.

Если исследовательский вопрос касается стабильности:

- выполняйте повторения по заранее определённому плану;
- не выбирайте только удобные run после просмотра результатов;
- сохраняйте failed/partial runs, если они принадлежат protocol execution;
- отдельно анализируйте variability и coverage.

Текущий application UI не превращает такую повторную статистику автоматически в полноценный inferential-statistics pipeline.

## 17. Что нельзя смешивать

Не смешивайте без явного перехода/обоснования:

- Training run и evaluation run;
- Dataset ID и Dataset byte identity;
- model path и model byte identity;
- старый/new portrait с неизвестным protocol metadata;
- `VALID_SCORE` и полный item success;
- bounded diagnostic `RAW_RESPONSE` и lossless generation transcript;
- arithmetic delta и statistical significance;
- model behavioral measurement и клиническую диагностику человека;
- human-like interpretation и доказанное внутреннее психическое состояние модели.

## 18. Безопасная формулировка результата

Корректнее писать:

```text
Версия модели X, оценённая протоколом battery=B / scoring=S
в зафиксированном PTL execution context, получила такие factor KPI.
```

Для сравнения:

```text
При одинаковом battery/scoring arithmetic delta между сохранёнными
run X и Y составила ...; coverage/status указаны отдельно.
```

Не следует сокращать это до:

```text
Fine-tune доказал, что у модели появилась настоящая человеческая черта X.
```

Такой вывод сильнее данных, которые текущий PTL protocol измеряет.

## 19. Связанные документы

Training implementation/provenance:

```text
docs/training_pipeline.md
docs/user-guide/training.md
```

Evaluation/scoring:

```text
docs/personality_portrait.md
docs/user-guide/tests-and-analysis.md
docs/reference/evaluation-contract.md
```

Методологические границы:

```text
docs/methodology_limits.md
```
