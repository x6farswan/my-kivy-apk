import html
import json
import os
import re
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
from kivy.core.text import Label as CoreLabel
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, PopMatrix, PushMatrix, Rectangle,
                           RoundedRectangle, Translate)
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
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
        try:
            kw = dict(text=text, font_size=sp(fs), font_name=font, bold=bold,
                      halign=halign, valign="top")
            if width:
                kw["text_size"] = (width, None)
            if lines:
                kw["max_lines"] = lines
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
                pass
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


class Dim(Widget):
    def __init__(self, cb, **kw):
        super().__init__(**kw)
        self.cb = cb
        with self.canvas:
            self.col = Color(0, 0, 0, 0)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_touch_down(self, touch):
        self.cb()
        return True

    def on_touch_move(self, touch):
        return True

    def on_touch_up(self, touch):
        return True


class Sheet(FloatLayout):
    """iOS style bottom action sheet."""

    def __init__(self, app, title, opts, **kw):
        super().__init__(**kw)
        self.app = app
        self.closing = False
        self.dim = Dim(self.dismiss)
        self.add_widget(self.dim)
        n = len(opts)
        ph = dp(34) + dp(56) + n * dp(54)
        self.panel = Panel(orientation="vertical", size_hint=(1, None),
                           height=ph, bg="card", radius=24,
                           padding=[dp(10), dp(16), dp(10), dp(18)],
                           spacing=dp(2))
        self.panel.add_widget(Txt(title, fs=13, color="sub",
                                  max_lines=2, size_hint_y=None))
        for icon, label, cb in opts:
            r = Card(orientation="horizontal", size_hint_y=None,
                     height=dp(52), padding=[dp(12), 0, dp(12), 0],
                     spacing=dp(14), radius=14)
            r.add_widget(Glyph(icon))
            r.add_widget(Txt(label, fs=15, fill=True))
            r.bind(on_release=lambda x, f=cb: self.pick(f))
            self.panel.add_widget(r)
        self.add_widget(self.panel)

    def show(self):
        self.app.sheet = self
        Window.add_widget(self)
        self.panel.y = -self.panel.height
        Animation(y=0, d=.26, t="out_cubic").start(self.panel)
        Animation(a=.6, d=.26).start(self.dim.col)

    def pick(self, cb):
        self.dismiss()
        Clock.schedule_once(lambda dt: cb(), .06)

    def dismiss(self):
        if self.closing:
            return
        self.closing = True
        a = Animation(y=-self.panel.height, d=.2, t="in_cubic")
        a.bind(on_complete=lambda *x: self._gone())
        a.start(self.panel)
        Animation(a=0, d=.2).start(self.dim.col)

    def _gone(self):
        try:
            Window.remove_widget(self)
        except Exception:
            pass
        if self.app.sheet is self:
            self.app.sheet = None


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
        self.prof.setdefault("hidden", [])
        self.saved = self.load_json("saved.json", [])
        self.cache = self.load_json("cache.json", {})
        if not isinstance(self.cache, dict):
            self.cache = {}
        self.wx_vals = tuple(self.cache.get("wx", ["--°", "Loading", ""]))
        self.cat = CATS[0]
        self.cat_items = []
        self.cat_msg = "Pick a category above."
        self.cat_loaded = False
        self.live_text = "UPDATED --:--   ·   AUTO REFRESH"
        self.live_links = []
        self.last = 0
        self.cur = "home"
        self.prev = "home"
        self.cur_item = None
        self.sheet = None
        self.live_dot = None
        self.apply_palette()
        Window.bind(on_keyboard=self.on_key)
        return self.make_root()

    def on_start(self):
        self.load_home()
        self.load_live()
        Clock.schedule_interval(lambda dt: self.load_live(), 120)

    def on_pause(self):
        return True

    def on_resume(self):
        if time.time() - self.last > 300:
            self.load_home()
            self.load_live()

    def on_key(self, win, key, *a):
        if key != 27:
            return False
        if self.sheet is not None:
            self.sheet.dismiss()
            return True
        if self.cur == "detail":
            self.close_detail()
            return True
        if self.cur != "home":
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
        if self.sheet is not None:
            self.sheet.dismiss()
        if self.cur == "detail":
            self.cur = self.prev
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
                  self.build_profile(), self.build_detail()):
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

    def goto(self, key, fade=True):
        self.cur = key
        for k, it in self.nav.items():
            it.active(k == key)
        if fade:
            self.sm.transition = FadeTransition(duration=.16)
        self.sm.current = key
        self.pulse(key == "live")
        if key == "explore" and not self.cat_loaded:
            self.cat_loaded = True
            self.load_cat()

    def pulse(self, on):
        d = self.live_dot
        if d is None:
            return
        Animation.cancel_all(d)
        d.opacity = 1
        if on:
            a = Animation(opacity=.25, d=.9) + Animation(opacity=1, d=.9)
            a.repeat = True
            a.start(d)

    def header(self, title, actions=(), live=False):
        h = BoxLayout(size_hint_y=None, height=dp(64),
                      padding=[dp(20), 0, dp(10), 0])
        if live:
            dot = Label(text=ic("circle"), font_name="MDI",
                        font_size=sp(12), color=(.92, .25, .25, 1),
                        size_hint=(None, None), size=(dp(22), dp(22)),
                        pos_hint={"center_y": .5})
            self.live_dot = dot
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
                        scroll_distance=dp(6), scroll_timeout=40)
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

    def visible(self, items):
        hid = set(self.prof.get("hidden", []))
        return [x for x in items if x.get("src") not in hid]

    # ----- screens -----
    def build_home(self):
        s = Screen(name="home")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Sandesh", [
            ("refresh", self.load_home),
            ("theme-light-dark", self.toggle_theme)]))
        self.home_rv = make_rv()
        col.add_widget(self.home_rv)
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
        prow = BoxLayout(size_hint_x=None, spacing=dp(8),
                         padding=[dp(16), dp(6)])
        prow.bind(minimum_width=prow.setter("width"))
        self.pills = {}
        for n in CATS:
            p = Pill(n)
            p.bind(on_release=lambda x, nm=n: self.pick_cat(nm))
            self.pills[n] = p
            prow.add_widget(p)
        psv.add_widget(prow)
        col.add_widget(psv)
        self.cat_rv = make_rv()
        col.add_widget(self.cat_rv)
        s.add_widget(col)
        return s

    def build_live(self):
        s = Screen(name="live")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Live", [
            ("refresh", self.load_live),
            ("theme-light-dark", self.toggle_theme)], live=True))
        self.live_rv = make_rv()
        col.add_widget(self.live_rv)
        s.add_widget(col)
        return s

    def build_saved(self):
        s = Screen(name="saved")
        col = BoxLayout(orientation="vertical")
        col.add_widget(self.header("Saved", [
            ("theme-light-dark", self.toggle_theme)]))
        self.saved_rv = make_rv()
        col.add_widget(self.saved_rv)
        s.add_widget(col)
        return s

    def build_detail(self):
        s = Screen(name="detail")
        self.detail_col = BoxLayout(orientation="vertical")
        s.add_widget(self.detail_col)
        self.d_star = None
        self.d_status = None
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
        box.add_widget(Txt("PREFERENCES", fs=12, color="gold", bold=True))
        box.add_widget(self.row_btn(
            "Appearance", "Dark" if self.prof["dark"] else "Light",
            lambda v: self.toggle_theme()))
        box.add_widget(self.row_btn("Language", self.lang_label(),
                                    self.cycle_lang))
        box.add_widget(self.row_btn(
            "Hidden sources", str(len(self.prof.get("hidden", []))),
            self.clear_hidden))
        box.add_widget(self.row_btn("Version", "Sandesh 4.0",
                                    lambda v: None))
        col.add_widget(sv)
        cred = BoxLayout(orientation="vertical", size_hint_y=None,
                         height=dp(96), padding=[0, dp(4)])
        cred.add_widget(Txt(
            "Made in Gopeshwar with [color=ff4d6d][font=MDI]%s[/font]"
            "[/color]" % ic("heart"), fs=12, color="sub",
            halign="center", markup=True))
        l1 = LinkLabel(
            text="by Rohit  ·  [color=%s]@x6_farswan[/color]" % hexc("gold"),
            markup=True, font_size=sp(12), color=P["sub"],
            size_hint_y=None, height=dp(28))
        l1.bind(on_release=lambda x: open_url(INSTA))
        cred.add_widget(l1)
        l2 = LinkLabel(
            text="[color=%s]x6farswan.github.io[/color]" % hexc("gold"),
            markup=True, font_size=sp(12), color=P["sub"],
            size_hint_y=None, height=dp(28))
        l2.bind(on_release=lambda x: open_url(SITE))
        cred.add_widget(l2)
        col.add_widget(cred)
        s.add_widget(col)
        return s

    # ----- small builders -----
    def gold_btn(self, text, cb):
        b = Card(bg="gold", size_hint_y=None, height=dp(48), radius=24)
        b.add_widget(Txt(text, fs=15, color="onGold", bold=True,
                         fill=True, halign="center"))
        b.bind(on_release=lambda x: cb())
        return b

    def row_btn(self, title, value, cb):
        r = Card(orientation="horizontal", size_hint_y=None,
                 height=dp(54), padding=[dp(18), 0, dp(18), 0], radius=14)
        r.add_widget(Txt(title, fs=15, fill=True))
        v = Txt(value, fs=15, color="gold", fill=True, halign="right")
        r.add_widget(v)
        r.bind(on_release=lambda x: cb(v))
        return r

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

    def clear_hidden(self, v):
        self.prof["hidden"] = []
        self.save_prof()
        v.text = "0"
        self.render_feeds()
        self.toast("Showing all sources")

    def save_name(self):
        n = self.name_in.text.strip() or "user1"
        self.prof["name"] = n
        self.save_prof()
        self.name_lbl.text = n
        self.name_lbl.font_name = fnt(n, SERIF)
        self.avatar.set_photo(self.prof.get("photo"), n)
        self.render_home()
        self.toast("Saved")

    # ----- story page -----
    def is_saved(self, it):
        return any(s["link"] == it["link"] for s in self.saved)

    def open_detail(self, it):
        self.cur_item = it
        self.pulse(False)
        if self.cur != "detail":
            self.prev = self.cur
        self.cur = "detail"
        col = self.detail_col
        col.clear_widgets()
        on = self.is_saved(it)
        h = BoxLayout(size_hint_y=None, height=dp(64),
                      padding=[dp(8), 0, dp(8), 0])
        back = IconBtn("arrow-left", fs=24, color="text", box=48,
                       pos_hint={"center_y": .5})
        back.bind(on_release=lambda x: self.close_detail())
        h.add_widget(back)
        h.add_widget(Txt("Story", fs=22, color="gold", serif=True,
                         wrap=False, fill=True))
        self.d_star = IconBtn("star" if on else "star-outline", fs=24,
                              color="gold" if on else "text", box=48,
                              pos_hint={"center_y": .5})
        self.d_star.bind(on_release=lambda x: self.toggle_save(
            self.cur_item))
        h.add_widget(self.d_star)
        dots = IconBtn("dots-vertical", fs=24, color="text", box=48,
                       pos_hint={"center_y": .5})
        dots.bind(on_release=lambda x: self.open_menu(self.cur_item))
        h.add_widget(dots)
        col.add_widget(h)
        sv, box = self.scroll()
        box.spacing = dp(14)
        box.add_widget(Txt((it.get("src") or "News").upper(), fs=12,
                           color="gold", bold=True))
        box.add_widget(Txt(it["title"], fs=24, serif=True))
        when = time.strftime("%d %b %Y, %H:%M", time.localtime(it["ts"]))
        box.add_widget(Txt("%s   ·   %s" % (ago(it["ts"]), when), fs=12,
                           color="sub"))
        self.d_status = Txt("", fs=12, color="sub")
        box.add_widget(self.d_status)
        self.sync_detail()
        box.add_widget(self.gold_btn(
            "Open in browser", lambda: open_url(self.cur_item["link"])))
        rel = it.get("rel") or []
        if rel:
            box.add_widget(Txt("ALSO REPORTED BY  (%d)" % len(rel), fs=12,
                               color="gold", bold=True))
            for r in rel:
                c = Card(orientation="vertical", size_hint_y=None,
                         padding=[dp(16), dp(12), dp(16), dp(12)],
                         spacing=dp(4), radius=14)
                c.bind(minimum_height=c.setter("height"))
                c.add_widget(Txt(r["title"], fs=15, serif=True))
                c.add_widget(Txt(r["src"], fs=12, color="gold", bold=True))
                c.bind(on_release=lambda x, u=r["link"]: open_url(u))
                box.add_widget(c)
        else:
            box.add_widget(Txt(
                "No other sources are grouped with this story right now.",
                fs=13, color="sub"))
        col.add_widget(sv)
        self.sm.transition = SlideTransition(direction="left", duration=.2)
        self.sm.current = "detail"

    def sync_detail(self):
        if self.cur != "detail" or self.cur_item is None:
            return
        on = self.is_saved(self.cur_item)
        if self.d_star is not None:
            self.d_star.set("star" if on else "star-outline",
                            "gold" if on else "text")
        if self.d_status is not None:
            self.d_status.text = (
                "Saved on this phone with full details" if on else
                "Temporary: details clear when the feed refreshes. "
                "Tap the star to keep it.")

    def close_detail(self):
        self.sm.transition = SlideTransition(direction="right",
                                             duration=.2)
        self.goto(self.prev, fade=False)

    def open_menu(self, it):
        on = self.is_saved(it)
        opts = [
            ("open-in-new", "Open in browser", lambda: open_url(it["link"])),
            ("share-variant", "Share", lambda: self.share(it)),
            ("link-variant", "Copy link",
             lambda: self.copy(it["link"], "Link copied")),
            ("content-copy", "Copy headline",
             lambda: self.copy(it["title"], "Headline copied")),
            ("star" if on else "star-outline",
             "Remove from Saved" if on else "Save with details",
             lambda: self.toggle_save(it)),
            ("magnify", "Search this on Google",
             lambda: open_url("https://www.google.com/search?q="
                              + quote(it["title"]))),
        ]
        src = it.get("src")
        if src:
            opts.append(("eye-off", "Hide news from %s" % src,
                         lambda: self.hide_source(src)))
        Sheet(self, it["title"], opts).show()

    def copy(self, text, msg):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(text)
            self.toast(msg)
        except Exception:
            self.toast("Copy not available")

    def hide_source(self, src):
        h = self.prof.setdefault("hidden", [])
        if src not in h:
            h.append(src)
        self.save_prof()
        self.toast("Hidden: " + src)
        self.render_feeds()
        if self.cur == "detail":
            self.close_detail()

    def toggle_save(self, it):
        if self.is_saved(it):
            self.saved = [s for s in self.saved if s["link"] != it["link"]]
            self.toast("Removed from Saved")
        else:
            self.saved.insert(
                0, {k: v for k, v in it.items() if k != "kind"})
            self.toast("Saved")
        self.save_json("saved.json", self.saved)
        self.render_saved()
        self.sync_detail()

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
    def home_rows(self, err=False):
        hr = time.localtime().tm_hour
        g = ("Good morning" if hr < 12 else
             "Good afternoon" if hr < 17 else "Good evening")
        rows = [
            row({"kind": "greet",
                 "a": "%s, %s" % (g, self.prof["name"]),
                 "b": time.strftime("%A, %d %B")}, dp(64)),
            row({"kind": "hero", "t": self.wx_vals[0],
                 "c": self.wx_vals[1], "m": self.wx_vals[2]}, dp(112)),
            row({"kind": "section", "a": "LATEST FROM CHAMOLI"}, dp(30)),
        ]
        items = self.visible(fresh(self.cache.get("home", [])))
        msg = ("No connection. Tap refresh." if err and not items else
               "No Chamoli news in the last 24 hours.")
        return rows + news_rows(items, msg)

    def render_home(self, err=False):
        self.home_rv.data = self.home_rows(err)

    def render_cat(self):
        self.cat_rv.data = news_rows(self.visible(self.cat_items),
                                     self.cat_msg)

    def render_live(self):
        items = self.visible(fresh(self.cache.get("live", [])))
        rows = [row({"kind": "section", "a": self.live_text}, dp(30))]
        self.live_rv.data = rows + news_rows(items,
                                             "No fresh news right now.")

    def render_saved(self):
        self.saved_rv.data = news_rows(
            self.saved, "Nothing saved yet. Tap the star on any news.",
            "star")

    def render_feeds(self):
        self.render_home()
        self.render_cat()
        self.render_live()

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
        self.save_json("cache.json", self.cache)
        try:
            d = self.home_rv.data
            d[1]["d"].update({"t": r[0], "c": r[1], "m": r[2]})
            self.home_rv.refresh_from_data()
        except Exception:
            self.render_home()

    def pick_cat(self, name):
        self.cat = name
        self.paint_pills()
        self.cat_items = []
        self.cat_msg = "Loading..."
        self.render_cat()
        self.load_cat()

    def load_cat(self, *a):
        qs = [(CAT_Q[lg][self.cat] + " when:1d", lg) for lg in self.langs()]
        self.bg(lambda: gather(qs), self.cat_done)

    def cat_done(self, r):
        if r is None:
            self.cat_items = []
            self.cat_msg = "No connection. Tap refresh."
        else:
            self.cat_items = r
            self.cat_msg = "No fresh news in this category."
        self.render_cat()

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
            return
        links = [x["link"] for x in r[:25]]
        self.cache["live"] = r[:25]
        self.live_text = ("UPDATED %s   ·   AUTO REFRESH"
                          % time.strftime("%H:%M"))
        self.save_json("cache.json", self.cache)
        if links == self.live_links:
            try:
                d = self.live_rv.data
                d[0]["d"]["a"] = self.live_text
                self.live_rv.refresh_from_data()
            except Exception:
                pass
            return
        self.live_links = links
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


def start():
    SandeshApp().run()