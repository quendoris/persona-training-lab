# Persona Training Lab — Architecture

## 1. Слои системы
### 1.1 Product / Workflow
Определяет жизненный цикл личности модели:
dataset → training → snapshot → tests → analysis

### 1.2 UI Shell
Содержит:
- main window
- sidebar
- docking / floating panels
- brand block
- theme toggle / window visibility menu

### 1.3 Screens
Отдельные рабочие экраны:
- dashboard
- profiles
- datasets
- training
- snapshots
- tests
- analysis
- style
- docs

### 1.4 ViewModels
Каждый экран получает данные через свой viewmodel. ViewModel описывает состояние экрана, а не бизнес-логику применения модели.

### 1.5 Theme Layer
Theme manager отвечает за:
- цвета
- light/dark compatibility
- border / radius / surface logic
- поведение общих UI-паттернов

### 1.6 Assets
SVG-иконки и графические ресурсы:
- `ui/assets/icons/brand/main.svg`
- `ui/assets/icons/sidebar/*.svg`

### 1.7 Project Context
Документация, handoff и changelog:
- `docs/context/00_PROJECT_STATE.md`
- `docs/context/01_ARCHITECTURE.md`
- `docs/context/02_UI_RULES.md`
- `docs/context/03_CODEX_HANDOFF.md`
- `docs/context/04_GIT_WORKFLOW.md`
- `docs/context/05_CHANGELOG.md`

## 2. Структурные принципы
- интерфейс на русском
- внутренняя техническая структура и код на английском
- повторяемые UI-паттерны выносятся в helpers / theme manager
- локальный hardcode допустим только как временная заглушка
- scroll-контейнеры должны иметь один общий визуальный паттерн

## 3. Модули
### Dashboard
Обзор активного состояния системы, быстрые действия, связи между сущностями.

### Profiles
Реестр personality profiles, карта черт, связанные артефакты, следующий шаг.

### Datasets
Версии curated datasets, preview записей, validation result.

### Training
Сессия обучения, progress, checkpoints, hardware monitor, live logs.

### Snapshots
Жизненный цикл snapshot, статус версии, lineage, quality summary.

### Tests
Контексты проверки, результаты, problematic cases, interpretation context.

### Analysis
Compare двух версий, ключевые выводы, парные кейсы, дельта и риски.

### Style
Управление темами и визуальными настройками.

### Docs
Встроенная project help / quick reference.

## 4. Общие reusable-паттерны
- PanelCard
- PanelCardSoft
- AccentCard
- StableScrollShell / CheckpointScrollShell
- MutedText / CardTitle / MetricValue
