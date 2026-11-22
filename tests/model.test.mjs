import test from 'node:test';
import assert from 'node:assert/strict';
import {monthsFor,compare,csv} from '../web/model.mjs';
const dates=['202301','202302','202401','202402','202403'];
test('compares matching months for year-to-date and no partial prior period',()=>{
  assert.deepEqual(monthsFor('202402','ytd',dates),{selected:['202401','202402'],previous:['202301','202302']});
  assert.deepEqual(monthsFor('202403','ytd',dates).previous,[]);
  assert.deepEqual(monthsFor('202402','month',dates),{selected:['202402'],previous:['202302']});
});
test('new and departed partners use all destinations in each period',()=>{
  const r=compare({'202301':{US:25,JP:75},'202401':{US:50,CN:50}},{selected:['202401'],previous:['202301']});
  assert.equal(r.rows.find(x=>x.code==='US').change,25);
  assert.equal(r.rows.find(x=>x.code==='JP').change,-75);
  assert.equal(r.rows.find(x=>x.code==='CN').change,50);
});
test('no reported total or prior data yields unavailable shares',()=>{
  assert.equal(compare({'202301':{US:10}},{selected:['202401'],previous:['202301']}).rows[0].share,null);
  assert.equal(compare({'202401':{US:10}},{selected:['202401'],previous:[]}).rows[0].change,null);
});
test('CSV quotes commas, quotes and missing fields',()=>{
  assert.equal(csv([['A, B','"C"',null]]),'"A, B","""C""",""\r\n');
});
