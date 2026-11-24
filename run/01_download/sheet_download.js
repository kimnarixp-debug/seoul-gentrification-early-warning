// 서울 열린데이터광장 데이터셋 시트 화면에서 "내려받기(CSV)"를 실행해 파일을 저장한다.
// 사용법: node sheet_download.js OA-15568 out.csv
const { chromium } = require('playwright');
const [id, out] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({acceptDownloads:true});
  p.on('request', r=>{ if(r.method()==='POST' && !/dataView/.test(r.url())) console.log('REQ', r.url(), (r.postData()||'').slice(0,300)); });
  p.on('dialog', async d=>{ console.log('DIALOG', d.message()); await d.accept(); });
  await p.goto(`https://data.seoul.go.kr/dataList/${id}/S/1/datasetView.do`, {waitUntil:'load', timeout:90000});
  await p.waitForTimeout(4000);
  const dlp = p.waitForEvent('download', {timeout: 600000});
  await p.evaluate(()=>serviceDownload('csv'));
  const d = await dlp; console.log('file', d.suggestedFilename()); await d.saveAs(out); console.log('saved', out);
  await b.close();
})().catch(e=>{console.log('ERR', e.message); process.exit(1)});
