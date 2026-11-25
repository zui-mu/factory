"""Real MySQL checks for migration, rollback, constraints, isolation and SQL backups."""
import json,os,sqlite3,tempfile,threading,time,unittest
from pathlib import Path
from backend.db import SCHEMA
from backend.mysql_store import connect,DatabaseError,IntegrityError,raw_connection,identifier
from backend.tools.migrate_sqlite import import_database
from backend.tools.backup import dump_database
from backend.tools.setup_mysql import provision
from mysql_support import TestDatabases

class MySQLStorageTests(unittest.TestCase):
    def setUp(self):
        self.mysql=TestDatabases();self.addCleanup(self.mysql.close)
        with connect(config=self.mysql.config) as c:c.executescript(SCHEMA)
    def test_transaction_rollback_and_foreign_key(self):
        with self.assertRaises(RuntimeError):
            with connect(config=self.mysql.config) as c:
                c.execute("INSERT INTO factories VALUES(9,'测试','园区')")
                raise RuntimeError('abort')
        with connect(config=self.mysql.config) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM factories').fetchone()[0],0)
            with self.assertRaises(IntegrityError):c.execute("INSERT INTO devices(factory_id,code) VALUES(999,'invalid')")
    def test_only_one_active_task_per_anomaly(self):
        with connect(config=self.mysql.config) as c:
            c.execute("INSERT INTO factories VALUES(1,'测试','园区')")
            c.execute("INSERT INTO anomalies(id,factory_id,title) VALUES(1,1,'异常')")
            c.execute("INSERT INTO tasks(anomaly_id,status) VALUES(1,'待接单')")
            with self.assertRaises(IntegrityError):c.execute("INSERT INTO tasks(anomaly_id,status) VALUES(1,'处理中')")
            c.execute("UPDATE tasks SET status='已关闭'")
            c.execute("INSERT INTO tasks(anomaly_id,status) VALUES(1,'待接单')")
            self.assertEqual(c.execute('SELECT count(*) FROM tasks').fetchone()[0],2)
    def test_competing_business_writes_do_not_lose_updates(self):
        with connect(config=self.mysql.config) as c:c.execute("INSERT INTO materials(id,stock) VALUES(1,100)")
        barrier=threading.Barrier(2);errors=[]
        def change():
            try:
                barrier.wait()
                with connect(config=self.mysql.config) as c:
                    c.begin_write();stock=c.execute('SELECT stock FROM materials WHERE id=1').fetchone()[0]
                    time.sleep(.05)
                    c.execute('UPDATE materials SET stock=? WHERE id=1',(stock-1,))
            except Exception as e:errors.append(e)
        threads=[threading.Thread(target=change) for _ in (1,2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=10)
        self.assertFalse(errors)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        with connect(config=self.mysql.config) as c:self.assertEqual(c.execute('SELECT stock FROM materials WHERE id=1').fetchone()[0],98)
    def test_sqlite_migration_preserves_unicode_ids_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'original.db';old=sqlite3.connect(file)
            try:
                old.execute('CREATE TABLE factories(id INTEGER PRIMARY KEY,name TEXT,city TEXT)')
                old.execute('INSERT INTO factories VALUES(77,?,?)',("星铸🚀 '?;%\\",'园区'));old.commit()
            finally:old.close()
            target={'config':self.mysql.config}
            self.assertEqual(import_database(file,target),{'factories':1})
            with connect(config=self.mysql.config) as c:
                self.assertEqual(c.execute('SELECT name FROM factories WHERE id=77').fetchone()[0],"星铸🚀 '?;%\\")
                self.assertGreater(c.execute("INSERT INTO factories(name) VALUES('下一条')").lastrowid,77)
            with self.assertRaises(ValueError):import_database(file,target)
    def test_standard_sql_backup_roundtrip(self):
        name="星铸🚀 '?;%\\"
        with connect(config=self.mysql.config) as c:c.execute('INSERT INTO factories VALUES(77,?,?)',(name,'园区'))
        dump=dump_database(config=self.mysql.config).decode('utf-8')
        restored=TestDatabases();self.addCleanup(restored.close)
        with connect(config=restored.config) as c:
            c.executescript(dump)
            self.assertEqual(c.execute('SELECT name FROM factories WHERE id=77').fetchone()[0],name)
    def test_provisioned_accounts_cannot_read_other_factories(self):
        database=self.mysql.config['database']+'_scope'
        admin=json.loads(Path(os.environ['ZY_MYSQL_TEST_CONFIG']).read_text(encoding='utf-8'))
        config,_=provision(admin,database)
        def cleanup():
            with raw_connection(admin,select_database=False) as c:
                with c.cursor() as q:
                    for name in [database]+list(config['node_databases'].values()):q.execute('DROP DATABASE '+identifier(name))
                    for account in [config]+list(config['node_users'].values()):q.execute('DROP USER %s@%s',(account['user'],'localhost'))
        self.addCleanup(cleanup)
        with connect(config=config) as c:
            with self.assertRaises(DatabaseError):c.execute('SELECT * FROM '+identifier(config['node_databases']['1'])+'.samples')
        with connect(config=config,factory=1) as c:
            c.execute('SELECT count(*) FROM samples')
            with self.assertRaises(DatabaseError):c.execute('SELECT * FROM '+identifier(config['node_databases']['2'])+'.samples')
