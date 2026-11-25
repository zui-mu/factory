"""Optional source adapter; the shipped fixture already contains sanitized records."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.legacy import build_snapshot,FIXTURE

if __name__=="__main__":
    p=argparse.ArgumentParser(description="读取两个已有项目的白名单业务字段，生成可追溯存档")
    p.add_argument("--ktg-sql",required=True);p.add_argument("--huixi-zip",required=True)
    args=p.parse_args();result=build_snapshot(args.ktg_sql,args.huixi_zip)
    FIXTURE.parent.mkdir(parents=True,exist_ok=True)
    FIXTURE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({s["key"]:{"records":len(s["records"]),"skipped":s["skipped"]} for s in result["sources"]},ensure_ascii=False,indent=2))
