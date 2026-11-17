// Uses only public PluginAPI. The loopback relay exists only while this page is open.
(() => {
  const api = PluginAPI;
  let stopped=false, sessionId=null, wakeTimer=null, connectionError='', pendingResult=null;
  const pageId=crypto.randomUUID();
  const controllers=new Set();
  const allowed = ['title', 'notes', 'isDone', 'dueDay', 'tagIds', 'timeEstimate', 'priority'];
  function assertText(value, name, max) { if (typeof value !== 'string' || !value.trim() || value.length > max) throw new Error(name + '不能为空或过长'); }
  const bridge = {
    version: '2.0.0',
    async call(method, args = {}) {
      const tasks = await api.getTasks();
      if (method === 'status') return { connected: !!sessionId, version: this.version, tasks: tasks.length, language: api.getCurrentLanguage(), projects:(await api.getAllProjects()).length };
      if (method === 'list_projects') return await api.getAllProjects();
      if (method === 'list_tags') return await api.getAllTags();
      if (method === 'list_tasks') return tasks.filter(t => (args.includeDone || !t.isDone) && (!args.projectId || t.projectId === args.projectId) && (!args.tagId || (t.tagIds||[]).includes(args.tagId)) && (!args.query || (t.title + ' ' + (t.notes || '')).toLowerCase().includes(args.query.toLowerCase()))).slice(0, Math.min(args.limit || 100, 500));
      if (method === 'get_task') { const task = tasks.find(t => t.id === args.id); if (!task) throw new Error('未找到任务'); return task; }
      if (method === 'create_task') {
        assertText(args.title, '任务标题', 500);
        const id = await api.addTask({title: args.title, notes: args.notes || '', projectId: args.projectId || 'INBOX_PROJECT', tagIds: args.tagIds || [], ...(args.dueDay ? {dueDay: args.dueDay} : {}), isIgnoreShortSyntax: true});
        return { id, task: (await api.getTasks()).find(t => t.id === id) };
      }
      if (method === 'update_task' || method === 'complete_task') {
        const task = tasks.find(t => t.id === args.id); if (!task) throw new Error('未找到任务');
        if (task.projectId === 'tao-hold' || (task.tagIds||[]).includes('tao-hold-tag')) throw new Error('此任务仍暂停；不能由普通任务更新自动恢复或完成。');
        const updates = method === 'complete_task' ? {isDone: args.isDone !== false} : args.updates;
        if (!updates || typeof updates !== 'object' || Object.keys(updates).some(k => !allowed.includes(k))) throw new Error('更新包含不支持的字段');
        if (updates.title !== undefined) assertText(updates.title, '任务标题', 500);
        if (updates.notes !== undefined && (typeof updates.notes !== 'string' || updates.notes.length > 20000)) throw new Error('备注过长或格式错误');
        await api.updateTask(args.id, updates, {isIgnoreShortSyntax:true});
        const updated = (await api.getTasks()).find(t => t.id === args.id);
        return { id: args.id, task: updated, verified: Object.entries(updates).every(([k,v])=>JSON.stringify(updated?.[k])===JSON.stringify(v)) };
      }
      throw new Error('不支持的任务操作');
    }
  };
  async function post(path,body) {
    const controller=new AbortController();controllers.add(controller);
    try {
      const response=await fetch('/tao-api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal,cache:'no-store'});
      const data=await response.json();
      if(!data.ok){const error=new Error(data.error||'任务连接失败');error.code=data.code;throw error;}
      return data.result;
    } finally {controllers.delete(controller);}
  }
  async function metadata() {
    return {language:api.getCurrentLanguage(),tasks:(await api.getTasks()).length,projects:(await api.getAllProjects()).length,title:document.title,path:location.hash};
  }
  async function connect(takeover=false) {
    const result=await post('connect',{pageId,metadata:await metadata(),takeover});
    sessionId=result.sessionId;connectionError='';return result;
  }
  function schedule(delay=1000) {
    if(stopped)return;
    wakeTimer=setTimeout(loop,delay);
  }
  async function loop() {
    if(stopped)return;
    try {
      if(!sessionId)await connect(false);
      if(pendingResult) {await post('result',pendingResult);pendingResult=null;}
      const next=await post('next',{sessionId,metadata:await metadata()});
      if(stopped)return;
      if(next.command){
        const command=next.command;
        try {pendingResult={sessionId,id:command.id,ok:true,result:await bridge.call(command.method,command.args)};}
        catch(error){pendingResult={sessionId,id:command.id,ok:false,error:String(error.message||error)};}
        // A failed result upload is retried as a receipt, never as another task operation.
        await post('result',pendingResult);pendingResult=null;
      }
      schedule(0);
    } catch(error) {
      connectionError=String(error.message||error);
      if(error.code==='SESSION_EXPIRED'||error.code==='PAGE_ALREADY_CONNECTED'){sessionId=null;pendingResult=null;}
      schedule(error.code==='PAGE_ALREADY_CONNECTED'?5000:2000);
    }
  }
  Object.defineProperty(window, 'TaoCodexTaskBridge', { value: bridge, writable: false, configurable: true });
  api.registerMenuEntry({label:'Codex任务连接',icon:'link',onClick:async()=>{
    try {
      if(sessionId){api.showSnack({msg:'Codex已连接当前工作总台：可读写待办；暂停事项保持锁定。',type:'SUCCESS'});return;}
      // Clicking this named menu explicitly selects this page as the task-management target.
      await connect(true);api.showSnack({msg:'Codex任务连接已切换到当前页面。',type:'SUCCESS'});
    } catch(error){api.showSnack({msg:'连接未完成：'+(error.message||connectionError),type:'ERROR'});}
  }});
  api.registerMenuEntry({label:'视频资料库',icon:'video_library',onClick:()=>window.open('/library.html','_blank','noopener')});
  api.onReady?.(()=>{schedule(0);});
  api.onUnload?.(() => {stopped=true;clearTimeout(wakeTimer);for(const controller of controllers)controller.abort();if(window.TaoCodexTaskBridge===bridge)delete window.TaoCodexTaskBridge;});
})();
