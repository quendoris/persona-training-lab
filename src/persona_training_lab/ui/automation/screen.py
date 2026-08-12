from __future__ import annotations

from pathlib import Path
from threading import Event
from uuid import uuid4

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.application.automation import AutomationCommandRequest
from persona_training_lab.application.automation.execution import (
    DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES,
)
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.automation import (
    AutomationRecipeView,
    AutomationRunView,
    AutomationText,
    AutomationTextValue,
    AutomationViewModel,
)
from persona_training_lab.ui.viewmodels.automation_command import (
    AUTOMATION_COMMAND_DRAFT_ERROR_KEYS,
    AutomationCommandDraft,
    build_automation_command_request,
)


AUTOMATION_SOURCE_KEYS = {
    "builtin": "automation.source.builtin",
    "workspace": "automation.source.workspace",
}
AUTOMATION_ACCESS_KEYS = {
    "read": "automation.access.read",
    "write": "automation.access.write",
}
AUTOMATION_EXECUTION_MODE_KEYS = {
    "exec": "automation.adhoc.mode.exec",
    "shell": "automation.adhoc.mode.shell",
}


class _AutomationRunWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        vm: AutomationViewModel,
        *,
        recipe_id: str = "",
        inputs: dict[str, str] | None = None,
        command_request: AutomationCommandRequest | None = None,
    ) -> None:
        super().__init__()
        self._vm = vm
        self._recipe_id = recipe_id
        self._inputs = dict(inputs or {})
        self._command_request = command_request
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        try:
            if self._command_request is not None:
                result = self._vm.run_command(
                    self._command_request,
                    cancel_requested=self._cancelled.is_set,
                )
            else:
                result = self._vm.run_recipe(
                    self._recipe_id,
                    self._inputs,
                    cancel_requested=self._cancelled.is_set,
                )
        except Exception as exc:
            self.failed.emit(repr(exc))
            return
        self.finished.emit(result)


class AutomationScreen(QWidget):
    def __init__(
        self,
        view_model: AutomationViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization
        self._recipes: dict[str, AutomationRecipeView] = {}
        self._selected_recipe_id = ""
        self._input_fields: dict[str, QLineEdit] = {}
        self._thread: QThread | None = None
        self._worker: _AutomationRunWorker | None = None
        self._running = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)
        self._title = QLabel()
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label("")
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        registry = PanelCard()
        registry.setMinimumWidth(310)
        registry_layout = registry._layout
        self._registry_title = QLabel()
        self._registry_title.setObjectName("SectionTitle")
        self._registry_note = make_muted_label("")
        registry_layout.addWidget(self._registry_title)
        registry_layout.addWidget(self._registry_note)

        self._search = QLineEdit()
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._refresh_registry)
        registry_layout.addWidget(self._search)

        registry_actions = QHBoxLayout()
        self._refresh_btn = QPushButton()
        self._refresh_btn.setObjectName("SecondaryButton")
        self._refresh_btn.clicked.connect(self._refresh_registry)
        self._import_btn = QPushButton()
        self._import_btn.setObjectName("SecondaryButton")
        self._import_btn.clicked.connect(self._import_recipe)
        registry_actions.addWidget(self._refresh_btn)
        registry_actions.addWidget(self._import_btn)
        registry_layout.addLayout(registry_actions)

        self._recipe_list = QListWidget()
        self._recipe_list.setObjectName("StableList")
        self._recipe_list.currentItemChanged.connect(self._select_recipe_item)
        registry_layout.addWidget(self._recipe_list, 1)

        self._issues_title = QLabel()
        self._issues_title.setObjectName("CardTitle")
        registry_layout.addWidget(self._issues_title)
        self._issues = QListWidget()
        self._issues.setMaximumHeight(150)
        registry_layout.addWidget(self._issues)
        splitter.addWidget(registry)

        detail_scroll = QScrollArea()
        detail_scroll.setObjectName("StableScrollArea")
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_scrollbar_style(detail_scroll)
        detail_host = QWidget()
        detail_host.setProperty("transparentBg", True)
        detail_layout = QVBoxLayout(detail_host)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(14)

        self._detail_card = PanelCard()
        self._detail_title = QLabel()
        self._detail_title.setObjectName("ScreenTitle")
        self._detail_description = make_muted_label("")
        self._detail_card.add_widget(self._detail_title)
        self._detail_card.add_widget(self._detail_description)

        self._meta = QLabel()
        self._meta.setWordWrap(True)
        self._meta.setObjectName("MutedText")
        self._detail_card.add_widget(self._meta)
        detail_layout.addWidget(self._detail_card)

        self._inputs_card = PanelCard()
        self._inputs_title = QLabel()
        self._inputs_title.setObjectName("SectionTitle")
        self._inputs_card.add_widget(self._inputs_title)
        self._inputs_host = QWidget()
        self._inputs_host.setProperty("transparentBg", True)
        self._inputs_form = QFormLayout(self._inputs_host)
        self._inputs_form.setContentsMargins(0, 0, 0, 0)
        self._inputs_form.setSpacing(10)
        self._inputs_card.add_widget(self._inputs_host)
        detail_layout.addWidget(self._inputs_card)

        self._contract_card = PanelCard()
        self._contract_title = QLabel()
        self._contract_title.setObjectName("SectionTitle")
        self._outputs_label = QLabel()
        self._outputs_label.setWordWrap(True)
        self._resources_label = QLabel()
        self._resources_label.setWordWrap(True)
        self._contract_card.add_widget(self._contract_title)
        self._contract_card.add_widget(self._outputs_label)
        self._contract_card.add_widget(self._resources_label)
        detail_layout.addWidget(self._contract_card)

        self._command_card = PanelCard()
        self._command_title = QLabel()
        self._command_title.setObjectName("SectionTitle")
        self._command = QPlainTextEdit()
        self._command.setReadOnly(True)
        self._command.setMaximumHeight(110)
        self._command_card.add_widget(self._command_title)
        self._command_card.add_widget(self._command)
        detail_layout.addWidget(self._command_card)

        self._adhoc_card = PanelCard()
        self._adhoc_title = QLabel()
        self._adhoc_title.setObjectName("SectionTitle")
        self._adhoc_description = make_muted_label("")
        self._adhoc_card.add_widget(self._adhoc_title)
        self._adhoc_card.add_widget(self._adhoc_description)

        adhoc_form = QFormLayout()
        adhoc_form.setContentsMargins(0, 0, 0, 0)
        adhoc_form.setSpacing(10)

        self._adhoc_mode_label = QLabel()
        self._adhoc_mode = QComboBox()
        self._adhoc_mode.addItem("", "exec")
        self._adhoc_mode.addItem("", "shell")
        self._adhoc_mode.currentIndexChanged.connect(self._apply_adhoc_mode)
        adhoc_form.addRow(self._adhoc_mode_label, self._adhoc_mode)

        self._adhoc_command_label = QLabel()
        self._adhoc_command = QPlainTextEdit()
        self._adhoc_command.setMaximumHeight(110)
        adhoc_form.addRow(self._adhoc_command_label, self._adhoc_command)
        self._adhoc_command_help = make_muted_label("")
        self._adhoc_command_help.setWordWrap(True)
        adhoc_form.addRow(self._adhoc_command_help)

        self._adhoc_cwd_label = QLabel()
        self._adhoc_cwd = QLineEdit()
        adhoc_form.addRow(self._adhoc_cwd_label, self._adhoc_cwd)

        self._adhoc_timeout_label = QLabel()
        self._adhoc_timeout = QLineEdit()
        self._adhoc_timeout.setText("0")
        adhoc_form.addRow(self._adhoc_timeout_label, self._adhoc_timeout)

        self._adhoc_output_limit_label = QLabel()
        self._adhoc_output_limit = QLineEdit()
        self._adhoc_output_limit.setText(
            str(DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES)
        )
        adhoc_form.addRow(
            self._adhoc_output_limit_label,
            self._adhoc_output_limit,
        )

        self._adhoc_environment_label = QLabel()
        self._adhoc_environment = QPlainTextEdit()
        self._adhoc_environment.setMaximumHeight(90)
        adhoc_form.addRow(
            self._adhoc_environment_label,
            self._adhoc_environment,
        )
        self._adhoc_environment_help = make_muted_label("")
        self._adhoc_environment_help.setWordWrap(True)
        adhoc_form.addRow(self._adhoc_environment_help)

        self._adhoc_resources_label = QLabel()
        self._adhoc_resources = QPlainTextEdit()
        self._adhoc_resources.setMaximumHeight(90)
        adhoc_form.addRow(
            self._adhoc_resources_label,
            self._adhoc_resources,
        )
        self._adhoc_resources_help = make_muted_label("")
        self._adhoc_resources_help.setWordWrap(True)
        adhoc_form.addRow(self._adhoc_resources_help)
        self._adhoc_card._layout.addLayout(adhoc_form)

        self._adhoc_inherit_environment = QCheckBox()
        self._adhoc_inherit_environment.setChecked(True)
        self._adhoc_card.add_widget(self._adhoc_inherit_environment)
        detail_layout.addWidget(self._adhoc_card)

        detail_layout.addStretch(1)
        detail_scroll.setWidget(detail_host)
        splitter.addWidget(detail_scroll)

        runner = PanelCard()
        runner.setMinimumWidth(360)
        runner_layout = runner._layout
        self._runner_title = QLabel()
        self._runner_title.setObjectName("SectionTitle")
        self._runner_note = make_muted_label("")
        runner_layout.addWidget(self._runner_title)
        runner_layout.addWidget(self._runner_note)

        self._run_status = make_status_label("")
        runner_layout.addWidget(self._run_status)
        run_actions = QHBoxLayout()
        self._run_btn = QPushButton()
        self._run_btn.setObjectName("PrimaryButton")
        self._run_btn.clicked.connect(self._run_selected)
        self._run_command_btn = QPushButton()
        self._run_command_btn.setObjectName("PrimaryButton")
        self._run_command_btn.clicked.connect(self._run_command)
        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("SecondaryButton")
        self._cancel_btn.clicked.connect(self._cancel_run)
        self._cancel_btn.setEnabled(False)
        run_actions.addWidget(self._run_btn)
        run_actions.addWidget(self._run_command_btn)
        run_actions.addWidget(self._cancel_btn)
        runner_layout.addLayout(run_actions)

        self._operation = make_muted_label("")
        self._operation.setWordWrap(True)
        runner_layout.addWidget(self._operation)
        self._output_title = QLabel()
        self._output_title.setObjectName("CardTitle")
        runner_layout.addWidget(self._output_title)
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        runner_layout.addWidget(self._output, 1)
        splitter.addWidget(runner)
        splitter.setSizes([340, 760, 430])

        self._apply_language()
        self._refresh_registry()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def request_leave_workspace(self) -> bool:
        if not self._running:
            return True
        self._run_status.setText(self._text("automation.run.leave_blocked"))
        return False

    def _refresh_registry(self, _value: object = None) -> None:
        selected = self._selected_recipe_id
        recipes = self._vm.recipes(self._search.text())
        self._recipes = {recipe.recipe_id: recipe for recipe in recipes}
        self._recipe_list.blockSignals(True)
        self._recipe_list.clear()
        selected_row = -1
        for index, recipe in enumerate(recipes):
            item = QListWidgetItem(self._render_value(recipe.title))
            item.setData(Qt.ItemDataRole.UserRole, recipe.recipe_id)
            item.setToolTip(recipe.recipe_id)
            self._recipe_list.addItem(item)
            if recipe.recipe_id == selected:
                selected_row = index
        self._recipe_list.blockSignals(False)

        issues = self._vm.discovery_issues()
        self._issues.clear()
        for issue in issues:
            text = self._text(
                "automation.discovery.issue",
                message=self._render(issue.message),
                path=issue.path,
            )
            item = QListWidgetItem(text)
            item.setToolTip(issue.detail)
            self._issues.addItem(item)
        self._issues.setVisible(bool(issues))
        self._issues_title.setVisible(bool(issues))

        if selected_row >= 0:
            self._recipe_list.setCurrentRow(selected_row)
        elif self._recipe_list.count() > 0:
            self._recipe_list.setCurrentRow(0)
        else:
            self._selected_recipe_id = ""
            self._render_recipe(None)

    def _select_recipe_item(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        recipe_id = (
            str(current.data(Qt.ItemDataRole.UserRole) or "") if current else ""
        )
        self._selected_recipe_id = recipe_id
        self._render_recipe(self._recipes.get(recipe_id))

    def _render_recipe(self, recipe: AutomationRecipeView | None) -> None:
        previous_inputs = {
            name: field.text() for name, field in self._input_fields.items()
        }
        self._clear_form()
        if recipe is None:
            self._detail_title.setText(self._text("automation.empty.title"))
            self._detail_description.setText(
                self._text("automation.empty.description")
            )
            self._meta.clear()
            self._outputs_label.clear()
            self._resources_label.clear()
            self._command.clear()
            self._run_btn.setEnabled(False)
            return

        self._detail_title.setText(self._render_value(recipe.title))
        self._detail_description.setText(self._render_value(recipe.description))
        source_key = AUTOMATION_SOURCE_KEYS.get(
            recipe.source,
            "automation.source.unknown",
        )
        tags = ", ".join(recipe.tags) or "—"
        self._meta.setText(
            self._text(
                "automation.recipe.meta",
                recipe_id=recipe.recipe_id,
                version=recipe.version,
                source=self._text(source_key),
                tags=tags,
            )
        )
        for name, required, default, description in recipe.inputs:
            field = QLineEdit()
            field.setText(previous_inputs.get(name, default))
            if description:
                field.setToolTip(description)
            label = self._text(
                "automation.input.label",
                name=name,
                required=self._text(
                    "automation.input.required"
                    if required
                    else "automation.input.optional"
                ),
            )
            self._inputs_form.addRow(label, field)
            self._input_fields[name] = field
        if not recipe.inputs:
            empty = make_muted_label(self._text("automation.inputs.none"))
            self._inputs_form.addRow(empty)

        outputs = " · ".join(
            name if not description else f"{name} — {description}"
            for name, description in recipe.outputs
        ) or self._text("automation.outputs.none")
        self._outputs_label.setText(
            self._text("automation.outputs.summary", outputs=outputs)
        )
        resources = " · ".join(
            self._text(
                "automation.resource.item",
                access=self._text(
                    AUTOMATION_ACCESS_KEYS.get(
                        access,
                        "automation.access.unknown",
                    )
                ),
                kind=kind,
                resource_id=resource_id,
            )
            for kind, resource_id, access in recipe.resources
        ) or self._text("automation.resources.none")
        self._resources_label.setText(
            self._text("automation.resources.summary", resources=resources)
        )
        self._command.setPlainText(recipe.command)
        self._run_btn.setEnabled(not self._running)

    def _clear_form(self) -> None:
        self._input_fields.clear()
        while self._inputs_form.rowCount():
            self._inputs_form.removeRow(0)

    def _import_recipe(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            self._text("automation.import.dialog_title"),
            "",
            self._text("automation.import.filter"),
        )
        if not path:
            return
        try:
            recipe = self._vm.import_recipe(Path(path))
        except Exception as exc:
            self._run_status.setText(
                self._text("automation.import.failed", detail=str(exc))
            )
            return
        self._selected_recipe_id = recipe.recipe_id
        self._run_status.setText(self._text("automation.import.succeeded"))
        self._refresh_registry()

    def _run_selected(self) -> None:
        recipe = self._recipes.get(self._selected_recipe_id)
        if recipe is None or self._running:
            return
        inputs = {name: field.text() for name, field in self._input_fields.items()}
        self._start_worker(
            _AutomationRunWorker(
                self._vm,
                recipe_id=recipe.recipe_id,
                inputs=inputs,
            )
        )

    def _run_command(self) -> None:
        if self._running:
            return
        draft = AutomationCommandDraft(
            mode=str(self._adhoc_mode.currentData() or ""),
            command_text=self._adhoc_command.toPlainText(),
            working_directory=self._adhoc_cwd.text(),
            environment_text=self._adhoc_environment.toPlainText(),
            inherit_environment=self._adhoc_inherit_environment.isChecked(),
            resource_claims_text=self._adhoc_resources.toPlainText(),
            timeout_text=self._adhoc_timeout.text(),
            output_limit_text=self._adhoc_output_limit.text(),
        )
        parsed = build_automation_command_request(
            draft,
            command_id=f"command_{uuid4().hex[:12]}",
        )
        if parsed.request is None:
            key = AUTOMATION_COMMAND_DRAFT_ERROR_KEYS.get(
                parsed.error_code,
                "automation.run.status.command_invalid",
            )
            self._run_status.setText(self._text(key))
            self._operation.clear()
            self._output.clear()
            return
        self._start_worker(
            _AutomationRunWorker(
                self._vm,
                command_request=parsed.request,
            )
        )

    def _start_worker(self, worker: _AutomationRunWorker) -> None:
        self._running = True
        self._run_btn.setEnabled(False)
        self._run_command_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._run_status.setText(self._text("automation.run.status.running"))
        self._operation.clear()
        self._output.clear()

        self._thread = QThread(self)
        self._worker = worker
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_run_finished)
        self._worker.failed.connect(self._on_run_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _cancel_run(self) -> None:
        if self._worker is None or not self._running:
            return
        self._cancel_btn.setEnabled(False)
        self._run_status.setText(self._text("automation.run.status.cancelling"))
        self._worker.cancel()

    def _on_run_finished(self, result: object) -> None:
        if not isinstance(result, AutomationRunView):
            self._on_run_failed(repr(result))
            return
        self._finish_run_state()
        self._run_status.setText(self._render(result.status))
        operation = self._text(
            "automation.run.operation",
            operation_id=result.operation_id or "—",
            return_code=(
                result.return_code if result.return_code is not None else "—"
            ),
        )
        execution = self._text(
            "automation.run.execution",
            mode=result.execution_mode,
            working_directory=result.working_directory or "—",
        )
        self._operation.setText(operation + "\n" + execution)

        sections: list[str] = []
        if result.command:
            sections.append(
                self._text("automation.run.command") + "\n" + result.command
            )
        if result.stdout:
            stdout_key = (
                "automation.run.stdout_truncated"
                if result.stdout_truncated
                else "automation.run.stdout"
            )
            sections.append(
                self._text(stdout_key) + "\n" + result.stdout.rstrip()
            )
        if result.stderr:
            stderr_key = (
                "automation.run.stderr_truncated"
                if result.stderr_truncated
                else "automation.run.stderr"
            )
            sections.append(
                self._text(stderr_key) + "\n" + result.stderr.rstrip()
            )
        self._output.setPlainText("\n\n".join(sections))

    def _on_run_failed(self, detail: str) -> None:
        self._finish_run_state()
        self._run_status.setText(self._text("automation.run.status.internal_error"))
        self._operation.clear()
        self._output.setPlainText(
            self._text("automation.run.stderr") + "\n" + detail
        )

    def _finish_run_state(self) -> None:
        self._running = False
        self._run_btn.setEnabled(bool(self._selected_recipe_id))
        self._run_command_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

    def _apply_adhoc_mode(self, _value: object = None) -> None:
        mode = str(self._adhoc_mode.currentData() or "")
        if mode == "shell":
            help_key = "automation.adhoc.command.shell_help"
            placeholder_key = "automation.adhoc.command.shell_placeholder"
        else:
            help_key = "automation.adhoc.command.exec_help"
            placeholder_key = "automation.adhoc.command.exec_placeholder"
        self._adhoc_command_help.setText(self._text(help_key))
        self._adhoc_command.setPlaceholderText(self._text(placeholder_key))

    def _apply_language(self, _locale: str = "") -> None:
        self._title.setText(self._text("automation.title"))
        self._subtitle.setText(self._text("automation.subtitle"))
        self._registry_title.setText(self._text("automation.registry.title"))
        self._registry_note.setText(self._text("automation.registry.description"))
        self._search.setPlaceholderText(self._text("automation.search.placeholder"))
        self._refresh_btn.setText(self._text("automation.action.refresh"))
        self._import_btn.setText(self._text("automation.action.import"))
        self._issues_title.setText(self._text("automation.discovery.title"))
        self._inputs_title.setText(self._text("automation.inputs.title"))
        self._contract_title.setText(self._text("automation.contract.title"))
        self._command_title.setText(self._text("automation.command.title"))
        self._adhoc_title.setText(self._text("automation.adhoc.title"))
        self._adhoc_description.setText(self._text("automation.adhoc.description"))
        self._adhoc_mode_label.setText(self._text("automation.adhoc.mode.label"))
        for index in range(self._adhoc_mode.count()):
            mode = str(self._adhoc_mode.itemData(index) or "")
            key = AUTOMATION_EXECUTION_MODE_KEYS.get(mode)
            if key:
                self._adhoc_mode.setItemText(index, self._text(key))
        self._adhoc_command_label.setText(
            self._text("automation.adhoc.command.label")
        )
        self._adhoc_cwd_label.setText(
            self._text("automation.adhoc.working_directory.label")
        )
        self._adhoc_cwd.setPlaceholderText(
            self._text("automation.adhoc.working_directory.placeholder")
        )
        self._adhoc_timeout_label.setText(
            self._text("automation.adhoc.timeout.label")
        )
        self._adhoc_output_limit_label.setText(
            self._text("automation.adhoc.output_limit.label")
        )
        self._adhoc_environment_label.setText(
            self._text("automation.adhoc.environment.label")
        )
        self._adhoc_environment_help.setText(
            self._text("automation.adhoc.environment.help")
        )
        self._adhoc_resources_label.setText(
            self._text("automation.adhoc.resources.label")
        )
        self._adhoc_resources_help.setText(
            self._text("automation.adhoc.resources.help")
        )
        self._adhoc_inherit_environment.setText(
            self._text("automation.adhoc.inherit_environment")
        )
        self._apply_adhoc_mode()
        self._runner_title.setText(self._text("automation.runner.title"))
        self._runner_note.setText(self._text("automation.runner.description"))
        self._run_btn.setText(self._text("automation.action.run"))
        self._run_command_btn.setText(
            self._text("automation.action.run_command")
        )
        self._cancel_btn.setText(self._text("automation.action.cancel"))
        self._output_title.setText(self._text("automation.run.output"))
        self._refresh_registry()

    def _render_value(self, value: AutomationTextValue) -> str:
        return self._render(value) if isinstance(value, AutomationText) else value

    def _render(self, text: AutomationText) -> str:
        values = {
            key: self._render(value) if isinstance(value, AutomationText) else value
            for key, value in text.values.items()
        }
        return self._text(text.key, **values)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)
