# -*- coding: utf-8 -*-
"""Anonymous labels for sample factories and previously persisted display text."""
FACTORIES = [(1,"星铸工厂","星铸园区"),(2,"云枢工厂","云枢园区"),(3,"曜光工厂","曜光园区")]
ALIASES = (
    ("星河精工 · 苏州一厂","工厂 A"),
    ("星河精工 · 无锡二厂","工厂 B"),
    ("协作工厂 · 常州","工厂 C"),
    ("苏州一厂","工厂 A"),("无锡二厂","工厂 B"),
    ("协作厂工程师","工厂 C 工程师"),("二厂工程师","工厂 B 工程师"),
    ("凯途管项目业务存档","来源项目 A · 业务存档"),
    ("慧析云坊项目业务存档","来源项目 B · 业务存档"),
    ("星河精工","示例企业"),("协作工厂","工厂 C"),
    ("苏州","区域 A"),("无锡","区域 B"),("常州","区域 C"),
    ("工厂 B 工程师","云枢工厂工程师"),("工厂 C 工程师","曜光工厂工程师"),
    ("工厂 A","星铸工厂"),("工厂 B","云枢工厂"),("工厂 C","曜光工厂"),
    ("区域 A","星铸园区"),("区域 B","云枢园区"),("区域 C","曜光园区"),
)

def anonymous_text(value):
    if not isinstance(value,str):return value
    for original,replacement in ALIASES:value=value.replace(original,replacement)
    return value

def migrate_display_names(c):
    for factory,name,region in FACTORIES:
        c.execute('UPDATE factories SET name=?,city=? WHERE id=? AND (NOT (name <=> ?) OR NOT (city <=> ?))',(name,region,factory,name,region))
    # Only display content changes. Credentials, identifiers, hashes and quantities stay intact.
    fields={
        'users':['name'], 'devices':['name','line'],
        'orders':['product','batch'], 'quality':['batch','defect_type','inspector'],
        'anomalies':['title','description','source'], 'analyses':['result'],
        'tasks':['title','action','note','review_note'], 'task_events':['user_name','note'],
        'materials':['name','spec','location'], 'stock_moves':['note','user_name'],
        'samples':['source'], 'training_jobs':['result','error'], 'training_events':['detail'],
        'assistant_messages':['question','response'], 'audit':['user_name','entity','detail'],
        'source_records':['label'], 'idempotency':['response'],
    }
    for table,columns in fields.items():
        primary=[r[0] for r in c.execute("SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND CONSTRAINT_NAME='PRIMARY' ORDER BY ORDINAL_POSITION",(table,))]
        names=primary+columns
        for record in c.execute('SELECT '+','.join('`'+name+'`' for name in names)+' FROM `'+table+'`').fetchall():
            changes={name:anonymous_text(record[name]) for name in columns if anonymous_text(record[name])!=record[name]}
            if changes:
                c.execute('UPDATE `'+table+'` SET '+','.join('`'+name+'`=?' for name in changes)+' WHERE '+' AND '.join('`'+name+'`=?' for name in primary),tuple(changes.values())+tuple(record[name] for name in primary))
