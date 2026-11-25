#!/usr/bin/env node
'use strict';
// Chromium responsive + accessibility/interaction regression against generated Pages output.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.BASE_URL || 'http://127.0.0.1:8765/';
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for(const width of [360,390,1280]){
      const page=await browser.newPage({viewport:{width,height:850},acceptDownloads:true});
      for(const [path,card] of [['jobs.html','.job-card'],['regions.html','.region-card']]){
        await page.goto(base+path,{waitUntil:'load'});
        const all=await page.locator(card).count();
        assert.ok(all>0, path+' should contain original records');
        const reset=page.locator('#filter-reset');
        assert.equal(await reset.count(),1,'reset must be in generated source');
        assert.equal(await reset.isDisabled(),true,'empty filters leave reset disabled');
        const query=page.locator('#filter-query');
        await query.fill('no-such-evidence-xyz-2026');
        assert.equal(await page.locator(card+':visible').count(),0,'search hides nonmatching cards');
        assert.match(await page.locator('#filter-count').innerText(),/0 \/ /);
        assert.equal(await page.locator('#filter-empty').isVisible(),true);
        await reset.click();
        assert.equal(await query.inputValue(),'');
        assert.equal(await page.locator(card+':visible').count(),all,'reset restores all records');
        assert.equal(await page.locator('#filter-empty').isVisible(),false);
        assert.equal(await reset.isDisabled(),true);
        await page.locator('#filter-verified').check();
        assert.equal(await reset.isEnabled(),true);
        await reset.click();
        assert.equal(await page.locator('#filter-verified').isChecked(),false);
        const selects=page.locator('#filter-region option');
        if(await selects.count()>1){
          const first=(await selects.nth(1).getAttribute('value'))||(await selects.nth(1).textContent());
          await page.locator('#filter-region').selectOption(first);
          assert.equal(await reset.isEnabled(),true);
          await reset.click();
          assert.equal(await page.locator('#filter-region').inputValue(),'');
        }

        if(path==='jobs.html'){
          assert.equal(await page.locator('#filter-export').count(),1,'job audit download exists');
          assert.equal(await page.locator('#filter-export').isDisabled(),false,'visible records can be exported');
          await query.fill('Graphcore');
          assert.equal(await page.locator('.job-card:visible').count(),1);
          assert.equal(await page.locator('.job-card:visible .deadline-audit').isVisible(),true,'past recorded deadline must be flagged');
          assert.match(await page.locator('.job-card:visible .deadline-audit').innerText(),/2026-11-15/);
          const wait=page.waitForEvent('download');
          await page.locator('#filter-export').click();
          const download=await wait;
          assert.match(download.suggestedFilename(),/^AI岗位研究核验清单-\d{4}-\d{2}-\d{2}\.txt$/);
          const content=fs.readFileSync(await download.path(),'utf8');
          for(const term of ['Graphcore','JD-UK-01','2026-11-15','2026-11-13','job-boards.greenhouse.io','AIPMAndy','metaver.vip','a6no1.cn'])assert.ok(content.includes(term),'missing export field '+term);
          assert.ok(!content.includes('Atlassian'),'filtered export should not include nonmatching records');
          await reset.click();
        }
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),true,'no horizontal overflow at '+width);
        assert.match(await page.locator('footer').innerText(),/AIPMAndy/);
        assert.match(await page.locator('footer').innerText(),/a6no1.cn/);
      }
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.goto(base+'self-check.html',{waitUntil:'load'});
      const wizard=page.locator('#route-wizard');
      const result=page.locator('#wizard-result');
      for(const [name,value] of Object.entries({eligibility:'confirmed',programming:'independent',math:'strong',research:'independent',preference:'research'})){
        await wizard.locator('#'+name).selectOption(value);
      }
      await wizard.locator('button[type=submit]').click();
      assert.match(await result.innerText(),/你已自报完成资格核查/);
      const eligibility=wizard.locator('#eligibility');
      await eligibility.focus();
      await eligibility.selectOption('blocked');
      assert.match(await result.innerText(),/之前的判断已失效/);
      assert.equal(await result.locator('a').count(),0,'old actionable links removed');
      assert.equal(await eligibility.evaluate(el=>document.activeElement===el),true,'editing focus retained');
      await wizard.locator('button[type=submit]').click();
      assert.match(await result.innerText(),/本轮先排除该岗位的资格障碍/);
      await wizard.locator('#programming').selectOption('');
      assert.match(await result.innerText(),/之前的判断已失效/);
      await wizard.locator('button[type=submit]').click();
      assert.match(await result.innerText(),/之前的判断已失效/,'invalid form cannot recreate recommendation');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),true,'self check no horizontal overflow');
      await page.close();
    }
    console.log('PASS: source-dated JD deadline cautions, UTF-8 filtered TXT export, both filters, 360/390/1280px');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
