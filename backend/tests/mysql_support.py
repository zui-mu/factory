"""MySQL tests create UUID-named schemas; production schema names are never accepted."""
import json,os,tempfile,uuid
from pathlib import Path
from backend.mysql_store import raw_connection,identifier

class TestDatabases:
    def __init__(self):
        file=os.environ.get('ZY_MYSQL_TEST_CONFIG')
        if not file:raise RuntimeError('请设置 ZY_MYSQL_TEST_CONFIG，指向测试 MySQL 管理连接配置；不会使用生产业务库。')
        self.config=json.loads(Path(file).read_text(encoding='utf-8-sig'))
        self.config['database']='zyyl_test_'+uuid.uuid4().hex[:16]
        self.config['node_databases']={str(f):self.config['database']+'_factory_'+str(f) for f in (1,2,3)}
        self.config.pop('node_users',None)
        self.names=[self.config['database']]+list(self.config['node_databases'].values())
        self.created=[];self.temp=tempfile.TemporaryDirectory(prefix='zyyl-mysql-config-')
        self.path=Path(self.temp.name)/'mysql.json'
        self.path.write_text(json.dumps(self.config),encoding='utf-8')
        try:
            with raw_connection(self.config,select_database=False) as c:
                with c.cursor() as q:
                    for name in self.names:
                        q.execute('CREATE DATABASE '+identifier(name)+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin')
                        self.created.append(name)
        except BaseException:self.close();raise
    def close(self):
        try:
            with raw_connection(self.config,select_database=False) as c:
                with c.cursor() as q:
                    for name in reversed(self.created):
                        if not name.startswith('zyyl_test_'):raise RuntimeError('Refusing to drop a non-test database')
                        q.execute('DROP DATABASE '+identifier(name))
            self.created=[]
        finally:self.temp.cleanup()
