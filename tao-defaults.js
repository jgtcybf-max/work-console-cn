// Local work-console defaults. Upstream BackupService owns validation and persistence.
(() => {
  function merge(current, template, day) {
    const backup=structuredClone(current), data=backup.data;
    if(data.project?.entities?.['tao-console'])return {changed:false,backup};
    const seed=structuredClone(template.data);
    for(const key of ['task','project','tag','note','taskRepeatCfg']) {
      const target=data[key]??={ids:[],entities:{}};
      for(const id of seed[key].ids) {
        const incoming=seed[key].entities[id];
        if(!target.entities[id]) {target.ids.push(id);target.entities[id]=incoming;}
        else if(key==='project'||key==='tag') {
          for(const list of ['taskIds','backlogTaskIds','noteIds'])if(incoming[list])target.entities[id][list]=[...new Set([...(target.entities[id][list]||[]),...incoming[list]])];
        }
      }
    }
    const dailyIds=seed.tag.entities.TODAY.taskIds;
    for(const id of dailyIds)if(data.task.entities[id])data.task.entities[id].dueDay=day;
    for(const id of seed.taskRepeatCfg.ids){data.taskRepeatCfg.entities[id].lastTaskCreationDay=day;data.taskRepeatCfg.entities[id].lastTaskCreation=Date.now();}
    data.menuTree??={projectTree:[],tagTree:[]};
    for(const key of ['projectTree','tagTree']){const known=new Set(data.menuTree[key].map(n=>n.id));data.menuTree[key].push(...seed.menuTree[key].filter(n=>!known.has(n.id)));}
    data.boards??={boardCfgs:[]};
    if(!data.boards.boardCfgs.some(b=>b.id==='TAO_CONSOLE'))data.boards.boardCfgs.push(...seed.boards.boardCfgs);
    data.globalConfig.localization={...(data.globalConfig.localization||{}),lng:'zh'};
    data.globalConfig.appFeatures={...data.globalConfig.appFeatures,isBoardsEnabled:true,isPlannerEnabled:true,isProjectNotesEnabled:true,isSearchEnabled:true,isFinishDayEnabled:true,isSchedulerEnabled:true,isFocusModeEnabled:true,isHabitsEnabled:true};
    data.pluginMetadata??=[];
    if(!data.pluginMetadata.some(p=>p.id==='tao-codex-task-bridge'))data.pluginMetadata.push({id:'tao-codex-task-bridge',isEnabled:true});
    backup.timestamp=Date.now();backup.lastUpdate=Date.now();
    return {changed:true,backup};
  }
  async function start(backupService, router) {
    const response=await fetch('/tao-seed.json',{cache:'no-store'});
    if(!response.ok)throw new Error('工作总台初始配置读取失败');
    const current=await backupService.loadCompleteBackup(true);
    const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    const result=merge(current,await response.json(),day);
    if(result.changed)await backupService.importCompleteBackup(result.backup,false,true,false);
    localStorage.setItem('SUP_EXAMPLE_TASKS_CREATED','true');
    localStorage.setItem('SUP_IS_SHOW_TOUR','true');
    // Let the existing route finish before choosing the default work view.
    // Direct hash writes can race the upstream initial navigation back to Today.
    if(router&&!router.navigated)await new Promise(resolve=>{const subscription=router.events.subscribe(event=>{if('urlAfterRedirects' in event){subscription.unsubscribe();resolve();}});});
    if(!location.hash||location.hash==='#/'||location.hash==='#/tag/TODAY/tasks') {
      if(router)await router.navigateByUrl('/boards/TAO_CONSOLE',{replaceUrl:true});
      else location.hash='/boards/TAO_CONSOLE';
    }
    return {initialized:result.changed,language:'zh'};
  }
  // Upstream uses these local preferences before its task store is hydrated.
  for(const key of ['SUP_IS_PROJECT_LIST_EXPANDED','SUP_IS_TAG_LIST_EXPANDED','SUP_IS_VIEW_LIST_EXPANDED'])if(localStorage.getItem(key)===null)localStorage.setItem(key,'true');
  window.TaoConsoleDefaults={merge,start};
})();
