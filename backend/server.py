import json,time,secrets,threading,mimetypes,traceback,csv,io,socket,re
from pathlib import Path
from http import cookies
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs,unquote
from .db import ROOT,DATA,connect,one,rows,check_password,audit,now,IntegrityError,DatabaseError
from .api import dispatch,ApiError,role,get_entity,scope

WRITE_LOCK=threading.RLock()
LOGIN_ATTEMPTS={}
WEB=(ROOT/"frontend").resolve()
def create_server(host,port,federation):
    class PlatformHTTPServer(ThreadingHTTPServer):
        # Windows SO_REUSEADDR can allow a second live listener on the same port.
        allow_reuse_address=not hasattr(socket,"SO_EXCLUSIVEADDRUSE")
        def server_bind(self):
            if hasattr(socket,"SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            super().server_bind()
    class Handler(BaseHTTPRequestHandler):
        server_version="ZhiyinYunlian/1.0"
        def log_message(self,fmt,*args):pass
        def response(self,data,status=200,ctype="application/json; charset=utf-8",headers=None,*,allow_wasm=False):
            body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if ctype.startswith("application/json") else data
            self.send_response(status)
            self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(body)))
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("X-Frame-Options","DENY")
            self.send_header("Referrer-Policy","same-origin")
            self.send_header("Cache-Control","no-store" if self.path.startswith("/api") else "no-cache")
            script_src="'self' 'wasm-unsafe-eval'" if allow_wasm else "'self'"
            self.send_header("Content-Security-Policy",f"default-src 'self'; script-src {script_src}; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
            for k,v in (headers or {}).items():self.send_header(k,v)
            self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
        def authenticate(self):
            cookie=cookies.SimpleCookie()
            try:cookie.load(self.headers.get("Cookie",""))
            except cookies.CookieError:raise ApiError("请先登录",401)
            token=cookie.get("zy_session")
            if not token:raise ApiError("请先登录",401)
            with connect() as c:
                u=one(c,"SELECT u.id,u.username,u.name,u.role,u.factory_id,s.csrf,s.token FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.active=1",(token.value,time.time()))
            if not u:raise ApiError("登录已过期，请重新登录",401)
            return u
        def read_body(self):
            try:size=int(self.headers.get("Content-Length","0"))
            except ValueError:raise ApiError("无效的请求长度")
            if size<0 or size>4*1024*1024:raise ApiError("请求内容过大",413)
            try:b=json.loads(self.rfile.read(size)) if size else {}
            except (ValueError,UnicodeDecodeError):raise ApiError("请求必须为有效 JSON")
            if not isinstance(b,dict):raise ApiError("请求必须为 JSON 对象")
            return b
        def process(self):
            parsed=urlsplit(self.path);path=unquote(parsed.path);params={k:v[-1] for k,v in parse_qs(parsed.query).items()}
            if self.command=="GET" and path=="/api/health":
                return self.response({"ok":True,"name":"质因云联","version":"1.5.0","database":"MySQL"})
            if not path.startswith("/api/"):
                if self.command!="GET":raise ApiError("不支持的方法",405)
                file=(WEB/("index.html" if path=="/" else path.lstrip("/"))).resolve()
                if WEB not in file.parents or not file.is_file():raise ApiError("文件不存在",404)
                ctype="application/wasm" if file.suffix.lower()==".wasm" else mimetypes.guess_type(str(file))[0] or "application/octet-stream"
                return self.response(file.read_bytes(),ctype=ctype,allow_wasm=path in ("/","/index.html"))
            body=self.read_body() if self.command=="POST" else {}
            if self.command=="POST":
                origin=self.headers.get("Origin")
                if origin and origin not in ("http://"+self.headers.get("Host",""),"https://"+self.headers.get("Host","")):raise ApiError("请求来源不匹配",403)
            if path=="/api/login" and self.command=="POST":
                key=self.client_address[0];failed=[t for t in LOGIN_ATTEMPTS.get(key,[]) if time.time()-t<60]
                if len(failed)>=12:raise ApiError("尝试过于频繁，请一分钟后重试",429)
                username=body.get("username","");password=body.get("password","")
                if not isinstance(username,str) or not isinstance(password,str) or len(username)>100 or len(password)>300:raise ApiError("账号或密码格式无效")
                with connect() as c:
                    u=one(c,"SELECT * FROM users WHERE username=? AND active=1",(username,))
                    if not u or not check_password(password,u["password"]):
                        LOGIN_ATTEMPTS[key]=failed+[time.time()];raise ApiError("账号或密码不正确",401)
                    LOGIN_ATTEMPTS.pop(key,None)
                    token=secrets.token_urlsafe(36);csrf=secrets.token_urlsafe(24)
                    c.execute("DELETE FROM sessions WHERE expires<?",(time.time(),))
                    c.execute("INSERT INTO sessions VALUES(?,?,?,?)",(token,u["id"],csrf,time.time()+8*3600))
                    audit(c,u,"登录","用户")
                    result={k:u[k] for k in ("id","username","name","role","factory_id")};result["csrf"]=csrf
                return self.response(result,headers={"Set-Cookie":"zy_session="+token+"; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800"})
            user=self.authenticate()
            if path=="/api/me" and self.command=="GET":
                return self.response({k:v for k,v in user.items() if k!="token"})
            if self.command=="POST" and not secrets.compare_digest(self.headers.get("X-CSRF-Token",""),user["csrf"]):raise ApiError("请求校验失败，请刷新页面",403)
            if path=="/api/logout" and self.command=="POST":
                with connect() as c:
                    c.execute("DELETE FROM sessions WHERE token=?",(user["token"],))
                    audit(c,user,"退出登录","用户")
                return self.response({"ok":True},headers={"Set-Cookie":"zy_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
            if path.startswith("/api/media/") and self.command=="GET":
                name=path.rsplit("/",1)[1]
                if name not in ("factory.mp4","liushuixian.mp4","liushuixiantwo.mp4"):raise ApiError("视频不存在",404)
                file=ROOT/"backend"/"assets"/name
                if not file.is_file():raise ApiError("视频素材缺失",404)
                size=file.stat().st_size;start=0;end=size-1;status=200;headers={"Accept-Ranges":"bytes"}
                requested=self.headers.get("Range")
                if requested:
                    match=re.fullmatch(r"bytes=(\d*)-(\d*)",requested)
                    if not match or not any(match.groups()):return self.response(b"",416,"video/mp4",{"Content-Range":"bytes */"+str(size)})
                    if match[1]:start=int(match[1]);end=min(int(match[2]),size-1) if match[2] else size-1
                    else:start=max(0,size-int(match[2]))
                    if start>end or start>=size:return self.response(b"",416,"video/mp4",{"Content-Range":"bytes */"+str(size)})
                    status=206;headers["Content-Range"]="bytes %s-%s/%s"%(start,end,size)
                with file.open("rb") as f:f.seek(start);content=f.read(end-start+1)
                return self.response(content,status,"video/mp4",headers)
            if path.startswith("/api/photos/") and self.command=="GET":
                with connect() as c:
                    a=one(c,"SELECT * FROM attachments WHERE id=?",(path.rsplit("/",1)[1],))
                    if not a:raise ApiError("照片不存在",404)
                    t=get_entity(c,user,"tasks",a["task_id"])
                    if user["role"]=="operator" and t["assignee"]!=user["id"]:raise ApiError("无权访问",403)
                return self.response((DATA/"uploads"/a["filename"]).read_bytes(),ctype=a["mime"])
            if path=="/api/export" and self.command=="GET":
                kind=params.get("kind","quality")
                if kind not in ("orders","quality","tasks","materials","audit"):raise ApiError("不支持的导出类型")
                result=dispatch("GET","/api/"+kind,params,{},user,self.server.federation)
                out=io.StringIO(newline="");writer=csv.writer(out)
                if result:
                    fields=list(result[0]);writer.writerow(fields)
                    for r in result:
                        vals=[]
                        for k in fields:
                            v=r.get(k,"")
                            if isinstance(v,str) and v.startswith(("=","+","-","@","\t","\r")):v="'"+v
                            vals.append(v)
                        writer.writerow(vals)
                return self.response(("\ufeff"+out.getvalue()).encode(),ctype="text/csv; charset=utf-8",headers={"Content-Disposition":'attachment; filename="'+kind+'.csv"'})
            if self.command=="POST":
                with WRITE_LOCK:
                    idem=self.headers.get("Idempotency-Key","")[:128]
                    if idem:
                        with connect() as c:saved=one(c,"SELECT response FROM idempotency WHERE user_id=? AND `key`=? AND path=?",(user["id"],idem,path))
                        if saved:return self.response(json.loads(saved["response"]))
                    result=dispatch(self.command,path,params,body,user,self.server.federation)
                    if idem:
                        with connect() as c:c.execute("INSERT IGNORE INTO idempotency VALUES(?,?,?,?,?)",(user["id"],idem,path,json.dumps(result,ensure_ascii=False),now()))
            else:result=dispatch(self.command,path,params,body,user,self.server.federation)
            return self.response(result)
        def handle_request(self):
            try:self.process()
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
            except ApiError as e:self.response({"error":e.message},e.status)
            except (ValueError,TypeError,KeyError) as e:self.response({"error":"参数不正确，请检查输入"},400)
            except IntegrityError:self.response({"error":"记录冲突或关联数据不正确，请刷新后重试"},409)
            except DatabaseError:
                traceback.print_exc();self.response({"error":"数据库连接或事务失败，请检查 MySQL 服务后重试"},503)
            except Exception:
                traceback.print_exc();self.response({"error":"服务处理失败，请查看运行日志"},500)
        do_GET=handle_request
        do_POST=handle_request
    server=PlatformHTTPServer((host,port),Handler);server.daemon_threads=True;server.federation=federation
    return server
