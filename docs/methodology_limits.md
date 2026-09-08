# Methodology limits

Persona Training Lab измеряет **наблюдаемое поведение модели в явно заданном evaluation protocol**. Текущий personality portrait не является клинической диагностикой человека и сам по себе не доказывает наличие у модели человеческого внутреннего психического состояния.

Этот документ описывает ограничения текущей реализации и интерпретации. Он не является roadmap будущих функций.

Точный machine/scoring contract: `docs/reference/evaluation-contract.md`.

## 1. Что именно измеряется

Текущий built-in portrait задаёт модели 10 scored Big Five/IPIP-style items и просит ответить score на шкале 1–5.

Результат зависит как минимум от:

```text
model/artifact
battery items
instruction/prompt wording
scoring rules
local inference path
generation configuration
runtime environment
```

Поэтому factor KPI следует интерпретировать как результат этой измерительной процедуры, а не как context-free свойство модели.

## 2. Короткая батарея

Current built-in battery содержит два items на каждый из пяти факторов.

Такая батарея удобна для быстрого повторяемого инженерно-исследовательского сравнения, но небольшое число items ограничивает силу более широких психологических выводов.

PTL не заявляет, что `big_five_short_v1` автоматически эквивалентна полной валидированной человеческой психометрической методике.

## 3. Prompt sensitivity

Модель отвечает не на абстрактную «черту», а на конкретно сформулированный prompt/instruction.

Изменение:

- wording;
- языка items;
- system/instruction prompt;
- chat-template route;
- generation behavior

может изменить распределение ответов даже при тех же model weights.

Поэтому изменение научного смысла prompt/battery не должно молча сохранять прежнюю `battery_version`/`scoring_version`.

## 4. UI locale не переводит батарею

Смена языка интерфейса PTL не означает перевод evaluation protocol.

Текущий questionnaire/user prompt path остаётся русскоязычным независимо от выбранной UI locale.

Следовательно, сравнение результатов между UI locales не является проверкой multilingual psychometric invariance: сама батарея при этом не переключается на independently validated language version.

## 5. Score — ответ, а не доступ к внутреннему состоянию

Когда модель возвращает:

```text
SCORE: 4
```

PTL наблюдает и сохраняет protocol response.

Из этого нельзя напрямую вывести, что внутри модели существует человеческое субъективное переживание «уровня 4» соответствующей черты.

Корректный объект анализа — **response behavior under protocol**.

## 6. Parser терпимее инструкции

Instruction требует короткий ответ формы:

```text
SCORE: <1-5>
```

Но parser ищет валидный `SCORE: N` token и может принять его даже при дополнительном тексте вокруг.

Поэтому «score распознан» и «модель идеально соблюла output-format instruction» — не одно и то же утверждение.

## 7. `VALID_SCORE` не равен полному item success

`VALID_SCORE: 1` означает успешное распознавание числового score.

Текущий item failure predicate отдельно учитывает local-model response `STATUS`.

При аудите case необходимо рассматривать как минимум:

```text
STATUS
VALID_SCORE
RESPONSE
```

а не только один parse flag.

## 8. Partial run может иметь KPI

Если не все items завершились успешно, normal persisted evaluation может иметь status:

```text
partial
```

При этом factor aggregation использует доступные валидные adjusted scores и не требует обязательно полного nominal item count для каждого factor.

Для текущей батареи nominal coverage — два item на factor, но один валидный item уже может дать математически определённый mean для этого factor.

Следовательно:

> factor KPI из partial run нельзя автоматически интерпретировать как эквивалент KPI из complete run.

Глобальные error/coverage данные должны сопровождать интерпретацию.

## 9. UI не показывает отдельный обязательный `n` для каждого factor

Current factor presentation не предоставляет отдельный first-class per-factor sample count рядом с каждым mean.

Это особенно важно для partial runs: одинаково выглядящее значение может быть рассчитано по разному числу валидных cases.

При строгом анализе восстанавливайте coverage из persisted CASE data.

## 10. Reverse scoring привязан к шкале 1–5

Текущая формула:

```text
adjusted = 6 - raw_score
```

корректна для текущего range 1–5.

Другой scale требует изменения scoring implementation/identity. Нельзя просто заменить scale metadata и считать прежнюю формулу универсальной.

## 11. Factor mean — простое среднее

Для доступных valid adjusted scores:

```text
mean_trait = round(sum(scores) / len(scores), 2)
```

Current PTL не добавляет к этому автоматически:

- confidence intervals;
- standard errors;
- reliability coefficients;
- significance testing;
- effect-size model.

Поэтому отображаемый KPI — descriptive mean, а не полный статистический вывод.

## 12. Delta — арифметическая разница

Для protocol-compatible пары:

```text
delta = latest_mean - previous_mean
```

Это не p-value, не confidence interval и не causal estimate.

Даже большая абсолютная delta сама по себе не доказывает, что изменение вызвано именно Training, если экспериментальный дизайн не контролирует другие факторы.

## 13. Protocol guard проверяет identity, а не содержимое батареи

Current comparability key:

```text
(battery_version, scoring_version)
```

Numerical delta разрешается только при известном одинаковом ключе.

Но PTL v1.0 не сохраняет SHA-256 bundled battery JSONL в portrait result.

Поэтому guard предполагает честную version discipline:

```text
same protocol identifiers
```

не являются cryptographic proof того, что bytes battery file никогда не менялись.

## 14. Совпадение protocol identity не гарантирует одинаковую полноту

Guard проверяет battery/scoring identity, но не требует одинакового case coverage для двух partial runs.

Следовательно, numeric delta может быть математически вычислима по common factors при одинаковом protocol, хотя число валидных items в сравниваемых run различается.

Для сильных научных выводов coverage надо учитывать отдельно.

## 15. Model artifact identity ограничена

Evaluation может быть связана с `model_version_id` и `artifact_path`, однако portrait row не хранит hash всей model artifact directory.

Если bytes по тому же path заменены in-place, один persisted result не способен криптографически доказать, какие именно weights/tokenizer files были загружены.

Для строгой репликации сохраняйте immutable artifact или отдельный cryptographic inventory.

## 16. Base-model identity Training также ограничена

Training pin'ит Profile Training representation и Dataset bytes, но base model в v1.0 идентифицируется path/reference, а не hash всей директории.

Поэтому end-to-end вывод «всё входное состояние полностью content-addressed PTL» неверен.

Исходную модель следует сохранять/идентифицировать отдельно, если byte-level provenance является частью исследования.

## 17. Generation environment сохраняется неполностью

Current portrait metadata не содержит полного self-contained environment manifest.

Например, не представлены first-class persisted fields для всего набора:

```text
exact PyTorch version
exact Transformers version
CUDA/driver version
GPU model
model directory hash
tokenizer hashes
chat-template hash
native-template vs fallback route
versioned full generation-parameter payload
```

Следовательно, PTL v1.0 поддерживает практическое локальное сравнение, но один portrait row не является полным replication package.

## 18. `RAW_RESPONSE` ограничен

Persisted `RAW_RESPONSE` очищается/нормализуется и ограничивается по длине.

Он подходит как diagnostic evidence короткого score contract, но не как lossless transcript полной generation.

Исследование, которому нужны полные тексты, должно сохранять их отдельным способом.

## 19. Deterministic generation не решает всю воспроизводимость

Current local generation path использует `do_sample=false`, но этого недостаточно, чтобы объявить абсолютную cross-machine/cross-version bitwise reproducibility.

На результат могут влиять модель/tokenizer bytes, library/runtime versions, template behavior, hardware/backend details и изменения implementation.

«Sampling выключен» — узкая гарантия, а не полный reproducibility proof.

## 20. Повторные измерения и стабильность

Current UI не предоставляет готовый inferential-statistics pipeline для repeated portrait runs.

Если исследовательский вопрос касается стабильности score:

- заранее определите число/условия повторов;
- сохраняйте все run, включая partial/failed, если они входят в protocol;
- анализируйте variability отдельно;
- не отбирайте только удобные результаты после просмотра outcome.

Это требование исследовательского дизайна, а не автоматически выполненная функция PTL.

## 21. Human psychometrics и model behavior — разные объекты

Названия Big Five факторов дают удобную интерпретационную систему, но человеческая валидность инструмента не переносится автоматически на языковую модель.

Отдельного обоснования требуют вопросы:

- construct validity для моделей;
- sensitivity к prompt/style compliance;
- temporal stability между generation contexts;
- влияние fine-tune на test-taking strategy;
- связь score с поведением вне questionnaire;
- multilingual equivalence.

PTL сам по себе не закрывает эти методологические вопросы.

## 22. Клинические утверждения не поддерживаются

Current protocol не предназначен для диагностики людей и не должен использоваться для утверждений о психическом здоровье человека.

Он также не даёт основания автоматически использовать клинические human labels для модели.

## 23. Безопасная формулировка результата

Поддерживаемая по смыслу формулировка:

```text
Модель/версия X в PTL protocol battery=B, scoring=S
получила такие factor scores при указанном execution context.
```

Если run partial:

```text
Результат рассчитан по доступным валидным cases; coverage/error state указан отдельно.
```

Если сравниваются две версии:

```text
При одинаковом known battery/scoring arithmetic delta между run X и Y составила ...
```

Неподдерживаемая текущими данными формулировка:

```text
У модели доказана настоящая клиническая личность такого-то типа.
```

## 24. Что фиксировать рядом с результатом

Для серьёзного исследования сохраняйте доступную provenance chain:

```text
PTL commit/release
model_version/artifact provenance
base-model source/revision/checksum при необходимости
Profile Training fingerprint
Dataset approved SHA-256
Training run/hyperparameters/metadata
battery_version
scoring_version
evaluation status и case coverage
существенные runtime/library/hardware details
```

Если какой-то элемент не хранится PTL как first-class field, это нужно явно отметить, а не заполнять догадкой задним числом.

## 25. Связанные документы

Исследовательская последовательность:

```text
docs/experiment_protocol.md
```

Текущий portrait:

```text
docs/personality_portrait.md
```

Machine/scoring contract:

```text
docs/reference/evaluation-contract.md
```

Training provenance:

```text
docs/training_pipeline.md
```
