from html.parser import HTMLParser
from pathlib import Path

STATIC_DIRECTORY = Path(__file__).resolve().parents[1] / "src" / "medibot" / "static"
HTML_PATH = STATIC_DIRECTORY / "index.html"
CSS_PATH = STATIC_DIRECTORY / "medibot.css"
JAVASCRIPT_PATH = STATIC_DIRECTORY / "medibot.js"


class InterfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.controls: set[str] = set()
        self.labelled_controls: set[str] = set()
        self.landmarks: list[str] = []
        self.inline_script_or_style = False
        self.event_attributes: list[str] = []
        self.asset_urls: list[str] = []
        self.attributes_by_id: dict[str, dict[str, str | None]] = {}
        self._label_depth = 0
        self._button_id: str | None = None
        self._button_text: dict[str, list[str]] = {}

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")

        if tag == "label":
            self._label_depth += 1
            label_target = attributes.get("for")
            if label_target:
                self.labelled_controls.add(label_target)
        if tag in {"header", "main", "footer"}:
            self.landmarks.append(tag)
        if tag in {"script", "style"} and not attributes.get("src"):
            self.inline_script_or_style = True
        for name in attributes:
            if name.lower().startswith("on"):
                self.event_attributes.append(name)

        if element_id:
            self.ids.append(element_id)
            self.attributes_by_id[element_id] = attributes
        if tag in {"button", "select", "textarea"} and element_id:
            self.controls.add(element_id)
            if self._label_depth:
                self.labelled_controls.add(element_id)
        if tag == "button" and element_id:
            self._button_id = element_id
            self._button_text[element_id] = []
            if attributes.get("aria-label"):
                self.labelled_controls.add(element_id)
        if tag == "script" and attributes.get("src"):
            self.asset_urls.append(attributes["src"] or "")
        if tag == "link" and attributes.get("href"):
            self.asset_urls.append(attributes["href"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "label":
            self._label_depth -= 1
        if tag == "button" and self._button_id:
            if "".join(self._button_text[self._button_id]).strip():
                self.labelled_controls.add(self._button_id)
            self._button_id = None

    def handle_data(self, data: str) -> None:
        if self._button_id:
            self._button_text[self._button_id].append(data)


def parse_interface() -> InterfaceParser:
    parser = InterfaceParser()
    parser.feed(HTML_PATH.read_text(encoding="utf-8"))
    return parser


def test_interface_has_unique_ids_and_labels_every_control() -> None:
    parser = parse_interface()

    assert len(parser.ids) == len(set(parser.ids))
    assert parser.controls <= parser.labelled_controls


def test_interface_has_required_landmarks_and_no_inline_execution() -> None:
    parser = parse_interface()

    assert parser.landmarks == ["header", "main", "header", "footer"]
    assert parser.inline_script_or_style is False
    assert parser.event_attributes == []
    assert all(url.startswith("/assets/") for url in parser.asset_urls)


def test_sensitive_message_control_disables_browser_persistence_hints() -> None:
    parser = parse_interface()
    form = parser.attributes_by_id["message-form"]
    message = parser.attributes_by_id["message-input"]
    country = parser.attributes_by_id["country-code"]

    assert form["autocomplete"] == "off"
    assert message["autocomplete"] == "off"
    assert message["autocorrect"] == "off"
    assert message["spellcheck"] == "false"
    assert message["maxlength"] == "4000"
    assert message["aria-describedby"] == "composer-privacy character-count"
    assert country["name"] == "country_code"


def test_country_selector_does_not_assume_user_location() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")

    empty_option = '<option value="" selected>Select country</option>'
    assert empty_option in html
    assert html.index(empty_option) < html.index('<option value="PK">Pakistan</option>')


def test_javascript_avoids_persistence_and_unsafe_html_sinks() -> None:
    javascript = JAVASCRIPT_PATH.read_text(encoding="utf-8")

    for prohibited in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "localStorage",
        "sessionStorage",
        "document.cookie",
    ):
        assert prohibited not in javascript
    assert "textContent" in javascript
    assert "Promise.allSettled" in javascript


def test_emergency_route_uses_assertive_accessible_notification() -> None:
    javascript = JAVASCRIPT_PATH.read_text(encoding="utf-8")

    assert 'payload.route === "emergency"' in javascript
    assert 'article.setAttribute("role", "alert")' in javascript
    assert 'article.setAttribute("aria-live", "assertive")' in javascript


def test_styles_preserve_focus_and_reduced_motion_support() -> None:
    stylesheet = CSS_PATH.read_text(encoding="utf-8")

    assert ":focus-visible" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
    assert '.message[role="alert"]' in stylesheet
    assert "@media (max-width: 1050px)" in stylesheet
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in stylesheet
