"""Small MySQL adapter: bound parameters, transactions and named/indexed rows."""
import hashlib, json, os, re
from decimal import Decimal
from pathlib import Path
import pymysql

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('ZY_DATA_DIR', str(ROOT/'data')))
IntegrityError = pymysql.IntegrityError
DatabaseError = pymysql.Error
TOKENS = re.compile(r"('(?:''|\\.|[^'\\])*'|\"(?:\"\"|\\.|[^\"\\])*\"|`[^`]*`|--[^\n]*(?:\n|$)|/\*.*?\*/)", re.S)

def settings():
    path = Path(os.environ.get('ZY_MYSQL_CONFIG', str(DATA/'mysql.json')))
    config = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    for field in ('host','port','user','password','database'):
        value = os.environ.get('ZY_MYSQL_'+field.upper())
        if value is not None: config[field] = value
    config.setdefault('host','127.0.0.1');config['port']=int(config.get('port',3306))
    config.setdefault('database','zhiyinyunlian')
    config.setdefault('node_databases', {str(f):config['database']+'_factory_'+str(f) for f in (1,2,3)})
    if not config.get('user') or 'password' not in config:
        raise RuntimeError('MySQL 尚未配置，请先运行 setup.bat；连接配置保存在 data/mysql.json。')
    for name in [config['database']]+list(config['node_databases'].values()):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',name):raise ValueError('MySQL 数据库名称无效')
    return config

def database_name(factory=None, config=None):
    config=config or settings()
    if factory is not None and factory not in (1,2,3):raise ValueError('Invalid factory')
    return config['database'] if factory is None else config['node_databases'][str(factory)]

def raw_connection(config=None, factory=None, select_database=True):
    config=config or settings()
    credentials=config.get('node_users',{}).get(str(factory),config) if factory else config
    kwargs={k:config[k] for k in ('host','port')}
    kwargs.update(user=credentials['user'], password=credentials['password'], charset='utf8mb4',
                  connect_timeout=8,read_timeout=30,write_timeout=30,autocommit=False)
    if select_database:kwargs['database']=database_name(factory,config)
    return pymysql.connect(**kwargs)

def identifier(name):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):raise ValueError('Invalid SQL identifier')
    return '`'+name+'`'

def bind_sql(sql):
    # Existing service queries use DB-API qmark placeholders. Quoted text is never rewritten.
    return ''.join(part.replace('%','%%').replace('?','%s') if i%2==0 else part.replace('%','%%')
                   for i,part in enumerate(TOKENS.split(sql)))

def split_sql(script):
    current=''
    for i,part in enumerate(TOKENS.split(script)):
        if i%2:current+=part;continue
        chunks=part.split(';')
        for chunk in chunks[:-1]:
            current+=chunk
            if current.strip():yield current.strip()
            current=''
        current+=chunks[-1]
    if current.strip():yield current.strip()

def json_number(value):
    if isinstance(value,Decimal):return int(value) if value==value.to_integral_value() else float(value)
    return value

class Row(dict):
    def __getitem__(self,key):
        return tuple(self.values())[key] if isinstance(key,(int,slice)) else super().__getitem__(key)

class Result:
    def __init__(self,cursor):
        self.lastrowid=cursor.lastrowid;self.rowcount=cursor.rowcount;self.index=0
        names=[col[0] for col in cursor.description] if cursor.description else []
        self.records=[Row(zip(names,map(json_number,row))) for row in cursor.fetchall()] if names else []
    def fetchone(self):
        if self.index>=len(self.records):return None
        row=self.records[self.index];self.index+=1;return row
    def fetchall(self):
        rows=self.records[self.index:];self.index=len(self.records);return rows
    def __iter__(self):return iter(self.fetchall())

class Connection:
    def __init__(self,factory=None,config=None):
        self.config=config or settings();self.database=database_name(factory,self.config)
        self.raw=raw_connection(self.config,factory);self.lock_name=None
        with self.raw.cursor() as cursor:
            cursor.execute('SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED')
    def execute(self,sql,args=()):
        with self.raw.cursor() as cursor:
            cursor.execute(bind_sql(sql),args)
            return Result(cursor)
    def executemany(self,sql,values):
        with self.raw.cursor() as cursor:
            cursor.executemany(bind_sql(sql),values)
            return Result(cursor)
    def executescript(self,script):
        for sql in split_sql(script):self.execute(sql)
    def begin_write(self):
        # Serialize read-modify-write business operations across the API and telemetry worker.
        # The lock is scoped to this database and is released on commit/rollback/connection loss.
        if self.lock_name:return
        lock='zyyl-write-'+hashlib.sha256(self.database.encode()).hexdigest()[:40]
        if self.execute('SELECT GET_LOCK(?,20)',(lock,)).fetchone()[0]!=1:
            raise pymysql.OperationalError(1205,'Timed out waiting for business transaction')
        self.lock_name=lock
        self.raw.begin()
    def _unlock(self):
        if self.lock_name:
            name=self.lock_name;self.lock_name=None
            self.execute('SELECT RELEASE_LOCK(?)',(name,))
    def commit(self):
        try:self.raw.commit()
        finally:self._unlock()
    def rollback(self):
        try:self.raw.rollback()
        finally:self._unlock()
    def close(self):
        if self.raw.open:
            try:self.rollback()
            finally:self.raw.close()
    def __enter__(self):return self
    def __exit__(self,typ,value,tb):
        try:
            if typ is None:self.commit()
            else:self.rollback()
        finally:self.close()

def connect(*,factory=None,config=None):
    return Connection(factory,config)
