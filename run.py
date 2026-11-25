"""python run.py --open ; Python 3.9+, MySQL 8.0.16+ and PyMySQL."""
import argparse,atexit,sys,threading,webbrowser,signal,json,urllib.request,socket
from backend.db import initialize,DatabaseError
from backend.federation import Federation
from backend.server import create_server
from backend.live import LiveRuntime
from backend.mysql_store import settings
from backend.local_mysql import ensure_local_server

def main():
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser(description="质因云联 · 智慧工厂平台")
    p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",type=int,default=8765);p.add_argument("--open",action="store_true")
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
        try:
            with urllib.request.urlopen(url+"/api/health",timeout=2) as response:running=json.load(response)
            if running.get("name")=="质因云联":
                if running.get("version")!="1.5.0":
                    print("检测到旧版服务仍在运行（%s），当前代码版本为 1.5.0。"%running.get("version","未知"))
                    print("请在原启动窗口按 Ctrl+C 停止旧服务，再重新启动；仅刷新网页不会更新后台。")
                    return 1
                if args.host=="0.0.0.0":
                    print("当前端口已有平台服务，本次未启动新的局域网服务。")
                    print("请先停止该端口的旧服务再运行 start-lan.bat，或指定其他端口：--port 8767")
                    return 1
                print("质因云联已在运行：",url)
                if args.open:webbrowser.open(url)
                return 0
        except Exception:pass
        print("端口被占用，请关闭已有窗口或使用 --port 8766");return 1
    try:fed=Federation();server.federation=fed
    except Exception:
        server.server_close();raise
    atexit.register(fed.close)
    live=LiveRuntime();atexit.register(live.close)
    def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    print("\n质因云联——从车间感知到生产决策的智慧工厂平台\n")
    print("访问地址:",url)
    if args.host=="0.0.0.0":
        for address in sorted(set(socket.gethostbyname_ex(socket.gethostname())[2])):
            if not address.startswith("127."):print("手机同一局域网访问：http://%s:%s"%(address,args.port))
    print("演示账号: admin / Zyyl@2026")
    print("保持此窗口运行。Ctrl+C 停止服务。内置数据为模拟数据。\n",flush=True)
    if args.open:threading.Timer(.8,lambda:webbrowser.open(url)).start()
    try:server.serve_forever(poll_interval=.2)
    finally:server.server_close();live.close();fed.close();atexit.unregister(fed.close);atexit.unregister(live.close)
    return 0
if __name__=="__main__":sys.exit(main())
