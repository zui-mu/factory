"""Export standard MySQL SQL and uploaded files; pause business writes/training first."""
import sys,zipfile,hashlib,json
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.mysql_store import DATA,connect,identifier

def dump_database(config=None,factory=None):
    output=['-- MySQL 8.0; import into the matching empty database.','SET NAMES utf8mb4;','SET FOREIGN_KEY_CHECKS=0;']
    with connect(config=config,factory=factory) as c:
        c.execute('SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        c.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT')
        for item in c.execute('SHOW TABLES'):
            table=item[0]
            ddl=c.execute('SHOW CREATE TABLE '+identifier(table)).fetchone()[1]
            output.append(ddl.replace('CREATE TABLE ','CREATE TABLE IF NOT EXISTS ',1)+';')
            names=[r[0] for r in c.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COALESCE(GENERATION_EXPRESSION,'')='' ORDER BY ORDINAL_POSITION",(table,))]
            columns=','.join(identifier(name) for name in names)
            for row in c.execute('SELECT '+columns+' FROM '+identifier(table)):
                values=','.join(c.raw.escape(value) for value in row.values())
                output.append('INSERT INTO '+identifier(table)+' ('+columns+') VALUES ('+values+');')
    output.append('SET FOREIGN_KEY_CHECKS=1;')
    return ('\n'.join(output)+'\n').encode('utf-8')

def main():
    folder=DATA/'backups';folder.mkdir(parents=True,exist_ok=True)
    destination=folder/('zyyl-mysql-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip')
    manifest={}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for factory in (None,1,2,3):
            name='platform.sql' if factory is None else 'factory_%s.sql'%factory
            content=dump_database(factory=factory);z.writestr(name,content)
            manifest[name]=hashlib.sha256(content).hexdigest()
        for file in (DATA/'uploads').glob('*'):
            if file.is_file():
                name='uploads/'+file.name;content=file.read_bytes();z.writestr(name,content)
                manifest[name]=hashlib.sha256(content).hexdigest()
        z.writestr('sha256.json',json.dumps(manifest,indent=2))
    print(destination)
if __name__=="__main__":main()
