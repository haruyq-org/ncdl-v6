from collections import deque
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from urllib.parse import urlparse

from rich.align import Align
from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Input, Static

from ui.commands import (
    RESOLUTION_COMMAND,
    RESOLUTION_COMMAND_ALIASES,
    RESOLUTION_DESCRIPTION,
    RESOLUTION_OPTIONS,
    CommandSuggester,
    is_resolution_command,
    is_resolution_number_match,
    normalize_resolution,
    parse_resolution_command,
)
from ui.logo import LOGO_PRIMARY, LOGO_SECONDARY, render_ncdl_logo
from ui.settings import SettingsScreen
from utils import config, ytd
from utils.paths import get_resource_dir, is_frozen
from utils.tools import get_ytd_version

CSS_PATH = str(Path(__file__).resolve().parent / "css" / "ui.css")
if is_frozen():
    CSS_PATH = str(get_resource_dir() / "ui" / "css" / "ui.css")

MODE_COLORS = {
    "MP4": LOGO_PRIMARY,
    "MP3": LOGO_SECONDARY,
}

@dataclass
class DownloadJob:
    id: int
    uri: str
    mode: str
    resolution_height: int | None = None
    title: str | None = None

def format_mode(mode: str, resolution_height: int | None) -> str:
    if resolution_height is None:
        return mode

    return f"{mode} {resolution_height}p"

class NCDLApp(App):
    CSS_PATH = CSS_PATH
    BINDINGS = [
        Binding("tab", "toggle_mode", "モード切替", priority=True),
        Binding("ctrl+p", "open_settings", "設定", priority=True),
    ]

    mode = reactive("MP4", init=False)
    ytd_version = reactive("Unknown", init=False)

    def __init__(self):
        super().__init__()
        self.download_queue = deque()
        self.active_job: DownloadJob | None = None
        self.job_ids = count(1)
        self.queue_dots = 0
        self.logo_frame = 0

    @property
    def mode_color(self) -> str:
        return MODE_COLORS[self.mode]

    def state(self) -> str:
        default_resolution = self.get_default_resolution_height() if self.mode == "MP4" else None
        mode = format_mode(self.mode, default_resolution)
        dl_state = f"[{self.mode_color}]{mode}[/]"
        platform = f"[dim] ・ yt-dlp {self.ytd_version}[/]"
        return f"{dl_state}{platform}"

    def queue_label(self, label: str, max_length: int) -> str:
        if len(label) <= max_length:
            return label

        return f"{label[:max_length - 3]}..."

    def get_default_resolution_height(self) -> int | None:
        return normalize_resolution(config.get_default_resolution())

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
                            placeholder="URLを入力...",
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
            config.get_output_path().as_posix(),
            id="output_path",
        )

        with Horizontal(id="footer"):
            with Container(id="download_queue"):
                yield Static("QUEUE", id="queue_title")
                yield Static("", id="queue_items")

    def on_mount(self) -> None:
        self.ytd_version = get_ytd_version()
        self.update_mode_view()
        self.update_queue_view()
        self.update_command_help("")
        self.set_interval(0.12, self.update_logo_animation)
        self.set_interval(0.4, self.update_queue_dots)

    def watch_mode(self, mode: str) -> None:
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

    def update_logo_animation(self) -> None:
        if not self.is_mounted:
            return

        self.logo_frame += 1
        self.query_one("#logo", Static).update(Align.center(render_ncdl_logo(self.logo_frame)))

    def action_toggle_mode(self) -> None:
        self.mode = "MP3" if self.mode == "MP4" else "MP4"

    def action_open_settings(self) -> None:
        if isinstance(self.screen, SettingsScreen):
            self.screen.dismiss(None)
            return

        self.push_screen(SettingsScreen())

    def update_settings_view(self) -> None:
        self.query_one("#output_path", Static).update(config.get_output_path().as_posix())
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
        resolution_command = is_resolution_command(command)

        if resolution_command:
            lines.append(
                f"[#050505 on {LOGO_PRIMARY}] {RESOLUTION_COMMAND.ljust(14)} [/]"
                f"[#050505 on {LOGO_PRIMARY}] {RESOLUTION_DESCRIPTION} [/]"
            )
        else:
            lines.append("[#d8d8d8]該当するコマンドがありません[/]")

        if resolution_command:
            options = []
            for number, height in RESOLUTION_OPTIONS.items():
                style = f"#050505 on {LOGO_PRIMARY}" if is_resolution_number_match(value, number) else "#8fc9d9"
                options.append(f"[{style}] {number}:{height}p [/]")

            lines.append(" ".join(options[:4]))
            lines.append(" ".join(options[4:]))

        command_help_items.update("\n".join(lines))

    def handle_input_submit(self, value: str) -> None:
        try:
            mode = self.mode
            resolution_height = self.get_default_resolution_height() if mode == "MP4" else None
            uri = value

            if value.startswith("/"):
                command = value.split(maxsplit=1)[0].casefold()
                if command not in RESOLUTION_COMMAND_ALIASES:
                    self.notify("不明なコマンドです。", severity="error")
                    return

                try:
                    uri, resolution_height = parse_resolution_command(value)
                except ValueError as e:
                    self.notify(str(e), severity="error")
                    return

                mode = "MP4"

            parsed_url = urlparse(uri)
            if not parsed_url.scheme or not parsed_url.netloc:
                self.notify("無効なURLです。", severity="error")
                return

            self.download_queue.append(
                DownloadJob(
                    id=next(self.job_ids),
                    uri=uri,
                    mode=mode,
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
            mode = escape(format_mode(self.active_job.mode, self.active_job.resolution_height))
            color = MODE_COLORS[self.active_job.mode]
            lines.append(f"[{color}]{mode}  [/] [#d8d8d8]{title}[/] [dim]{dots}[/]")

        for i, job in enumerate(jobs[:3], start=1):
            title = escape(self.queue_label(job.title or job.uri, 42))
            mode = escape(format_mode(job.mode, job.resolution_height))
            color = MODE_COLORS[job.mode]
            lines.append(f"[dim]{i:02}[/] [{color}]{mode}[/] [#8a8a8a]{title}[/]")

        if len(jobs) > 3:
            lines.append(f"[dim]+{len(jobs) - 3} more[/]")

        queue_title.update(f"[dim]QUEUE[/] [{LOGO_PRIMARY}]{len(jobs)}[/]")
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
        output_path = config.get_output_path()
        try:
            title = ytd.get_title(job.uri) or job.uri
            self.call_from_thread(self.update_job_title, job.id, title)

            if job.mode == "MP4":
                ytd.download_mp4(
                    job.uri,
                    output_path,
                    resolution_height=job.resolution_height,
                )
            elif job.mode == "MP3":
                ytd.download_mp3(job.uri, output_path)
        except Exception:
            pass

        self.call_from_thread(self.finish_job, job.id)
