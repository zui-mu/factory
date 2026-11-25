"""MySQL persistence and reproducible demonstration fixtures."""
import hashlib, secrets, random, math
from pathlib import Path
from datetime import datetime, timedelta
from .mysql_store import ROOT, DATA, connect, IntegrityError, DatabaseError
from .naming import FACTORIES,migrate_display_names

SCHEMA=(ROOT/'backend/sql/schema.sql').read_text(encoding='utf-8')
NODE_SCHEMA=(ROOT/'backend/sql/node.sql').read_text(encoding='utf-8')

def now(): return datetime.now().isoformat(timespec="seconds")
def rows(c,sql,args=()): return [dict(r) for r in c.execute(sql,args)]
def one(c,sql,args=()):
    r=c.execute(sql,args).fetchone()
    return dict(r) if r else None
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+":"+hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),180000).hex()
def check_password(password,stored):
    return secrets.compare_digest(password_hash(password,stored.split(":")[0]),stored)
def audit(c,user,action,entity,detail="",factory=None):
    c.execute("INSERT INTO audit(user_name,action,entity,detail,factory_id,created_at) VALUES(?,?,?,?,?,?)",
      (user["username"],action,entity,str(detail)[:1500],factory if factory is not None else user.get("factory_id"),now()))
def observations(seed,n,shift=0):
    r=random.Random(seed); result=[]
    for i in range(n):
        material=int(r.random()<(.25+shift*.10))
        product=int(r.random()<(.35+shift*.12))
        temp=int(r.random()<(.12+.46*material+.10*product))
        pressure=int(r.random()<(.17+.19*product))
        wear=int(r.random()<(.14+.13*shift))
        logit=-3.35+1.65*temp+1.12*pressure+1.03*wear+.85*material+.45*product
        defect=int(r.random()<1/(1+math.exp(-logit)))
        result.append((temp,pressure,wear,material,product,defect))
    return result
def initialize_platform():
    DATA.mkdir(parents=True,exist_ok=True)
    (DATA/"nodes").mkdir(exist_ok=True)
    (DATA/"uploads").mkdir(exist_ok=True)
    with connect() as c:
        c.executescript(SCHEMA)
        c.begin_write()
        if c.execute("SELECT count(*) FROM users").fetchone()[0]: return
        c.executemany("INSERT INTO factories VALUES(?,?,?)",FACTORIES)
        accounts=[("admin","平台管理员","admin",None),("engineer","质量工程师","engineer",1),("operator","现场班组长","operator",1),("manager","生产负责人","manager",1),("factory_b","云枢工厂工程师","engineer",2),("factory_c","曜光工厂工程师","engineer",3)]
        for i,(username,name,role,factory) in enumerate(accounts,1):
            c.execute("INSERT INTO users VALUES(?,?,?,?,?,?,1)",(i,username,password_hash("Zyyl@2026"),name,role,factory))
        r=random.Random(20261001)
        for f,name,city in FACTORIES:
            c.execute("INSERT INTO node_status VALUES(?,1)",(f,))
            for j in range(4):
                did=(f-1)*4+j+1
                c.execute("INSERT INTO devices VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                 (did,f,"EQ-%02d"%did,["精密注塑单元","数控加工中心","自动装配单元","在线检测单元"][j],["成型一线","加工二线","装配三线","检测四线"][j],
                  "预警" if j==0 else "待机" if j==3 else "运行",94.2 if j==0 else 68+j*3,7.8 if j==0 else 5.2,2.6 if j==0 else .8,2800+j*430,now()))
                for k in range(30):
                    t=datetime.now()-timedelta(minutes=29-k)
                    c.execute("INSERT INTO readings(device_id,temperature,pressure,vibration,created_at) VALUES(?,?,?,?,?)",
                     (did,round((76+k*.62 if j==0 else 68+j*3)+r.uniform(-1,1),1),round(5.2+(k*.09 if j==0 else 0)+r.uniform(-.2,.2),2),round(.8+(k*.06 if j==0 else 0),2),t.isoformat(timespec="seconds")))
            for j in range(3):
                oid=(f-1)*3+j+1
                c.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                 (oid,f,"MO-202610-%03d"%oid,["精密连接器外壳","传动定位组件","工业传感器支架"][j],"LOT-%02d-%03d"%(f,j+1),[2400,1800,1200][j],[1480,560,0][j],"生产中" if j<2 else "待排产","紧急" if j==0 else "普通",(datetime.now()+timedelta(days=j+1)).date().isoformat(),(f-1)*4+j+1,now()))
            for day in range(20,-1,-1):
                for j in range(3):
                    n=180+r.randrange(50);bad=max(1,round(n*(.018+r.random()*.02+(0.065 if day==0 and j==0 else 0))))
                    c.execute("INSERT INTO quality(factory_id,order_id,batch,sample_size,defects,defect_type,inspector,created_at) VALUES(?,?,?,?,?,?,?,?)",
                     (f,(f-1)*3+j+1,"LOT-%02d-%03d"%(f,j+1),n,bad,"尺寸偏差" if j==0 else "外观缺陷","演示质检员",(datetime.now()-timedelta(days=day)).replace(hour=10+j).isoformat(timespec="seconds")))
            c.execute("INSERT INTO anomalies(factory_id,device_id,order_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?,?)",
             (f,(f-1)*4+1,(f-1)*3+1,"连接器外壳尺寸偏差上升","高","成型一线质检不合格率超过 5%，伴随温度升高。请核对原料与工艺条件。","模拟质检数据",now()))
            c.execute("INSERT INTO anomalies(factory_id,device_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?)",
             (f,(f-1)*4+2,"加工中心点检待确认","中","累计运行时间达到点检周期，请安排现场检查。","演示点检计划",now()))
            for j,(name,spec,unit,stock,minimum,loc) in enumerate([("工程塑料 PA66","阻燃级","kg",850,300,"原料仓 A-01"),("铝合金棒料","6061 / Ø20","kg",120,200,"原料仓 A-03"),("连接器外壳","标准件","件",3680,1000,"成品仓 B-02"),("润滑油","工业级","L",65,40,"辅料仓 C-01")]):
                c.execute("INSERT INTO materials(factory_id,code,name,spec,unit,stock,min_stock,location) VALUES(?,?,?,?,?,?,?,?)",
                 (f,"MAT-%s-%s"%(f,j+1),name,spec,unit,stock,minimum,loc))
            c.executemany("INSERT INTO samples(factory_id,temp,pressure,wear,material,product,defect,source,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
             [(f,)+s+("已知生成机制的模拟工艺样本",now()) for s in observations(42+f,1800,f-1)])
        audit(c,{"username":"system","factory_id":None},"初始化","演示数据","固定种子的合成数据；不代表真实工厂收益")
def initialize_nodes():
    for f,_,_ in FACTORIES:
        with connect(factory=f) as c:
            c.executescript(NODE_SCHEMA)
            c.begin_write()
            for split,size,seed in [("train",[900,450,180][f-1],700+f),("validation",240,900+f),("test",400,1100+f)]:
                if c.execute("SELECT 1 FROM samples WHERE split=? LIMIT 1",(split,)).fetchone():continue
                c.executemany("INSERT INTO samples(temp,pressure,wear,material,product,defect,split) VALUES(?,?,?,?,?,?,?)",
                  [s+(split,) for s in observations(seed,size,f-1)])

def initialize():
    initialize_platform()
    initialize_nodes()
    from .legacy import import_snapshot
    with connect() as c:
        import_snapshot(c)
        migrate_display_names(c)
    from .workforce import initialize as initialize_workforce
    with connect() as c:
        initialize_workforce(c)
