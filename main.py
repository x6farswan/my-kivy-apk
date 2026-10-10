from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
import urllib.request
import json

class NewsApp(App):
    def build(self):
        self.title = "Daily News Feeds"
        root = ScrollView()
        layout = BoxLayout(orientation='vertical', size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        try:
            url = "https://hacker-news.firebaseio.com/v0/topstories.json?print=json"
            req = urllib.request.urlopen(url)
            story_ids = json.loads(req.read().decode())[:10]

            for s_id in story_ids:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{s_id}.json?print=json"
                item_req = urllib.request.urlopen(item_url)
                item_data = json.loads(item_req.read().decode())
                title = item_data.get('title', 'No Title')
                lbl = Label(text=f"• {title}", size_hint_y=None, height=100, text_size=(350, None))
                layout.add_widget(lbl)
        except Exception as e:
            layout.add_widget(Label(text=f"Error: {str(e)}", size_hint_y=None, height=100))

        root.add_widget(layout)
        return root

if __name__ == '__main__':
    NewsApp().run()
