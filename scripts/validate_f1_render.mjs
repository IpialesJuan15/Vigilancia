// Automated local UI check using the technical fixture created by validate_f1_live.py.
// The child process returns a test session through a private pipe; it is never logged.
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { readFileSync, mkdirSync } from 'node:fs';
const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium, expect } = require('@playwright/test');
const base = 'http://localhost:3000';
const python = `from sqlalchemy import select
from fastapi import Response
from http.cookies import SimpleCookie
from app.db import SessionLocal
from app.models import User
from app.security import set_session
with SessionLocal() as db:
    user=db.scalar(select(User).where(User.email=='f1-validation@tests.example.org'))
    assert user and user.name=='Validación técnica F1'
    response=Response()
    set_session(response,user)
    cookie=SimpleCookie();cookie.load(response.headers['set-cookie'])
    print(cookie['session'].value)
`;
const cookie = execFileSync('docker', ['compose','exec','-T','api','sh','/app/entrypoint.sh','python','-'], {input:python,encoding:'utf8'}).trim();
const report = JSON.parse(readFileSync('docs/evidence/f1-live.json','utf8'));
mkdirSync('/tmp/f1-ui-proof',{recursive:true});
const browser = await chromium.launch({ executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || '/usr/bin/chromium', headless:true });
try {
  for (const width of [1440,390]) {
    const context=await browser.newContext({viewport:{width,height:1000}});
    await context.addCookies([{name:'session',value:cookie,url:base,httpOnly:true,sameSite:'Lax'}]);
    const page=await context.newPage();
    for (const [index, article] of report.articles.entries()) {
      await page.goto(`${base}/revisiones/${article.review_id}`);
      await expect(page.locator('h1')).toHaveText(article.title);
      await page.getByRole('tab',{name:`Tablas (${article.tables})`,exact:true}).click();
      await expect(page.getByRole('cell').filter({hasText:article.sample_cell}).first()).toBeVisible();
      if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)) throw new Error(`Horizontal page overflow: ${article.doi} at ${width}`);
      await page.screenshot({path:`/tmp/f1-ui-proof/review-${index+1}-${width}.png`});
      await page.getByRole('tab',{name:`Referencias (${article.references})`,exact:true}).click();
      await expect(page.locator('.reference').first()).toBeVisible();
      console.log(article.doi,width,'tables/references visible');
    }
    await context.close();
  }
} finally { await browser.close(); }
