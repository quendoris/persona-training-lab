from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.style.service import StylePreferencesService


@dataclass(slots=True)
class StyleViewModel:
    style_service: StylePreferencesService

    def load(self) -> dict[str, str | None]:
        return self.style_service.load_preferences()

    def save(self, theme: str, accent_palette: str, button_style_preset: str) -> None:
        current = self.load()
        self.style_service.save_preferences(
            {
                "theme": theme,
                "accent_palette": accent_palette,
                "button_style_preset": button_style_preset,
                "ui_scale": current.get("ui_scale") or "auto",
            }
        )

    def save_ui_scale(self, ui_scale: str) -> None:
        current = self.load()
        self.style_service.save_preferences(
            {
                "theme": current.get("theme") or "velvet",
                "accent_palette": current.get("accent_palette") or "cyan",
                "button_style_preset": current.get("button_style_preset") or "soft_glow",
                "ui_scale": ui_scale,
            }
        )
