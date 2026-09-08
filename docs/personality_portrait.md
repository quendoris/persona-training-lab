# Personality portrait

Вкладки **Тесты** и **Анализ** собирают и интерпретируют исследовательский scored-портрет поведения выбранной версии модели по текущему Big Five/IPIP-style протоколу PTL.

Это не проверка «умеет ли модель говорить» и не клиническая диагностика. Результат — измерение ответов модели внутри конкретной versioned evaluation battery и конкретных scoring rules.

Полный machine-level контракт: `docs/reference/evaluation-contract.md`.

## Текущий встроенный протокол

Ресурс батареи:

```text
persona_training_lab.application.experiments.test_batteries/
    big_five_short_v1.jsonl
```

Текущая protocol identity:

```text
battery_version = big_five_short_v1
instrument      = BIG_FIVE_SHORT
scoring_version = big_five_score_v1
scale           = 1..5
response_format = SCORE: <1-5>
```

В батарее сейчас 10 items: по два на каждый из пяти факторов.

Каждый item содержит/задаёт данные вроде:

```text
battery_version
instrument
scoring_version
trait
key
item
reverse
scale_min
scale_max
response_format
```

## Факторы и ключи

Текущий набор:

```text
Extraversion         E1, E2R
Agreeableness        A1, A2R
Conscientiousness    C1, C2R
Emotional Stability  S1, S2R
Openness             O1, O2R
```

Второй item каждого фактора сейчас reverse-scored.

Важно: scoring implementation использует явное поле `reverse`, а не угадывает reversal по букве `R` в ключе.

## Как выбирается модель

Если Tests запускается для конкретной `model_version_id`, PTL ищет именно эту зарегистрированную model version.

Если у выбранной версии есть `artifact_path`, evaluation использует его. Если выбранной версии нет или artifact недоступен, PTL не подменяет её случайной другой версией.

Когда конкретная model version не выбрана, evaluation может использовать текущую default local model path.

Перед запуском батареи PTL проверяет доступность выбранного model path.

## Формат ответа модели

Инструкция просит вернуть одну строку:

```text
SCORE: 1
SCORE: 2
SCORE: 3
SCORE: 4
SCORE: 5
```

Текущий parser ищет token формы:

```regex
\bSCORE\s*:\s*([1-5])\b
```

без учёта регистра.

То есть generation instruction строгая, но parser немного терпимее: корректный `SCORE: N` может быть распознан даже при дополнительном тексте вокруг.

## Что сохраняется для каждого CASE

Текущий serialized case содержит поля вида:

```text
CASE <index>
BATTERY_VERSION: <battery_version>
SCORING_VERSION: <scoring_version>
INSTRUMENT: <instrument>
TRAIT: <trait>
KEY: <key>
REVERSE: <0|1>
SCALE: <min>-<max>
ITEM: <statement>
PROMPT: <one-line prompt>
STATUS: <local model status>
VALID_SCORE: <0|1>
RAW_RESPONSE: <bounded diagnostic response>
RESPONSE: <normalized score or INVALID marker>
```

Пример распознанного score:

```text
STATUS: responding
VALID_SCORE: 1
RAW_RESPONSE: SCORE: 4
RESPONSE: SCORE: 4
```

Нераспознанный score получает:

```text
VALID_SCORE: 0
RESPONSE: INVALID: ...
```

Но `VALID_SCORE: 1` означает именно успешное распознавание score. Для полного item success важен также `STATUS`: модель должна иметь нормализованный local-model status `responding`.

Поэтому при аудите CASE нельзя смотреть только на `VALID_SCORE`.

## `RAW_RESPONSE` — не полный raw transcript

Название поля исторически звучит сильнее, чем текущая гарантия.

Перед persistence ответ нормализуется и ограничивается:

- NUL заменяется пробелом;
- whitespace схлопывается;
- literal `<think>` / `</think>` удаляются;
- пустой ответ превращается в диагностический marker;
- длинный текст ограничивается примерно 120 символами.

Следовательно:

> `RAW_RESPONSE` в v1.0 — bounded diagnostic representation, а не lossless forensic capture полного generation output.

Если исследованию нужны полные поколения, их надо сохранять отдельным механизмом.

## Reverse scoring

Для валидного raw score `x` на текущей шкале 1–5:

```text
reverse = false -> adjusted = x
reverse = true  -> adjusted = 6 - x
```

Число `6` здесь связано именно с текущей шкалой 1–5. Другой scale требует соответствующего scoring/version change.

## KPI факторов

Анализ группирует валидные adjusted scores по точному `trait` и считает:

```text
mean_trait = round(sum(adjusted_scores) / len(adjusted_scores), 2)
```

Факторы отображаются как:

```text
E — Extraversion
A — Agreeableness
C — Conscientiousness
S — Emotional Stability
O — Openness
```

В расчёт конкретного фактора не входят CASE, где:

```text
trait пуст
adjusted score отсутствует
VALID_SCORE ложен
```

## Partial run и неполный фактор

Текущий Analysis не требует, чтобы для вычисления factor mean обязательно присутствовали оба nominal items.

Поэтому partial run может показать factor KPI, рассчитанный по одному доступному валидному item.

Это математически определённое среднее по доступным данным, но методологически оно слабее полного factor coverage.

В текущем UI нет отдельного обязательного per-factor `n`, поэтому при интерпретации partial run необходимо смотреть на общий item/error coverage.

## Статус всего evaluation run

После выполнения items:

```text
0 item failures -> completed
>0 item failures -> partial
```

Обычные отдельные ошибки item не превращают сохранённый questionnaire автоматически в `failed`; нормальный частично успешный путь сохраняется как `partial`.

Unexpected outer failures обрабатываются отдельно через safe-stop/result-code путь.

## Анализ и дельта

Analysis работает по уже сохранённым experiment payloads; он не запускает новую model inference.

Для двух protocol-compatible портретов factor delta считается как:

```text
latest_mean_trait - previous_mean_trait
```

Это обычная арифметическая разница.

Она **не** означает автоматически:

- statistical significance;
- effect size;
- причинность изменения;
- психологическую/клиническую значимость.

## Когда два портрета сравнимы

Числовая дельта разрешается только когда оба run имеют известный и одинаковый protocol key:

```text
(battery_version, scoring_version)
```

Если battery/scoring различаются или metadata неизвестны:

- текущий portrait можно показывать отдельно;
- предыдущий summary можно показывать отдельно;
- numeric delta должна быть заменена на `—`;
- UI объясняет, что протоколы должны совпадать.

PTL не считает два run сравнимыми только потому, что у них похожие названия факторов.

## Versioning батареи

Изменение научного смысла evaluation protocol не должно молча сохранять прежнюю identity.

Изменения вроде:

- item wording/language;
- числа items;
- factor assignment;
- `reverse` flags;
- scale;
- normalization;
- aggregation rules

должны сопровождаться изменением `battery_version` и/или `scoring_version` по смыслу изменения.

Текущий v1.0 guard сравнивает именно version identifiers, а не hash файла батареи.

## Ограничения воспроизводимости

Сохранённый portrait содержит protocol identity и model/artifact references, но не является полным self-contained replication package.

В нём нет first-class persisted manifest для всех параметров среды, например:

- полного hash model directory;
- tokenizer hashes;
- exact PyTorch/Transformers/CUDA/driver versions;
- chat-template hash/identity;
- полного versioned generation-parameter object;
- полного lossless generation transcript.

Также `battery_version`/`scoring_version` не сопровождаются persisted SHA-256 самого bundled battery file.

Поэтому версия протокола и дисциплина неизменности артефактов остаются частью research provenance boundary.

## Как интерпретировать результат

Корректная формулировка:

> Модель получила такие scores в конкретном PTL evaluation protocol при конкретной сохранённой model/artifact reference и текущем execution path.

Некорректно автоматически превращать это в утверждение:

> У модели доказана человеческая черта личности X на уровне Y.

PTL измеряет наблюдаемое поведение в тестовом протоколе. Более сильные психологические или причинные выводы требуют отдельного исследовательского обоснования.

## Что фиксировать для исследования

Минимально сохраняйте вместе с результатами:

```text
model_version_id / artifact provenance
battery_version
scoring_version
evaluation status и coverage
Dataset/Training provenance исходной model version
commit/release PTL
существенные generation/runtime environment details
```

Для строгой репликации дополнительно сохраняйте hashes и версии внешних/локальных артефактов, которые v1.0 portrait row сам не content-addresses.

## Дальше

Пользовательский workflow:

```text
docs/user-guide/tests-and-analysis.md
```

Точный machine/scoring/persistence контракт:

```text
docs/reference/evaluation-contract.md
```

Методологические ограничения:

```text
docs/methodology_limits.md
```
