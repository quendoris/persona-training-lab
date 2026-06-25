# Personality portrait

Вкладка **Тесты** собирает исследовательский портрет модели через scored Big Five/IPIP-style items.

## Цель

Не проверять «умеет ли модель говорить», а получить численный профиль поведения модели после изменения весов.

## Методика текущей версии

Файл батареи:

```text
src/persona_training_lab/application/experiments/test_batteries/big_five_short_v1.jsonl
```

Каждый пункт содержит:

- `battery_version`;
- `instrument`;
- `scoring_version`;
- `trait`;
- `key`;
- `reverse`;
- `item`;
- `scale_min` / `scale_max`;
- `response_format`.

## Формат ответа модели

Валидный ответ:

```text
SCORE: 1
SCORE: 2
SCORE: 3
SCORE: 4
SCORE: 5
```

В сохранённом CASE результат фиксируется так:

```text
VALID_SCORE: 1
RAW_RESPONSE: SCORE: 4
RESPONSE: SCORE: 4
```

Если ответ не распознан, сохраняется:

```text
VALID_SCORE: 0
RESPONSE: INVALID: ...
```

Только `VALID_SCORE: 1` попадает в KPI. Всё остальное считается invalid и не участвует в анализе.

## Reverse scoring

Если `REVERSE: 1`, итоговый score считается так:

```text
score = 6 - raw_score
```

## KPI факторов

Анализ считает среднее по факторам:

- `E` — Extraversion;
- `A` — Agreeableness;
- `C` — Conscientiousness;
- `S` — Emotional Stability;
- `O` — Openness.

## Дельта

Если есть минимум два портрета, анализ показывает:

```text
latest - previous
```

Это нужно для сравнения модели до и после fine-tune.

## Ограничение

`big_five_short_v1` — рабочая исследовательская батарея v0, а не финальная валидированная русская методика. Для статьи нужно фиксировать версию батареи, scoring rules, модель, параметры генерации и датасет.
