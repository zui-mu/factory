"""Local stub verifies the optional external model adapter without network egress."""
import unittest,os,json,threading
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from backend.assistant import optional_model

class ProviderTests(unittest.TestCase):
    def test_optional_adapter_and_safe_failure(self):
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                content=json.dumps({"choices":[{"message":{"content":"请先核对现场温控记录，再安排复检。"}}]},ensure_ascii=False).encode()
                self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(content)));self.end_headers();self.wfile.write(content)
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch.dict(os.environ,{"ZY_AI_URL":"http://127.0.0.1:%s/chat/completions"%server.server_port,"ZY_AI_MODEL":"local-test","ZY_AI_KEY":"stub"}):
                text=optional_model("该怎么排查？",{"sample_count":1800,"risk_difference":.2},[])
                self.assertIn("复检",text)
                body=received[0];self.assertEqual(body["model"],"local-test")
                self.assertNotIn("password",json.dumps(body))
                self.assertIn("1800",body["messages"][-1]["content"])
            with patch.dict(os.environ,{"ZY_AI_URL":"http://untrusted.example/api","ZY_AI_MODEL":"test"}):
                with self.assertRaises(ValueError):optional_model("问题",{},[])
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
