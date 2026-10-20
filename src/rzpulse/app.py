"""Keyboard-first read-only Razorpay workspace."""
import json
from datetime import datetime, timezone
from pathlib import Path

from rich.syntax import Syntax
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, LoadingIndicator, Select, Static,
)

from rzpulse.api.client import RazorpayClient
from rzpulse.api.errors import APIError
from rzpulse.api.registry import REGISTRY
from rzpulse.config import ConfigurationError, Settings
from rzpulse.services.analytics import refund_summary, summarize
from rzpulse.services.export import export_records
from rzpulse.utils.formatting import money, timestamp
from rzpulse.utils.security import redact

RESOURCES = ("payments", "orders", "refunds", "settlements")


class Detail(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, title: str, data):
        super().__init__()
        self.title_text = title
        self.data = data

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.title_text, markup=False)
            with VerticalScroll():
                yield Static(Syntax(json.dumps(self.data, indent=2, ensure_ascii=False), "json",
                                    word_wrap=True))
            yield Button("Close [Esc]", id="close")

    @on(Button.Pressed, "#close")
    def close_dialog(self):
        self.dismiss()


class ExportDialog(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, records, secrets):
        super().__init__()
        self.records = records
        self.secrets = secrets

    def compose(self):
        with Vertical(id="export-dialog"):
            yield Label("Export current visible page • sensitive fields masked")
            yield Input(placeholder="Path ending in .json or .csv", id="export-path")
            yield Static("Existing files will never be overwritten.", id="export-status")
            yield Button("Export", id="save")

    @on(Button.Pressed, "#save")
    def save(self):
        path = Path(self.query_one(Input).value).expanduser()
        if path.suffix.lower() not in {".json", ".csv"}:
            self.query_one("#export-status", Static).update("Choose .json or .csv.")
            return
        try:
            export_records(path, self.records, self.secrets)
        except (OSError, ValueError):
            self.query_one("#export-status", Static).update(
                "Export failed. Check destination permissions or choose a new filename.")
            return
        self.dismiss()


class RZPulse(App):
    TITLE = "RZPulse"
    SUB_TITLE = "Read-only Razorpay workspace"
    CSS = """
    Screen { background: #0d1420; color: #d8e2f0; }
    Header { background: #17263b; }
    Footer { background: #17263b; }
    #body { height: 1fr; }
    #sidebar { width: 23; padding: 1; background: #111e30; overflow-y: auto; }
    #sidebar Button { width: 100%; margin-bottom: 1; border: none; text-align: left; }
    #main { width: 1fr; padding: 1 2; }
    #mode { height: 2; color: #66aaff; text-style: bold; }
    #heading { height: 2; text-style: bold; }
    #status { height: auto; min-height: 2; color: #9db4d2; }
    #summary { height: auto; margin: 1 0; }
    #controls { height: auto; }
    #controls Input { width: 1fr; }
    #controls Button { min-width: 8; }
    #filters { height: auto; max-height: 20; }
    #filters Input { margin-bottom: 1; }
    #explorer { height: auto; max-height: 65%; overflow-y: auto; }
    #parameters { height: auto; }
    #op-info { height: auto; margin: 1 0; }
    #results { height: 1fr; }
    #table { height: 1fr; }
    #json { height: auto; }
    #loading { height: 3; }
    #dialog { width: 90%; height: 90%; padding: 1 2; background: #17263b; border: solid #4b91ed; }
    #export-dialog { width: 80%; height: auto; padding: 2; background: #17263b; border: solid #4b91ed; }
    Detail, ExportDialog { align: center middle; background: #000000 60%; }
    .hidden { display: none; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"), Binding("r", "refresh", "Refresh"),
        Binding("slash", "search", "Search"), Binding("f", "filters", "Filters"),
        Binding("e", "export", "Export"), Binding("question_mark", "help", "Help"),
        Binding("j", "down", "Down", show=False), Binding("k", "up", "Up", show=False),
        Binding("escape", "back", "Back", show=False),
    ]

    def __init__(self, settings: Settings | None = None, client=None):
        super().__init__()
        self.configuration_error = ""
        try:
            self.settings = settings or Settings.load()
        except ConfigurationError as exc:
            self.settings = None
            self.configuration_error = str(exc)
        self.client = client or (RazorpayClient(self.settings) if self.settings else None)
        self.section = "dashboard" if self.client else "settings"
        self.records: list[dict] = []
        self.visible_records: list[dict] = []
        self.skip = 0
        self.page_size = 25
        self.has_next = False
        self.date_filters: dict = {}
        self.loaded_at = ""

    def compose(self):
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                for section in ("dashboard", *RESOURCES):
                    yield Button(section.title(), id=f"nav-{section}")
                for future in ("Customers", "Subscriptions", "Payment Links", "Invoices"):
                    yield Button(f"{future} (future)", disabled=True)
                yield Button("API Explorer", id="nav-explorer")
                yield Button("Settings", id="nav-settings")
            with Vertical(id="main"):
                yield Static(id="mode")
                yield Static(id="heading")
                yield Static(id="status", markup=False)
                yield Static(id="summary", markup=False)
                with Vertical(id="explorer", classes="hidden"):
                    yield Select([(key, key) for key in REGISTRY], value="payments.list", id="operation")
                    yield Static(id="op-info", markup=False)
                    yield Vertical(id="parameters")
                    yield Button("Execute GET", id="execute", variant="primary")
                with Horizontal(id="controls"):
                    yield Input(placeholder="Search visible page…", id="search")
                    yield Button("◀ Prev", id="prev")
                    yield Button("Next ▶", id="next")
                    yield Button("Sort ID", id="sort")
                    yield Button("Export", id="export")
                with Vertical(id="filters", classes="hidden"):
                    yield Input(placeholder="From: YYYY-MM-DD (UTC, inclusive)", id="from-date")
                    yield Input(placeholder="To: YYYY-MM-DD (UTC, inclusive)", id="to-date")
                    yield Button("Apply date range", id="apply-filter")
                yield LoadingIndicator(id="loading", classes="hidden")
                with VerticalScroll(id="results"):
                    yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
                    yield Static(id="json", markup=False)
        yield Footer()

    async def on_mount(self):
        self.theme = "textual-dark"
        self.query_one("#table", DataTable).add_columns("Identifier", "Status", "Amount", "Created (UTC)")
        await self.navigate(self.section)

    async def on_unmount(self):
        if self.client:
            await self.client.close()

    def secrets(self):
        if not self.settings:
            return ()
        return (self.settings.key_id.get_secret_value(), self.settings.key_secret.get_secret_value())

    def check_action(self, action, parameters):
        if isinstance(self.focused, Input) and action in {
            "quit", "refresh", "search", "filters", "export", "help", "down", "up"
        }:
            return False
        return True

    async def navigate(self, section):
        self.workers.cancel_group(self, "request")
        self.section = section
        self.skip = 0
        self.records = []
        self.visible_records = []
        self.has_next = False
        self.query_one("#search", Input).value = ""
        self.query_one("#mode", Static).update(
            f"● {self.settings.mode.upper()} • READ ONLY" if self.settings else "● NOT CONFIGURED • READ ONLY")
        self.query_one("#heading", Static).update(section.replace("explorer", "API Explorer").title())
        for element in ("summary", "json", "status"):
            self.query_one(f"#{element}", Static).update("")
        self.query_one("#loading").add_class("hidden")
        self.query_one("#table", DataTable).clear()
        self.query_one("#explorer").set_class(section != "explorer", "hidden")
        self.query_one("#controls").set_class(section not in (*RESOURCES, "dashboard"), "hidden")
        self.query_one("#table").set_class(section not in (*RESOURCES, "dashboard"), "hidden")
        self.query_one("#filters").add_class("hidden")
        if section == "settings":
            self.query_one("#json", Static).update(
                "Configure .env in the working directory, then restart RZPulse.\n\n"
                "RZP_MODE=test\nRZP_TEST_KEY_ID=rzp_test_…\nRZP_TEST_KEY_SECRET=…\n\n"
                "Use RZP_LIVE_KEY_ID / RZP_LIVE_KEY_SECRET with RZP_MODE=live.\n"
                "RZP_KEY_ID / RZP_KEY_SECRET also supported. Environment overrides .env.\n"
                "Mode is never switched automatically. No credentials are displayed.\n\n"
                + (self.configuration_error or "Configuration validated locally; API access is not yet verified."))
        elif section == "explorer":
            await self.build_parameters()
        else:
            self.load_page()

    @on(Button.Pressed)
    async def button_pressed(self, event: Button.Pressed):
        name = event.button.id or ""
        if name.startswith("nav-"):
            await self.navigate(name[4:])
        elif name == "next" and self.has_next:
            self.skip += self.page_size
            self.load_page()
        elif name == "prev" and self.skip:
            self.skip = max(0, self.skip - self.page_size)
            self.load_page()
        elif name == "execute":
            self.execute_explorer()
        elif name == "apply-filter":
            self.apply_filters()
        elif name == "export":
            self.action_export()
        elif name == "sort":
            self.records.sort(key=lambda row: str(row.get("id", "")))
            self.render_table()

    @work(exclusive=True, group="request")
    async def load_page(self):
        if not self.client:
            self.query_one("#status", Static).update("No credentials. Open Settings to configure access.")
            return
        self.query_one("#loading").remove_class("hidden")
        self.query_one("#status", Static).update("Loading from Razorpay…")
        self.query_one("#prev", Button).disabled = True
        self.query_one("#next", Button).disabled = True
        self.records = []
        self.render_table()
        try:
            resource = "payments" if self.section == "dashboard" else self.section
            params = {**self.date_filters, "count": self.page_size, "skip": self.skip}
            data = await self.client.execute(f"{resource}.list", params)
            self.records = data["items"]
            self.has_next = len(self.records) == self.page_size
            self.loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            date_range = "all dates" if not self.date_filters else ", ".join(
                f"{k}: {timestamp(v)}" for k, v in self.date_filters.items())
            self.query_one("#status", Static).update(
                f"HTTP {self.client.last_status} • {date_range} • refreshed {self.loaded_at}\n"
                f"Page sample: {len(self.records)} records, offset {self.skip}. "
                "Not account-wide totals." + (" Next page may exist." if self.has_next else ""))
            if self.section == "dashboard":
                stats = summarize(self.records)
                amounts = " · ".join(money(v, k) for k, v in stats["captured"].items()) or "—"
                lines = [
                    f"PAYMENTS ON PAGE  {stats['payments']}    CAPTURED  {stats['successful']}    "
                    f"FAILED  {stats['failed']}", f"Captured amounts: {amounts}",
                ]
                for related in ("refunds", "settlements"):
                    try:
                        sample = await self.client.execute(f"{related}.list", params)
                        items = sample["items"]
                        if related == "refunds":
                            refunds = refund_summary(items)
                            refunded = " · ".join(money(v, k) for k, v in refunds["amounts"].items()) or "—"
                            lines.append(f"REFUND PAGE  {refunds['count']} records • "
                                         f"{refunds['processed']} processed • processed amounts: {refunded}")
                        else:
                            processed = sum(item.get("status") == "processed" for item in items)
                            lines.append(f"SETTLEMENT PAGE  {len(items)} records • {processed} processed")
                    except APIError as exc:
                        lines.append(f"{related.upper()} unavailable: {exc}")
                lines.append("Independent page samples at the same offset; no account-wide totals. Recent payments below.")
                self.query_one("#summary", Static).update("\n".join(lines))
            self.render_table()
        except (APIError, ValueError) as exc:
            status = getattr(exc, "status", None)
            self.query_one("#status", Static).update(f"{f'HTTP {status} • ' if status else ''}{exc}")
            self.has_next = False
            self.query_one("#summary", Static).update("")
        finally:
            self.query_one("#loading").add_class("hidden")
            self.query_one("#prev", Button).disabled = self.skip == 0
            self.query_one("#next", Button).disabled = not self.has_next

    def render_table(self):
        table = self.query_one("#table", DataTable)
        table.clear()
        term = self.query_one("#search", Input).value.casefold()
        safe = redact(self.records, self.secrets())
        self.visible_records = [r for r in safe if term in json.dumps(r).casefold()]
        for index, record in enumerate(self.visible_records):
            # Rich Text avoids interpreting returned values as terminal markup.
            from rich.text import Text
            table.add_row(Text(str(record.get("id", "—"))), Text(str(record.get("status", "—"))),
                          Text(money(record.get("amount"), record.get("currency"))),
                          Text(timestamp(record.get("created_at"))), key=str(index))
        if not self.visible_records and self.records:
            self.query_one("#summary", Static).update("No records match this page search.")
        elif not self.records:
            self.query_one("#summary", Static).update("No records loaded.")

    @on(Input.Changed, "#search")
    def search_changed(self):
        self.render_table()

    @on(DataTable.RowSelected, "#table")
    def record_selected(self, event):
        index = int(str(event.row_key.value))
        if index < len(self.visible_records):
            record = self.visible_records[index]
            self.show_record(str(record.get("id", "")))

    @work(exclusive=True, group="request")
    async def show_record(self, record_id):
        if not self.client:
            return
        try:
            resource = "payments" if self.section == "dashboard" else self.section
            data = await self.client.execute(f"{resource}.fetch", {"id": record_id})
            self.push_screen(Detail("Record detail • full returned JSON, sensitive fields masked",
                                    redact(data, self.secrets())))
        except (APIError, ValueError) as exc:
            self.query_one("#status", Static).update(str(exc))

    @on(Select.Changed, "#operation")
    async def operation_changed(self):
        if self.is_mounted and self.section == "explorer":
            self.workers.cancel_group(self, "request")
            self.query_one("#json", Static).update("")
            await self.build_parameters()

    async def build_parameters(self):
        selected = self.query_one("#operation", Select).value
        if selected is Select.BLANK:
            return
        op = REGISTRY[str(selected)]
        self.query_one("#op-info", Static).update(
            f"{op.method} {op.path}\n{op.description}\n{op.authentication}\n"
            f"{op.availability}\n{op.documentation}\n"
            "Required: " + (", ".join(op.required) or "none") +
            " • Optional: " + (", ".join(op.optional) or "none"))
        container = self.query_one("#parameters", Vertical)
        await container.remove_children()
        for param in (*op.required, *op.optional):
            await container.mount(Input(placeholder=f"{param}" +
                                        (" (required)" if param in op.required else " (optional)"),
                                        id=f"param-{param}"))

    @work(exclusive=True, group="request")
    async def execute_explorer(self):
        if not self.client:
            self.query_one("#status", Static).update("Configure credentials in Settings first.")
            return
        selected = str(self.query_one("#operation", Select).value)
        params = {widget.id[6:]: widget.value for widget in
                  self.query_one("#parameters").query(Input) if widget.value}
        self.query_one("#loading").remove_class("hidden")
        self.query_one("#json", Static).update("")
        try:
            op = REGISTRY[selected]
            path, query = op.prepare(params)
            self.query_one("#status", Static).update(
                f"GET {path} • {json.dumps(redact(query, self.secrets()))}\nAuthorization: [REDACTED]")
            data = await self.client.execute(selected, params)
            self.query_one("#status", Static).update(
                f"HTTP {self.client.last_status} • GET {path}\n"
                f"Query: {json.dumps(redact(query, self.secrets()))} • Authorization: [REDACTED]")
            self.query_one("#json", Static).update(
                Syntax(json.dumps(redact(data, self.secrets()), indent=2), "json", word_wrap=True))
        except (ValueError, APIError) as exc:
            status = getattr(exc, "status", None)
            self.query_one("#status", Static).update(f"{f'HTTP {status} • ' if status else ''}{exc}")
        finally:
            self.query_one("#loading").add_class("hidden")

    def apply_filters(self):
        dates = {}
        try:
            for field in ("from", "to"):
                value = self.query_one(f"#{field}-date", Input).value
                if value:
                    dates[field] = int(datetime.strptime(value, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc).timestamp()) + (86399 if field == "to" else 0)
            REGISTRY["payments.list"].prepare(dates)
        except ValueError:
            self.query_one("#status", Static).update("Use valid YYYY-MM-DD dates; from must precede to.")
            return
        self.date_filters = dates
        self.skip = 0
        self.load_page()

    def action_refresh(self):
        if self.section in (*RESOURCES, "dashboard"):
            self.load_page()

    def action_search(self):
        if self.section in (*RESOURCES, "dashboard"):
            self.query_one("#search", Input).focus()

    def action_filters(self):
        if self.section in (*RESOURCES, "dashboard"):
            self.query_one("#filters").toggle_class("hidden")
            self.query_one("#from-date", Input).focus()

    def action_export(self):
        if self.visible_records:
            self.push_screen(ExportDialog(self.visible_records, self.secrets()))
        else:
            self.notify("No visible records to export.")

    def action_down(self):
        self.query_one("#table", DataTable).action_cursor_down()

    def action_up(self):
        self.query_one("#table", DataTable).action_cursor_up()

    def action_back(self):
        self.query_one("#table", DataTable).focus()

    def action_help(self):
        self.push_screen(Detail("RZPulse • Keyboard help", {
            "Tab / Shift+Tab": "Move focus between navigation, controls and table",
            "j / k or arrows": "Move table cursor; Enter opens record",
            "/": "Search current page only", "r": "Refresh", "f": "UTC date filters",
            "e": "Export visible page as masked JSON or CSV", "Esc": "Close dialog / leave input",
            "Ctrl+P": "Textual command palette", "q": "Quit (outside text inputs)",
            "coverage": "Payments, orders, refunds, settlements: list and fetch only",
            "scope": "Dashboard metrics summarize one payment page; currencies never combined",
        }))
