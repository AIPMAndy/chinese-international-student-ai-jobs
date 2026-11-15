#!/usr/bin/env node
'use strict';
// Chromium responsive + accessibility/interaction regression against generated Pages output.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const base = process.env.BASE_URL || 'http://127.0.0.1:8765/';
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for(const width of [360,390,1280]){
      const page=await browser.newPage({viewport:{width,height:850}});
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
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),true,'no horizontal overflow at '+width);
        assert.match(await page.locator('footer').innerText(),/AIPMAndy/);
        assert.match(await page.locator('footer').innerText(),/a6no1.cn/);
      }
      await page.close();
    }
    console.log('PASS: AI jobs and region filters, reset, accessible state and 360/390/1280px views');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
