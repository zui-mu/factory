"""Provision new MySQL databases and scoped accounts; never modifies existing schemas/users."""
import argparse,getpass,json,re,secrets,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pymysql
from backend.mysql_store import DATA,connect,identifier
from backend.db import SCHEMA,NODE_SCHEMA
from backend.tools.migrate_sqlite import migrate
from backend.local_mysql import initialize_local,ensure_local_server

def provision(admin,database,source=None):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,45}',database):raise ValueError('数据库名称须为字母开头，最多46个字母、数字或下划线')
    config={k:admin[k] for k in ('host','port')}
    config['database']=database
    config['node_databases']={str(f):database+'_factory_'+str(f) for f in (1,2,3)}
    config['node_users']={}
    names=[database]+list(config['node_databases'].values())
    credentials={k:admin[k] for k in ('host','port','user','password')}
    created=[];users=[];account_host=admin.get('app_host','localhost')
    with pymysql.connect(**credentials,charset='utf8mb4',autocommit=True,connect_timeout=8) as raw:
        with raw.cursor() as q:
            q.execute('SELECT VERSION()');version=q.fetchone()[0]
            numbers=tuple(int(x) for x in version.split('-')[0].split('.')[:3])
            if 'MariaDB' in version or numbers<(8,0,16):raise ValueError('需要 MySQL 8.0.16 或更新版本')
            for name in names:
                q.execute('SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s',(name,))
                if q.fetchone():raise ValueError('数据库已存在，未执行任何覆盖操作：'+name)
            try:
                prefix='zyyl_'+secrets.token_hex(4)
                for factory,name in zip((None,1,2,3),names):
                    q.execute('CREATE DATABASE '+identifier(name)+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin')
                    created.append(name)
                    user=prefix+('_app' if factory is None else '_f'+str(factory));password=secrets.token_urlsafe(30)
                    q.execute('CREATE USER %s@%s IDENTIFIED BY %s',(user,account_host,password));users.append(user)
                    # Escape grant-pattern wildcards so the grant covers exactly this database.
                    q.execute('SELECT @@partial_revokes');partial=bool(q.fetchone()[0])
                    grant_name=name if partial else name.replace('_','\\_')
                    q.execute('GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON `'+grant_name+'`.* TO %s@%s',(user,account_host))
                    dest=config if factory is None else config['node_users'].setdefault(str(factory),{})
                    dest.update(user=user,password=password)
                for factory in (None,1,2,3):
                    with connect(config=config,factory=factory) as c:c.executescript(SCHEMA if factory is None else NODE_SCHEMA)
                report=migrate(Path(source),config) if source else None
                return config,report
            except BaseException:
                for name in reversed(created):q.execute('DROP DATABASE '+identifier(name))
                for user in users:q.execute('DROP USER %s@%s',(user,account_host))
                raise

def main():
    p=argparse.ArgumentParser(description='首次配置 MySQL：创建独立业务库、三节点库及限定权限的账号')
    p.add_argument('--admin-config',type=Path)
    p.add_argument('--database',default='zhiyinyunlian')
    p.add_argument('--source-sqlite',type=Path)
    p.add_argument('--config-output',type=Path,default=DATA/'mysql.json')
    p.add_argument('--local',action='store_true',help='使用已安装的 MySQL 程序，在项目 data 中建立专用实例，无需原 MySQL 密码')
    p.add_argument('--mysql-port',type=int,default=3307)
    args=p.parse_args()
    if args.config_output.exists():
        existing=json.loads(args.config_output.read_text(encoding='utf-8-sig'))
        ensure_local_server(existing)
        with connect(config=existing) as c:c.execute('SELECT 1')
        print('MySQL 已配置，保留现有连接与业务记录。');return
    file=args.admin_config or DATA/'mysql-admin.json'
    managed=None
    if args.local:admin,managed=initialize_local(args.mysql_port)
    elif file.exists():admin=json.loads(file.read_text(encoding='utf-8-sig'))
    else:
        admin={'host':input('MySQL 地址 [127.0.0.1]：').strip() or '127.0.0.1',
               'port':int(input('MySQL 端口 [3306]：').strip() or 3306),
               'user':input('MySQL 管理账号 [root]：').strip() or 'root',
               'password':getpass.getpass('MySQL 管理密码（不会显示或写入源码）：')}
    source=args.source_sqlite
    if source is None and (DATA/'platform.db').exists():
        raise ValueError('发现原 SQLite 业务数据。请先停止旧平台，再加 --source-sqlite data 迁移；不会自动创建空白演示库。')
    config,report=provision(admin,args.database,source)
    if managed:config['managed_server']=managed
    args.config_output.parent.mkdir(parents=True,exist_ok=True)
    args.config_output.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    if report:(args.config_output.parent/'mysql-migration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('MySQL 配置完成：'+config['database']+'；三个工厂使用各自的库和账号。')
    print('连接配置：'+str(args.config_output)+'；现在可以运行 start.bat。')

if __name__=='__main__':
    try:main()
    except pymysql.Error as error:
        print('MySQL 配置失败，错误编号：'+str(error.args[0])+'。请检查服务、账号密码和建库权限。');sys.exit(1)
    except (ValueError,RuntimeError) as error:print(str(error));sys.exit(1)
