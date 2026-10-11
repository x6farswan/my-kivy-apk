import traceback
try:
    import newsapp
    newsapp.start()
except Exception:
    err = traceback.format_exc()
    from kivy.app import App
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    class Err(App):
        def build(self):
            sv = ScrollView()
            lb = Label(text=err, size_hint_y=None, font_size='11sp',
                       halign='left', valign='top')
            lb.bind(width=lambda i, w: setattr(i, 'text_size', (w - 20, None)))
            lb.bind(texture_size=lambda i, s: setattr(i, 'height', s[1]))
            sv.add_widget(lb)
            return sv

    Err().run()
