"""Local-only web host. No media scan, job execution, or filesystem write API."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import mimetypes,os,sys,threading,webbrowser
from urllib.parse import urlsplit,unquote
from console_relay import route,token

ROOT=Path(__file__).resolve().parent
PORT=int(os.environ.get('WORK_CONSOLE_PORT','18765'))
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
    def do_POST(self):
        if not route(self):self.send_error(404)
    def translate_path(self,path):
        if unquote(urlsplit(path).path)=='/ngsw-worker.js':return str(ROOT/'web'/'safety-worker.js')
        return super().translate_path(path)
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()
    def log_message(self,*args):pass

if __name__=='__main__':
    if not (ROOT/'web'/'.work-console-build').exists():raise SystemExit('请先运行 python install.py')
    mimetypes.add_type('text/javascript','.js');token()
    print('工作总台 http://127.0.0.1:'+str(PORT),flush=True)
    if '--open' in sys.argv:threading.Timer(0.5,lambda:webbrowser.open('http://127.0.0.1:'+str(PORT)+'/#/boards/TAO_CONSOLE')).start()
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
