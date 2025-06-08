import html
import os
import re
from urllib.parse import quote
import pandas as pd
from .core import NodeId, Metadata
from typing import Any, Callable

class Html:
    def __init__(self, string):
        self.string = string
    
    def __str__(self):
        return self.string

def _read_default_css():
    pandas_csv_path = os.path.join(os.path.dirname(__file__), 'styles', 'default.css')
    with open(pandas_csv_path, 'r') as file:
        return file.read()
    
default_css = _read_default_css()

def render_html(res: Any, metadata: Metadata, href_eval: Callable[[NodeId], str], href_download_csv: Callable[[NodeId], str]) -> str:
    if type(res) is Html:
        res = _inject_details(str(res), _details_html(metadata, href_eval))
        return res
    else:
        return f"""
        <html>
        <head>
            <title>{metadata.node_id.id}</title>
            <style type='text/css'>
            {default_css}
            </style>
        </head>
        <body>
        {_obj_to_html(res, metadata.node_id, href_download_csv)}
        {_details_html(metadata, href_eval)}
        </body></html>
        """

def _inject_details(html, details_html):
    needs_to_append = []
    for tag in ['</body>','</html>']:
        if re.search(tag, html, re.IGNORECASE):
            html = re.sub(tag, '', html, flags=re.IGNORECASE)
            needs_to_append += tag
    return html + details_html + ''.join(needs_to_append)

def _details_html(metadata: Metadata, href_eval: Callable[[NodeId], str]):
    return f"""
    <div id=details_toggle style="cursor:pointer;position:fixed;bottom:0;right:0;font-size:50%;border:1px solid gray;">memoizer details</div>
    <div id=details style="display:none">
    <iframe style="width:100%" height="1000px" frameborder=0 srcdoc='""" + html.escape(_details_content_html(metadata, href_eval)) + """'></iframe>
    </div>
    <script>
        (function(){
            var toggleButton = document.getElementById("details_toggle"),
                toggleDiv = document.getElementById("details");
            function toggle(){
                if (toggleDiv.style.display ==="none") {
                    toggleDiv.style.display = "block";
                    toggleButton.innerText = "hide details";
                } else {
                    toggleDiv.style.display = "none";
                    toggleButton.innerText = "memoizer details";
                }
            };
            toggleButton.addEventListener("click", toggle);
            if(window.location.hash.includes('details')) toggle();
        })();
    </script>
    """

def _details_content_html(metadata: Metadata, href_eval: Callable[[NodeId], str]):
    return """
    <html>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/styles/lightfair.min.css" integrity="sha512-7XR4V1+vHjARBIMw1snyPoLn7d9U9gjBUhGAXVMRXRvXpfyjfmHiAnwxc9eP4imeh0gr7cBvDg9XO06OBj3+jA==" crossorigin="anonymous" referrerpolicy="no-referrer" />
        <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js" integrity="sha512-6yoqbrcLAHDWAdQmiRlHG4+m0g/CT/V9AGyxabG8j7Jk8j3r3K6due7oqpiRMZqcYe9WM2gPcaNNxnl2ux+3tA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/languages/python.min.js" integrity="sha512-Q4s1KlNQrISoyXajz4f6ueVt5h4BPLEkAQ10SjTktC/G5cgEuGbfPLFx/1Q2VsK0cZ146upkwvAjfVLVa4EStQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script>hljs.initHighlightingOnLoad();</script>
        <style type="text/css">
        td { vertical-aligh: top; }
        </style>
    <head>
    </head>""" + f"""
    <body>
        <h3>Memoizer</h3>
        <table>
        <tr><td>node id</td><td><code>{metadata.node_id.id}</code></td></tr>
        <tr><td>return type</td><td><code>{metadata.return_type}</code></td></tr>
        <tr><td>source</td><td><div><pre><code class="python" style="position: relative; top: -4px; padding: 0px">{html.escape(metadata.source)}</code></pre></div></td></tr>
        {'' if len(metadata.children)==0 else '<tr><td>children</td><td>' + '<br>'.join(['<code><a href="'+href_eval(_id)+'#details" target="_top">'+_id.id+'</a></code>' for _id in metadata.children]) + '</td></tr>'}
        <tr><td>start time</td><td><code>{metadata.start_time.isoformat()}</code></td></tr>
        <tr><td>end time</td><td><code>{metadata.end_time.isoformat()}</code></td></tr>
        <tr><td>cpu time</td><td><code>{"{:.3f}".format(metadata.cpu_time_sec)}</code></td></tr>
        </table>
    </body>
    </html>
    """

def _obj_to_html(obj, node_id: NodeId, href_download_csv: Callable[[NodeId], str]) -> str:
    assert type(node_id) is NodeId
    res = f"<div><code><pre>{node_id.id}</pre></code></div>"
    assert type(obj) is not Html
    pd_max_rows = 10000
    if type(obj) is pd.Series:
        obj = obj.to_frame()
    if type(obj) is pd.DataFrame:
        res += f'<div>{len(obj)} total rows'
        if len(obj) > pd_max_rows:
            res += f', only showing the top {pd_max_rows} rows'
            obj = obj.head(pd_max_rows)
        res += '. '
        download_url = href_download_csv(node_id)
        if download_url is not None and download_url != "":
            res += f'<a href="{download_url}">download as csv</a>'
        res += '</div>'
        res += obj.to_html()
    else:
        res += f"<code><pre>{html.escape(repr(obj))}</pre></code>"
    return res