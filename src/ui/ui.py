import os
from collections import deque
from dataclasses import dataclass
from itertools import count
from urllib.parse import urlparse
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Container
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static
from rich.align import Align
from rich.markup import escape
from textual.reactive import reactive
from textual.suggester import Suggester

from ui.logo import render_ncdl_logo
from utils.config import Config
from utils.ytd import RESOLUTION_OPTIONS, YTD, YTDUpdater

RESOLUTION_COMMAND = "/r"
RESOLUTION_COMMAND_ALIASES = (RESOLUTION_COMMAND, "/resolution")
RESOLUTION_DESCRIPTION = "解像度を番号で指定してMP4をダウンロード"

class CommandSuggester(Suggester):
    async def get_suggestion(self, value: str) -> str | None:
        if not value.startswith("/"):
            return None

        for alias in RESOLUTION_COMMAND_ALIASES:
            if alias.startswith(value):
                return f"{alias} "

        command = value.split(maxsplit=1)[0]
        if command in RESOLUTION_COMMAND_ALIASES and value.startswith(f"{command} "):
            argument = value.removeprefix(f"{command} ")
            if " " in argument:
                return None

            for number in RESOLUTION_OPTIONS:
                suggestion = str(number)
                if suggestion.startswith(argument):
                    return f"{command} {suggestion} "

        return None

@dataclass
class DownloadJob:
    id: int
    uri: str
    mode: str
    mode_color: str
    resolution_height: int | None = None
    title: str | None = None

class SettingsScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "cancel", "閉じる", priority=True),
        Binding("up", "settings_focus_previous", "前へ", show=False, priority=True),
        Binding("down", "settings_focus_next", "次へ", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        saved_resolution = Config.get_default_resolution()
        default_resolution = saved_resolution if saved_resolution in RESOLUTION_OPTIONS.values() else 0
        resolution_options = [("最高画質", 0)]
        resolution_options.extend((f"{height}p", height) for height in RESOLUTION_OPTIONS.values())

        with Container(id="settings_dialog"):
            yield Static("[#b94fff]CONFIG[/]", id="settings_title")
            yield Label("保存先", classes="settings_label")
            with Horizontal(id="settings_output_row"):
                yield Input(
                    value=Config.get_output_path_value(),
                    placeholder="downloads",
                    id="settings_output_path",
                )
                yield Button("フォルダを開く", id="settings_browse")
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
        Config.save_download(output_path, default_resolution)

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

            initial_dir = Config.get_output_path()
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
                self.apply_settings()
        except Exception as e:
            self.notify(str(e), severity="error")
        finally:
            if root is not None:
                root.destroy()

class NCDLApp(App):
    CSS_PATH = os.path.dirname(__file__) + "\\css\\ui.css"
    BINDINGS = [
        Binding("tab", "toggle_mode", "モード切替", priority=True),
        Binding("ctrl+p", "open_settings", "設定", priority=True),
    ]

    mode = reactive("MP4", init=False)
    mode_color = reactive("#b94fff", init=False)
    
    ytd_version = reactive("Unknown", init=False)

    def __init__(self):
        super().__init__()
        self.download_queue = deque()
        self.active_job: DownloadJob | None = None
        self.job_ids = count(1)
        self.queue_dots = 0
    
    def state(self) -> str:
        mode = self.mode
        default_resolution = self.get_default_resolution_height()
        if mode == "MP4" and default_resolution is not None:
            mode = f"{mode} {default_resolution}p"

        dl_state = f"[{self.mode_color}]{mode}[/]"
        platform = f"[dim] ・ yt-dlp {self.ytd_version}[/]"
        return f"{dl_state}{platform}"

    def queue_label(self, label: str, max_length: int) -> str:
        if len(label) <= max_length:
            return label

        return f"{label[:max_length - 3]}..."

    def get_default_resolution_height(self) -> int | None:
        default_resolution = Config.get_default_resolution()
        if default_resolution in RESOLUTION_OPTIONS.values():
            return default_resolution

        return None

    def compose(self) -> ComposeResult:
        with Container(id="container"):
            with Vertical(id="hero"):
                
                with Container(id="command_help"):
                    yield Static("", id="command_help_items")

                yield Static(Align.center(render_ncdl_logo()), id="logo")
            
                with Horizontal(id="prompt_row"):
                    yield Static("", id="prompt_border", classes="mode_indicator")

                    with Container(id="prompt_panel"):
                        yield Input(
                            placeholder='URLを入力...',
                            suggester=CommandSuggester(),
                            id="uri",
                        )
                        yield Static(
                            self.state(),
                            id="state",
                        )
                yield Static(
                    "[dim]tab[/] モード切替  [dim]ctrl+p[/] 設定  [dim]/[/] コマンド",
                    id="shortcut_bar",
                )
            
        yield Static(
            Config.get_output_path().as_posix(),
            id="output_path",
        )
        
        with Horizontal(id="footer"):
            with Container(id="download_queue"):
                yield Static("QUEUE", id="queue_title")
                yield Static("", id="queue_items")

    def on_mount(self) -> None:
        self.ytd_version = YTDUpdater.get_ytd_version()
        self.update_mode_view()
        self.update_queue_view()
        self.update_command_help("")
        self.set_interval(0.4, self.update_queue_dots)

    def watch_mode(self, mode: str) -> None:
        self.update_mode_view()

    def watch_mode_color(self, mode_color: str) -> None:
        self.update_mode_view()

    def watch_ytd_version(self, ytd_version: str) -> None:
        self.update_mode_view()

    def update_mode_view(self) -> None:
        if not self.is_mounted:
            return
        
        self.query_one("#state", Static).update(self.state())
        self.query_one(
            "#prompt_border",
            Static,
        ).styles.border_left = ("solid", self.mode_color)

    def action_toggle_mode(self) -> None:
        self.mode = "MP3" if self.mode == "MP4" else "MP4"
        self.mode_color = "#4fd8ff" if self.mode == "MP3" else "#b94fff"

    def action_open_settings(self):
        return self.push_screen(SettingsScreen())

    def update_settings_view(self) -> None:
        self.query_one("#output_path", Static).update(Config.get_output_path().as_posix())
        self.update_mode_view()

    @on(Input.Changed, "#uri")
    def on_uri_changed(self, event: Input.Changed) -> None:
        self.update_command_help(event.value)

    @on(Input.Submitted, "#uri")
    def on_uri_submitted(self, event: Input.Submitted) -> None:
        uri = event.value.strip()
        if uri == "":
            return
        
        event.input.value = ""
        self.update_command_help("")

        self.handle_input_submit(uri)

    def update_command_help(self, value: str) -> None:
        if not self.is_mounted:
            return

        command_help = self.query_one("#command_help", Container)
        command_help_items = self.query_one("#command_help_items", Static)
        value = value.strip()

        if not value.startswith("/"):
            command_help.display = False
            command_help_items.update("")
            return

        command_help.display = True
        lines = []
        command = value.split(maxsplit=1)[0].casefold()

        if self.is_resolution_command(command):
            lines.append(
                f"[#050505 on #4fd8ff] {RESOLUTION_COMMAND.ljust(14)} [/]"
                f"[#050505 on #4fd8ff] {RESOLUTION_DESCRIPTION} [/]"
            )
        else:
            lines.append("[#d8d8d8]該当するコマンドがありません[/]")

        if self.is_resolution_command(command):
            options = []
            for number, height in RESOLUTION_OPTIONS.items():
                style = "#050505 on #4fd8ff" if self.is_resolution_number_match(value, number) else "#8fc9d9"
                options.append(f"[{style}] {number}:{height}p [/]")

            lines.append(" ".join(options[:4]))
            lines.append(" ".join(options[4:]))

        command_help_items.update("\n".join(lines))

    def is_resolution_command(self, command: str) -> bool:
        return any(alias.startswith(command) or command == alias for alias in RESOLUTION_COMMAND_ALIASES)

    def is_resolution_number_match(self, value: str, number: int) -> bool:
        parts = value.split(maxsplit=2)
        if len(parts) < 2:
            return number == next(iter(RESOLUTION_OPTIONS))

        return str(number).startswith(parts[1])

    def parse_resolution_command(self, command: str) -> tuple[str, int] | None:
        parts = command.split(maxsplit=2)
        if len(parts) != 3:
            self.notify("使い方: /r 番号 URL", severity="error")
            return None

        try:
            number = int(parts[1])
            resolution_height = RESOLUTION_OPTIONS[number]
        except (ValueError, KeyError):
            options = ", ".join(f"{number}={height}p" for number, height in RESOLUTION_OPTIONS.items())
            self.notify(f"解像度番号は {options} から指定してください。", severity="error")
            return None

        return parts[2].strip(), resolution_height

    def handle_input_submit(self, value: str) -> None:
        output_path = Config.get_output_path()
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            mode = self.mode
            mode_color = self.mode_color
            resolution_height = self.get_default_resolution_height() if mode == "MP4" else None
            uri = value

            if value.startswith("/"):
                command = value.split(maxsplit=1)[0].casefold()
                if command not in RESOLUTION_COMMAND_ALIASES:
                    self.notify("不明なコマンドです。", severity="error")
                    return

                parsed_command = self.parse_resolution_command(value)
                if parsed_command is None:
                    return

                uri, resolution_height = parsed_command
                mode = "MP4"
                mode_color = "#b94fff"

            parsed_url = urlparse(uri)
            if not parsed_url.scheme or not parsed_url.netloc:
                self.notify("無効なURLです。", severity="error")
                return

            self.download_queue.append(
                DownloadJob(
                    id=next(self.job_ids),
                    uri=uri,
                    mode=mode,
                    mode_color=mode_color,
                    resolution_height=resolution_height,
                )
            )
            self.update_queue_view()
            self.start_next_download()

        except Exception as e:
            self.notify(str(e), severity="error")

    def start_next_download(self) -> None:
        if self.active_job is not None or not self.download_queue:
            return

        self.active_job = self.download_queue.popleft()
        self.active_job.title = "タイトル取得中"
        self.queue_dots = 0
        self.update_queue_view()
        self.download_job(self.active_job)

    def update_queue_dots(self) -> None:
        if self.active_job is None:
            return

        self.queue_dots = (self.queue_dots + 1) % 3
        self.update_queue_view()

    def job_mode_label(self, job: DownloadJob) -> str:
        if job.resolution_height is None:
            return job.mode

        return f"{job.mode} {job.resolution_height}p"

    def update_queue_view(self) -> None:
        if not self.is_mounted:
            return

        queue_panel = self.query_one("#download_queue", Container)
        queue_title = self.query_one("#queue_title", Static)
        queue_items = self.query_one("#queue_items", Static)
        jobs = list(self.download_queue)
        lines = []

        if self.active_job is not None:
            title = escape(self.queue_label(self.active_job.title or self.active_job.uri, 44))
            dots = "." * (self.queue_dots + 1)
            mode = escape(self.job_mode_label(self.active_job))
            lines.append(f"[{self.active_job.mode_color}]{mode}  [/] [#d8d8d8]{title}[/] [dim]{dots}[/]")

        for i, job in enumerate(jobs[:3], start=1):
            title = escape(self.queue_label(job.title or job.uri, 42))
            mode = escape(self.job_mode_label(job))
            lines.append(f"[dim]{i:02}[/] [{job.mode_color}]{mode}[/] [#8a8a8a]{title}[/]")

        if len(jobs) > 3:
            lines.append(f"[dim]+{len(jobs) - 3} more[/]")

        queue_title.update(f"[dim]QUEUE[/] [#4fd8ff]{len(jobs)}[/]")
        queue_items.update("\n".join(lines))

        target_opacity = 1.0 if self.active_job is not None or jobs else 0.0
        queue_panel.styles.animate(
            "opacity",
            target_opacity,
            duration=0.2,
            easing="out_cubic",
        )

    def update_job_title(self, job_id: int, title: str) -> None:
        if self.active_job is None or self.active_job.id != job_id:
            return

        self.active_job.title = title
        self.update_queue_view()

    def finish_job(self, job_id: int) -> None:
        if self.active_job is None or self.active_job.id != job_id:
            return

        self.active_job = None
        self.update_queue_view()
        self.start_next_download()

    @work(thread=True)
    def download_job(self, job: DownloadJob) -> None:
        output_path = Config.get_output_path()
        try:
            title = YTD.get_title(job.uri) or job.uri
            self.call_from_thread(self.update_job_title, job.id, title)

            if job.mode == "MP4":
                result = YTD.download_mp4(
                    job.uri,
                    output_path,
                    resolution_height=job.resolution_height,
                )
            elif job.mode == "MP3":
                result = YTD.download_mp3(job.uri, output_path)
            else:
                result = False
        except Exception:
            result = False

        self.call_from_thread(self.finish_job, job.id)
