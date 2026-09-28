/** Explicitly imported by a host application; never loaded by the agent runner.
 * Requires @solana/web3.js v1. No wallet secret is read here.
 * Builders tested against compiled SBF in LiteSVM; send guards use synthetic RPC tests.
 * No devnet deployment or real-wallet execution is established by those tests.
 */
import {PublicKey, SystemProgram, TransactionInstruction, Transaction} from '@solana/web3.js';
import {DEVNET_GENESIS, createQuestionData, forecastData, resolutionData, decodeQuestion} from './codec.mjs';

export class RegistryClient {
  constructor(connection, programId) {this.connection=connection;this.programId=new PublicKey(programId);}
  questionAddress(authority,id){return PublicKey.findProgramAddressSync([Buffer.from('question'),new PublicKey(authority).toBuffer(),Buffer.from(id)],this.programId)[0];}
  forecastAddress(question,forecaster){return PublicKey.findProgramAddressSync([Buffer.from('forecast'),new PublicKey(question).toBuffer(),new PublicKey(forecaster).toBuffer()],this.programId)[0];}
  create(authority,args){
    const payer=new PublicKey(authority),question=this.questionAddress(payer,args.id);
    return {question,instruction:new TransactionInstruction({programId:this.programId,
      keys:[{pubkey:payer,isSigner:true,isWritable:true},{pubkey:question,isSigner:false,isWritable:true},{pubkey:SystemProgram.programId,isSigner:false,isWritable:false}],data:createQuestionData(args)})};
  }
  forecast(forecaster,question,bps){
    const payer=new PublicKey(forecaster),q=new PublicKey(question),forecast=this.forecastAddress(q,payer);
    return {forecast,instruction:new TransactionInstruction({programId:this.programId,
      keys:[{pubkey:payer,isSigner:true,isWritable:true},{pubkey:q,isSigner:false,isWritable:true},{pubkey:forecast,isSigner:false,isWritable:true},{pubkey:SystemProgram.programId,isSigner:false,isWritable:false}],data:forecastData(bps)})};
  }
  resolve(resolver,question,outcome,evidenceHash){return new TransactionInstruction({programId:this.programId,
    keys:[{pubkey:new PublicKey(resolver),isSigner:true,isWritable:false},{pubkey:new PublicKey(question),isSigner:false,isWritable:true}],data:resolutionData(outcome,evidenceHash)});}
  async checkDevnet(){
    const genesis=await this.connection.getGenesisHash();if(genesis!==DEVNET_GENESIS)throw Error('Only the expected devnet is permitted');
    const program=await this.connection.getAccountInfo(this.programId,'confirmed');
    if(!program?.executable)throw Error('Program is not deployed/executable');return genesis;
  }
  async read(question){
    await this.checkDevnet();const key=new PublicKey(question),a=await this.connection.getAccountInfo(key,'confirmed');
    if(!a||a.executable||!a.owner.equals(this.programId))throw Error('Unexpected account owner/type');
    const decoded=decodeQuestion(a.data);
    if(!this.questionAddress(decoded.authority,Buffer.from(decoded.id,'hex')).equals(key))throw Error('Question PDA mismatch');
    return decoded;
  }
  async send(instruction,wallet,{approveDevnetTransaction=false}={}){
    if(!approveDevnetTransaction)throw Error('Human approval required for this individual devnet transaction');
    if(!instruction.programId.equals(this.programId))throw Error('Unexpected program');
    if(!wallet?.publicKey||typeof wallet.signTransaction!=='function')throw Error('A connected human wallet is required');
    await this.checkDevnet();
    const recent=await this.connection.getLatestBlockhash('confirmed');
    const tx=new Transaction({feePayer:wallet.publicKey,...recent}).add(instruction);
    const before=tx.serializeMessage();
    const signed=await wallet.signTransaction(tx); // Rejection propagates; no retry/fallback signing.
    if(!signed.serializeMessage().equals(before))throw Error('Wallet modified the reviewed transaction');
    const signature=await this.connection.sendRawTransaction(signed.serialize(),{skipPreflight:false,maxRetries:0});
    const receipt=await this.connection.confirmTransaction({signature,...recent},'confirmed');
    if(receipt.value.err)throw Error('Transaction failed; inspect signature before retrying');
    return {signature,commitment:'confirmed',cluster:'devnet',programId:this.programId.toBase58(),slot:receipt.context.slot};
  }
}
