import importlib.util
import io
import json
from pathlib import Path
import threading
import time
import unittest

APP=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('console_relay',APP/'console_relay.py')
relay=importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)

class RelayTests(unittest.TestCase):
    def setUp(self):self.r=relay.Relay(lease_seconds=1,call_timeout=.08,poll_seconds=.02)
    def test_offline_and_whitelist(self):
        self.assertFalse(self.r.call('status',{})['connected'])
        with self.assertRaisesRegex(relay.RelayError,'离线'):self.r.call('list_tasks',{})
        with self.assertRaisesRegex(relay.RelayError,'不支持'):self.r.call('delete_task',{})
    def test_one_page_and_explicit_takeover(self):
        a=self.r.connect('test-page-a',{'language':'zh'})
        with self.assertRaisesRegex(relay.RelayError,'另一个'):self.r.connect('test-page-b',{})
        b=self.r.connect('test-page-b',{},takeover=True)
        self.assertNotEqual(a['sessionId'],b['sessionId'])
        with self.assertRaisesRegex(relay.RelayError,'失效'):self.r.next(a['sessionId'],{})
    def test_command_result_and_metadata(self):
        s=self.r.connect('test-page-a',{'language':'zh','tasks':18})['sessionId']
        out=[]
        t=threading.Thread(target=lambda:out.append(self.r.call('list_tasks',{})))
        t.start();command=self.r.next(s,{'language':'zh','tasks':18})['command']
        self.r.result(s,command['id'],True,[{'id':'kept'}]);t.join()
        self.assertEqual(out,[[{'id':'kept'}]])
        self.assertEqual(self.r.call('status',{})['tasks'],18)
    def test_queued_timeout_removes_effect(self):
        s=self.r.connect('test-page-a',{})['sessionId']
        with self.assertRaisesRegex(relay.RelayError,'超时'):self.r.call('create_task',{'title':'must-not-run'})
        self.assertIsNone(self.r.next(s,{})['command'])
    def test_dispatched_timeout_is_uncertain(self):
        s=self.r.connect('test-page-a',{})['sessionId'];errors=[]
        def caller():
            try:self.r.call('create_task',{'title':'example'})
            except relay.RelayError as e:errors.append(e.code)
        t=threading.Thread(target=caller);t.start();self.r.next(s,{});t.join()
        self.assertEqual(errors,['OUTCOME_UNKNOWN'])
    def test_request_origin_host_and_token(self):
        class Handler:
            client_address=('127.0.0.1',1234)
            path='/tao-api/connect'
            headers={'Host':'127.0.0.1:18765','Origin':'https://evil.example','Content-Type':'application/json','Content-Length':'2'}
            rfile=io.BytesIO(b'{}');wfile=io.BytesIO()
            def send_response(self,status):self.status=status
            def send_header(self,*args):pass
            def end_headers(self):pass
        h=Handler();self.assertTrue(relay.route(h));self.assertEqual(h.status,403)
        h=Handler();h.headers={**h.headers,'Host':'evil.example','Origin':'http://127.0.0.1:18765'};h.wfile=io.BytesIO();relay.route(h);self.assertEqual(h.status,403)
        h=Handler();h.path='/tao-api/call';h.headers={**h.headers,'Origin':'http://127.0.0.1:18765'};h.wfile=io.BytesIO();relay.route(h);self.assertEqual(h.status,403)

if __name__=='__main__':unittest.main()
