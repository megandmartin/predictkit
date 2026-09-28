/** Local byte-codec utilities, independently unit tested; NOT a chain SDK/test. */
import {createHash} from 'node:crypto';
export const PROGRAM_SEED = 'question';
export const DEVNET_GENESIS = 'EtWTRABZaYq6iMfeYKouRu166VU2xqa1';
export const MAX_QUESTION_BYTES = 200;
// RPC instruction data can exceed address/signature lengths. Keep decoding
// bounded while allowing the full base58 payload of a Solana transaction.
const MAX_BASE58_CHARS = 2048;
const alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
export function fromBase58(s, expectedLength) {
  if(typeof s!=='string' || !s.length || s.length>MAX_BASE58_CHARS) throw Error('Invalid base58');
  let n=0n;for(const c of s){const i=alphabet.indexOf(c);if(i<0)throw Error('Invalid base58');n=n*58n+BigInt(i);}
  let hex=n.toString(16); if(hex.length%2)hex='0'+hex;
  const tail=n===0n?Buffer.alloc(0):Buffer.from(hex,'hex');
  let zeros=0;while(s[zeros]==='1')zeros++;
  const b=Buffer.concat([Buffer.alloc(zeros),tail]);
  if(expectedLength!==undefined && b.length!==expectedLength)throw Error('Wrong byte length');
  return b;
}
export function toBase58(b) {
  b=Buffer.from(b);if(!b.length)throw Error('Empty key');
  let zeros=0;while(zeros<b.length&&b[zeros]===0)zeros++;
  let n=BigInt('0x'+(b.toString('hex')||'0')),s='';
  while(n){s=alphabet[Number(n%58n)]+s;n/=58n;}return '1'.repeat(zeros)+s;
}
export const digest=b=>createHash('sha256').update(b).digest();
export const discriminator=(kind,name)=>digest(`${kind}:${name}`).subarray(0,8);
function hash32(h){
  // Buffer.from(hex) silently truncates invalid/odd hex; reject that ambiguity.
  if(typeof h==='string'&&!/^[0-9a-fA-F]{64}$/.test(h))throw Error('Exactly 64 hexadecimal characters required');
  const b=typeof h==='string'?Buffer.from(h,'hex'):Buffer.from(h);
  if(b.length!==32||b.every(x=>x===0))throw Error('Nonzero 32-byte hash required');return b;
}
export function rulesHash(rule, voidPolicy, source) {
  // Versioned canonical form: an ordered JSON array of three exact strings.
  for(const s of [rule,voidPolicy,source])if(typeof s!=='string'||!s.trim())throw Error('Explicit rule, void policy and source required');
  return digest(JSON.stringify(['predictkit-rules-v1',rule,voidPolicy,source]));
}
const i64=n=>{if(typeof n!=='bigint')throw Error('Timestamp must be bigint seconds');const b=Buffer.alloc(8);b.writeBigInt64LE(n);return b;};
export function createQuestionData({id,question,rulesHash,closesAt,resolvesAfter,resolver}) {
  const q=Buffer.from(question,'utf8');
  if(!question.trim()||q.length>MAX_QUESTION_BYTES)throw Error('Invalid question bytes');
  if(resolvesAfter<closesAt)throw Error('Invalid schedule');
  const idBytes=Buffer.from(id);if(idBytes.length!==32)throw Error('32-byte question ID required');
  const resolverBytes=fromBase58(resolver,32);if(resolverBytes.every(x=>x===0))throw Error('Invalid resolver');
  const len=Buffer.alloc(4);len.writeUInt32LE(q.length);
  return Buffer.concat([discriminator('global','create_question'),idBytes,len,q,hash32(rulesHash),i64(closesAt),i64(resolvesAfter),resolverBytes]);
}
export function forecastData(bps){if(!Number.isInteger(bps)||bps<0||bps>10000)throw Error('Invalid probability');const b=Buffer.alloc(2);b.writeUInt16LE(bps);return Buffer.concat([discriminator('global','submit_forecast'),b]);}
export function resolutionData(outcome,evidenceHash){const n={YES:1,NO:2,VOID:3}[outcome];if(!n)throw Error('Invalid outcome');return Buffer.concat([discriminator('global','resolve_question'),Buffer.from([n]),hash32(evidenceHash)]);}
export function decodeQuestion(data) {
  const b=Buffer.from(data);let p=0;
  function take(n){if(p+n>b.length)throw Error('Truncated account');const v=b.subarray(p,p+n);p+=n;return v;}
  if(!take(8).equals(discriminator('account','Question')))throw Error('Wrong account discriminator');
  const authority=toBase58(take(32)),resolver=toBase58(take(32)),id=take(32).toString('hex');
  const length=take(4).readUInt32LE();if(length>200)throw Error('Invalid question length');
  const question=new TextDecoder('utf-8',{fatal:true}).decode(take(length));
  const rulesHash=take(32).toString('hex');
  const closesAt=take(8).readBigInt64LE(),resolvesAfter=take(8).readBigInt64LE();
  const code=take(1)[0];if(code>3)throw Error('Invalid outcome in account');
  const resolvedAt=take(8).readBigInt64LE(),evidenceHash=take(32).toString('hex');
  const forecastCount=take(8).readBigUInt64LE(),bump=take(1)[0];
  // Account allocation has zero padding for the bounded String capacity.
  if(b.length!==8+398 || b.subarray(p).some(x=>x!==0))throw Error('Unexpected account size/padding');
  return {authority,resolver,id,question,rulesHash,closesAt,resolvesAfter,outcome:['OPEN','YES','NO','VOID'][code],resolvedAt,evidenceHash,forecastCount,bump};
}
