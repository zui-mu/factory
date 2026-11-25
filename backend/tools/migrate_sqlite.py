"""One-way, verified import into empty MySQL schemas. Never deletes source databases."""
import argparse,json,sqlite3,sys
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.db import SCHEMA,NODE_SCHEMA
from backend.mysql_store import connect,settings,identifier,DATA

def import_database(source,target):
    if not source.is_file():raise ValueError('缺少迁移源文件：'+str(source))
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as old:
        if old.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('源数据库完整性检查失败')
        if old.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('源数据库存在无效外键')
        tables=[r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
        with connect(config=target['config'],factory=target.get('factory')) as new:
            new.begin_write()
            current=[r[0] for r in new.execute('SHOW TABLES')]
            if any(new.execute('SELECT count(*) FROM '+identifier(t)).fetchone()[0] for t in current):
                raise ValueError('目标 MySQL 数据库已有数据，拒绝覆盖：'+new.database)
            if set(tables)-set(current):raise ValueError('源数据库含当前平台不支持的表')
            report={}
            for table in tables:
                cols=[r[1] for r in old.execute('PRAGMA table_info('+identifier(table)+')')]
                names=','.join(identifier(col) for col in cols)
                original=old.execute('SELECT '+names+' FROM '+identifier(table)).fetchall()
                if original:new.executemany('INSERT INTO '+identifier(table)+' ('+names+') VALUES ('+','.join('?' for _ in cols)+')',original)
                copied=[tuple(r.values()) for r in new.execute('SELECT '+names+' FROM '+identifier(table))]
                order=lambda row:repr(tuple(row))
                if sorted(original,key=order)!=sorted(copied,key=order):raise ValueError('迁移逐行校验失败：'+table)
                report[table]=len(original)
            return report

def migrate(folder,config):
    results={}
    for factory in (None,1,2,3):
        source=folder/'platform.db' if factory is None else folder/'nodes'/('factory_%s.db'%factory)
        with connect(config=config,factory=factory) as c:c.executescript(SCHEMA if factory is None else NODE_SCHEMA)
        results['platform' if factory is None else 'factory_'+str(factory)]=import_database(source,{'config':config,'factory':factory})
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='停止旧服务后，将 SQLite 数据完整导入空的 MySQL 平台库和三节点库')
    parser.add_argument('--source',type=Path,default=DATA)
    args=parser.parse_args()
    print(json.dumps(migrate(args.source,settings()),ensure_ascii=False,indent=2))
