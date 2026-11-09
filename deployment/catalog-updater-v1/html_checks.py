from html.parser import HTMLParser

class Indexability(HTMLParser):
    def __init__(self):
        super().__init__(); self.noindex=False; self.canonicals=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta' and a.get('name','').lower() in ('robots','googlebot'):
            self.noindex |= any(v in a.get('content','').lower().replace(',',' ').split() for v in ('noindex','none'))
        if tag=='link' and 'canonical' in a.get('rel','').lower().split(): self.canonicals.append(a.get('href'))

