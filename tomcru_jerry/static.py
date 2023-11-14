import os
import re
from collections import defaultdict

import jinja2
import pynliner
import htmlmin
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, send_from_directory
from werkzeug.routing import BaseConverter


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


class StaticWebsite:
    def __init__(self, index, path, static_files):

        template_folder, static_folder = self.get_paths(path)

        self.index = index if index is not None else 'index.html'
        self.template_folder = template_folder if template_folder is not None else 'templates/'
        self.static_folder = static_folder if static_folder is not None else 'public/'
        self.template: jinja2.Template = None
        self.pyl: pynliner.Pynliner = None
        self.args = {}
        self.kept_styles = defaultdict(list)
        self.static_files = static_files

    def get_paths(self, path='webapp'):
        template_folder = os.path.join(path, 'templates')
        static_folder = os.path.join(path, 'public')

        return template_folder,static_folder

    def _get_template(self, beautify=False):
        # render jinja2 template
        template_loader = jinja2.FileSystemLoader(searchpath=self.template_folder)
        template_env = jinja2.Environment(loader=template_loader)

        if not beautify:
            template_env.trim_blocks = True
            template_env.lstrip_blocks = True
            template_env.strip_trailing_newlines = True

        self.template = template_env.get_template(self.index)

    def set_args(self, **args):
        self.args.update(args)

    def render(self, fileto, beautify=False, **args):
        self.args.update(args)

        if self.template is None:
            self._get_template(beautify)

        output = self.template.render(**self.args)
        output = htmlmin.minify(output, remove_empty_space=True)
        # output = output

        with open(fileto+'.html', 'w') as fh:
            fh.write(output)

    def build(self, **kwargs):
        # previews email in Flask (also uses Jinja2)
        self.app = Flask('', static_folder=self.static_folder, template_folder=self.template_folder)
        #self.app.url_map.converters['regex'] = RegexConverter

        pattern = re.compile('('+'|'.join(self.static_files)+'/).*')

        @self.app.route('/', defaults={'path': ''})
        @self.app.route('/<path:path>')
        def _index(path=None):
            if re.match(pattern, path):
                return send_from_directory(self.static_folder, path)

            d = kwargs
            d.update(**request.args)
            return render_template(self.index, **d)

        self.app.config['TEMPLATES_AUTO_RELOAD'] = True
        return self.app

    def run(self, *args, **kwargs):
        return self.app.run(*args, **kwargs)


class Ememail(StaticWebsite):
    def __init__(self, *args, **kwargs):
        super(Ememail, self).__init__(*args, **kwargs)

    def _parse_head(self):
        # removes all elements from head
        self.pyl._get_soup()
        soup: BeautifulSoup = self.pyl.soup
        i = 0

        for _link_css in soup.find_all("link"):
            el = _link_css.extract()

            # read in CSS content
            css_file = el['href']
            if css_file.startswith('/'):
                css_file = css_file[1:]
            with open(os.path.join(self.static_folder, css_file)) as fh:
                css = fh.read()

            # fate of external CSS is either becoming internal or inline:
            if 'as-internal' in el.attrs:
                # internal: re-added later
                self.kept_styles[el.get('as-internal', i)].append(css)
                i+=1
            elif el.get('type') in ('text/css', None):
                # as inline => forward to pynlinter
                self.pyl.with_cssString(css)

        for _link_css in soup.find_all("style"):
            # internal CSS is removed automatically
            if 'as-internal' in _link_css.attrs:
                el = _link_css.extract()
                css = el.contents

                self.kept_styles[_link_css.get('as-internal', i)].append(css)
                i+=1

            # otherwise, style will be removed and parsed by pynlinter

    def _transpile_css(self, pretty=False):
        # forces inline CSS
        out = self.pyl.run()
        soup = self.pyl.soup

        # TODO: strip classes out

        # re-add force-kept internal styles
        for csss in self.kept_styles.values():
            css = ['<style>']
            for _css in csss:
                css.append(_css)
            css.append('</style>')

            soup.head.append(BeautifulSoup('\n'.join(css), 'html.parser'))

        if pretty:
             return soup.prettify(), soup.get_text()
        else:
            return str(soup), soup.get_text()

    def render(self, fileto, pretty=False, quoted_printable=True, **args):
        self.args.update(args)

        if self.template is None:
            self._get_template()
        output = self.template.render(**self.args)
        self.pyl = pynliner.Pynliner().from_string(output)

        # transform template (forced inline CSS)
        self._parse_head()
        output, text = self._transpile_css(pretty=pretty)

        with open(fileto+'.html', 'w') as fh:
            fh.write(output)

        # ordered set from dict keys
        uniquelines = dict.fromkeys(text.split('\n'))
        with open(fileto + '.txt', 'w') as fh:
            fh.write('\n'.join(uniquelines.keys()))
