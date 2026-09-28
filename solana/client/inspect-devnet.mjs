/** Read-only evidence inspection. No keys, signing, airdrops or transaction sends. */
import {fromBase58,decodeQuestion,discriminator} from './codec.mjs';
import {DEVNET_GENESIS} from './codec.mjs';
import {writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
export const RPC='https://api.devnet.solana.com';
let nextId=1;
export async function rpc(method,params=[]){
  const id=nextId++;
  const response=await fetch(RPC,{method:'POST',redirect:'error',signal:AbortSignal.timeout(12000),
    headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id,method,params})});
  if(!response.ok)throw Error(`RPC HTTP ${response.status}`);
  const text=await response.text();if(text.length>2000000)throw Error('RPC response exceeds limit');
  const r=JSON.parse(text);if(r.id!==id||r.error||!('result' in r))throw Error('RPC returned error/invalid envelope');return r.result;
}
export function verifyObservation({genesis,program,account,programId,transaction,signature,questionAddress}){
  if(genesis!==DEVNET_GENESIS)throw Error('Wrong cluster');
  fromBase58(programId,32);fromBase58(questionAddress,32);
  if(!program?.value?.executable)throw Error('Program is not executable');
  const a=account?.value;
  if(!a||a.executable||a.owner!==programId||a.data?.[1]!=='base64')throw Error('Wrong/missing account owner or encoding');
  const decoded=decodeQuestion(Buffer.from(a.data[0],'base64'));
  let invocation=null;
  if(signature){
    fromBase58(signature,64);
    if(!transaction||transaction.meta?.err!==null||!transaction.transaction?.signatures?.includes(signature))throw Error('Missing or failed transaction');
    const keys=transaction.transaction.message.accountKeys;
    const signers=new Set(keys.filter(k=>k.signer).map(k=>k.pubkey));
    const names=['create_question','submit_forecast','resolve_question'];
    invocation=transaction.transaction.message.instructions.find(i=>i.programId===programId && i.accounts?.includes(questionAddress)
      && i.data && names.some(n=>fromBase58(i.data).subarray(0,8).equals(discriminator('global',n))));
    if(!invocation)throw Error('Signature does not invoke this registry/question');
    const name=names.find(n=>fromBase58(invocation.data).subarray(0,8).equals(discriminator('global',n)));
    if(name==='resolve_question'&&!signers.has(decoded.resolver))throw Error('Missing expected resolver signature');
    if(name==='create_question'&&!signers.has(decoded.authority))throw Error('Missing expected creator signature');
    if(name==='submit_forecast'&&!signers.has(invocation.accounts[0]))throw Error('Missing forecaster signature');
    invocation={instruction:name,signature,slot:transaction.slot};
  }
  return {genesis,programId,questionAddress,accountSlot:account.context.slot,question:decoded,invocation,
    boundary:'Read-only RPC observation, not proof of deployed bytecode/source equivalence, SVM test coverage, resolver truth or production security'};
}
async function main(){
  const args=process.argv.slice(2);if(!args.includes('--allow-network'))throw Error('Add --allow-network to explicitly permit read-only public devnet requests');
  const get=k=>{const n=args.indexOf(k);return n>=0?args[n+1]:undefined;};
  const programId=get('--program'),questionAddress=get('--question'),signature=get('--signature');
  fromBase58(programId,32);fromBase58(questionAddress,32);if(signature)fromBase58(signature,64);
  const genesis=await rpc('getGenesisHash');if(genesis!==DEVNET_GENESIS)throw Error('Wrong cluster');
  const [program,account]=await Promise.all([rpc('getAccountInfo',[programId,{encoding:'base64',commitment:'confirmed'}]),rpc('getAccountInfo',[questionAddress,{encoding:'base64',commitment:'confirmed'}])]);
  const transaction=signature?await rpc('getTransaction',[signature,{encoding:'jsonParsed',commitment:'confirmed',maxSupportedTransactionVersion:0}]):null;
  const report={kind:'live-read-only-devnet-observation',observedAt:new Date().toISOString(),rpc:RPC,
    ...verifyObservation({genesis,program,account,programId,questionAddress,transaction,signature})};
  const text=JSON.stringify(report,(_,v)=>typeof v==='bigint'?v.toString():v,2);
  if(get('--out'))await writeFile(get('--out'),text,{flag:'wx'});console.log(text);
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main().catch(e=>{console.error(e.message);process.exitCode=1;});
