"""Staffing business rules exercised through HTTP against isolated MySQL schemas."""
import json
import threading
import unittest
from unittest.mock import patch
from datetime import datetime,timedelta
import test_system as system
from backend.mysql_store import connect
from backend import workforce


class WorkforceTests(unittest.TestCase):
    start_server=classmethod(system.PlatformTests.start_server.__func__)
    @classmethod
    def setUpClass(cls):
        system.PlatformTests.setUpClass.__func__(cls)
        cls.manager=system.Client(cls.base,'manager')
        cls.day=(datetime.now()+timedelta(days=60)).date().isoformat()
        cls.nextday=(datetime.now()+timedelta(days=61)).date().isoformat()
    @classmethod
    def tearDownClass(cls): system.PlatformTests.tearDownClass.__func__(cls)

    def get_data(self,client=None,factory=1,date=None):
        status,result=(client or self.admin).call('/workforce?factory_id='+str(factory)+'&date='+(date or self.day))
        self.assertEqual(status,200,result)
        return result

    def employee(self,code,skills=None):
        b={'factory_id':1,'name':'测试员工 '+code,'code':code,'workshop':'成型车间','position':'操作员','team':'测试班组','skills':skills or ['生产操作','设备点检'],'status':'在职'}
        status,result=self.manager.call('/workforce/employees',b)
        self.assertEqual(status,200,result)
        return result['id']

    def shift(self,name,start='20:00',end='04:00'):
        status,result=self.manager.call('/workforce/shifts',{'factory_id':1,'name':name,'start_time':start,'end_time':end})
        self.assertEqual(status,200,result)
        return result['id']

    def plan(self,eid,sid,**extra):
        body={'factory_id':1,'employee_ids':[eid],'shift_id':sid,'work_date':self.day,'line':'成型一线','required_count':2,'required_skill':'生产操作','note':'测试排班',**extra}
        return body,self.manager.call('/workforce/plans',body)

    def test_01_access_scope_and_personal_privacy(self):
        d=self.get_data(self.op)
        self.assertEqual(len(d['employees']),1)
        self.assertEqual(d['employees'][0]['user_id'],3)
        self.assertEqual(d['accounts'],[])
        self.assertEqual(d['warnings'],[])
        self.assertEqual(self.op.call('/workforce?factory_id=2')[0],403)
        self.assertEqual(self.manager.call('/workforce?factory_id=2')[0],403)
        self.assertEqual(self.eng.call('/workforce/employees',{'factory_id':1})[0],403)
        self.assertEqual(self.op.call('/workforce/candidates?anomaly_id=1')[0],403)
        e=self.get_data(factory=2)['employees'][0]
        self.assertEqual(self.manager.call('/workforce/employees',{'id':e['id'],'version':1})[0],403)
        self.assertEqual(self.get_data(factory=3)['employees'][0]['factory_id'],3)

    def test_02_overnight_conflicts_skills_and_version(self):
        eid=self.employee('T-OVER'); sid=self.shift('跨日测试')
        body,(status,result)=self.plan(eid,sid)
        self.assertEqual(status,200,result); pid=result['id']
        self.assertTrue(result['warnings'])
        other=self.shift('凌晨测试','02:00','08:00')
        _,r=self.plan(eid,other,work_date=self.nextday,line='加工二线')
        self.assertEqual(r[0],409,r)
        self.assertIn('跨日',r[1]['error'])
        _,r=self.plan(eid,other,work_date=self.nextday,line='加工二线',required_skill='质量检验')
        self.assertEqual(r[0],400,r)
        p=next(p for p in self.get_data()['plans'] if p['id']==pid)
        self.assertEqual(p['end_at'],self.nextday+'T04:00:00')
        self.assertEqual(p['shortage'],1)
        self.assertEqual(self.manager.call('/workforce/plans',{**body,'id':pid,'version':2})[0],409)
        # Shift edits must not rewrite the published plan, even on a staffing-only edit.
        self.assertEqual(self.manager.call('/workforce/shifts',{'id':sid,'version':1,'name':'跨日测试','start_time':'21:00','end_time':'05:00'})[0],200)
        self.assertEqual(self.manager.call('/workforce/plans',{**body,'id':pid,'version':1})[0],200)
        self.assertEqual(next(p for p in self.get_data()['plans'] if p['id']==pid)['start_at'],self.day+'T20:00:00')
        # Rejected conflicting edit is atomic: original assignments survive.
        with connect(config=self.mysql.config) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM staff_assignments WHERE plan_id=?',(pid,)).fetchone()[0],1)

    def test_03_leave_approval_shortage_and_replacement(self):
        eid=self.employee('T-LEAVE'); substitute=self.employee('T-SUB')
        sid=self.shift('请假测试','08:00','16:00')
        body,(status,result)=self.plan(eid,sid,line='加工二线',required_count=1)
        self.assertEqual(status,200,result); pid=result['id']
        leave={'employee_id':eid,'start_at':self.day+'T09:00','end_at':self.day+'T12:00','reason':'私人请假原因'}
        self.assertEqual(self.op.call('/workforce/leaves',leave)[0],403)
        status,r=self.manager.call('/workforce/leaves',leave); self.assertEqual(status,200,r); lid=r['id']
        self.assertEqual(self.manager.call('/workforce/leaves',leave)[0],409)
        review={'id':lid,'version':1,'action':'approve','review_note':'批准并安排替班'}
        self.assertEqual(self.eng.call('/workforce/leaves',review)[0],403)
        status,r=self.manager.call('/workforce/leaves',review);self.assertEqual(status,200,r);self.assertIn(pid,r['affected_plans'])
        self.assertEqual(self.manager.call('/workforce/leaves',review)[0],409)
        data=self.get_data();p=next(p for p in data['plans'] if p['id']==pid)
        self.assertEqual(p['shortage'],1);self.assertEqual(p['available_count'],0)
        self.assertNotIn('私人请假原因',json.dumps(self.get_data(self.eng),ensure_ascii=False))
        self.assertEqual(self.manager.call('/workforce/plans',{**body,'id':pid,'version':1})[0],409)
        status,r=self.manager.call('/workforce/plans',{**body,'id':pid,'version':1,'employee_ids':[substitute],'note':'请假替班'})
        self.assertEqual(status,200,r)
        p=next(p for p in self.get_data()['plans'] if p['id']==pid)
        self.assertEqual(p['employee_ids'],[substitute]);self.assertEqual(p['shortage'],0)

    def test_04_operator_own_leave_and_cancel(self):
        own=self.get_data(self.op)['own_employee_id']
        b={'employee_id':own,'start_at':self.nextday+'T08:00','end_at':self.nextday+'T09:00','reason':'本人申请测试'}
        status,r=self.op.call('/workforce/leaves',b);self.assertEqual(status,200,r)
        l=next(l for l in self.get_data(self.op)['leaves'] if l['id']==r['id'])
        self.assertEqual(l['reason'],'本人申请测试')
        self.assertEqual(self.op.call('/workforce/leaves',{'id':r['id'],'version':1,'action':'approve','review_note':'自行批准'})[0],403)
        self.assertEqual(self.op.call('/workforce/leaves',{'id':r['id'],'version':1,'action':'cancel','review_note':'本人撤回'})[0],200)

    def test_05_dispatch_qualification_and_record(self):
        # Manager has no initial assignments. An explicit exception is required and retained.
        body={'anomaly_id':2,'assignee':4,'action':'预约下个班次检查设备'}
        status,r=self.eng.call('/tasks',body);self.assertEqual(status,400,r)
        self.assertIn('调度说明',r['error'])
        status,r=self.eng.call('/tasks',{**body,'dispatch_note':'已确认下个班次由生产负责人协调点检'})
        self.assertEqual(status,200,r)
        status,detail=self.eng.call('/tasks/'+str(r['id']))
        self.assertIn('已确认下个班次',detail['events'][0]['note'])
        # Current approved leave excludes a user even if a bypass explanation is provided.
        own=next(e for e in self.get_data()['employees'] if e['user_id']==2)
        start=datetime.now()-timedelta(minutes=10);end=start+timedelta(hours=1)
        status,r=self.admin.call('/workforce/leaves',{'employee_id':own['id'],'start_at':start.isoformat(timespec='minutes'),'end_at':end.isoformat(timespec='minutes'),'reason':'临时请假'})
        self.assertEqual(status,200,r)
        self.assertEqual(self.admin.call('/workforce/leaves',{'id':r['id'],'version':1,'action':'approve','review_note':'批准'})[0],200)
        status,r=self.eng.call('/tasks',{'anomaly_id':1,'assignee':2,'action':'检查','dispatch_note':'尝试绕过请假'})
        self.assertEqual(status,409,r)

    def test_06_atomic_concurrent_plan_creation(self):
        eid=self.employee('T-RACE');sid=self.shift('并发测试','08:00','16:00')
        body={'factory_id':1,'employee_ids':[eid],'shift_id':sid,'work_date':self.nextday,'line':'检测四线','required_count':1,'required_skill':'生产操作'}
        barrier=threading.Barrier(2);responses=[]
        def publish():
            client=system.Client(self.base,'manager');barrier.wait();responses.append(client.call('/workforce/plans',body)[0])
        threads=[threading.Thread(target=publish) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=20)
        self.assertEqual(sorted(responses),[200,409])

    def test_07_validation_and_idempotency(self):
        self.assertEqual(self.manager.call('/workforce/shifts',{'factory_id':1,'name':'24小时','start_time':'08:00','end_time':'08:00'})[0],400)
        self.assertEqual(self.admin.call('/workforce?factory_id=1&date=2026-02-31')[0],400)
        body={'factory_id':1,'name':'幂等班次','start_time':'06:00','end_time':'14:00'}
        first=self.manager.call('/workforce/shifts',body,key='workforce-shift-key')
        self.assertEqual(first,self.manager.call('/workforce/shifts',body,key='workforce-shift-key'))
        self.assertEqual(first[0],200)
        eid=self.employee('T-STOP');sid=self.shift('停用测试','06:00','14:00')
        _,(code,result)=self.plan(eid,sid,work_date=self.nextday,line='装配三线')
        self.assertEqual(code,200,result)
        employee=next(e for e in self.get_data()['employees'] if e['id']==eid)
        self.assertEqual(self.manager.call('/workforce/employees',{**employee,'status':'停用'})[0],409)

    def test_08_seed_idempotency_and_recommendation(self):
        with connect(config=self.mysql.config) as c:
            before=c.execute('SELECT count(*) FROM staff_plans').fetchone()[0]
            workforce.initialize(c)
            self.assertEqual(c.execute('SELECT count(*) FROM staff_plans').fetchone()[0],before)
            user={'id':1,'username':'admin','role':'admin','factory_id':None}
            # Pick a seeded operator's first shift; freeze recommendation time to its interior.
            p=c.execute('SELECT p.* FROM staff_plans p JOIN staff_assignments a ON a.plan_id=p.id JOIN staff_employees e ON e.id=a.employee_id WHERE e.user_id=3 ORDER BY p.start_at LIMIT 1').fetchone()
            at=(datetime.fromisoformat(p['start_at'])+timedelta(minutes=30)).isoformat()
            with patch('backend.workforce.now',return_value=at):
                result=workforce.candidates(c,user,{'anomaly_id':1})
            operator=next(u for u in result['candidates'] if u['id']==3)
            self.assertTrue(operator['recommended']);self.assertTrue(operator['same_line']);self.assertTrue(operator['skill_match'])
            self.assertTrue(all(u['id'] not in (5,6) for u in result['candidates']))
