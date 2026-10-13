import html
import json
import os
import re
import threading
import time
import traceback
import webbrowser
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import certifi
import requests
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, PopMatrix, PushMatrix, Rectangle,
                           RoundedRectangle, Translate)
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import (FadeTransition, Screen, ScreenManager,
                                    SlideTransition)
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

BASE = os.path.dirname(os.path.abspath(__file__))
MAX_AGE = 24 * 3600
WX = (30.41, 79.32)
SITE = "https://x6farswan.github.io"
INSTA = "https://instagram.com/x6_farswan"


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


def parse_related(desc, link, title):
    out = []
    if not desc:
        return out
    pat = (r'<a href="([^"]+)"[^>]*>(.*?)</a>\s*(?:&nbsp;|\xa0|\s)*'
           r'<font[^>]*>(.*?)</font>')
    for href, ttl, src in re.findall(pat, desc, re.S):
        ttl = html.unescape(re.sub(r"<[^>]+>", "", ttl)).strip()
        src = html.unescape(re.sub(r"<[^>]+>", "", src)).strip()
        href = html.unescape(href)
        if href == link or ttl == title or not ttl:
            continue
        out.append({"title": ttl, "src": src, "link": href})
    return out[:8]


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
            link = it.findtext("link")
            out.append({"title": title, "src": src, "link": link,
                        "ts": ts,
                        "rel": parse_related(it.findtext("description"),
                                             link, title)})
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


# ---------- text textures (used by the fast list rows) ----------
_TC = {}


def tex(text, fs, font="Roboto", bold=False, width=None, lines=0,
        halign="left"):
    if not text:
        return None
    key = (text, fs, font, bold, width, lines, halign)
    t = _TC.get(key)
    if t is None:
        if len(_TC) > 160:
            _TC.clear()
        kw = dict(text=text, font_size=sp(fs), font_name=font, bold=bold,
                  halign=halign, valign="top")
        if width:
            kw["text_size"] = (width, None)
        if lines:
            kw["max_lines"] = lines
        try:
            lb = CoreLabel(**kw)
            lb.refresh()
            t = lb.texture
        except Exception:
            try:
                kw["font_name"] = "Roboto"
                lb = CoreLabel(**kw)
                lb.refresh()
                t = lb.texture
            except Exception:
                t = None
        _TC[key] = t
    return t


def news_h():
    return dp(150)


def row(d, h):
    return {"d": d, "height": h, "size_hint_y": None}


def news_rows(items, empty, icon="newspaper"):
    if not items:
        return [row({"kind": "note", "icon": icon, "a": empty}, dp(190))]
    return [row(dict(it, kind="news"), news_h()) for it in items[:30]]


class Row(RecycleDataViewBehavior, Widget):
    """One list row, drawn directly on the canvas (very light)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.d = None
        self._tr = None
        self._press = False
        self._cancel = False
        self._pop = False
        self.bind(size=self.redraw, pos=self._move)

    def refresh_view_attrs(self, rv, index, data):
        super().refresh_view_attrs(rv, index, data)
        self._press = False
        self.redraw()

    def _move(self, *a):
        if self._tr is not None:
            self._tr.xy = self.pos

    def redraw(self, *a):
        self.canvas.clear()
        d = self.d
        if not d or self.width < dp(150):
            return
        with self.canvas:
            PushMatrix()
            self._tr = Translate(self.x, self.y)
            try:
                getattr(self, "k_" + d["kind"])(d, self.width, self.height)
            except Exception:
                traceback.print_exc()
            PopMatrix()

    # --- drawing helpers (local coordinates) ---
    def put(self, t, x, ytop, col):
        if t is None:
            return
        Color(*col)
        Rectangle(texture=t, pos=(x, ytop - t.height), size=t.size)

    def box(self, w, h, col, r=18, alpha=None):
        c = P[col]
        Color(c[0], c[1], c[2], c[3] if alpha is None else alpha)
        RoundedRectangle(pos=(0, 0), size=(w, h), radius=[dp(r)])

    # --- row kinds ---
    def k_greet(self, d, w, h):
        t = tex(d["a"], 22, fnt(d["a"], SERIF), width=w - dp(8))
        self.put(t, dp(4), h - dp(4), P["text"])
        self.put(tex(d["b"], 12), dp(4), h - dp(40), P["sub"])

    def k_hero(self, d, w, h):
        self.box(w, h, "card", 18)
        t = tex(d["t"], 46, SERIF)
        if t is not None:
            self.put(t, dp(20), h / 2 + t.height / 2, P["gold"])
        x = dp(130)
        iw = max(dp(60), w - x - dp(80))
        self.put(tex("Chamoli", 18, bold=True), x, h - dp(18), P["text"])
        self.put(tex(d["c"], 14, fnt(d["c"]), width=iw, lines=1), x,
                 h - dp(48), P["gold"])
        self.put(tex(d["m"], 12, fnt(d["m"]), width=iw, lines=1), x,
                 h - dp(72), P["sub"])
        g = tex(ic(WX_ICON.get(d["c"], "weather-partly-cloudy")), 40, "MDI")
        if g is not None:
            self.put(g, w - dp(18) - g.width, h / 2 + g.height / 2,
                     P["gold"])

    def k_section(self, d, w, h):
        self.put(tex(d["a"], 12, fnt(d["a"]), bold=True), dp(2), h - dp(6),
                 P["gold"])

    def k_note(self, d, w, h):
        g = tex(ic(d.get("icon", "newspaper")), 44, "MDI")
        if g is not None:
            self.put(g, (w - g.width) / 2, h - dp(26), P["gold"])
        self.put(tex(d["a"], 14, fnt(d["a"]), width=w - dp(40),
                     halign="center"), dp(20), h - dp(100), P["sub"])

    def k_news(self, d, w, h):
        self.box(w, h, "card", 18)
        if self._press:
            self.box(w, h, "gold", 18, .12)
        title = d["title"]
        t = tex(title, 17, fnt(title, SERIF), width=w - dp(36), lines=3)
        self.put(t, dp(18), h - dp(16), P["text"])
        app = App.get_running_app()
        saved = app.is_saved(d)
        cy = dp(22)
        tm = tex(ago(d["ts"]), 12)
        tw = tm.width if tm is not None else 0
        smax = max(dp(40), w - dp(18) - dp(100) - tw - dp(10))
        src = d.get("src") or ""
        st = tex(src, 12, fnt(src), bold=True)
        if st is not None and st.width > smax:
            st = tex(src, 12, fnt(src), bold=True, width=smax, lines=1)
        x = dp(18)
        if st is not None:
            self.put(st, x, cy + st.height / 2, P["gold"])
            x += (min(st.width, smax)) + dp(10)
        if tm is not None:
            self.put(tm, x, cy + tm.height / 2, P["sub"])
        sz = 27 if self._pop else 22
        si = tex(ic("star" if saved else "star-outline"), sz, "MDI")
        if si is not None:
            self.put(si, w - dp(74) - si.width / 2, cy + si.height / 2,
                     P["gold"] if saved else P["sub"])
        di = tex(ic("dots-vertical"), 22, "MDI")
        if di is not None:
            self.put(di, w - dp(28) - di.width / 2, cy + di.height / 2,
                     P["sub"])

    # --- touch ---
    def on_touch_down(self, touch):
        if (touch.is_mouse_scrolling or not self.d
                or self.d.get("kind") != "news"
                or not self.collide_point(*touch.pos)):
            return False
        touch.grab(self)
        self._press = True
        self._cancel = False
        self.redraw()
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if not self._cancel and (abs(touch.x - touch.ox) > dp(10)
                                     or abs(touch.y - touch.oy) > dp(10)):
                self._cancel = True
                self._press = False
                self.redraw()
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        ok = self._press and not self._cancel
        self._press = False
        self.redraw()
        if ok and self.collide_point(*touch.pos):
            self.tapped(touch)
        return True

    def tapped(self, touch):
        app = App.get_running_app()
        d = self.d
        lx = touch.x - self.x
        ly = touch.y - self.y
        if ly < dp(46) and lx > self.width - dp(50):
            app.open_menu(d)
        elif ly < dp(46) and lx > self.width - dp(100):
            self._pop = True
            app.toggle_save(d)
            self.redraw()
            Clock.schedule_once(self._unpop, .14)
        else:
            app.open_detail(d)

    def _unpop(self, dt):
        self._pop = False
        self.redraw()


def make_rv():
    rv = RecycleView(bar_width=0, do_scroll_x=False,
                     scroll_distance=dp(6), scroll_timeout=40)
    rv.viewclass = Row
    lay = RecycleBoxLayout(default_size=(None, news_h()),
                           default_size_hint=(1, None), size_hint_y=None,
                           orientation="vertical", spacing=dp(12),
                           padding=[dp(16), dp(4), dp(16), dp(18)])
    lay.bind(minimum_height=lay.setter("height"))
    rv.add_widget(lay)
    return rv


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


class Glyph(Label):
    def __init__(self, icon, fs=22, color="gold", box=34, **kw):
        super().__init__(text=ic(icon), font_name="MDI", font_size=sp(fs),
                         color=P[color], size_hint=(None, 1),
                         width=dp(box), **kw)


class LinkLabel(ButtonBehavior, Label):
    pass


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


class Pic(BoxLayout):
    def __init__(self, **kw):
        super().__init__(size_hint=(None, None),
                         size=(dp(116), dp(116)), **kw)
        self.tex = None
        with self.canvas.before:
            Color(*P["gold"])
            self._e = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._u, size=self._u)
        self.letter = Label(text="U", font_size=sp(46), bold=True,
                            font_name=SERIF, color=P["onGold"])
        self.add_widget(self.letter)

    def _u(self, *a):
        self._e.pos = self.pos
        self._e.size = self.size

    def set_name(self, n):
        n = (n or "").strip()
        self.letter.text = n[:1].upper() if n else "U"
        self.letter.font_name = fnt(self.letter.text, SERIF)


# ---------------- app ----------------
class NewsApp(App):
    title = "Sandesh"

    # ----- state -----
    def state_path(self):
        return os.path.join(self.user_data_dir, "state.json")

    def load_state(self):
        self.dark = True
        self.name = ""
        self.lang = "both"
        self.saved = []
        try:
            with open(self.state_path(), "r", encoding="utf-8") as f:
                s = json.load(f)
            self.dark = s.get("dark", True)
            self.name = s.get("name", "")
            self.lang = s.get("lang", "both")
            self.saved = s.get("saved", [])
        except Exception:
            pass

    def save_state(self):
        try:
            with open(self.state_path(), "w", encoding="utf-8") as f:
                json.dump({"dark": self.dark, "name": self.name,
                           "lang": self.lang, "saved": self.saved}, f,
                          ensure_ascii=False)
        except Exception:
            traceback.print_exc()

    # ----- build -----
    def build(self):
        self.load_state()
        P.clear()
        P.update(DARK if self.dark else LIGHT)
        self.data = {}
        self.rvs = {}
        self.navs = {}
        self.pills = {}
        self.lpills = {}
        self.cat = CATS[0]
        self.prev = "home"
        self.cur = None
        self.home_args = (None, None, None)
        root = self.make_ui()
        Window.bind(on_keyboard=self.on_key)
        Clock.schedule_once(lambda dt: self.refresh_all(), .3)
        Clock.schedule_interval(lambda dt: self.load_live(), 120)
        return root

    def make_ui(self):
        Window.clearcolor = P["bg"]
        root = BoxLayout(orientation="vertical")

        hdr = BoxLayout(size_hint_y=None, height=dp(60),
                        padding=[dp(20), dp(8), dp(12), dp(8)],
                        spacing=dp(4))
        hdr.add_widget(Txt("Sandesh", 28, "gold", serif=True, fill=True))
        b1 = IconBtn("refresh", 24, "text", 44)
        b1.bind(on_release=lambda *a: self.refresh_all())
        b2 = IconBtn("weather-night" if self.dark else "white-balance-sunny",
                     24, "text", 44)
        b2.bind(on_release=lambda *a: self.toggle_theme())
        hdr.add_widget(b1)
        hdr.add_widget(b2)

        sm = ScreenManager(transition=FadeTransition(duration=.12))
        self.sm = sm
        self.rvs = {}
        self.pills = {}
        self.lpills = {}

        for key in ("home", "live", "saved"):
            s = Screen(name=key)
            rv = make_rv()
            self.rvs[key] = rv
            s.add_widget(rv)
            sm.add_widget(s)

        # explore (pills + list)
        s = Screen(name="explore")
        box = BoxLayout(orientation="vertical")
        sv = ScrollView(size_hint_y=None, height=dp(50), do_scroll_y=False,
                        bar_width=0)
        inner = BoxLayout(size_hint_x=None, spacing=dp(8),
                          padding=[dp(16), dp(6), dp(16), dp(6)])
        inner.bind(minimum_width=inner.setter("width"))
        for c in CATS:
            p = Pill(c)
            p.bind(on_release=lambda i, c=c: self.pick(c))
            self.pills[c] = p
            inner.add_widget(p)
        sv.add_widget(inner)
        box.add_widget(sv)
        rv = make_rv()
        self.rvs["explore"] = rv
        box.add_widget(rv)
        s.add_widget(box)
        sm.add_widget(s)
        self.mark_pills()

        sm.add_widget(self.make_me())
        sm.add_widget(self.make_detail_screen())

        nav = Panel(bg="card", radius=0, size_hint_y=None, height=dp(64))
        self.navs = {}
        for key, icon, label in TABS:
            n = NavItem(icon, label)
            n.bind(on_release=lambda i, k=key: self.go(k))
            self.navs[key] = n
            nav.add_widget(n)

        root.add_widget(hdr)
        root.add_widget(sm)
        root.add_widget(nav)

        loading = [row({"kind": "note", "icon": "timer-sand",
                        "a": "Loading..."}, dp(190))]
        for k, rv in self.rvs.items():
            rows = self.data.get(k)
            if rows is None:
                rows = (news_rows(self.saved, "Koi saved khabar nahi.\n"
                                  "Star dabake save karo", "star-outline")
                        if k == "saved" else loading)
                self.data[k] = rows
            rv.data = rows
        self.navs["home"].active(True)
        return root

    def make_me(self):
        s = Screen(name="me")
        sv = ScrollView(bar_width=0, do_scroll_x=False)
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        spacing=dp(12), padding=[dp(16), dp(10), dp(16),
                                                 dp(24)])
        box.bind(minimum_height=box.setter("height"))

        anc = AnchorLayout(size_hint_y=None, height=dp(130))
        self.pic = Pic()
        self.pic.set_name(self.name)
        anc.add_widget(self.pic)
        box.add_widget(anc)

        self.nf = Field(text=self.name, hint_text="Your name")
        self.nf.bind(on_text_validate=self.set_name)
        box.add_widget(self.nf)

        box.add_widget(Txt("NEWS LANGUAGE", 12, "gold", bold=True))
        lrow = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        for code, label in (("en", "English"), ("hi", "Hindi"),
                            ("both", "Both")):
            p = Pill(label)
            p.bind(on_release=lambda i, c=code: self.set_lang(c))
            self.lpills[code] = p
            lrow.add_widget(p)
        lrow.add_widget(Widget())
        box.add_widget(lrow)
        self.mark_lang()

        for label, url in (("Website  -  x6farswan.github.io", SITE),
                           ("Instagram  -  @x6_farswan", INSTA)):
            c = Card(bg="card", size_hint_y=None, height=dp(52),
                     padding=[dp(16), 0])
            c.add_widget(Txt(label, 14, fill=True))
            c.bind(on_release=lambda i, u=url: open_url(u))
            box.add_widget(c)

        c = Card(bg="card", size_hint_y=None, height=dp(52),
                 padding=[dp(16), 0])
        c.add_widget(Txt("Clear saved news", 14, "sub", fill=True))
        c.bind(on_release=lambda *a: self.clear_saved())
        box.add_widget(c)

        sv.add_widget(box)
        s.add_widget(sv)
        return s

    def make_detail_screen(self):
        s = Screen(name="detail")
        box = BoxLayout(orientation="vertical")
        top = BoxLayout(size_hint_y=None, height=dp(48),
                        padding=[dp(8), 0, dp(8), 0])
        back = IconBtn("arrow-left", 24, "text", 44)
        back.bind(on_release=lambda *a: self.back())
        self.dstar = IconBtn("star-outline", 24, "sub", 44)
        self.dstar.bind(on_release=lambda *a: self.detail_star())
        top.add_widget(back)
        top.add_widget(Widget())
        top.add_widget(self.dstar)
        box.add_widget(top)
        sv = ScrollView(bar_width=0, do_scroll_x=False)
        self.dbox = BoxLayout(orientation="vertical", size_hint_y=None,
                              spacing=dp(12),
                              padding=[dp(16), dp(8), dp(16), dp(24)])
        self.dbox.bind(minimum_height=self.dbox.setter("height"))
        sv.add_widget(self.dbox)
        box.add_widget(sv)
        s.add_widget(box)
        return s

    # ----- navigation -----
    def go(self, key):
        self.sm.transition = FadeTransition(duration=.12)
        self.sm.current = key
        for k, n in self.navs.items():
            n.active(k == key)

    def on_key(self, window, key, *a):
        if key == 27:
            if self.sm.current == "detail":
                self.back()
                return True
            if self.sm.current != "home":
                self.go("home")
                return True
        return False

    def back(self):
        if self.sm.current == "detail":
            self.sm.transition = SlideTransition(direction="right",
                                                 duration=.18)
            self.sm.current = self.prev

    # ----- theme / settings -----
    def toggle_theme(self):
        self.dark = not self.dark
        P.clear()
        P.update(DARK if self.dark else LIGHT)
        self.save_state()
        cur = self.prev if self.sm.current == "detail" else self.sm.current
        old = self.root
        self.root = self.make_ui()
        Window.remove_widget(old)
        Window.add_widget(self.root)
        self.go(cur)

    def set_name(self, *a):
        self.name = self.nf.text.strip()
        self.pic.set_name(self.name)
        self.save_state()
        self.set_home(*self.home_args)

    def set_lang(self, code):
        self.lang = code
        self.save_state()
        self.mark_lang()
        self.refresh_all()

    def mark_lang(self):
        for c, p in self.lpills.items():
            p.set_on(c == self.lang)

    def mark_pills(self):
        for c, p in self.pills.items():
            p.set_on(c == self.cat)

    def pick(self, c):
        self.cat = c
        self.mark_pills()
        self.load_explore()

    # ----- data -----
    def qs(self, en, hi):
        if self.lang == "en":
            return [(en, "en")]
        if self.lang == "hi":
            return [(hi, "hi")]
        return [(en, "en"), (hi, "hi")]

    def set_rows(self, key, rows):
        self.data[key] = rows
        rv = self.rvs.get(key)
        if rv is not None:
            rv.data = rows
            rv.refresh_from_data()

    def loading(self, key):
        self.set_rows(key, [row({"kind": "note", "icon": "timer-sand",
                                 "a": "Loading..."}, dp(190))])

    def refresh_all(self):
        self.load_home()
        self.load_explore()
        self.load_live()

    def get_wx(self):
        try:
            u = ("https://api.open-meteo.com/v1/forecast?latitude=%s"
                 "&longitude=%s&current=temperature_2m,weather_code"
                 % WX)
            c = get(u).json()["current"]
            return ("%d\u00b0" % round(c["temperature_2m"]),
                    wx_text(int(c["weather_code"])))
        except Exception:
            return None

    def load_home(self):
        def work():
            try:
                local = gather(self.qs(CH_Q["en"], CH_Q["hi"]))
            except Exception:
                local = None
            try:
                uk = gather(self.qs("Uttarakhand", "उत्तराखंड"))
            except Exception:
                uk = None
            wx = self.get_wx()
            Clock.schedule_once(lambda dt: self.set_home(local, uk, wx))
        threading.Thread(target=work, daemon=True).start()

    def set_home(self, local, uk, wx):
        self.home_args = (local, uk, wx)
        h = time.localtime().tm_hour
        g = ("Good morning" if h < 12 else
             "Good afternoon" if h < 17 else "Good evening")
        if self.name:
            g += ", " + self.name
        rows = [row({"kind": "greet", "a": g,
                     "b": time.strftime("%A, %d %B")}, dp(64))]
        if wx:
            rows.append(row({"kind": "hero", "t": wx[0], "c": wx[1],
                             "m": "Gopeshwar, Uttarakhand"}, dp(110)))
        if local is None and uk is None:
            rows.append(row({"kind": "note", "icon": "wifi-off",
                             "a": "Internet nahi mil raha.\n"
                                  "Refresh dabake dobara try karo"},
                            dp(190)))
        else:
            rows.append(row({"kind": "section", "a": "CHAMOLI"}, dp(26)))
            rows += news_rows(local, "Chamoli ki koi taaza khabar nahi",
                              "map-marker-off")
            rows.append(row({"kind": "section", "a": "UTTARAKHAND"},
                            dp(26)))
            rows += news_rows(uk, "Koi taaza khabar nahi")
        self.set_rows("home", rows)

    def load_explore(self):
        cat = self.cat
        self.loading("explore")

        def work():
            try:
                items = gather(self.qs(CAT_Q["en"][cat], CAT_Q["hi"][cat]))
                msg = "Is category me koi taaza khabar nahi"
            except Exception:
                items = []
                msg = "Internet nahi mil raha"

            def done(dt):
                if cat == self.cat:
                    self.set_rows("explore", news_rows(items, msg))
            Clock.schedule_once(done)
        threading.Thread(target=work, daemon=True).start()

    def load_live(self):
        def work():
            try:
                items = fresh(gather([("breaking news India", "en"),
                                      ("ताज़ा खबर", "hi")]))
                msg = "Abhi koi live khabar nahi"
            except Exception:
                items = []
                msg = "Internet nahi mil raha"
            rows = [row({"kind": "section", "a": "LAST 24 HOURS"}, dp(26))]
            rows += news_rows(items, msg, "access-point-off")
            Clock.schedule_once(lambda dt: self.set_rows("live", rows))
        threading.Thread(target=work, daemon=True).start()

    # ----- saved -----
    def is_saved(self, d):
        link = d.get("link")
        return any(x.get("link") == link for x in self.saved)

    def toggle_save(self, d):
        link = d.get("link")
        if self.is_saved(d):
            self.saved = [x for x in self.saved if x.get("link") != link]
        else:
            item = {k: v for k, v in d.items() if k != "kind"}
            self.saved.insert(0, item)
        self.save_state()
        self.update_saved()
        if self.cur is not None and self.cur.get("link") == link:
            self.paint_dstar()

    def update_saved(self):
        self.set_rows("saved", news_rows(
            self.saved, "Koi saved khabar nahi.\nStar dabake save karo",
            "star-outline"))

    def clear_saved(self):
        self.saved = []
        self.save_state()
        self.update_saved()
        for rv in self.rvs.values():
            rv.refresh_from_data()

    # ----- detail / menu -----
    def paint_dstar(self):
        s = self.cur is not None and self.is_saved(self.cur)
        self.dstar.set("star" if s else "star-outline",
                       "gold" if s else "sub")

    def detail_star(self):
        if self.cur is not None:
            self.toggle_save(self.cur)
            for rv in self.rvs.values():
                rv.refresh_from_data()

    def open_detail(self, d):
        self.cur = d
        if self.sm.current != "detail":
            self.prev = self.sm.current
        box = self.dbox
        box.clear_widgets()
        box.add_widget(Txt(d["title"], 22, serif=True))
        meta = (d.get("src") or "") + "  -  " + ago(d["ts"])
        box.add_widget(Txt(meta, 13, "gold", bold=True))
        b = Card(bg="gold", size_hint_y=None, height=dp(52))
        b.add_widget(Txt("Open full story", 15, "onGold", bold=True,
                         halign="center", fill=True))
        b.bind(on_release=lambda *a: open_url(d["link"]))
        box.add_widget(b)
        rel = d.get("rel") or []
        if rel:
            box.add_widget(Txt("RELATED COVERAGE", 12, "gold", bold=True))
        for r in rel:
            c = Card(bg="card", orientation="vertical", size_hint_y=None,
                     height=dp(96), padding=dp(14), spacing=dp(2))
            c.add_widget(Txt(r["title"], 15, serif=True, fill=True,
                             max_lines=3))
            c.add_widget(Txt(r.get("src") or "", 11, "gold", bold=True))
            c.bind(on_release=lambda i, u=r["link"]: open_url(u))
            box.add_widget(c)
        self.paint_dstar()
        self.sm.transition = SlideTransition(direction="left", duration=.18)
        self.sm.current = "detail"

    def open_menu(self, d):
        mv = ModalView(size_hint=(.82, None), height=dp(190),
                       background="", background_color=(0, 0, 0, .55))
        panel = Panel(bg="card", orientation="vertical", padding=dp(12),
                      spacing=dp(8))

        def opt(label, fn):
            c = Card(bg="bg", size_hint_y=None, height=dp(46),
                     padding=[dp(14), 0])
            c.add_widget(Txt(label, 14, fill=True))

            def run(*a):
                mv.dismiss()
                fn()
            c.bind(on_release=run)
            panel.add_widget(c)

        def copy():
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(d["link"])
            except Exception:
                pass

        def sv():
            self.toggle_save(d)
            for rv in self.rvs.values():
                rv.refresh_from_data()

        opt("Open in browser", lambda: open_url(d["link"]))
        opt("Remove from saved" if self.is_saved(d) else "Save", sv)
        opt("Copy link", copy)
        mv.add_widget(panel)
        mv.open()


def start():
    NewsApp().run()


if __name__ == "__main__":
    start()
