// Use the supplied artwork without changing task content or upstream components.
(() => {
  const version='xiefurn-large-20261117';
  if(!document.getElementById('work-console-brand-style')) {
    const style=document.createElement('style');style.id='work-console-brand-style';
    style.textContent='.work-console-brand-icon{font-size:0!important;color:transparent!important;background:#fff url("/brand/logo.png?v='+version+'") center/contain no-repeat!important;border-radius:5px;display:inline-block!important;width:48px!important;height:48px!important;min-width:48px!important;flex-shrink:0!important}.page-title .work-console-brand-icon{width:60px!important;height:60px!important;min-width:60px!important}';
    document.head.append(style);
  }
  function update(){
    for(const node of document.querySelectorAll('[data-view-id="TAO_CONSOLE"] a mat-icon'))node.classList.add('work-console-brand-icon');
    const title=document.querySelector('page-title .page-title-text');
    const icon=document.querySelector('page-title .page-title-icon');
    if(icon)icon.classList.toggle('work-console-brand-icon',title?.textContent.trim()==='工作总台');
  }
  let pending=false;
  const observer=new MutationObserver(()=>{if(!pending){pending=true;requestAnimationFrame(()=>{pending=false;update();});}});
  update();observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  window.WorkConsoleBrand={version};
})();
