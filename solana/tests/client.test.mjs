/** Installed SDK client tests with explicit synthetic transports. No public RPC. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {RegistryClient} from '../client/client.mjs';
import {DEVNET_GENESIS} from '../client/codec.mjs';
const require=createRequire(new URL('../client/package.json',import.meta.url));
const {Keypair,PublicKey,SystemProgram}=require('@solana/web3.js');
const program=new PublicKey('8xG2yBTiVUPJRmHUW5JdsYUaBMoqboNoRBVSXL1nAjZT');
function setup(overrides={}){
 const signer=Keypair.generate(),calls={sign:0,send:0,confirm:0},blockhash=Keypair.generate().publicKey.toBase58();
 const connection={getGenesisHash:async()=>DEVNET_GENESIS,getAccountInfo:async()=>({executable:true}),getLatestBlockhash:async()=>({blockhash,lastValidBlockHeight:100}),sendRawTransaction:async()=>{calls.send++;return 'synthetic-receipt-only';},confirmTransaction:async()=>{calls.confirm++;return {value:{err:null},context:{slot:42}};},...overrides};
 const client=new RegistryClient(connection,program),wallet={publicKey:signer.publicKey,signTransaction:async tx=>{calls.sign++;tx.sign(signer);return tx;}};
 const args={id:Buffer.alloc(32,1),question:'Will the test pass?',rulesHash:Buffer.alloc(32,2),closesAt:110n,resolvesAfter:120n,resolver:signer.publicKey.toBase58()};
 return {client,wallet,calls,signer,instruction:client.create(signer.publicKey,args).instruction};
}
test('SDK derives canonical distinct question and forecast PDAs',()=>{const s=setup(),id=Buffer.alloc(32,1),q=s.client.questionAddress(s.signer.publicKey,id);assert.equal(q.toBase58(),PublicKey.findProgramAddressSync([Buffer.from('question'),s.signer.publicKey.toBuffer(),id],program)[0].toBase58());assert.notEqual(q.toBase58(),s.client.forecastAddress(q,s.signer.publicKey).toBase58());});
test('per-transaction approval required before signing or sending',async()=>{const s=setup();await assert.rejects(s.client.send(s.instruction,s.wallet),/Human approval/);assert.deepEqual(s.calls,{sign:0,send:0,confirm:0});});
test('wrong cluster stops before signing',async()=>{const s=setup({getGenesisHash:async()=> 'wrong-cluster'});await assert.rejects(s.client.send(s.instruction,s.wallet,{approveDevnetTransaction:true}),/devnet/);assert.equal(s.calls.sign,0);});
test('nonexecutable program stops before signing',async()=>{const s=setup({getAccountInfo:async()=>({executable:false})});await assert.rejects(s.client.send(s.instruction,s.wallet,{approveDevnetTransaction:true}),/executable/);assert.equal(s.calls.sign,0);});
test('wallet rejection produces no send and no fallback signing',async()=>{const s=setup();s.wallet.signTransaction=async()=>{s.calls.sign++;throw Error('user rejected');};await assert.rejects(s.client.send(s.instruction,s.wallet,{approveDevnetTransaction:true}),/user rejected/);assert.deepEqual(s.calls,{sign:1,send:0,confirm:0});});
test('wallet message mutation rejected before send',async()=>{const s=setup();s.wallet.signTransaction=async tx=>{s.calls.sign++;tx.add(SystemProgram.transfer({fromPubkey:s.signer.publicKey,toPubkey:Keypair.generate().publicKey,lamports:1}));tx.sign(s.signer);return tx;};await assert.rejects(s.client.send(s.instruction,s.wallet,{approveDevnetTransaction:true}),/modified/);assert.deepEqual(s.calls,{sign:1,send:0,confirm:0});});
test('RPC error propagates with one attempt and no resubmission',async()=>{const s=setup();s.client.connection.sendRawTransaction=async()=>{s.calls.send++;throw Error('synthetic RPC failure');};await assert.rejects(s.client.send(s.instruction,s.wallet,{approveDevnetTransaction:true}),/RPC failure/);assert.deepEqual(s.calls,{sign:1,send:1,confirm:0});});
test('failed confirmation stays a failure with no automatic resend',async()=>{const s=setup();s.client.connection.confirmTransaction=async()=>{s.calls.confirm++;return {value:{err:'InstructionError'},context:{slot:42}};};await assert.rejects(s.client.send(s.instruction,s.wallet,{approveDevnetTransaction:true}),/Transaction failed/);assert.deepEqual(s.calls,{sign:1,send:1,confirm:1});});
test('successful synthetic receipt is explicitly only client transport behavior',async()=>{const s=setup(),result=await s.client.send(s.instruction,s.wallet,{approveDevnetTransaction:true});assert.equal(result.signature,'synthetic-receipt-only');assert.equal(result.slot,42);assert.deepEqual(s.calls,{sign:1,send:1,confirm:1});});
