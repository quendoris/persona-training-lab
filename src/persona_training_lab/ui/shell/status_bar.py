from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar

from persona_training_lab.ui.i18n.manager import LocalizationManager


class AppStatusBar(QStatusBar):
    def __init__(
        self,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._localization = localization
        self._message_key: str | None = None
        self._message_values: dict[str, object] = {}
        self._left = QLabel()
        self._right = QLabel()
        self.addWidget(self._left)
        self.addPermanentWidget(self._right)
        self.set_message_key("status.ready")
        if localization is not None:
            localization.language_changed.connect(self._refresh_message)

    def set_message(self, text: str) -> None:
        self._message_key = None
        self._message_values.clear()
        self._left.setText(text)

    def set_message_key(self, key: str, **values: object) -> None:
        self._message_key = key
        self._message_values = dict(values)
        self._refresh_message()

    def set_style_message(self, text: str) -> None:
        self._right.setText(text)

    def _refresh_message(self, _locale: str = "") -> None:
        key = self._message_key
        if key is None:
            return
        if self._localization is None:
            self._left.setText(key)
            return
        self._left.setText(
            self._localization.text(key, **self._message_values)
        )
