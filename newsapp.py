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
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

BASE = os.path.dirname(os.path.abspath(__file__))
MAX_AGE = 24 * 3600
WX = (30.41, 79.32)


def reg(name, fn):
    p = os.path.join(BASE, "fonts", fn)
    try:
        if os.path.exists(p) and os.path.getsize(p) > 50000:
            LabelBase.register(name=name, fn_regular=p)
            return True
    except Exception:
        pass
    return False


SERIF = "Serif" if reg("Serif", "serif.ttf") else "Roboto"
HINDI = "Hindi" if reg("Hindi", "hindi.ttf") else None
try:
    import kivymd
    from kivymd.icon_definitions import md_icons
    LabelBase.register(
        name="MDI",
        fn_regular=os.path.join(kivymd.fonts_path,
                                "materialdesignicons-webfont.ttf"))
except Exception:
    md_icons = {}


def ic(n):
    return md_icons.get(n, "•")


DARK = dict(bg=(.043, .043, .059, 1), card=(.09, .09, .115, 1),
            gold=(.83, .69, .22, 1), text=(.96, .94, .90, 1),
            sub=(.62, .60, .55, 1), line=(.17, .17, .2, 1),
            onGold=(.07, .06, .03, 1))
LIGHT = dict(bg=(.97, .95, .91, 1), card=(1, 1, 1, 1),
             gold=(.69, .50, .10, 1), text=(.10, .09, .08, 1),
             sub=(.45, .42, .38, 1), line=(.88, .85, .80, 1),
             onGold=(1, 1, 1, 1))
P = dict(DARK)

CH_Q = {
    "en": ("Chamoli OR Gopeshwar OR Joshimath OR Badrinath OR "
           "Karnaprayag OR Pipalkoti OR Tharali OR Gairsain"),
    "hi": ("चमोली OR गोपेश्वर OR जोशीमठ OR बदरीनाथ OR "
           "कर्णप्रयाग OR पीपलकोटी OR थराली OR गैरसैंण"),
}
CATS = ["Uttarakhand", "India", "Sports", "Tech", "Business", "Movies",
        "Health", "Jobs", "Exams"]
CAT_Q = {
    "en": {"Uttarakhand": "Uttarakhand", "India": "India news",
           "Sports": "sports India", "Tech": "technology",
           "Business": "business India", "Movies": "Bollywood",
           "Health": "health India", "Jobs": "sarkari naukri recruitment",
           "Exams": "exam result admit card"},
    "hi": {"Uttarakhand": "उत्तराखंड", "India": "भारत समाचार",
           "Sports": "खेल समाचार", "Tech": "टेक्नोलॉजी",
           "Business": "व्यापार", "Movies": "बॉलीवुड",
           "Health": "स्वास्थ्य", "Jobs": "सरकारी नौकरी",
           "Exams": "परीक्षा परिणाम"},
}
LOC = {"en": "hl=en-IN&gl=IN&ceid=IN:en", "hi": "hl=hi&gl=IN&ceid=IN:hi"}
TABS = [("home", "home", "Home"), ("explore", "compass", "Explore"),
        ("live", "access-point", "Live"), ("saved", "star", "Saved"),
        ("me", "account", "Profile")]
WX_ICON = {"Clear": "weather-sunny", "Cloudy": "weather-partly-cloudy",
           "Fog": "weather-fog", "Rain": "weather-rainy",
           "Snow": "weather-snowy", "Thunderstorm": "weather-lightning"}


# ---------------- helpers ----------------
def get(url):
    return requests.get(url, timeout=15, verify=certifi.where())


def has_hi(t):
    return any("\u0900" <= c <= "\u097f" for c in t)


def fnt(t, base="Roboto"):
    return HINDI if (HINDI and has_hi(t)) else base


def hexc(name):
    return "%02x%02x%02x" % tuple(int(c * 255) for c in P[name][:3])


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
    return "Cloudy"


def ago(ts):
    m = int((time.time() - ts) // 60)
    if m < 1:
        return "just now"
    if m < 60:
        return "%d min ago" % m
    if m < 1440:
        return "%d hr ago" % (m // 60)
    return "%d d ago" % (m // 1440)


def fresh(lst):
    now = time.time()
    return [x for x in lst if now - x["ts"] < MAX_AGE]


def fetch(query, lang):
    url = ("https://news.google.com/rss/search?q=" + quote(query)
           + "&" + LOC[lang])
    out = []
    root = ET.fromstring(get(url).content)
    now = time.time()
    for it in root.iter("item"):
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate")).timestamp()
            if now - ts > MAX_AGE:
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


def gather(qs):
    res = [None] * len(qs)

    def one(i, q, lang):
        try:
            res[i] = fetch(q, lang)
        except Exception:
            res[i] = None
    ths = [threading.Thread(target=one, args=(i, q, lg))
           for i, (q, lg) in enumerate(qs)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    ok = [r for r in res if r is not None]
    if not ok:
        raise RuntimeError("offline")
    return merge(ok)


def open_url(url):
    try:
        from jnius import autoclass
        PA = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        it = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        it.setPackage("com.android.chrome")
        try:
            PA.mActivity.startActivity(it)
        except Exception:
            PA.mActivity.startActivity(
                Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass


# ---------------- widgets ----------------
class Txt(Label):
    def __init__(self, text="", fs=14, color="text", bold=False,
                 serif=False, halign="left", wrap=True, fill=False, **kw):
        base = SERIF if serif else "Roboto"
        col = P[color] if isinstance(color, str) else color
        super().__init__(text=text, font_size=sp(fs), bold=bold,
                         halign=halign, valign="middle", color=col,
                         font_name=fnt(text, base), **kw)
        if fill:
            self.bind(size=lambda i, s: setattr(i, "text_size", s))
        else:
            self.size_hint_y = None
            if wrap:
                self.bind(width=lambda i, w: setattr(i, "text_size",
                                                     (w, None)))
            self.bind(texture_size=lambda i, ts: setattr(
                i, "height", ts[1] + dp(2)))


class Panel(BoxLayout):
    def __init__(self, bg="card", radius=18, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*P[bg])
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[dp(radius)])
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class Card(ButtonBehavior, Panel):
    def on_press(self):
        Animation.cancel_all(self, "opacity")
        Animation(opacity=.86, d=.05).start(self)
        Clock.schedule_once(self._rest, .22)

    def _rest(self, dt):
        Animation(opacity=1, d=.18).start(self)


class IconBtn(ButtonBehavior, Label):
    def __init__(self, icon, fs=22, color="sub", box=38, **kw):
        super().__init__(text=ic(icon), font_name="MDI", font_size=sp(fs),
                         color=P[color], size_hint=(None, None),
                         size=(dp(box), dp(box)), **kw)
        self.base = fs

    def set(self, icon, color):
        self.text = ic(icon)
        self.color = P[color]

    def pop(self):
        a = (Animation(font_size=sp(self.base + 7), d=.08)
             + Animation(font_size=sp(self.base), d=.14))
        a.start(self)


class Pill(ButtonBehavior, Label):
    def __init__(self, text, **kw):
        super().__init__(text=text, font_size=sp(13), size_hint=(None, 1),
                         **kw)
        with self.canvas.before:
            self._c = Color(*P["card"])
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[dp(18)])
        self.bind(pos=self._u, size=self._u,
                  texture_size=lambda i, ts: setattr(i, "width",
                                                     ts[0] + dp(34)))
        self.set_on(False)

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size

    def set_on(self, on):
        self._c.rgba = P["gold"] if on else P["card"]
        self.color = P["onGold"] if on else P["sub"]
        self.bold = on


class NavItem(ButtonBehavior, BoxLayout):
    def __init__(self, icon, label, **kw):
        super().__init__(orientation="vertical",
                         padding=[0, dp(8), 0, dp(6)], spacing=dp(2), **kw)
        self.i = Label(text=ic(icon), font_name="MDI", font_size=sp(24),
                       color=P["sub"])
        self.t = Label(text=label, font_size=sp(10), color=P["sub"],
                       size_hint_y=None, height=dp(14))
        self.add_widget(self.i)
        self.add_widget(self.t)

    def active(self, on):
        c = P["gold"] if on else P["sub"]
        Animation(color=c, d=.18).start(self.i)
        Animation(color=c, d=.18).start(self.t)


class Field(TextInput):
    def __init__(self, **kw):
        super().__init__(multiline=False, background_normal="",
                         background_active="", background_color=P["card"],
                         foreground_color=P["text"], cursor_color=P["gold"],
                         hint_text_color=P["sub"],
                         padding=[dp(16), dp(14)], font_size=sp(16),
                         size_hint_y=None, height=dp(50), **kw)


class Avatar(Label):
    pass


class Pic(BoxLayout):
    def __init__(self, **kw):
        super().__init__(size_hint=(None, None),
                         size=(dp(116), dp(116)), **kw)
        self.tex = None
        self.letter = Label(text="U", font_size=sp(46), bold=True,
                            font_name=SERIF, color=P["onGold"])
        self.add_widget(self.letter)
        self.bind(pos=self.redraw, size=self.redraw)

    def set_photo(self, path, name):
        self.tex = None
        if path and os.path.exists(path):
            try:
                t = CoreImage(path).texture
                s = min(t.width, t.height)
                self.tex = t.get_region((t.width - s) // 2,
                                        (t.height - s) // 2, s, s)
            except Exception:
                self.tex = None
        txt = "" if self.tex else ((name or "U")[:1].upper())
        self.letter.text = txt
        self.letter.font_name = fnt(txt, SERIF)
        self.redraw()

    def redraw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*P["gold"])
            Ellipse(pos=self.pos, size=self.size)
            if self.tex:
                Color(1, 1, 1, 1)
                Ellipse(pos=(self.x + dp(3), self.y + dp(3)),
                        size=(self.width - dp(6), self.height - dp(6)),
                        texture=self.tex)


class Toast(Label):
    def __init__(self, text, **kw):
        super().__init__(text=text, font_size=sp(14), color=P["onGold"],
                         size_hint=(None, None), **kw)
        with self.canvas.before:
            Color(*P["gold"])
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[dp(20)])
        self.bind(pos=self._u, size=self._u, texture_size=self._fit)

    def _fit(self, i, ts):
        self.size = (ts[0] + dp(36), ts[1] + dp(18))
        self.center_x = Window.width / 2

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


# ---------------- app ----------------
class SandeshApp(App):
    def build(self):
        self.title = "Sandesh"
        Window.softinput_mode = "below_target"
        self.prof = self.load_json("profile.json", {})
        if not isinstance(self.prof, dict):
            self.prof = {}
        self.prof.setdefault("name", "user1")
        self.prof.setdefault("dark", True)
        self.prof.setdefault("lang", "both")
        self.prof.setdefault("photo", "")
        self.saved = self.load_json("saved.json", [])
        self.cache = self.load_json("cache.json", {})
        if not isinstance(self.cache, dict):
            self.cache = {}
        self.wx_vals = tuple(self.cache.get("wx", ["--°", "Loading", ""]))
        self.cat = CATS[0]
        self.cat_items = []
        self.cat_loaded = False
        self.last = 0
        self.cur = "home"
        self.apply_palette()
        Window.bind(on_keyboard=self.on_key)
        return self.make_root()

    def on_start(self):
        self.load_home()
        self.load_live()
        Clock.schedule_interval(lambda dt: self.load_live(), 90)

    def on_pause(self):
        return True

    def on_resume(self):
        if time.time() - self.last > 300:
            self.load_home()
            self.load_live()

    def on_key(self, win, key, *a):
        if key == 27 and self.cur != "home":
            self.goto("home")
            return True
        return False

    # ----- storage -----
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

    def save_prof(self):
        self.save_json("profile.json", self.prof)

    # ----- theme -----
    def apply_palette(self):
        P.clear()
        P.update(DARK if self.prof.get("dark", True) else LIGHT)
        Window.clearcolor = P["bg"]

    def toggle_theme(self):
        self.prof["dark"] = not self.prof.get("dark", True)
        self.save_prof()
        self.apply_palette()
        Window.remove_widget(self.root)
        self.root = self.make_root()
        Window.add_widget(self.root)

    def toast(self, msg):
        t = Toast(msg)
        t.opacity = 0
        t.y = dp(90)
        Window.add_widget(t)
        a = (Animation(opacity=1, d=.15) + Animation(opacity=1, d=1.2)
             + Animation(opacity=0, d=.3))
        a.bind(on_complete=lambda *x: Window.remove_widget(t))
        a.start(t)

    # ----- structure -----
    def make_root(self):
        root = BoxLayout(orientation="vertical")
        self.sm = ScreenManager(transition=FadeTransition(duration=.16))
        for s in (self.build_home(), self.build_explore(),
                  self.build_live(), self.build_saved(),
                  self.build_profile()):
            self.sm.add_widget(s)
        root.add_widget(self.sm)
        root.add_widget(self.make_nav())
        self.sm.current = self.cur
        self.nav[self.cur].active(True)
        self.render_home()
        self.render_cat()
        self.render_live()
        self.render_saved()
        self.paint_pills()
        return root

    def make_nav(self):
        bar = BoxLayout(size_hint_y=None, height=dp(64))
        with bar.canvas.before:
            Color(*P["card"])
            rect = Rectangle(pos=bar.pos, size=bar.size)
            Color(*P["line"])
            ln = Rectangle(pos=(bar.x, bar.top - 1), size=(bar.width, 1))

        def upd(*a):
            rect.pos = bar.pos
            rect.size = bar.size
            ln.pos = (bar.x, bar.top - 1)
            ln.size = (bar.width, 1)
        bar.bind(pos=upd, size=upd)
        self.nav = {}
        for key, icon, label in TABS:
            it = NavItem(icon, label)
            it.bind(on_release=lambda x, k=key: self.goto(k))
            self.nav[key] = it
            bar.add_widget(it)
        return bar

    def goto(self, key):
        self.cur = key
        for k, it in self.nav.items():
            it.active(k == key)
        self.sm.current = key
        if key == "explore" and not self.cat_loaded:
            self.cat_loaded = True
            self.load_cat()

    def header(self, title, actions=(), live=False):
        h = BoxLayout(size_hint_y=None, height=dp(64),
                      padding=[dp(20), 0, dp(10), 0])
        if live:
            dot = Label(text=ic("circle"), font_name="MDI",
                        font_size=sp(12), color=(.92, .25, .25, 1),
                        size_hint=(None, None), size=(dp(22), dp(22)),
                        pos_hint={"center_y": .5})
            a = Animation(opacity=.25, d=.9) + Animation(opacity=1, d=.9)
            a.repeat = True
            a.start(dot)
            h.add_widget(dot)
        h.add_widget(Txt(title, fs=26, color="gold", serif=True,
                         wrap=False, fill=True))
        for icon, cb in actions:
            b = IconBtn(icon, fs=22, color="text", box=44,
                        pos_hint={"center_y": .5})
            b.bind(on_release=lambda x, f=cb: f())
            h.add_widget(b)
        return h

    def scroll(self):
        sv = ScrollView(bar_width=0, do_scroll_x=False,
                        scroll_distance=dp(6), scroll_timeout=50)
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        spacing=dp(12),
                        padding=[dp(16), dp(4), dp(16), dp(18)])
        box.bind(minimum_height=box.setter("height"))
        sv.add_widget(box)
        return sv, box

    def langs(self):
        if not HINDI:
            return ["en"]
        return {"en": ["en"], "hi": ["hi"]}.get(
            self.prof.get("lang", "both"), ["en", "hi"])

    # ----- screens -----
    def build_home(self):
        s = Screen(name="home")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Sandesh", [
            ("refresh", self.load_home),
            ("theme-light-dark", self.toggle_theme)]))
        sv, self.home_box = self.scroll()
        col.add_widget(sv)
        s.add_widget(col)
        return s

    def build_explore(self):
        s = Screen(name="explore")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Explore", [
            ("refresh", self.load_cat),
            ("theme-light-dark", self.toggle_theme)]))
        psv = ScrollView(size_hint_y=None, height=dp(52), bar_width=0,
                         do_scroll_y=False)
        row = BoxLayout(size_hint_x=None, spacing=dp(8),
                        padding=[dp(16), dp(6)])
        row.bind(minimum_width=row.setter("width"))
        self.pills = {}
        for n in CATS:
            p = Pill(n)
            p.bind(on_release=lambda x, nm=n: self.pick_cat(nm))
            self.pills[n] = p
            row.add_widget(p)
        psv.add_widget(row)
        col.add_widget(psv)
        sv, self.cat_box = self.scroll()
        col.add_widget(sv)
        s.add_widget(col)
        return s

    def build_live(self):
        s = Screen(name="live")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Live", [
            ("refresh", self.load_live),
            ("theme-light-dark", self.toggle_theme)], live=True))
        sv, self.live_box = self.scroll()
        self.live_info = Txt("Fetching latest...", fs=12, color="sub")
        col.add_widget(sv)
        s.add_widget(col)
        return s

    def build_saved(self):
        s = Screen(name="saved")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Saved", [
            ("theme-light-dark", self.toggle_theme)]))
        sv, self.saved_box = self.scroll()
        col.add_widget(sv)
        s.add_widget(col)
        return s

    def build_profile(self):
        s = Screen(name="me")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Profile", [
            ("theme-light-dark", self.toggle_theme)]))
        sv, box = self.scroll()
        name = self.prof["name"]
        self.avatar = Pic(pos_hint={"center_x": .5})
        self.avatar.set_photo(self.prof.get("photo"), name)
        box.add_widget(self.avatar)
        self.name_lbl = Txt(name, fs=24, serif=True, halign="center")
        box.add_widget(self.name_lbl)
        cp = Card(size_hint=(None, None), size=(dp(170), dp(40)),
                  pos_hint={"center_x": .5}, radius=20)
        cp.add_widget(Txt("Change photo", fs=14, color="gold", bold=True,
                          fill=True, halign="center"))
        cp.bind(on_release=lambda x: self.pick_photo())
        box.add_widget(cp)
        self.name_in = Field(text=name, hint_text="Your name")
        box.add_widget(self.name_in)
        box.add_widget(self.gold_btn("Save name", self.save_name))
        box.add_widget(self.section("Preferences"))
        box.add_widget(self.row(
            "Appearance", "Dark" if self.prof["dark"] else "Light",
            lambda v: self.toggle_theme()))
        box.add_widget(self.row("Language", self.lang_label(),
                                self.cycle_lang))
        box.add_widget(self.row("Version", "Sandesh 3.0", lambda v: None))
        col.add_widget(sv)
        cred = BoxLayout(orientation="vertical", size_hint_y=None,
                         height=dp(70), padding=[0, dp(4)])
        cred.add_widget(Txt(
            "Made in Gopeshwar with [color=ff4d6d][font=MDI]%s[/font]"
            "[/color]" % ic("heart"), fs=12, color="sub",
            halign="center", markup=True))
        link = ButtonBehaviorLabel(
            text="by Rohit  ·  [color=%s]@x6_farswan[/color]" % hexc("gold"),
            markup=True, font_size=sp(12), color=P["sub"],
            size_hint_y=None, height=dp(28))
        link.bind(on_release=lambda x: open_url(
            "https://instagram.com/x6_farswan"))
        cred.add_widget(link)
        col.add_widget(cred)
        s.add_widget(col)
        return s

    # ----- small builders -----
    def section(self, t):
        return Txt(t.upper(), fs=12, color="gold", bold=True)

    def gold_btn(self, text, cb):
        b = Card(bg="gold", size_hint_y=None, height=dp(48), radius=24)
        b.add_widget(Txt(text, fs=15, color="onGold", bold=True,
                         fill=True, halign="center"))
        b.bind(on_release=lambda x: cb())
        return b

    def row(self, title, value, cb):
        r = Card(orientation="horizontal", size_hint_y=None,
                 height=dp(54), padding=[dp(18), 0, dp(18), 0], radius=14)
        r.add_widget(Txt(title, fs=15, fill=True))
        v = Txt(value, fs=15, color="gold", fill=True, halign="right")
        r.add_widget(v)
        r.bind(on_release=lambda x: cb(v))
        return r

    def note(self, msg, icon="newspaper"):
        b = BoxLayout(orientation="vertical", size_hint_y=None,
                      height=dp(190), spacing=dp(10),
                      padding=[dp(20), dp(30), dp(20), 0])
        b.add_widget(IconBtn(icon, fs=44, color="gold", box=64,
                             pos_hint={"center_x": .5}))
        b.add_widget(Txt(msg, fs=14, color="sub", halign="center"))
        return b

    def lang_label(self):
        if not HINDI:
            return "English only"
        return {"en": "English", "hi": "हिंदी"}.get(
            self.prof.get("lang", "both"), "English + हिंदी")

    def cycle_lang(self, v):
        order = ["both", "en", "hi"]
        cur = self.prof.get("lang", "both")
        nxt = order[(order.index(cur) + 1) % 3] if cur in order else "both"
        self.prof["lang"] = nxt
        self.save_prof()
        v.text = self.lang_label()
        v.font_name = fnt(v.text)
        self.load_home()
        self.load_live()
        self.cat_loaded = False
        if self.cur == "explore":
            self.goto("explore")

    def save_name(self):
        n = self.name_in.text.strip() or "user1"
        self.prof["name"] = n
        self.save_prof()
        self.name_lbl.text = n
        self.name_lbl.font_name = fnt(n, SERIF)
        self.avatar.set_photo(self.prof.get("photo"), n)
        self.render_home()
        self.toast("Saved")

    # ----- news cards -----
    def is_saved(self, it):
        return any(s["link"] == it["link"] for s in self.saved)

    def news_card(self, it, idx=0):
        on = self.is_saved(it)
        c = Card(orientation="vertical", size_hint_y=None,
                 padding=[dp(18), dp(16), dp(10), dp(6)], spacing=dp(4))
        c.bind(minimum_height=c.setter("height"))
        c.add_widget(Txt(it["title"], fs=17, serif=True))
        row = BoxLayout(size_hint_y=None, height=dp(40))
        row.add_widget(Txt(it["src"], fs=12, color="gold", bold=True,
                           fill=True, shorten=True))
        row.add_widget(Txt(ago(it["ts"]), fs=12, color="sub", fill=True,
                           halign="right", size_hint_x=None,
                           width=dp(76)))
        sh = IconBtn("share-variant", fs=20, pos_hint={"center_y": .5})
        sh.bind(on_release=lambda b, i=it: self.share(i))
        star = IconBtn("star" if on else "star-outline", fs=22,
                       color="gold" if on else "sub",
                       pos_hint={"center_y": .5})
        star.bind(on_release=lambda b, i=it: self.toggle_save(i, b))
        row.add_widget(sh)
        row.add_widget(star)
        c.add_widget(row)
        c.bind(on_release=lambda x, u=it["link"]: open_url(u))
        if idx < 8:
            c.opacity = 0
            Clock.schedule_once(
                lambda dt, w=c: Animation(opacity=1, d=.3).start(w),
                idx * .05)
        return c

    def cards_into(self, box, items, empty):
        if not items:
            box.add_widget(self.note(empty))
            return
        for i, it in enumerate(items[:25]):
            box.add_widget(self.news_card(it, i))

    def toggle_save(self, it, btn):
        if self.is_saved(it):
            self.saved = [s for s in self.saved if s["link"] != it["link"]]
            on = False
            self.toast("Removed from Saved")
        else:
            self.saved.insert(0, dict(it))
            on = True
            self.toast("Saved")
        btn.set("star" if on else "star-outline", "gold" if on else "sub")
        btn.pop()
        self.save_json("saved.json", self.saved)
        self.render_saved()

    def share(self, it):
        try:
            from jnius import autoclass
            PA = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            String = autoclass("java.lang.String")
            i = Intent()
            i.setAction(Intent.ACTION_SEND)
            i.putExtra(Intent.EXTRA_TEXT,
                       String("%s\n%s" % (it["title"], it["link"])))
            i.setType("text/plain")
            PA.mActivity.startActivity(
                Intent.createChooser(i, String("Share news")))
        except Exception:
            self.toast("Share works on the phone only")

    # ----- renderers -----
    def hero(self):
        c = Panel(orientation="horizontal", size_hint_y=None,
                  height=dp(112), padding=[dp(20), dp(12), dp(12), dp(12)],
                  spacing=dp(8))
        self.wx_temp = Txt(self.wx_vals[0], fs=46, color="gold",
                           serif=True, wrap=False, fill=True,
                           size_hint_x=None, width=dp(112))
        c.add_widget(self.wx_temp)
        info = BoxLayout(orientation="vertical")
        info.add_widget(Txt("Chamoli", fs=18, bold=True, fill=True))
        self.wx_cond = Txt(self.wx_vals[1], fs=14, color="gold", fill=True)
        info.add_widget(self.wx_cond)
        self.wx_more = Txt(self.wx_vals[2], fs=12, color="sub", fill=True)
        info.add_widget(self.wx_more)
        c.add_widget(info)
        self.wx_icon = IconBtn(WX_ICON.get(self.wx_vals[1],
                                           "weather-partly-cloudy"),
                               fs=40, color="gold", box=56,
                               pos_hint={"center_y": .5})
        c.add_widget(self.wx_icon)
        return c

    def render_home(self, err=False):
        b = self.home_box
        b.clear_widgets()
        h = time.localtime().tm_hour
        g = ("Good morning" if h < 12 else
             "Good afternoon" if h < 17 else "Good evening")
        b.add_widget(Txt("%s, %s" % (g, self.prof["name"]), fs=22,
                         serif=True))
        b.add_widget(Txt(time.strftime("%A, %d %B"), fs=12, color="sub"))
        b.add_widget(self.hero())
        b.add_widget(self.section("Latest from Chamoli"))
        items = fresh(self.cache.get("home", []))
        msg = ("No connection. Tap refresh." if err and not items else
               "No Chamoli news in the last 24 hours.")
        self.cards_into(b, items, msg)

    def render_cat(self, msg="Pick a category above."):
        self.cat_box.clear_widgets()
        self.cards_into(self.cat_box, self.cat_items, msg)

    def render_live(self):
        b = self.live_box
        b.clear_widgets()
        b.add_widget(self.live_info)
        self.cards_into(b, fresh(self.cache.get("live", [])),
                        "No fresh news right now.")

    def render_saved(self):
        b = self.saved_box
        b.clear_widgets()
        if not self.saved:
            b.add_widget(self.note(
                "Nothing saved yet. Tap the star on any news.", "star"))
            return
        for i, it in enumerate(self.saved[:50]):
            b.add_widget(self.news_card(it, i))

    def paint_pills(self):
        for n, p in self.pills.items():
            p.set_on(n == self.cat)

    # ----- loading -----
    def bg(self, fn, cb):
        def w():
            try:
                r = fn()
            except Exception:
                r = None
            Clock.schedule_once(lambda dt: cb(r))
        threading.Thread(target=w, daemon=True).start()

    def load_home(self, *a):
        qs = [(CH_Q[lg] + " when:1d", lg) for lg in self.langs()]
        self.bg(lambda: gather(qs), self.home_done)
        self.bg(self.get_weather, self.wx_done)

    def home_done(self, r):
        if r is None:
            self.render_home(err=True)
            self.toast("No connection")
            return
        self.cache["home"] = r[:25]
        self.last = time.time()
        self.save_json("cache.json", self.cache)
        self.render_home()

    def get_weather(self):
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s"
               "&longitude=%s&current=temperature_2m,weather_code,"
               "relative_humidity_2m,wind_speed_10m" % WX)
        w = get(url).json()["current"]
        return ["%d°" % round(w["temperature_2m"]),
                wx_text(w["weather_code"]),
                "Humidity %d%%  ·  Wind %d km/h" % (
                    round(w["relative_humidity_2m"]),
                    round(w["wind_speed_10m"]))]

    def wx_done(self, r):
        if not r:
            return
        self.cache["wx"] = r
        self.wx_vals = tuple(r)
        try:
            self.wx_temp.text = r[0]
            self.wx_cond.text = r[1]
            self.wx_more.text = r[2]
            self.wx_icon.set(WX_ICON.get(r[1], "weather-partly-cloudy"),
                             "gold")
        except Exception:
            pass
        self.save_json("cache.json", self.cache)

    def pick_cat(self, name):
        self.cat = name
        self.paint_pills()
        self.cat_box.clear_widgets()
        self.cat_box.add_widget(self.note("Loading..."))
        self.load_cat()

    def load_cat(self, *a):
        qs = [(CAT_Q[lg][self.cat] + " when:1d", lg) for lg in self.langs()]
        self.bg(lambda: gather(qs), self.cat_done)

    def cat_done(self, r):
        if r is None:
            self.cat_items = []
            self.render_cat("No connection. Tap refresh.")
            return
        self.cat_items = r
        self.render_cat("No fresh news in this category.")

    def load_live(self, *a):
        qs = []
        for lg in self.langs():
            if lg == "en":
                qs += [("India news when:1h", lg),
                       ("Uttarakhand when:6h", lg)]
            else:
                qs += [("भारत समाचार when:1h", lg),
                       ("उत्तराखंड when:6h", lg)]
            qs.append((CH_Q[lg] + " when:1d", lg))
        self.bg(lambda: gather(qs), self.live_done)

    def live_done(self, r):
        if r is None:
            self.live_info.text = "No connection."
            return
        self.cache["live"] = r[:25]
        self.live_info.text = "Updated " + time.strftime("%H:%M")
        self.save_json("cache.json", self.cache)
        self.render_live()

    # ----- profile photo -----
    def pick_photo(self):
        try:
            from android import activity
            from jnius import autoclass
            PA = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            i = Intent(Intent.ACTION_GET_CONTENT)
            i.setType("image/*")
            activity.bind(on_activity_result=self.on_pick)
            PA.mActivity.startActivityForResult(
                Intent.createChooser(i, "Select photo"), 7781)
        except Exception:
            self.toast("Photo picker works on the phone only")

    def on_pick(self, req, res, data):
        if req != 7781:
            return
        try:
            from android import activity
            activity.unbind(on_activity_result=self.on_pick)
        except Exception:
            pass
        if res != -1 or data is None:
            return
        try:
            from jnius import autoclass
            PA = autoclass("org.kivy.android.PythonActivity")
            uri = data.getData()
            stream = PA.mActivity.getContentResolver().openInputStream(uri)
            BF = autoclass("android.graphics.BitmapFactory")
            Opt = autoclass("android.graphics.BitmapFactory$Options")
            o = Opt()
            o.inSampleSize = 4
            bmp = BF.decodeStream(stream, None, o)
            stream.close()
            CF = autoclass("android.graphics.Bitmap$CompressFormat")
            FOS = autoclass("java.io.FileOutputStream")
            dst = os.path.join(self.user_data_dir,
                               "avatar_%d.jpg" % int(time.time()))
            out = FOS(dst)
            bmp.compress(CF.JPEG, 90, out)
            out.flush()
            out.close()
            old = self.prof.get("photo")
            self.prof["photo"] = dst
            self.save_prof()
            try:
                if old and os.path.exists(old):
                    os.remove(old)
            except Exception:
                pass
            Clock.schedule_once(lambda dt: self.avatar.set_photo(
                dst, self.prof["name"]))
        except Exception:
            Clock.schedule_once(
                lambda dt: self.toast("Could not load that photo"))


class ButtonBehaviorLabel(ButtonBehavior, Label):
    pass


def start():
    SandeshApp().run()
