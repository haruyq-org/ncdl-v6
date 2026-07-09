import os

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from ui.commands import RESOLUTION_OPTIONS, normalize_resolution
from ui.logo import LOGO_PRIMARY
from utils import config

class SettingsScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "cancel", "閉じる", priority=True),
        Binding("up", "settings_focus_previous", "前へ", show=False, priority=True),
        Binding("down", "settings_focus_next", "次へ", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        saved_resolution = normalize_resolution(config.get_default_resolution())
        default_resolution = saved_resolution if saved_resolution is not None else 0
        resolution_options = [("最高画質", 0)]
        resolution_options.extend((f"{height}p", height) for height in RESOLUTION_OPTIONS.values())

        with Container(id="settings_dialog"):
            yield Static(f"[{LOGO_PRIMARY}]CONFIG[/]", id="settings_title")
            yield Label("ダウンロード先", classes="settings_label")
            with Horizontal(id="settings_output_row"):
                yield Input(
                    value=config.get_output_path_value(),
                    placeholder="downloads",
                    id="settings_output_path",
                )
                yield Button("...", id="settings_browse")
            yield Label("標準画質", classes="settings_label")
            yield Select(
                resolution_options,
                value=default_resolution,
                allow_blank=False,
                id="settings_default_resolution",
            )

    def on_mount(self) -> None:
        self.query_one("#settings_output_path", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_settings_focus_previous(self) -> None:
        self.focus_previous()

    def action_settings_focus_next(self) -> None:
        self.focus_next()

    def apply_settings(self) -> None:
        output_path = self.query_one("#settings_output_path", Input).value.strip() or "downloads"
        select = self.query_one("#settings_default_resolution", Select)
        default_resolution = select.value if isinstance(select.value, int) and select.value > 0 else None
        config.save_download(output_path, default_resolution)

        if hasattr(self.app, "update_settings_view"):
            self.app.update_settings_view()

    @on(Input.Changed, "#settings_output_path")
    def on_output_path_changed(self) -> None:
        self.apply_settings()

    @on(Select.Changed, "#settings_default_resolution")
    def on_default_resolution_changed(self) -> None:
        self.apply_settings()

    @on(Button.Pressed, "#settings_browse")
    def on_browse_pressed(self) -> None:
        root = None
        try:
            from tkinter import Tk, filedialog

            initial_dir = config.get_output_path()
            if not initial_dir.exists():
                initial_dir = initial_dir.parent
            if not initial_dir.exists():
                initial_dir = os.getcwd()

            root = Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(
                initialdir=str(initial_dir),
                title="出力先フォルダを選択",
            )

            if folder:
                self.query_one("#settings_output_path", Input).value = folder
        except Exception as e:
            self.notify(str(e), severity="error")
        finally:
            if root is not None:
                root.destroy()
