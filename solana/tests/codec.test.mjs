import test from 'node:test';import assert from 'node:assert/strict';
import {fromBase58,toBase58,digest,discriminator,rulesHash,createQuestionData,forecastData,resolutionData,decodeQuestion,DEVNET_GENESIS} from '../client/codec.mjs';
import {verifyObservation} from '../client/inspect-devnet.mjs';
const authority=toBase58(Buffer.alloc(32,7)),resolver=toBase58(Buffer.alloc(32,8)),programId=toBase58(Buffer.alloc(32,9)),questionAddress=toBase58(Buffer.alloc(32,10));
function fixture(){const b=Buffer.alloc(406);let p=0;const put=x=>{Buffer.from(x).copy(b,p);p+=x.length;};put(discriminator('account','Question'));put(fromBase58(authority,32));put(fromBase58(resolver,32));put(Buffer.alloc(32,5));const q=Buffer.from('Ship by Friday?');const l=Buffer.alloc(4);l.writeUInt32LE(q.length);put(l);put(q);put(digest('rules'));for(const n of [200n,300n]){const v=Buffer.alloc(8);v.writeBigInt64LE(n);put(v);}put([0]);put(Buffer.alloc(8));put(Buffer.alloc(32));put(Buffer.alloc(8));put([255]);return b;}
const args={id:Buffer.alloc(32,1),question:'Ship by Friday?',rulesHash:digest('rules'),closesAt:200n,resolvesAfter:300n,resolver};
test('base58 canonical all-zero key',()=>assert.deepEqual(fromBase58('1'.repeat(32),32),Buffer.alloc(32)));
test('base58 preserves leading zeros and roundtrips',()=>{for(let n=0;n<32;n++){const b=Buffer.concat([Buffer.alloc(n),Buffer.alloc(32-n,9)]);assert.deepEqual(fromBase58(toBase58(b),32),b);}});
test('invalid base58 rejected',()=>assert.throws(()=>fromBase58('O0Il',32)));
test('wrong key length rejected',()=>assert.throws(()=>fromBase58('111',32)));
test('rule hash deterministic and void-policy sensitive',()=>{assert.deepEqual(rulesHash('rule','void','source'),rulesHash('rule','void','source'));assert.notDeepEqual(rulesHash('rule','void','source'),rulesHash('rule','other','source'));});
test('empty resolution source rejected',()=>assert.throws(()=>rulesHash('rule','void','')));
test('create bytes carry discriminator and full question',()=>{const b=createQuestionData(args);assert.deepEqual(b.subarray(0,8),discriminator('global','create_question'));assert.equal(b.readUInt32LE(40),15);assert.equal(b.subarray(44,59).toString(),'Ship by Friday?');});
test('question limit uses UTF-8 bytes not characters',()=>assert.throws(()=>createQuestionData({...args,question:'界'.repeat(67)})));
test('reversed resolution schedule rejected',()=>assert.throws(()=>createQuestionData({...args,resolvesAfter:1n})));
test('zero rule hash rejected',()=>assert.throws(()=>createQuestionData({...args,rulesHash:Buffer.alloc(32)})));
test('all probability boundary bytes encoded correctly',()=>{for(const n of [0,1,9999,10000])assert.equal(forecastData(n).readUInt16LE(8),n);});
test('invalid probability types rejected',()=>{for(const n of [-1,10001,1.5,NaN,'50',true])assert.throws(()=>forecastData(n));});
test('resolution allows only YES NO VOID',()=>{for(const [i,n] of ['YES','NO','VOID'].entries())assert.equal(resolutionData(n,digest('evidence'))[8],i+1);assert.throws(()=>resolutionData('MAYBE',digest('evidence')));});
test('resolution requires evidence hash',()=>assert.throws(()=>resolutionData('YES',Buffer.alloc(32))));
test('decode account layout',()=>{const q=decodeQuestion(fixture());assert.equal(q.authority,authority);assert.equal(q.resolver,resolver);assert.equal(q.question,'Ship by Friday?');assert.equal(q.closesAt,200n);assert.equal(q.outcome,'OPEN');});
test('wrong account discriminator rejected',()=>{const b=fixture();b[0]^=1;assert.throws(()=>decodeQuestion(b));});
test('truncated account rejected',()=>assert.throws(()=>decodeQuestion(fixture().subarray(0,140))));
test('nonzero extra padding rejected',()=>{const b=fixture();b[b.length-1]=1;assert.throws(()=>decodeQuestion(b));});
function observation(){return {genesis:DEVNET_GENESIS,program:{value:{executable:true}},account:{context:{slot:12},value:{owner:programId,executable:false,data:[fixture().toString('base64'),'base64']}},programId,questionAddress};}
test('read-only observation decodes correct owner account',()=>assert.equal(verifyObservation(observation()).question.question,'Ship by Friday?'));
test('mainnet or unknown genesis rejected',()=>assert.throws(()=>verifyObservation({...observation(),genesis:'mainnet'})));
test('nonexecutable program rejected',()=>assert.throws(()=>verifyObservation({...observation(),program:{value:{executable:false}}})));
test('wrong account owner rejected',()=>{const o=observation();o.account.value.owner=resolver;assert.throws(()=>verifyObservation(o));});
test('unrelated successful transaction is not proof',()=>{const o=observation();o.signature=toBase58(Buffer.alloc(64,2));o.transaction={meta:{err:null},transaction:{signatures:[o.signature],message:{accountKeys:[],instructions:[]}}};assert.throws(()=>verifyObservation(o));});
test('resolver signature and registry invocation required',()=>{const o=observation();o.signature=toBase58(Buffer.alloc(64,2));o.transaction={slot:11,meta:{err:null},transaction:{signatures:[o.signature],message:{accountKeys:[{pubkey:resolver,signer:true}],instructions:[{programId,accounts:[resolver,questionAddress],data:toBase58(resolutionData('YES',digest('evidence')))}]}}};assert.equal(verifyObservation(o).invocation.instruction,'resolve_question');o.transaction.transaction.message.accountKeys[0].signer=false;assert.throws(()=>verifyObservation(o));});
test('create receipt inspection accepts full instruction data at question byte limit',()=>{
  const data=createQuestionData({...args,question:'界'.repeat(66)+'ab'});
  const encoded=toBase58(data);
  assert.ok(encoded.length>100);
  assert.deepEqual(fromBase58(encoded),data);
  const o=observation();o.signature=toBase58(Buffer.alloc(64,2));
  o.transaction={slot:11,meta:{err:null},transaction:{signatures:[o.signature],message:{
    accountKeys:[{pubkey:authority,signer:true}],
    instructions:[{programId,accounts:[authority,questionAddress,'1'.repeat(32)],data:encoded}]
  }}};
  assert.equal(verifyObservation(o).invocation.instruction,'create_question');
  o.transaction.transaction.message.accountKeys[0].signer=false;
  assert.throws(()=>verifyObservation(o),/creator signature/);
});
test('base58 instruction decoder retains a bounded input size',()=>assert.throws(()=>fromBase58('1'.repeat(2049)),/Invalid base58/));
test('hash strings reject trailing garbage, odd lengths and invalid characters',()=>{
  const valid='ab'.repeat(32);
  for(const invalid of [valid+'zz',valid+'a',valid+' ', '0x'+valid,valid.slice(0,-1)+'z']){
    assert.throws(()=>resolutionData('YES',invalid),/hexadecimal/);
    assert.throws(()=>createQuestionData({...args,rulesHash:invalid}),/hexadecimal/);
  }
  assert.deepEqual(resolutionData('YES',valid.toUpperCase()),resolutionData('YES',Buffer.from(valid,'hex')));
});
