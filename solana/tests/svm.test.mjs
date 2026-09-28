import test from 'node:test';
import assert from 'node:assert/strict';
import {Harness, PROGRAM, PROGRAM_HASH, PROGRAM_BYTES, PublicKey, SystemProgram, assertSuccess, assertFailure, rawCreateData, rawForecastData, TransactionErrorFieldless, TransactionErrorInstructionError, InstructionErrorCustom} from './svm-harness.mjs';
import {discriminator} from '../client/codec.mjs';

function created(h,args) {const result=h.create(h.authority,args);assertSuccess(result.result);return result;}
function bytes(h,key) {return Buffer.from(h.account(key).data);}
function duplicate(result) {assertFailure(result,/already in use/);assert.ok(result.err() instanceof TransactionErrorInstructionError);assert.equal(result.err().index,0);assert.ok(result.err().err() instanceof InstructionErrorCustom);assert.equal(result.err().err().code,0);}
function signatureFailure(result) {assertFailure(result);assert.equal(result.err(),TransactionErrorFieldless.SignatureFailure);}

test('compiled ELF is loaded into LiteSVM and create stores exact immutable fields',()=>{
  const h=new Harness(),{question,args}=created(h),q=h.question(question),account=h.account(question);
  assert.equal(account.programAddress,PROGRAM.toBase58());assert.equal(account.data.length,406);
  assert.equal(q.authority,h.authority.publicKey.toBase58());assert.equal(q.resolver,args.resolver);assert.equal(q.question,args.question);
  assert.equal(q.id,args.id.toString('hex'));assert.equal(q.rulesHash,args.rulesHash.toString('hex'));
  assert.equal(q.closesAt,110n);assert.equal(q.resolvesAfter,120n);assert.equal(q.forecastCount,0n);assert.equal(q.outcome,'OPEN');
  assert.equal(PublicKey.findProgramAddressSync([Buffer.from('question'),h.authority.publicKey.toBuffer(),args.id],PROGRAM)[1],q.bump);
  assert.ok(PROGRAM_BYTES.length>1000);assert.match(PROGRAM_HASH,/^[a-f0-9]{64}$/);
});

test('empty, whitespace and over-200-byte questions rejected by actual program',()=>{
  const h=new Harness();for(const question of ['', '   ', 'a'.repeat(201), 'é'.repeat(101)]){
    const result=h.create(h.authority,h.args({question}),true);assertFailure(result.result,/InvalidQuestion/);assert.equal(h.account(result.question).exists,false);
  }
});

test('exact 200-byte UTF-8 question succeeds and decodes',()=>{
  const h=new Harness(),q=created(h,h.args({question:'é'.repeat(100)}));assert.equal(h.question(q.question).question,'é'.repeat(100));
});

test('zero rule hash and default resolver rejected by program',()=>{
  const h=new Harness();for(const [override,expected] of [[{rulesHash:Buffer.alloc(32)},/InvalidHash/],[{resolver:SystemProgram.programId.toBase58()},/InvalidResolver/]]){
    const q=h.create(h.authority,h.args(override),true);assertFailure(q.result,expected);assert.equal(h.account(q.question).exists,false);
  }
});

test('past or current close and resolution before close rejected',()=>{
  const h=new Harness();for(const override of [{closesAt:99n},{closesAt:100n},{resolvesAfter:109n}])assertFailure(h.create(h.authority,h.args(override),true).result,/InvalidSchedule/);
});

test('duplicate creator/id rejected and original account unchanged',()=>{
  const h=new Harness(),q=created(h),before=bytes(h,q.question);
  duplicate(h.create(h.authority,{...q.args,question:'Attempted replacement'}).result);assert.deepEqual(bytes(h,q.question),before);
});

test('same ID with different creator produces distinct PDA',()=>{
  const h=new Harness(),q=created(h),other=h.key(),second=h.create(other,q.args);assertSuccess(second.result);assert.notEqual(second.question.toBase58(),q.question.toBase58());assert.equal(h.question(second.question).authority,other.publicKey.toBase58());
});

test('invalid creator signature rejected by enabled SVM signature checks',()=>{
  const h=new Harness(),args=h.args(),built=h.client.create(h.authority.publicKey,args);
  signatureFailure(h.send(built.instruction,[h.authority],'invalid-signature',{invalidSignature:true}));assert.equal(h.account(built.question).exists,false);
});

test('creator meta without signer flag rejected despite signed fee payer',()=>{
  const h=new Harness(),other=h.key(),built=h.client.create(h.authority.publicKey,h.args());built.instruction.keys[0].isSigner=false;
  assertFailure(h.send(built.instruction,[other]),/AccountNotSigner/);assert.equal(h.account(built.question).exists,false);
});

test('forecast endpoints 0 and 10000 accepted with independent immutable accounts',()=>{
  const h=new Harness(),q=created(h);for(const bps of [0,10000]){
    const f=h.forecast(q.question,bps);assertSuccess(f.result);const a=h.account(f.forecast),data=Buffer.from(a.data);
    assert.equal(a.programAddress,PROGRAM.toBase58());assert.equal(data.length,83);assert.deepEqual(data.subarray(0,8),discriminator('account','Forecast'));
    assert.deepEqual(data.subarray(8,40),q.question.toBuffer());assert.deepEqual(data.subarray(40,72),f.key.publicKey.toBuffer());assert.equal(data.readUInt16LE(72),bps);assert.equal(data.readBigInt64LE(74),100n);
  }assert.equal(h.question(q.question).forecastCount,2n);
});

test('forecast above 10000 rejected by Rust even when client guard bypassed',()=>{
  const h=new Harness(),q=created(h),before=bytes(h,q.question),f=h.forecast(q.question,10001,h.key(),true);
  assertFailure(f.result,/InvalidProbability/);assert.deepEqual(bytes(h,q.question),before);assert.equal(h.account(f.forecast).exists,false);
});

test('forecast just before close accepted; at and after close rejected',()=>{
  const h=new Harness(),q=created(h);h.clock(109n);assertSuccess(h.forecast(q.question,5000).result);
  for(const time of [110n,111n]){h.clock(time);const f=h.forecast(q.question,5000);assertFailure(f.result,/ForecastClosed/);assert.equal(h.account(f.forecast).exists,false);}
  assert.equal(h.question(q.question).forecastCount,1n);
});

test('same wallet/question cannot update forecast or increment count twice',()=>{
  const h=new Harness(),q=created(h),key=h.key(),f=h.forecast(q.question,4200,key);assertSuccess(f.result);const before=bytes(h,f.forecast);
  duplicate(h.forecast(q.question,7000,key).result);assert.deepEqual(bytes(h,f.forecast),before);assert.equal(h.question(q.question).forecastCount,1n);
});

test('question with wrong owner rejected',()=>{
  const h=new Harness(),q=created(h),account=h.account(q.question);h.svm.setAccount({...account,programAddress:SystemProgram.programId.toBase58()});
  assertFailure(h.forecast(q.question,5000).result,/AccountOwnedByWrongProgram/);
});

test('forged question at noncanonical PDA rejected',()=>{
  const h=new Harness(),q=created(h),forged=h.key().publicKey,account=h.account(q.question);h.svm.setAccount({...account,address:forged.toBase58()});
  assertFailure(h.forecast(forged,5000).result,/ConstraintSeeds/);assert.equal(h.question(q.question).forecastCount,0n);
});

test('wrong question discriminator rejected',()=>{
  const h=new Harness(),q=created(h),account=h.account(q.question),data=Buffer.from(account.data);data[0]^=1;h.svm.setAccount({...account,data});
  assertFailure(h.forecast(q.question,5000).result,/AccountDiscriminatorMismatch/);
});

test('unauthorized resolver rejected and original state retained',()=>{
  const h=new Harness(),q=created(h),before=bytes(h,q.question);h.clock(120n);assertFailure(h.resolve(q.question,'YES',h.key()),/ConstraintHasOne/);assert.deepEqual(bytes(h,q.question),before);
});

test('authorized resolver before resolves_after rejected',()=>{
  const h=new Harness(),q=created(h);h.clock(119n);assertFailure(h.resolve(q.question),/TooEarly/);assert.equal(h.question(q.question).outcome,'OPEN');
});

for(const outcome of ['YES','NO','VOID'])test(`${outcome} resolves at exact allowed time with immutable evidence`,()=>{
  const h=new Harness(),q=created(h);h.clock(120n);assertSuccess(h.resolve(q.question,outcome));const value=h.question(q.question);assert.equal(value.outcome,outcome);assert.equal(value.resolvedAt,120n);assert.equal(value.evidenceHash,Buffer.alloc(32,7).toString('hex'));
});

test('unknown outcome and zero evidence rejected by program',()=>{
  const h=new Harness(),q=created(h);h.clock(120n);for(const outcome of [0,4,255])assertFailure(h.resolve(q.question,outcome,h.resolver,Buffer.alloc(32,7),true),/InvalidOutcome/);
  assertFailure(h.resolve(q.question,1,h.resolver,Buffer.alloc(32),true),/InvalidHash/);assert.equal(h.question(q.question).outcome,'OPEN');
});

test('repeated resolution rejected without replacing evidence/outcome',()=>{
  const h=new Harness(),q=created(h);h.clock(120n);assertSuccess(h.resolve(q.question,'YES'));const before=bytes(h,q.question);h.clock(130n);
  assertFailure(h.resolve(q.question,'NO',h.resolver,Buffer.alloc(32,9)),/AlreadyResolved/);assert.deepEqual(bytes(h,q.question),before);
});

test('late forecast after resolution rejected without account/count mutation',()=>{
  const h=new Harness(),q=created(h);h.clock(120n);assertSuccess(h.resolve(q.question));const before=bytes(h,q.question),f=h.forecast(q.question,5000);
  assertFailure(f.result,/ForecastClosed/);assert.deepEqual(bytes(h,q.question),before);assert.equal(h.account(f.forecast).exists,false);
});

test('expired blockhash rejected by enabled SVM blockhash check',()=>{
  const h=new Harness(),old=h.svm.latestBlockhash();h.svm.expireBlockhash();const built=h.client.create(h.authority.publicKey,h.args());
  const rejection=h.send(built.instruction,[h.authority],'expired-blockhash',{blockhash:old});assertFailure(rejection);assert.equal(rejection.err(),TransactionErrorFieldless.BlockhashNotFound);assert.equal(h.account(built.question).exists,false);
});

test('forged forecast PDA rejected without incrementing question',()=>{
  const h=new Harness(),q=created(h),key=h.key(),built=h.client.forecast(key.publicKey,q.question,5000);
  built.instruction.keys[2].pubkey=h.key().publicKey;
  assertFailure(h.send(built.instruction,[key]),/ConstraintSeeds/);assert.equal(h.question(q.question).forecastCount,0n);
});

test('invalid forecaster and resolver signatures rejected',()=>{
  const h=new Harness(),q=created(h),key=h.key(),forecast=h.client.forecast(key.publicKey,q.question,5000);
  signatureFailure(h.send(forecast.instruction,[key],'invalid-forecaster',{invalidSignature:true}));assert.equal(h.question(q.question).forecastCount,0n);
  h.clock(120n);const instruction=h.client.resolve(h.resolver.publicKey,q.question,'YES',Buffer.alloc(32,7));
  signatureFailure(h.send(instruction,[h.resolver],'invalid-resolver',{invalidSignature:true}));assert.equal(h.question(q.question).outcome,'OPEN');
});

test('counter overflow rolls back new forecast account and retains prior question',()=>{
  const h=new Harness(),q=created(h),account=h.account(q.question),data=Buffer.from(account.data);
  const stringBytes=data.readUInt32LE(104),countOffset=108+stringBytes+32+8+8+1+8+32;
  data.writeBigUInt64LE(0xffffffffffffffffn,countOffset);h.svm.setAccount({...account,data});
  const before=bytes(h,q.question),f=h.forecast(q.question,5000);assertFailure(f.result,/Overflow/);
  assert.deepEqual(bytes(h,q.question),before);assert.equal(h.account(f.forecast).exists,false);
});
