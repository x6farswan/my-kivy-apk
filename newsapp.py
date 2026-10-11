import json
import os
import threading
import time
import webbrowser
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import certifi
import requests
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Ellipse
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.icon_definitions import md_icons
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.bottomnavigation import (MDBottomNavigation,
                                         MDBottomNavigationItem)
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

MAX_AGE = 24 * 3600
WX = (30.41, 79.32)
CHAMOLI_Q = ("Chamoli OR Gopeshwar OR Joshimath OR Badrinath OR "
             "Karnaprayag OR Pipalkoti OR Tharali OR Gairsain")
CATS = [
    ("Uttarakhand", "Uttarakhand"),
    ("India", "India news"),
    ("Sports", "sports India"),
    ("Tech", "technology"),
    ("Business", "business India"),
    ("Movies", "Bollywood"),
    ("Health", "health India"),
    ("Jobs", "sarkari naukri recruitment"),
    ("Exams", "exam result admit card"),
]


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


def ago(ts):
    m = int((time.time() - ts) // 60)
    if m < 1:
        return "just now"
    if m < 60:
        return "%d min ago" % m
    if m < 1440:
        return "%d hr ago" % (m // 60)
    return "%d d ago" % (m // 1440)


def clean(t):
    return t.replace("[", "(").replace("]", ")")


def fetch(query, max_age=MAX_AGE):
    url = ("https://news.google.com/rss/search?q=" + quote(query)
           + "&hl=en-IN&gl=IN&ceid=IN:en")
    out = []
    root = ET.fromstring(get(url).content)
    now = time.time()
    for it in root.iter("item"):
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate")).timestamp()
            if now - ts > max_age:
                continue
            title = it.findtext("title") or ""
            src = ""
            if " - " in title:
                title, src = title.rsplit(" - ", 1)
            out.append({"title": title, "src": src,
                        "link": it.findtext("link"), "ts": ts})
        except Exception:
            continue
    return out


def merge(lists):
    seen, out = set(), []
    for lst in lists:
        for x in lst:
            if x["link"] in seen:
                continue
            seen.add(x["link"])
            out.append(x)
    out.sort(key=lambda x: x["ts"], reverse=True)
    return out


class Avatar(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.letter = Label(text="U", font_size=dp(48), bold=True)
        self.add_widget(self.letter)
        self.bind(pos=self.redraw, size=self.redraw)

    def set_name(self, name):
        self.letter.text = (name[:1] or "U").upper()

    def redraw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.25, 0.32, 0.71, 1)
            Ellipse(pos=self.pos, size=self.size)


class NewsApp(MDApp):
    def build(self):
        self.title = "Chamoli News"
        self.theme_cls.primary_palette = "Indigo"
        self.prof = self.load_json("profile.json",
                                   {"name": "user1", "dark": True})
        self.saved = self.load_json("saved.json", [])
        self.theme_cls.theme_style = (
            "Dark" if self.prof.get("dark", True) else "Light")
        self.cur_cat = CATS[0][0]
        self.cat_btns = {}
        nav = MDBottomNavigation()
        self.add_tab(nav, "home", "Home", "home", self.build_home())
        self.add_tab(nav, "saved", "Saved", "star", self.build_saved())
        self.add_tab(nav, "cats", "Categories", "view-grid",
                     self.build_cats())
        self.add_tab(nav, "live", "Live", "access-point", self.build_live())
        self.add_tab(nav, "me", "Profile", "account", self.build_profile())
        return nav

    # ---------- storage ----------
    def load_json(self, name, default):
        try:
            p = os.path.join(self.user_data_dir, name)
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def save_json(self, name, obj):
        try:
            p = os.path.join(self.user_data_dir, name)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(obj, f)
        except Exception:
            pass

    def say(self, msg):
        try:
            from kivymd.toast import toast
            toast(msg)
        except Exception:
            pass

    # ---------- ui helpers ----------
    def add_tab(self, nav, name, text, icon, content):
        item = MDBottomNavigationItem(name=name, text=text, icon=icon)
        item.add_widget(content)
        nav.add_widget(item)

    def bar(self, title, refresh=None):
        acts = [["theme-light-dark", lambda x: self.toggle_theme()]]
        if refresh:
            acts.append(["refresh", lambda x: refresh()])
        return MDTopAppBar(title=title, right_action_items=acts)

    def make_list(self):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True,
                          spacing=dp(10), padding=dp(12))
        sv = MDScrollView()
        sv.add_widget(box)
        return box, sv

    def toggle_theme(self):
        dark = self.theme_cls.theme_style == "Dark"
        self.theme_cls.theme_style = "Light" if dark else "Dark"
        self.prof["dark"] = not dark
        self.save_json("profile.json", self.prof)
        self.paint_cats()

    # ---------- tabs ----------
    def build_home(self):
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.bar("Chamoli News", self.load_home))
        self.wx = MDLabel(text="Chamoli", font_style="Subtitle1",
                          adaptive_height=True, padding=(dp(16), dp(10)))
        root.add_widget(self.wx)
        self.home_box, sv = self.make_list()
        root.add_widget(sv)
        return root

    def build_saved(self):
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.bar("Saved"))
        self.saved_box, sv = self.make_list()
        root.add_widget(sv)
        return root

    def build_cats(self):
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.bar("Categories", self.load_cat))
        grid = GridLayout(cols=3, size_hint_y=None, height=dp(164),
                          spacing=dp(8), padding=dp(12))
        for name, q in CATS:
            b = MDRaisedButton(text=name, size_hint=(1, None),
                               height=dp(40),
                               on_release=lambda x, n=name: self.pick_cat(n))
            self.cat_btns[name] = b
            grid.add_widget(b)
        root.add_widget(grid)
        self.cat_box, sv = self.make_list()
        root.add_widget(sv)
        return root

    def build_live(self):
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.bar("Live", self.load_live))
        self.live_info = MDLabel(
            text="Fetching latest...", font_style="Caption",
            theme_text_color="Secondary", adaptive_height=True,
            padding=(dp(16), dp(8)))
        root.add_widget(self.live_info)
        self.live_box, sv = self.make_list()
        root.add_widget(sv)
        return root

    def build_profile(self):
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.bar("Profile"))
        body = MDBoxLayout(orientation="vertical", padding=dp(20),
                           spacing=dp(14))
        name = self.prof.get("name", "user1")
        self.avatar = Avatar(size_hint=(None, None),
                             size=(dp(120), dp(120)),
                             pos_hint={"center_x": .5})
        self.avatar.set_name(name)
        body.add_widget(self.avatar)
        self.name_lbl = MDLabel(text=name, halign="center",
                                font_style="H5", adaptive_height=True)
        body.add_widget(self.name_lbl)
        self.name_in = MDTextField(hint_text="Your name", text=name,
                                   mode="rectangle")
        body.add_widget(self.name_in)
        body.add_widget(MDRaisedButton(text="Save name",
                                       pos_hint={"center_x": .5},
                                       on_release=self.save_name))
        body.add_widget(Widget())
        heart = md_icons.get("heart", "")
        body.add_widget(MDLabel(
            text=("Made in Gopeshwar with "
                  "[color=ff4d6d][font=Icons]%s[/font][/color]" % heart),
            markup=True, halign="center", font_style="Caption",
            theme_text_color="Secondary", adaptive_height=True))
        body.add_widget(MDLabel(
            text="by Rohit", halign="center", font_style="Caption",
            theme_text_color="Secondary", adaptive_height=True))
        body.add_widget(MDFlatButton(
            text="@x6_farswan", pos_hint={"center_x": .5},
            on_release=lambda x: webbrowser.open(
                "https://instagram.com/x6_farswan")))
        root.add_widget(body)
        return root

    def save_name(self, *a):
        n = self.name_in.text.strip() or "user1"
        self.prof["name"] = n
        self.name_lbl.text = n
        self.avatar.set_name(n)
        self.save_json("profile.json", self.prof)
        self.say("Saved")

    # ---------- cards ----------
    def card(self, it):
        is_saved = any(s["link"] == it["link"] for s in self.saved)
        card = MDCard(orientation="vertical", size_hint_y=None,
                      height=dp(100), radius=[dp(18)])
        inner = MDBoxLayout(orientation="vertical", adaptive_height=True,
                            padding=dp(14), spacing=dp(4))
        inner.add_widget(MDLabel(text=clean(it["title"]),
                                 font_style="Subtitle1",
                                 adaptive_height=True))
        row = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        row.add_widget(MDLabel(
            text="%s  •  %s" % (it["src"], ago(it["ts"])),
            font_style="Caption", theme_text_color="Secondary",
            adaptive_height=True, pos_hint={"center_y": .5}))
        star = MDIconButton(icon="star" if is_saved else "star-outline")
        self.paint_star(star, is_saved)
        star.bind(on_release=lambda b, i=it: self.toggle_save(i, b))
        row.add_widget(star)
        inner.add_widget(row)
        inner.bind(height=lambda i, h, c=card: setattr(c, "height", h))
        card.add_widget(inner)
        card.bind(on_release=lambda x, u=it["link"]: webbrowser.open(u))
        return card

    def paint_star(self, btn, on):
        btn.theme_icon_color = "Custom"
        btn.icon_color = (1, 0.78, 0.1, 1) if on else (0.6, 0.6, 0.65, 1)

    def toggle_save(self, it, btn):
        if any(s["link"] == it["link"] for s in self.saved):
            self.saved = [s for s in self.saved if s["link"] != it["link"]]
            on = False
        else:
            self.saved.insert(0, dict(it))
            on = True
        btn.icon = "star" if on else "star-outline"
        self.paint_star(btn, on)
        self.save_json("saved.json", self.saved)
        self.render_saved()

    def render(self, box, items, empty):
        box.clear_widgets()
        if not items:
            box.add_widget(MDLabel(text=empty, halign="center",
                                   adaptive_height=True,
                                   padding=(dp(16), dp(30))))
            return
        for it in items[:30]:
            box.add_widget(self.card(it))

    def render_saved(self):
        self.render(self.saved_box, self.saved,
                    "No saved news yet. Tap the star on any news.")

    # ---------- loading ----------
    def bg(self, fn, cb):
        def w():
            try:
                r = fn()
            except Exception:
                r = None
            Clock.schedule_once(lambda dt: cb(r))
        threading.Thread(target=w, daemon=True).start()

    def load_home(self, *a):
        self.bg(lambda: fetch(CHAMOLI_Q + " when:1d"), self.home_done)
        self.bg(self.get_weather, self.wx_done)

    def get_weather(self):
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s"
               "&longitude=%s&current=temperature_2m,weather_code" % WX)
        w = get(url).json()["current"]
        return "Chamoli  •  %d°C  •  %s" % (
            round(w["temperature_2m"]), wx_text(w["weather_code"]))

    def wx_done(self, r):
        if r:
            self.wx.text = r

    def home_done(self, r):
        if r is None:
            self.render(self.home_box, [], "No connection. Tap refresh.")
            return
        r.sort(key=lambda x: x["ts"], reverse=True)
        self.render(self.home_box, r,
                    "No Chamoli news in the last 24 hours.")

    def pick_cat(self, name):
        self.cur_cat = name
        self.paint_cats()
        self.load_cat()

    def paint_cats(self):
        for n, b in self.cat_btns.items():
            if n == self.cur_cat:
                b.md_bg_color = self.theme_cls.primary_color
            else:
                b.md_bg_color = (0.3, 0.3, 0.36, 1)

    def load_cat(self, *a):
        q = dict(CATS)[self.cur_cat] + " when:1d"
        self.bg(lambda: fetch(q), self.cat_done)

    def cat_done(self, r):
        if r is None:
            self.render(self.cat_box, [], "No connection. Tap refresh.")
            return
        r.sort(key=lambda x: x["ts"], reverse=True)
        self.render(self.cat_box, r, "No fresh news in this category.")

    def load_live(self, *a):
        def job():
            parts, ok = [], False
            for q in ("India news when:1h", "Uttarakhand when:6h",
                      CHAMOLI_Q + " when:1d"):
                try:
                    parts.append(fetch(q))
                    ok = True
                except Exception:
                    pass
            if not ok:
                raise RuntimeError("offline")
            return merge(parts)
        self.bg(job, self.live_done)

    def live_done(self, r):
        if r is None:
            self.live_info.text = "No connection."
            return
        self.live_info.text = "Updated " + time.strftime("%H:%M")
        self.render(self.live_box, r, "No fresh news right now.")

    def on_start(self):
        self.paint_cats()
        self.render_saved()
        self.load_home()
        self.load_cat()
        self.load_live()
        Clock.schedule_interval(self.load_live, 90)


def start():
    NewsApp().run()
