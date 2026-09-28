/** Compare the byte codec with IDL sections emitted by compiled Anchor macros.
 * Usage: node solana/tests/compare-host-idl.mjs /path/to/host-generated-idl-sections.json
 * This does not execute a transaction or import the uninstalled web3 client.
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createQuestionData, forecastData, resolutionData, discriminator, fromBase58, toBase58} from '../client/codec.mjs';

if (!process.argv[2]) throw Error('Provide the generated host IDL sections JSON path');
const sections=JSON.parse(readFileSync(process.argv[2],'utf8'));
const idl=sections.program;
assert.equal(idl.metadata.name,'predictkit_registry');
const checks=[];
function check(name,fn){fn();checks.push(name);}
function encode(type,value){
  if(type==='pubkey')return fromBase58(value,32);
  if(type==='string'){const b=Buffer.from(value),length=Buffer.alloc(4);length.writeUInt32LE(b.length);return Buffer.concat([length,b]);}
  if(type==='i64'){const b=Buffer.alloc(8);b.writeBigInt64LE(value);return b;}
  if(type==='u16'){const b=Buffer.alloc(2);b.writeUInt16LE(value);return b;}
  if(type==='u8')return Buffer.from([value]);
  if(type?.array?.[0]==='u8'){assert.equal(value.length,type.array[1]);return Buffer.from(value);}
  throw Error('Unreviewed IDL field type: '+JSON.stringify(type));
}
function encodedInstruction(instruction,args){
  return Buffer.concat([Buffer.from(instruction.discriminator),...instruction.args.map(field=>encode(field.type,args[field.name]))]);
}
const question='界'.repeat(66)+'ab';
const creatorArgs={id:Buffer.alloc(32,1),question,rules_hash:Buffer.alloc(32,2),closes_at:200n,resolves_after:300n,resolver:toBase58(Buffer.alloc(32,8))};
const cases={
  create_question:[creatorArgs,createQuestionData({id:creatorArgs.id,question,rulesHash:creatorArgs.rules_hash,closesAt:200n,resolvesAfter:300n,resolver:creatorArgs.resolver})],
  submit_forecast:[{probability_bps:10000},forecastData(10000)],
  resolve_question:[{outcome:3,evidence_hash:Buffer.alloc(32,3)},resolutionData('VOID',Buffer.alloc(32,3))],
};
const accountOrder={
  create_question:[['authority',true,true],['question_account',false,true],['system_program',false,false]],
  submit_forecast:[['forecaster',true,true],['question_account',false,true],['forecast',false,true],['system_program',false,false]],
  resolve_question:[['resolver',true,false],['question_account',false,true]],
};
assert.deepEqual(idl.instructions.map(i=>i.name),Object.keys(cases));
for(const instruction of idl.instructions){
  check(instruction.name+' discriminator',()=>assert.deepEqual(Buffer.from(instruction.discriminator),discriminator('global',instruction.name)));
  check(instruction.name+' complete encoded bytes',()=>assert.deepEqual(encodedInstruction(instruction,cases[instruction.name][0]),cases[instruction.name][1]));
  check(instruction.name+' declared client account order/flags',()=>assert.deepEqual(instruction.accounts.map(a=>[a.name,!!a.signer,!!a.writable]),accountOrder[instruction.name]));
}
for(const account of idl.accounts){
  const name=account.name.split('::').at(-1);
  check(name+' account discriminator',()=>assert.deepEqual(Buffer.from(account.discriminator),discriminator('account',name)));
}
const expectedFields={
  Question:['authority','resolver','id','question','rules_hash','closes_at','resolves_after','outcome','resolved_at','evidence_hash','forecast_count','bump'],
  Forecast:['question','forecaster','probability_bps','created_at','bump'],
};
for(const type of idl.types){
  const name=type.name.split('::').at(-1);
  check(name+' account field order',()=>assert.deepEqual(type.type.fields.map(f=>f.name),expectedFields[name]));
}
console.log(JSON.stringify({kind:'compiled-host-idl-comparison',passed:checks.length,checks,boundary:'IDL/codec and declared metadata comparison only; no SBF/SVM execution, installed web3 client or deployment'},null,2));
