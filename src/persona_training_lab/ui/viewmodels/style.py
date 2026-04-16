from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.style.service import StylePreferencesService


@dataclass(slots=True)
class StyleViewModel:
    style_service: StylePreferencesService

    def load(self) -> dict[str, str | None]:
        return self.style_service.load_preferences()

    def save(self, theme: str, accent_palette: str, button_style_preset: str) -> None:
        self.style_service.save_preferences(
            {
                "theme": theme,
                "accent_palette": accent_palette,
                "button_style_preset": button_style_preset,
            }
        )
