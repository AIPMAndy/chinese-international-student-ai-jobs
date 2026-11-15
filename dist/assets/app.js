(function(){
  'use strict';
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const base=document.body.dataset.base||'';
  const menu=$('#menu-toggle'),nav=$('#nav-links');
  if(menu&&nav){menu.addEventListener('click',()=>{const open=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));menu.textContent=open?'收起':'目录';});}
  const temporaryState=new Map();
  const storage={get(k){try{return localStorage.getItem(k)??temporaryState.get(k)??null;}catch(e){return temporaryState.get(k)??null;}},set(k,v){temporaryState.set(k,v);try{localStorage.setItem(k,v);return true;}catch(e){return false;}}};
  const readButton=$('#mark-read');
  if(readButton){const key='ai-jobs-read:'+readButton.dataset.chapter;const update=()=>{const done=storage.get(key)==='1';readButton.textContent=done?'已读 · 取消标记':'标记已读';readButton.setAttribute('aria-pressed',String(done));};update();readButton.addEventListener('click',()=>{const done=storage.get(key)==='1';if(storage.set(key,done?'0':'1'))update();else{readButton.textContent=done?'标记已读':'本次已读（浏览器未保存）';readButton.setAttribute('aria-pressed',String(!done));}});}
  $$('[data-read-status]').forEach(el=>{if(storage.get('ai-jobs-read:'+el.dataset.readStatus)==='1')el.textContent='已读';});
  $$('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(button.dataset.copy);button.textContent='已复制';}catch(e){button.textContent='请长按复制 AIPMAndy';}}));
  function filterCards(kind){
    const cards=$$('.'+kind+'-card');
    if(!cards.length)return;
    const q=$('#filter-query'),country=$('#filter-region'),route=$('#filter-route');
    const check=$('#filter-verified'),count=$('#filter-count'),empty=$('#filter-empty'),reset=$('#filter-reset');
    function run(){
      const needle=(q?q.value:'').trim().toLocaleLowerCase();
      let n=0;
      cards.forEach(card=>{
        const show=(!needle||card.dataset.search.toLocaleLowerCase().includes(needle))&&
          (!country||!country.value||card.dataset.region===country.value)&&
          (!route||!route.value||card.dataset.route===route.value)&&
          (!check||!check.checked||card.dataset.verified==='yes');
        card.hidden=!show;
        if(show)n++;
      });
      if(count)count.textContent='显示 '+n+' / '+cards.length+' 条'+(kind==='job'?'岗位研究记录':'地区资格记录');
      if(empty)empty.hidden=n!==0;
      if(reset)reset.disabled=!(Boolean(needle)||(country&&country.value)||(route&&route.value)||(check&&check.checked));
    }
    [q,country,route,check].filter(Boolean).forEach(el=>el.addEventListener(el.tagName==='INPUT'&&el.type!=='checkbox'?'input':'change',run));
    if(reset)reset.addEventListener('click',()=>{
      if(q)q.value='';
      if(country)country.value='';
      if(route)route.value='';
      if(check)check.checked=false;
      run();
      if(q)q.focus();
    });
    run();
  }
  filterCards('job');filterCards('region');
  const wizard=$('#route-wizard');
  if(wizard){wizard.addEventListener('submit',event=>{event.preventDefault();const v=Object.fromEntries(new FormData(wizard).entries());const result=$('#wizard-result');let title='',reason='',actions=[],link='read/docs-02-gap-and-learning.html';if(v.programming==='none'){title='先建立编程证据，再选技术主线';reason='目前的信息不足以支持直接申请需要独立编码的 AI 技术岗位。先完成一个可自行修改、调试并解释的基础项目，再重新判断。';actions=['独立读取 JSON/CSV、编写函数，并解释报错。','运行第一个教学样例，改一条输入，找到对应输出。','把“照步骤运行”和“自己实现”分开记录。'];}else if(v.programming==='basic'){title='先补一段完整的工程链路';reason='会课程代码是起点。下一步要证明你能从输入、处理到测试独立完成一个小任务。暂不把研究或工程岗位的硬门槛当作已满足。';actions=['选一个目标 JD，列出三项必需能力及对应证据。','补 Python 调试、数据结构和测试；完成样例二的输入校验。','能不用提示解释一次失败后，再决定算法、工程或应用主线。'];}else if(v.preference==='research'&&v.math==='strong'&&v.research==='independent'){title='优先研究算法 / 机器学习路线';reason='你提供的基础允许开始逐 JD 对照研究或应用机器学习要求。研究型岗位还必须核对具体学历、研究方向和个人贡献；自查结果不表示通过招聘门槛。';actions=['把一项研究写成问题、基线、方法、实验、失败与限制。','按目标方向补对照与消融，证明结果不是数据泄漏。','逐岗位核对论文、学位、毕业时间与专业要求。'];link='read/docs-01-role-map.html';}else if(v.math==='strong'&&(v.preference==='research'||v.preference==='models')){title='优先研究应用机器学习路线';reason='编程与数学基础可用于建模和实验准备。没有独立研究证据时，先证明数据、基线、验证和误差分析，不把调用模型写成研究创新。';actions=['完成样例一，解释训练/验证/测试为何分开。','添加一个可比较基线和一次单变量实验。','把数据来源、个人贡献和测试集限制写进项目卡。'];link='read/docs-01-role-map.html';}else if(v.preference==='systems'){title='优先研究 AI 工程路线';reason='把现有编码能力用于模型服务、数据接口与系统可靠性。训练基础设施、GPU 或编译方向仍需要额外专项能力，不能由此直接推定适配。';actions=['完成样例二：正常请求、错误请求、版本与健康检查。','分别记录模型质量和服务延迟，说明硬件与请求条件。','准备一次回滚、超时和并发资源问题的讲解。'];link='projects.html#service';}else{title='优先研究 AI 应用工程路线';reason='先证明你能把检索或模型能力接入任务，并对效果与失败负责。应用工程仍要求独立开发、调试与评测能力。';actions=['完成样例三，分别看检索命中、最终结果和拒答。','加入一个原有样例没有覆盖的问题，保留失败分析。','能解释什么时候用确定性代码、检索或模型，以及权限边界。'];link='projects.html#retrieval';}
  let eligibility='';if(v.eligibility==='unknown'){eligibility='<div class="notice"><strong>第一步：先确认工作资格。</strong><p>当前身份、未来支持、工作地点或毕业窗口仍不明确。先把岗位标为“先确认”，不要把下面的学习方向当作可投结论。</p><a href="'+base+'regions.html">查看地区核验表</a></div>';}else if(v.eligibility==='blocked'){eligibility='<div class="notice"><strong>本轮先排除该岗位的资格障碍。</strong><p>已有明确不符合条件的事项。下面只提供学习方向；选择其他合格职位或取得书面确认后，再进入投递。</p><a href="'+base+'jobs.html">重新筛选岗位</a></div>';}else{eligibility='<p class="small-muted">你已自报完成资格核查。投递当天仍需复查原始 JD 与许可有效期。</p>';}
  result.innerHTML=eligibility+'<p class="eyebrow">下一步学习判断</p><h2>'+title+'</h2><p>'+reason+'</p><ul>'+actions.map(a=>'<li>'+a+'</li>').join('')+'</ul><a class="button secondary" href="'+base+link+'">开始补证据</a><p class="small-muted">这是规则化自查，不计算录用概率，不替代雇主资格审查。回答只在当前浏览器计算，不上传。</p>';result.hidden=false;result.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});});}
  const searchForm=$('#site-search');
  if(searchForm){const input=$('#search-query'),results=$('#search-results'),count=$('#search-count');const data=window.AI_JOBS_SEARCH||[];const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function search(){const query=input.value.trim();if(!query){results.innerHTML='<p class="small-muted">输入岗位名、技术词、国家或具体问题，如“工作资格”“macro F1”“加拿大”。</p>';count.textContent='';return;}const terms=query.toLocaleLowerCase().split(/\s+/).filter(Boolean);const ranked=data.map(d=>{const hay=(d.title+' '+d.text).toLocaleLowerCase();const ok=terms.every(t=>hay.includes(t));return {d,score:ok?terms.reduce((n,t)=>n+(d.title.toLocaleLowerCase().includes(t)?10:1),0):0};}).filter(x=>x.score).sort((a,b)=>b.score-a.score);count.textContent='找到 '+ranked.length+' 篇相关内容';results.innerHTML=ranked.slice(0,40).map(({d})=>{const pos=d.text.toLocaleLowerCase().indexOf(terms[0]);const start=Math.max(0,pos-45);const snippet=d.text.slice(start,start+190);return '<a class="search-item" href="'+base+escape(d.url)+'"><small>'+escape(d.section)+'</small><h2>'+escape(d.title)+'</h2><p>'+(start?'…':'')+escape(snippet)+(start+190<d.text.length?'…':'')+'</p></a>';}).join('')||'<div class="empty-state">没有找到匹配内容。试试更短的词，或从章节目录开始。</div>';}
    const params=new URLSearchParams(location.search);input.value=params.get('q')||'';search();searchForm.addEventListener('submit',e=>{e.preventDefault();search();try{history.replaceState(null,'','?q='+encodeURIComponent(input.value));}catch(err){}});input.addEventListener('input',search);}
})();
