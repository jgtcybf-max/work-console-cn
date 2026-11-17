"""Loopback task relay. Commands only reach the explicitly bound open app page."""
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit

HOST='127.0.0.1:'+os.environ.get('WORK_CONSOLE_PORT','18765')
ORIGIN='http://'+HOST
TOKEN_PATH=Path(__file__).resolve().parent/'relay-token.txt'
METHODS=frozenset({'status','list_tasks','get_task','list_projects','list_tags','create_task','update_task','complete_task'})

class RelayError(Exception):
    def __init__(self,message,code='RELAY_ERROR'):
        super().__init__(message);self.code=code

class Relay:
    def __init__(self,lease_seconds=25,call_timeout=30,poll_seconds=10):
        self.condition=threading.Condition()
        self.lease_seconds=lease_seconds;self.call_timeout=call_timeout;self.poll_seconds=poll_seconds
        self.session_id=None;self.page_id=None;self.seen=0;self.metadata={};self.commands={}

    def _online(self):return bool(self.session_id and time.monotonic()-self.seen<self.lease_seconds)
    def _session(self,session_id):
        if not self._online() or not secrets.compare_digest(str(session_id),self.session_id or ''):
            raise RelayError('当前页面任务连接已失效，请重新连接。','SESSION_EXPIRED')
    def connect(self,page_id,metadata,takeover=False):
        if not isinstance(page_id,str) or not 8<=len(page_id)<=100:
            raise RelayError('页面标识无效。','INVALID_REQUEST')
        with self.condition:
            if self._online() and self.page_id!=page_id and not takeover:
                raise RelayError('另一个工作总台页面正在连接；请点击当前页面的“Codex任务连接”后明确切换。','PAGE_ALREADY_CONNECTED')
            if self.page_id!=page_id or not self._online():
                for command in self.commands.values():
                    if not command['done']:
                        command.update(done=True,error='连接页面已切换，请先读取当前任务状态。',code='OUTCOME_UNKNOWN' if command['dispatched'] else 'SESSION_CHANGED')
                self.session_id=secrets.token_urlsafe(32)
            self.page_id=page_id;self.metadata=self._metadata(metadata);self.seen=time.monotonic()
            self.condition.notify_all()
            return {'connected':True,'sessionId':self.session_id,'version':'2.0.0'}

    @staticmethod
    def _metadata(value):
        if not isinstance(value,dict):return {}
        return {key:value[key] for key in ['language','tasks','projects','title','path'] if key in value}

    def next(self,session_id,metadata):
        with self.condition:
            self._session(session_id);self.metadata=self._metadata(metadata);self.seen=time.monotonic()
            deadline=time.monotonic()+self.poll_seconds
            while True:
                self._session(session_id)
                for identifier,command in self.commands.items():
                    if not command['done'] and not command['dispatched']:
                        command['dispatched']=True
                        self.seen=time.monotonic()
                        return {'command':{'id':identifier,'method':command['method'],'args':command['args']}}
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    self.seen=time.monotonic();return {'command':None}
                self.condition.wait(remaining)

    def result(self,session_id,identifier,ok,result=None,error=None):
        with self.condition:
            self._session(session_id);self.seen=time.monotonic()
            command=self.commands.get(identifier)
            if command is None:return {'accepted':False,'reason':'expired'}
            if command['done']:return {'accepted':False,'reason':'already-settled'}
            if not command['dispatched']:raise RelayError('请求尚未发送到页面。','INVALID_REQUEST')
            command.update(done=True,result=result,error=None if ok else str(error or '页面任务操作失败。'),code='PAGE_ERROR')
            self.condition.notify_all();return {'accepted':True}

    def call(self,method,args):
        if method not in METHODS:raise RelayError('不支持的任务操作。','METHOD_NOT_ALLOWED')
        if not isinstance(args,dict):raise RelayError('参数必须为对象。','INVALID_REQUEST')
        with self.condition:
            if method=='status':return {**self.metadata,'connected':self._online(),'version':'2.0.0','transport':'local-open-page'}
            if not self._online():raise RelayError('工作总台离线，请先打开工作总台页面。','OFFLINE')
            # Bound memory after earlier timed-out dispatches; never redispatch them.
            self.commands={key:value for key,value in self.commands.items() if not value['done']}
            identifier=secrets.token_urlsafe(20)
            command={'method':method,'args':args,'done':False,'dispatched':False,'result':None,'error':None}
            self.commands[identifier]=command;self.condition.notify_all()
            deadline=time.monotonic()+self.call_timeout
            while not command['done']:
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    self.commands.pop(identifier,None)
                    if command['dispatched']:raise RelayError('页面操作结果未知，请先读取状态；不要重复提交。','OUTCOME_UNKNOWN')
                    raise RelayError('等待总台页面超时；请求未执行。','TIMEOUT_NOT_DISPATCHED')
                self.condition.wait(remaining)
            self.commands.pop(identifier,None)
            if command['error']:raise RelayError(command['error'],command.get('code','PAGE_ERROR'))
            return command['result']

RELAY=Relay()
_token_lock=threading.Lock()
def token():
    with _token_lock:
        if not TOKEN_PATH.exists():
            try:
                with TOKEN_PATH.open('x',encoding='ascii') as f:f.write(secrets.token_urlsafe(48))
            except FileExistsError:pass
        return TOKEN_PATH.read_text(encoding='ascii').strip()

def _reply(handler,status,payload):
    body=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf8')
    handler.send_response(status);handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Cache-Control','no-store');handler.send_header('Content-Length',str(len(body)))
    handler.end_headers()
    try:handler.wfile.write(body)
    except (BrokenPipeError,ConnectionResetError):pass

def route(handler):
    """Handle the four /tao-api POST routes; return False for other paths."""
    path=urlsplit(handler.path).path
    if not path.startswith('/tao-api/'):return False
    try:
        if handler.client_address[0]!='127.0.0.1' or handler.headers.get('Host')!=HOST:
            raise RelayError('仅允许本机工作总台。','FORBIDDEN')
        if path not in ['/tao-api/connect','/tao-api/next','/tao-api/result','/tao-api/call']:
            raise RelayError('接口不存在。','NOT_FOUND')
        if path=='/tao-api/call':
            if handler.headers.get('Origin') not in (None,ORIGIN):raise RelayError('来源不允许。','FORBIDDEN')
            if not hmac.compare_digest(handler.headers.get('Authorization',''),'Bearer '+token()):
                raise RelayError('本机连接令牌无效。','FORBIDDEN')
        elif handler.headers.get('Origin')!=ORIGIN:
            raise RelayError('必须从工作总台当前页面连接。','FORBIDDEN')
        if not handler.headers.get('Content-Type','').lower().startswith('application/json'):
            raise RelayError('需要 JSON 请求。','INVALID_REQUEST')
        length=int(handler.headers.get('Content-Length','0'))
        if not 0<length<=2*1024*1024:raise RelayError('请求大小无效。','INVALID_REQUEST')
        data=json.loads(handler.rfile.read(length))
        if not isinstance(data,dict):raise RelayError('需要 JSON 对象。','INVALID_REQUEST')
        if path=='/tao-api/connect':result=RELAY.connect(data.get('pageId'),data.get('metadata',{}),data.get('takeover') is True)
        elif path=='/tao-api/next':result=RELAY.next(data.get('sessionId'),data.get('metadata',{}))
        elif path=='/tao-api/result':result=RELAY.result(data.get('sessionId'),data.get('id'),data.get('ok') is True,data.get('result'),data.get('error'))
        else:result=RELAY.call(data.get('method'),data.get('args',{}))
        _reply(handler,200,{'ok':True,'result':result})
    except RelayError as e:_reply(handler,403 if e.code=='FORBIDDEN' else 409,{'ok':False,'error':str(e),'code':e.code})
    except (ValueError,TypeError,json.JSONDecodeError):_reply(handler,400,{'ok':False,'error':'请求格式无效。','code':'INVALID_REQUEST'})
    return True
