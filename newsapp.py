import threading
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import certifi
import requests
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar

DEFAULT = ("Gopeshwar", 30.41, 79.32)


def get(url):
    return requests.get(url, timeout=15, verify=certifi.where())


def wx_text(code):
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Cloudy"
    if code in (45, 48):
        return "Fog"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "Rain"
    if 71 <= code <= 77:
        return "Snow"
    if code >= 95:
        return "Thunderstorm"
    return "Weather"


def ago(dt):
    m = int((datetime.now(timezone.utc) - dt).total_seconds() // 60)
    if m < 1:
        return "just now"
    if m < 60:
        return f"{m} min ago"
    return f"{m // 60} hr ago"


def rss(query):
    url = ("https://news.google.com/rss/search?q=" + quote(query)
           + "&hl=en-IN&gl=IN&ceid=IN:en")
    out = []
    root = ET.fromstring(get(url).content)
    for it in root.iter("item"):
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate"))
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            if age > 86400:
                continue
            title = it.findtext("title") or ""
            src = ""
            if " - " in title:
                title, src = title.rsplit(" - ", 1)
            out.append((dt, title, src, it.findtext("link")))
        except Exception:
            continue
    return out


class NewsApp(MDApp):
    def build(self):
        self.title = "Daily News"
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.theme_style = "Dark"
        self.items = []
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(MDTopAppBar(
            title="Daily News",
            right_action_items=[
                ["theme-light-dark", lambda x: self.toggle_theme()],
                ["refresh", lambda x: self.refresh()],
            ],
        ))
        self.weather = MDLabel(text="Loading...", adaptive_height=True,
                               padding=(dp(16), dp(10)))
        root.add_widget(self.weather)
        sv = MDScrollView()
        self.feed = MDBoxLayout(orientation="vertical", adaptive_height=True,
                                spacing=dp(10), padding=dp(12))
        sv.add_widget(self.feed)
        root.add_widget(sv)
        return root

    def on_start(self):
        self.refresh()

    def toggle_theme(self):
        self.theme_cls.theme_style = (
            "Light" if self.theme_cls.theme_style == "Dark" else "Dark")
        self.show(self.items)

    def refresh(self):
        self.weather.text = "Loading..."
        threading.Thread(target=self.load, daemon=True).start()

    def load(self):
        city, lat, lon = DEFAULT
        try:
            j = get("https://ipapi.co/json/").json()
            city, lat, lon = j["city"], j["latitude"], j["longitude"]
        except Exception:
            pass
        wtxt = city
        try:
            w = get("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
                    "&current=temperature_2m,weather_code" % (lat, lon)).json()["current"]
            wtxt = "%s  •  %d°C  •  %s" % (
                city, round(w["temperature_2m"]), wx_text(w["weather_code"]))
        except Exception:
            pass
        items = []
        try:
            items = rss(city + " when:1d")
            if len(items) < 5:
                items += rss("India news when:1d")
        except Exception:
            pass
        items.sort(key=lambda x: x[0], reverse=True)
        Clock.schedule_once(lambda dt: self.done(wtxt, items))

    def done(self, wtxt, items):
        self.items = items
        self.weather.text = wtxt
        self.show(items)

    def show(self, items):
        self.feed.clear_widgets()
        if not items:
            self.feed.add_widget(MDLabel(
                text="No fresh news. Check internet and tap refresh.",
                adaptive_height=True))
            return
        for dt, title, src, link in items[:40]:
            card = MDCard(orientation="vertical", padding=dp(14),
                          spacing=dp(6), size_hint_y=None,
                          adaptive_height=True, radius=[dp(16)],
                          elevation=1)
            card.add_widget(MDLabel(
                text=title.replace("[", "(").replace("]", ")"),
                font_style="Subtitle1", adaptive_height=True))
            card.add_widget(MDLabel(
                text="%s  •  %s" % (src, ago(dt)), font_style="Caption",
                theme_text_color="Secondary", adaptive_height=True))
            card.bind(on_release=lambda x, u=link: webbrowser.open(u))
            self.feed.add_widget(card)


def start():
    NewsApp().run()
