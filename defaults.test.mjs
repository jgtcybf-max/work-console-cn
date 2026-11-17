import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
const template=JSON.parse(await readFile(new URL('./demo-seed.json',import.meta.url),'utf8'));
const context={window:{},structuredClone,localStorage:{getItem:()=>null,setItem:()=>{}}};
vm.runInNewContext(await readFile(new URL('./tao-defaults.js',import.meta.url),'utf8'),context);
const defaults=context.window.TaoConsoleDefaults;
test('首次合并保留原任务并增加演示项目',()=>{
 const current=structuredClone(template);
 for(const key of ['task','tag','project','note','taskRepeatCfg'])current.data[key]={ids:[],entities:{}};
 current.data.task={ids:['mine'],entities:{mine:{id:'mine',title:'My task',projectId:'INBOX_PROJECT'}}};
 current.data.project={ids:['INBOX_PROJECT'],entities:{INBOX_PROJECT:{id:'INBOX_PROJECT',title:'Inbox',taskIds:['mine']}}};
 current.data.menuTree={projectTree:[],tagTree:[]};current.data.boards={boardCfgs:[]};
 const result=defaults.merge(current,template,'2026-01-02');
 assert.equal(result.changed,true);assert.equal(result.backup.data.task.entities.mine.title,'My task');
 assert.equal(result.backup.data.task.ids.length,14);assert.equal(result.backup.data.globalConfig.localization.lng,'zh');
 assert.equal(result.backup.data.boards.boardCfgs[0].title,'工作总台');
 assert.equal(result.backup.data.task.entities['demo-daily-1'].dueDay,'2026-01-02');
});
test('重开不覆盖完成状态或重新加入任务',()=>{
 const current=structuredClone(template);current.data.task.entities['demo-review-1'].isDone=true;
 const result=defaults.merge(current,template,'2026-01-03');
 assert.equal(result.changed,false);assert.equal(result.backup.data.task.entities['demo-review-1'].isDone,true);
 assert.equal(result.backup.data.task.ids.length,13);
});
