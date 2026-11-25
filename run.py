"""Start the factory platform, with an optional browser and 3D workshop."""
import argparse,atexit,sys,threading,time,webbrowser,signal,json,urllib.request,socket
from backend.db import initialize,DatabaseError
from backend.federation import Federation
from backend.server import create_server
from backend.live import LiveRuntime
from backend.mysql_store import settings
from backend.local_mysql import ensure_local_server

def server_health(url,timeout=.75):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url+"/api/health",timeout=timeout) as response:
            health=json.load(response)
    except (OSError,ValueError):
        return None
    return health if isinstance(health,dict) else None

def open_client(url,workshop,health):
    client=url
    if workshop:
        if health.get("webgl_ready") is True:
            client=url+"/?view=unity#workshop"
            print("Unity WebGL 已就绪，与网页共用服务地址。",flush=True)
        else:
            client=url+"/#workshop"
            print("Unity WebGL 构建文件未齐，先打开车间示意图。可从 Unity 中导出网页三维程序。",flush=True)
    print("浏览器入口:",client,flush=True)
    try:
        opened=webbrowser.open(client)
    except webbrowser.Error:
        opened=False
    if not opened:print("请在浏览器中手动打开上面的地址。",flush=True)

def open_when_ready(url,workshop):
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        health=server_health(url)
        if health and health.get("ok") is True and health.get("name")=="质因云联":
            open_client(url,workshop,health)
            return
        time.sleep(.2)
    print("网页服务就绪检查超时，请检查启动窗口后手动打开",url,flush=True)

def main():
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser(description="全景可视化数字工厂")
    p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",type=int,default=8765);p.add_argument("--open",action="store_true")
    p.add_argument("--workshop",action="store_true",help="配合 --open 打开内嵌三维车间")
    args=p.parse_args()
    url="http://127.0.0.1:%s"%args.port
    try:
        ensure_local_server(settings())
        initialize()
    except (DatabaseError,RuntimeError) as error:
        print("MySQL 未就绪，请检查 MySQL 服务和 data/mysql.json，首次使用请运行 setup.bat。")
        if isinstance(error,DatabaseError):print("MySQL 错误编号:",error.args[0])
        else:print(str(error))
        return 1
    try:server=create_server(args.host,args.port,None)
    except OSError:
        running=server_health(url,timeout=2)
        if running and running.get("ok") is True and running.get("name")=="质因云联":
            if running.get("version")!="1.5.0" or (args.workshop and "webgl_ready" not in running):
                print("检测到旧版服务仍在运行。请在原启动窗口按 Ctrl+C 停止服务，再重新双击启动脚本。")
                return 1
            if args.host=="0.0.0.0":
                print("当前端口已有平台服务，本次未启动新的局域网服务。")
                print("请先停止该端口的旧服务再运行 start-lan.bat，或指定其他端口：--port 8767")
                return 1
            print("全景可视化数字工厂已在运行：",url)
            if args.open:open_client(url,args.workshop,running)
            return 0
        print("端口被占用，请关闭已有窗口或使用 --port 8766");return 1
    port=server.server_port
    url="http://127.0.0.1:%s"%port
    try:fed=Federation();server.federation=fed
    except Exception:
        server.server_close();raise
    atexit.register(fed.close)
    live=LiveRuntime();atexit.register(live.close)
    def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    print("\n全景可视化数字工厂\n")
    print("访问地址:",url)
    if args.host=="0.0.0.0":
        for address in sorted(set(socket.gethostbyname_ex(socket.gethostname())[2])):
            if not address.startswith("127."):print("手机同一局域网访问：http://%s:%s"%(address,port))
    print("演示账号: admin / Zyyl@2026")
    print("保持此窗口运行。Ctrl+C 停止服务。内置数据为模拟数据。\n",flush=True)
    if args.open:threading.Thread(target=open_when_ready,args=(url,args.workshop),daemon=True).start()
    try:server.serve_forever(poll_interval=.2)
    finally:server.server_close();live.close();fed.close();atexit.unregister(fed.close);atexit.unregister(live.close)
    return 0
if __name__=="__main__":sys.exit(main())
