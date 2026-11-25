"""Read-only source adapters. Never execute MySQL SQL or import user secrets."""
import hashlib,json,re,sqlite3,tempfile,zipfile,math
from pathlib import Path
from .db import ROOT,now,audit
FIXTURE=ROOT/"backend"/"fixtures"/"business_sources.json"
TABLES=("dv_machinery","pro_workorder","qc_ipqc","md_item","wm_material_stock")

def sql_values(text):
    """Parse MySQL VALUES tuples, including quoted commas and escapes."""
    result=[];row=[];value=[];quoted=False;was_quoted=False;i=0
    def finish():
        nonlocal value,was_quoted
        s="".join(value)
        row.append(s if was_quoted else None if s.strip().lower()=="null" else s.strip())
        value=[];was_quoted=False
    while i<len(text):
        ch=text[i]
        if quoted:
            if ch=="\\" and i+1<len(text):
                i+=1;value.append({"n":"\n","r":"\r","t":"\t","0":"\0"}.get(text[i],text[i]))
            elif ch=="'":
                if i+1<len(text) and text[i+1]=="'":value.append("'");i+=1
                else:quoted=False
            else:value.append(ch)
        elif ch=="'":quoted=True;was_quoted=True
        elif ch=="(":row=[];value=[]
        elif ch==",":
            if value or was_quoted:finish()
        elif ch==")":
            finish();result.append(row);row=[]
        elif ch not in " \r\n\t;":value.append(ch)
        i+=1
    if quoted:raise ValueError("SQL quoted string was not closed")
    return result

def mysql_tables(path):
    data={t:[] for t in TABLES};columns={};current=None
    with Path(path).open(encoding="utf-8-sig") as f:
        for line in f:
            match=re.match(r"CREATE TABLE \x60([^\x60]+)\x60",line)
            if match:current=match[1] if match[1] in data else None;columns.setdefault(current,[])
            elif current:
                col=re.match(r"\s*\x60([^\x60]+)\x60",line)
                if col:columns[current].append(col[1])
                if line.startswith(")"):current=None
            match=re.match(r"INSERT INTO \x60([^\x60]+)\x60 VALUES (.*);\s*$",line)
            if match and match[1] in data:
                table=match[1]
                for values in sql_values(match[2]):
                    if len(values)!=len(columns[table]):raise ValueError("Unsupported SQL row: "+table)
                    data[table].append(dict(zip(columns[table],values)))
    return data

def whole(value):
    n=float(value or 0)
    if not math.isfinite(n) or n<0 or not n.is_integer():raise ValueError("数量不是非负整数")
    return int(n)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def build_snapshot(sql_path,zip_path):
    """Only allowlisted business fields; excludes contacts, users and configs."""
    result={"format":1,"created_at":now(),"sources":[]}
    ktg=mysql_tables(sql_path)
    src={"key":"KTG","label":"来源项目 A · 业务存档","factory_id":1,"sha256":digest(sql_path),"records":[],"skipped":[]}
    records=src["records"]
    for r in ktg["dv_machinery"]:
        records.append({"kind":"devices","source_id":str(r["machinery_id"]),"code":r["machinery_code"],"name":r["machinery_name"],
          "line":r.get("workshop_name") or "来源未注明车间","original_status":r["status"]})
    accepted=set()
    for r in ktg["pro_workorder"]:
        try:
            if str(r.get("unit_of_measure","")).upper() not in ("PCS","个","件","套"):raise ValueError("本平台报工以件计，原工单单位不同")
            quantity=whole(r["quantity"]);completed=whole(r["quantity_produced"])
            if quantity<1 or completed>quantity:raise ValueError("数量超出允许范围")
            records.append({"kind":"orders","source_id":str(r["workorder_id"]),"code":r["workorder_code"],
             "product":r["product_name"],"batch":r["batch_code"] or "来源未注明批次","quantity":quantity,"completed":completed,
             "due_date":(r["request_date"] or "")[:10],"created_at":r["create_time"],"original_status":r["status"]})
            accepted.add(str(r["workorder_id"]))
        except ValueError as e:src["skipped"].append({"kind":"orders","source_id":str(r["workorder_id"]),"reason":str(e)})
    for r in ktg["qc_ipqc"]:
        n=whole(r["quantity_check"]);bad=whole(r["quantity_unqualified"])
        if n>0 and bad<=n:
            records.append({"kind":"quality","source_id":str(r["ipqc_id"]),
             "order_source_id":str(r["workorder_id"]) if str(r["workorder_id"]) in accepted else None,
             "batch":r["ipqc_code"],"sample_size":n,"defects":bad,"created_at":r["inspect_date"],"original_status":r["check_result"]})
    items={str(r["item_id"]):r for r in ktg["md_item"]}
    for r in ktg["wm_material_stock"]:
        item=items.get(str(r["item_id"]),{})
        records.append({"kind":"materials","source_id":str(r["material_stock_id"]),"code":"STOCK-"+str(r["material_stock_id"]),
         "name":r["item_name"],"spec":r["specification"] or "来源未注明","unit":r["unit_of_measure"] or item.get("unit_of_measure") or "来源未注明",
         "stock":float(r["quantity_onhand"] or 0),"min_stock":0,
         "location":" / ".join(x for x in [r["warehouse_name"],r["location_name"],r["area_name"]] if x),
         "original_status":"历史库位余额；未套用物料级安全库存"})
    result["sources"].append(src)
    with zipfile.ZipFile(zip_path) as archive:
        dbname=next(n for n in archive.namelist() if n.endswith("/backend/factory.db"))
        with tempfile.TemporaryDirectory(prefix="zyyl-source-") as td:
            dbfile=Path(td)/"source.db";dbfile.write_bytes(archive.read(dbname))
            conn=sqlite3.connect(dbfile.as_uri()+"?mode=ro",uri=True);conn.row_factory=sqlite3.Row
            try:
                tables={t:[dict(r) for r in conn.execute("SELECT * FROM "+t)] for t in ("device","work_order","quality_record","material","stock","unit","workshop","warehouse")}
            finally:conn.close()
    src={"key":"HX","label":"来源项目 B · 业务存档","factory_id":2,"sha256":digest(zip_path),"records":[],"skipped":[]}
    records=src["records"]
    lookup=lambda table,key,value:next((r.get(value) for r in tables[table] if r["id"]==key),None)
    for r in tables["device"]:
        records.append({"kind":"devices","source_id":str(r["id"]),"code":r["device_code"],"name":r["device_name"],
         "line":lookup("workshop",r["workshop_id"],"workshop_name") or "来源未注明车间","original_status":str(r["device_status"])})
    accepted=set()
    for r in tables["work_order"]:
        try:
            quantity=whole(r["quantity"]);completed=whole(r["completed_quantity"])
            if quantity<1 or completed>quantity:raise ValueError("数量超出允许范围")
            records.append({"kind":"orders","source_id":str(r["id"]),"code":r["order_no"],
             "product":lookup("material",r["product_id"],"material_name") or "来源产品 #"+str(r["product_id"]),
             "batch":"来源未注明批次","quantity":quantity,"completed":completed,"due_date":r["plan_end_date"] or "",
             "created_at":r["create_time"],"original_status":str(r["status"])})
            accepted.add(str(r["id"]))
        except ValueError as e:src["skipped"].append({"kind":"orders","source_id":str(r["id"]),"reason":str(e)})
    for r in tables["quality_record"]:
        n=whole(r["sample_size"]);bad=whole(r["unqualified_count"])
        if n>0 and bad<=n:
            linked=str(r["source_id"]) if r["source_type"] in ("work_order","workorder") and str(r["source_id"]) in accepted else None
            records.append({"kind":"quality","source_id":str(r["id"]),"order_source_id":linked,"batch":r["batch_no"] or r["record_no"],
             "sample_size":n,"defects":bad,"created_at":r["check_time"] or "","original_status":str(r["check_result"])})
    for r in tables["stock"]:
        item=next(x for x in tables["material"] if x["id"]==r["material_id"])
        records.append({"kind":"materials","source_id":str(r["id"]),"code":"STOCK-"+str(r["id"]),"name":item["material_name"],
         "spec":item["spec"] or "来源未注明","unit":lookup("unit",item["unit_id"],"unit_name") or "来源未注明",
         "stock":float(r["quantity"]),"min_stock":0,
         "location":lookup("warehouse",r["warehouse_id"],"warehouse_name") or "来源未注明仓库",
         "original_status":"历史库位余额；未套用物料级安全库存；冻结量 "+str(r["frozen_quantity"])})
    result["sources"].append(src)
    return result

def import_snapshot(c,path=FIXTURE):
    """Idempotently bring source archives into the unified business views."""
    if not path.exists():return
    data=json.loads(path.read_text(encoding="utf-8"))
    for src in data["sources"]:
        added=0;factory=src["factory_id"]
        for r in src["records"]:
            kind=r["kind"];key=(src["key"],kind,r["source_id"])
            if c.execute("SELECT 1 FROM source_records WHERE source_key=? AND entity=? AND original_id=?",key).fetchone():continue
            stamp=r.get("created_at") or "";code=src["key"]+"-"+r.get("code","")
            if kind=="devices":
                id=c.execute("INSERT INTO devices(factory_id,code,name,line,status,updated_at) VALUES(?,?,?,?,?,?)",
                 (factory,code,r["name"],r["line"],"待采集","")).lastrowid
            elif kind=="orders":
                id=c.execute("INSERT INTO orders(factory_id,code,product,batch,quantity,completed,status,priority,due_date,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                 (factory,code,r["product"],r["batch"],r["quantity"],r["completed"],"历史归档","普通",r["due_date"],stamp)).lastrowid
            elif kind=="quality":
                linked=c.execute("SELECT record_id FROM source_records WHERE source_key=? AND entity='orders' AND original_id=?",
                 (src["key"],r.get("order_source_id"))).fetchone()
                id=c.execute("INSERT INTO quality(factory_id,order_id,batch,sample_size,defects,defect_type,inspector,created_at) VALUES(?,?,?,?,?,?,?,?)",
                 (factory,linked[0] if linked else None,r["batch"],r["sample_size"],r["defects"],"历史质检存档","来源未提供姓名",stamp)).lastrowid
            elif kind=="materials":
                id=c.execute("INSERT INTO materials(factory_id,code,name,spec,unit,stock,min_stock,location) VALUES(?,?,?,?,?,?,?,?)",
                 (factory,code,r["name"],r["spec"],r["unit"],r["stock"],r["min_stock"],r["location"])).lastrowid
            else:raise ValueError("Unknown source entity")
            c.execute("INSERT INTO source_records VALUES(?,?,?,?,?,?,?,?,?)",
             key+(id,factory,src["label"],src["sha256"],r.get("original_status",""),now()))
            added+=1
        if added:audit(c,{"username":"source-adapter","factory_id":factory},"导入项目业务存档",src["key"],str(added)+" 条；历史记录不充当实时传感或算法样本",factory)
