/** Execute create → forecast → clock close → resolve against compiled SBF, offline. */
import {mkdirSync, writeFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import assert from 'node:assert/strict';
import {Harness,PROGRAM,PROGRAM_HASH,PROGRAM_PATH,assertSuccess,assertFailure,serialize} from '../tests/svm-harness.mjs';
const h=new Harness(),created=h.create();assertSuccess(created.result);
const first=h.forecast(created.question,6800),second=h.forecast(created.question,4200);assertSuccess(first.result);assertSuccess(second.result);
const afterForecasts=h.question(created.question);assert.equal(afterForecasts.forecastCount,2n);
h.clock(110n);const rejected=h.forecast(created.question,5500);assertFailure(rejected.result,/ForecastClosed/);
h.clock(120n);assertSuccess(h.resolve(created.question,'YES'));
const final=h.question(created.question);assert.equal(final.outcome,'YES');assert.equal(final.forecastCount,2n);
const report=serialize({kind:'compiled-program-local-demo',environment:'isolated-local-svm',public_network:false,wallet_files_read:false,uses_synthetic_test_keys:true,program:PROGRAM.toBase58(),program_sha256:PROGRAM_HASH,program_path:PROGRAM_PATH,question_account:created.question.toBase58(),question:final.question,forecasts:[{probability_bps:6800,account:first.forecast.toBase58()},{probability_bps:4200,account:second.forecast.toBase58()}],after_forecasts:afterForecasts,final_account:final,transactions:h.receipts,boundary:'These signatures and balances exist only in this in-process LiteSVM test. There is no devnet/mainnet deployment, RPC or persistent wallet. The placeholder program ID is only the local test identity.'});
const path=process.argv[2];
if(path){const out=resolve(path);mkdirSync(dirname(out),{recursive:true});writeFileSync(out,JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify(report,null,2));
