/** Actual compiled SBF execution in an isolated LiteSVM process. No RPC or wallet files. */
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {RegistryClient} from '../client/client.mjs';
import {decodeQuestion, discriminator, toBase58} from '../client/codec.mjs';
const require = createRequire(new URL('../client/package.json', import.meta.url));
export const {LiteSVM, FailedTransactionMetadata, Clock} = require('litesvm');
export const {Keypair, PublicKey, SystemProgram, Transaction, TransactionInstruction} = require('@solana/web3.js');
const {getTransactionDecoder} = require('@solana/kit');
export const {TransactionErrorInstructionError, InstructionErrorCustom} = require('litesvm/dist/internal.js');
// Pinned LiteSVM1.5.0 TypeScript const-enum values are erased at runtime.
// Values are declared in dist/internal.d.ts and checked against observed errors.
export const TransactionErrorFieldless = Object.freeze({SignatureFailure:11, BlockhashNotFound:7});
export const PROGRAM = new PublicKey('8xG2yBTiVUPJRmHUW5JdsYUaBMoqboNoRBVSXL1nAjZT');
export const PROGRAM_PATH = process.env.PREDICTKIT_SBF_PATH || fileURLToPath(new URL('../target/sbpfv3-solana-solana/release/predictkit_registry.so', import.meta.url));
export const PROGRAM_BYTES = readFileSync(PROGRAM_PATH); // Missing .so is a hard failure, never a skip.
export const PROGRAM_HASH = createHash('sha256').update(PROGRAM_BYTES).digest('hex');
assert.equal(PROGRAM_BYTES.subarray(0, 4).toString('hex'), '7f454c46', 'Expected a compiled ELF program');

const i64 = value => { const b=Buffer.alloc(8); b.writeBigInt64LE(BigInt(value)); return b; };
export function rawCreateData(args) {
  const question=Buffer.from(args.question, 'utf8'), size=Buffer.alloc(4);size.writeUInt32LE(question.length);
  return Buffer.concat([discriminator('global','create_question'), Buffer.from(args.id), size, question,
    Buffer.from(args.rulesHash), i64(args.closesAt), i64(args.resolvesAfter), new PublicKey(args.resolver).toBuffer()]);
}
export function rawForecastData(bps) {const b=Buffer.alloc(2);b.writeUInt16LE(bps);return Buffer.concat([discriminator('global','submit_forecast'),b]);}
export function rawResolveData(outcome, hash=Buffer.alloc(32,7)) {return Buffer.concat([discriminator('global','resolve_question'),Buffer.from([outcome]),Buffer.from(hash)]);}
export function failed(result) {return result instanceof FailedTransactionMetadata;}
export function assertSuccess(result) {assert.ok(!failed(result), failed(result) ? result.toString() : 'Expected SVM success');return result;}
export function assertFailure(result, expectedLog) {
  assert.ok(failed(result), 'Expected the SVM to reject the transaction');
  if(expectedLog) assert.match(result.meta().logs().join('\n'), expectedLog);
  return result;
}
export function serialize(value) {return JSON.parse(JSON.stringify(value,(_key,v)=>typeof v==='bigint'?v.toString():v));}

export class Harness {
  constructor() {
    this.svm=new LiteSVM(); // Default signature and blockhash verification stay enabled.
    this.svm.addProgram(PROGRAM.toBase58(), PROGRAM_BYTES);
    this.client=new RegistryClient(null, PROGRAM);
    this.authority=this.key();this.resolver=this.key();this.nextId=1;this.receipts=[];
    this.clock(100n);
    assert.equal(this.svm.getAccount(PROGRAM.toBase58()).executable,true);
  }
  key() {
    const key=Keypair.generate();
    // Explicit synthetic account setup only. No public faucet, file, RPC or persistent secret.
    this.svm.setAccount({address:key.publicKey.toBase58(),programAddress:SystemProgram.programId.toBase58(),data:new Uint8Array(),executable:false,lamports:10_000_000_000n});
    return key;
  }
  clock(timestamp) {const clock=this.svm.getClock();clock.unixTimestamp=BigInt(timestamp);this.svm.setClock(clock);}
  account(key) {return this.svm.getAccount(new PublicKey(key).toBase58());}
  question(key) {return decodeQuestion(this.account(key).data);}
  args(overrides={}) {return {id:Buffer.alloc(32,this.nextId++),question:'Will the reviewed launch milestone be reached?',rulesHash:Buffer.alloc(32,5),closesAt:110n,resolvesAfter:120n,resolver:this.resolver.publicKey.toBase58(),...overrides};}
  create(authority=this.authority,args=this.args(),raw=false) {
    const question=this.client.questionAddress(authority.publicKey,args.id);
    const instruction=new TransactionInstruction({programId:PROGRAM,keys:[{pubkey:authority.publicKey,isSigner:true,isWritable:true},{pubkey:question,isSigner:false,isWritable:true},{pubkey:SystemProgram.programId,isSigner:false,isWritable:false}],data:raw?rawCreateData(args):this.client.create(authority.publicKey,args).instruction.data});
    return {question,args,instruction,result:this.send(instruction,[authority],'create_question')};
  }
  forecast(question,bps,key=this.key(),raw=false) {
    const built=this.client.forecast(key.publicKey,question,Math.min(bps,10000));
    if(raw)built.instruction.data=rawForecastData(bps);
    return {...built,key,result:this.send(built.instruction,[key],'submit_forecast')};
  }
  resolve(question,outcome='YES',resolver=this.resolver,hash=Buffer.alloc(32,7),raw=false) {
    const instruction=this.client.resolve(resolver.publicKey,question,'YES',Buffer.alloc(32,7));
    instruction.data=raw?rawResolveData(outcome,hash):this.client.resolve(resolver.publicKey,question,outcome,hash).data;
    return this.send(instruction,[resolver],'resolve_question');
  }
  transaction(instruction,signers,{invalidSignature=false,blockhash}={}) {
    const tx=new Transaction({feePayer:signers[0].publicKey,recentBlockhash:blockhash||this.svm.latestBlockhash()}).add(instruction);
    tx.sign(...signers);
    if(invalidSignature) tx.signatures[0].signature[0]^=1; // Nonzero forged test signature reaches SVM verification, rather than the kit missing-signature precheck.
    return tx;
  }
  send(instruction,signers,label='instruction',options={}) {
    const tx=this.transaction(instruction,signers,options);
    const bytes=tx.serialize({requireAllSignatures:false,verifySignatures:false});
    const result=this.svm.sendTransaction(getTransactionDecoder().decode(bytes));
    const meta=failed(result)?result.meta():result;
    this.receipts.push({instruction:label,environment:'isolated-local-svm',success:!failed(result),signature:tx.signature?toBase58(tx.signature):null,computeUnits:meta.computeUnitsConsumed().toString(),logs:meta.logs()});
    this.svm.expireBlockhash(); // Ensure repeated account operations test program constraints, not duplicate-transaction caching.
    return result;
  }
}
