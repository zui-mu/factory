"""Optional project-owned MySQL instance using an installed MySQL 8 server binary."""
import json,os,secrets,shutil,socket,subprocess,time
from pathlib import Path
import pymysql
from .mysql_store import DATA,raw_connection

def find_mysqld():
    candidates=[os.environ.get('ZY_MYSQLD'),shutil.which('mysqld')]
    for base in (os.environ.get('ProgramFiles','C:/Program Files'),'D:/Program Files'):
        candidates.extend(str(p) for p in sorted(Path(base).glob('MySQL/MySQL Server */bin/mysqld.exe'),reverse=True))
    for path in candidates:
        if path and Path(path).is_file():return Path(path).resolve()
    raise RuntimeError('未找到 MySQL Server。请先安装 MySQL 8.0.16+，或用 ZY_MYSQLD 指定 mysqld.exe 路径。')

def listening(port):
    with socket.socket() as sock:
        sock.settimeout(.3)
        return sock.connect_ex(('127.0.0.1',int(port)))==0

def launch(executable,ini,port,log):
    process=subprocess.Popen([str(executable),'--defaults-file='+str(ini)],
        cwd=ini.parent,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for _ in range(150):
        if listening(port):return process
        if process.poll() is not None:raise RuntimeError('项目 MySQL 启动失败，请查看 '+str(log))
        time.sleep(.2)
    process.terminate()
    raise RuntimeError('项目 MySQL 启动超时，请查看 '+str(log))

def initialize_local(port=3307):
    folder=(DATA/'mysql-local').resolve();admin_file=folder/'admin.json'
    exe=find_mysqld()
    if admin_file.exists():
        admin=json.loads(admin_file.read_text(encoding='utf-8'))
        managed={'folder':'mysql-local','mysqld':str(exe)}
        ensure_local_server(dict(admin,managed_server=managed),check_account=False)
        return admin,managed
    if listening(port):raise RuntimeError('本机端口 '+str(port)+' 已占用；请通过 --mysql-port 指定其他端口。')
    if (folder/'db').exists():raise RuntimeError('发现未完成初始化的 MySQL 目录，请先检查 '+str(folder))
    folder.mkdir(parents=True,exist_ok=True)
    ini=folder/'my.ini';log=folder/'mysql.log'
    # MySQL 8 Windows reads the option file using the native filesystem code page.
    encoding='mbcs' if os.name=='nt' else 'utf-8'
    ini.write_text('[mysqld]\nbasedir='+exe.parent.parent.as_posix()+'\ndatadir='+folder.as_posix()+'/db\nport='+str(port)+'\nbind-address=127.0.0.1\nmysqlx=0\nlog-error='+log.as_posix()+'\n',encoding=encoding)
    result=subprocess.run([str(exe),'--defaults-file='+str(ini),'--initialize-insecure'],
        capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=120)
    if result.returncode:raise RuntimeError('MySQL 初始化失败，请查看 '+str(log))
    process=launch(exe,ini,port,log)
    admin={'host':'127.0.0.1','port':port,'user':'root','password':secrets.token_urlsafe(30)}
    try:
        with pymysql.connect(host='127.0.0.1',port=port,user='root',password='',autocommit=True) as c:
            with c.cursor() as q:q.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s",(admin['password'],))
        admin_file.write_text(json.dumps(admin,indent=2),encoding='utf-8')
    except BaseException:
        process.terminate();process.wait(timeout=10);raise
    return admin,{'folder':'mysql-local','mysqld':str(exe)}

def ensure_local_server(config,check_account=True):
    managed=config.get('managed_server')
    if not managed:return
    folder=(DATA/managed['folder']).resolve()
    if DATA.resolve() not in folder.parents:raise RuntimeError('项目 MySQL 数据目录必须位于 data 内')
    if config['host']!='127.0.0.1':raise RuntimeError('项目 MySQL 实例仅支持本机连接')
    if not listening(config['port']):
        executable=Path(managed.get('mysqld',''))
        if not executable.is_file():executable=find_mysqld()
        # Refresh paths if the complete project directory has been moved locally.
        ini=folder/'my.ini';log=folder/'mysql.log'
        ini.write_text('[mysqld]\nbasedir='+executable.parent.parent.as_posix()+'\ndatadir='+folder.as_posix()+'/db\nport='+str(config['port'])+'\nbind-address=127.0.0.1\nmysqlx=0\nlog-error='+log.as_posix()+'\n',encoding='mbcs' if os.name=='nt' else 'utf-8')
        launch(executable,ini,config['port'],log)
    if check_account:
        with raw_connection(config) as c:
            with c.cursor() as q:q.execute('SELECT 1')

def stop_local():
    file=DATA/'mysql-local/admin.json'
    admin=json.loads(file.read_text(encoding='utf-8'))
    with pymysql.connect(**admin,autocommit=True) as c:
        with c.cursor() as q:q.execute('SHUTDOWN')
    print('项目 MySQL 已停止；下次运行 start.bat 会自动启动。')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='管理项目专用 MySQL 实例')
    parser.add_argument('--stop',action='store_true',required=True)
    parser.parse_args();stop_local()
