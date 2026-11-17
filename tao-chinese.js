// Local Chinese labels for upstream literals not using the translation catalogue.
(() => {
  const exact=new Map([['Super Productivity','工作总台'],['Changelog','更新日志'],['Logs','运行日志'],['Default','默认'],['Appearance','外观'],['Switch to compact mode','切换为紧凑模式'],['Switch to full mode','切换为完整模式'],['Resize sidenav','调整侧栏宽度'],['Show Help for section','查看本节帮助'],['Close right panel or drag to resize','关闭右侧面板或拖动调整宽度'],['Resize right panel','调整右侧面板宽度'],['High','高'],['Medium','中'],['Low','低']]);
  function translate(value){const trimmed=value.trim();if(exact.has(trimmed))return value.replace(trimmed,exact.get(trimmed));return value}
  function visit(root){if(root.nodeType===3){if(root.parentElement?.closest('textarea,input,script,style,code,pre,[contenteditable],.task-title,.task-title-wrapper'))return;const out=translate(root.nodeValue);if(out!==root.nodeValue)root.nodeValue=out;return}if(root.nodeType!==1)return;for(const attr of ['aria-label','title','placeholder']){if(root.hasAttribute(attr)){const old=root.getAttribute(attr),next=translate(old);if(old!==next)root.setAttribute(attr,next)}}for(const child of root.childNodes)visit(child)}
  let timer;const update=()=>{timer=null;visit(document.body);document.documentElement.lang='zh-CN';if(document.title!=='工作总台 · Super Productivity')document.title='工作总台 · Super Productivity'};
  const observer=new MutationObserver(()=>{if(!timer)timer=setTimeout(update,50)});
  update();observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['aria-label','title','placeholder']});window.TaoChineseLabels='1.0.1';
})();
