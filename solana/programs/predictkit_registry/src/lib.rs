//! Educational forecast registry. NO token trading, AMM, custody or payouts.
//! SBPFv3 compiled and executed in isolated LiteSVM tests; no public deployment.
use anchor_lang::prelude::*;

declare_id!("8xG2yBTiVUPJRmHUW5JdsYUaBMoqboNoRBVSXL1nAjZT");

#[program]
pub mod predictkit_registry {
    use super::*;

    pub fn create_question(
        ctx: Context<CreateQuestion>, id: [u8; 32], question: String,
        rules_hash: [u8; 32], closes_at: i64, resolves_after: i64, resolver: Pubkey,
    ) -> Result<()> {
        let now = Clock::get()?.unix_timestamp;
        require!(!question.trim().is_empty() && question.as_bytes().len() <= 200, RegistryError::InvalidQuestion);
        require!(rules_hash != [0u8; 32], RegistryError::InvalidHash);
        require!(closes_at > now && resolves_after >= closes_at, RegistryError::InvalidSchedule);
        require!(resolver != Pubkey::default(), RegistryError::InvalidResolver);
        let q = &mut ctx.accounts.question_account;
        q.authority = ctx.accounts.authority.key();
        q.resolver = resolver;
        q.id = id;
        q.question = question;
        q.rules_hash = rules_hash;
        q.closes_at = closes_at;
        q.resolves_after = resolves_after;
        q.outcome = 0;
        q.resolved_at = 0;
        q.evidence_hash = [0u8; 32];
        q.forecast_count = 0;
        q.bump = ctx.bumps.question_account;
        Ok(())
    }

    pub fn submit_forecast(ctx: Context<SubmitForecast>, probability_bps: u16) -> Result<()> {
        let now = Clock::get()?.unix_timestamp;
        let q = &mut ctx.accounts.question_account;
        require!(q.outcome == 0 && now < q.closes_at, RegistryError::ForecastClosed);
        require!(probability_bps <= 10000, RegistryError::InvalidProbability);
        let f = &mut ctx.accounts.forecast;
        f.question = q.key();
        f.forecaster = ctx.accounts.forecaster.key();
        f.probability_bps = probability_bps;
        f.created_at = now;
        f.bump = ctx.bumps.forecast;
        q.forecast_count = q.forecast_count.checked_add(1).ok_or(RegistryError::Overflow)?;
        Ok(())
    }

    pub fn resolve_question(ctx: Context<ResolveQuestion>, outcome: u8, evidence_hash: [u8; 32]) -> Result<()> {
        let now = Clock::get()?.unix_timestamp;
        let q = &mut ctx.accounts.question_account;
        require!(q.outcome == 0, RegistryError::AlreadyResolved);
        require!(now >= q.resolves_after, RegistryError::TooEarly);
        require!((1..=3).contains(&outcome), RegistryError::InvalidOutcome);
        require!(evidence_hash != [0u8; 32], RegistryError::InvalidHash);
        q.outcome = outcome; // 1 YES, 2 NO, 3 VOID. No monetary settlement.
        q.resolved_at = now;
        q.evidence_hash = evidence_hash; // Commitment to evidence, NOT proof the claim is true.
        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(id: [u8; 32])]
pub struct CreateQuestion<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    #[account(init, payer = authority, space = 8 + Question::SPACE,
        seeds = [b"question", authority.key().as_ref(), id.as_ref()], bump)]
    pub question_account: Account<'info, Question>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SubmitForecast<'info> {
    #[account(mut)]
    pub forecaster: Signer<'info>,
    #[account(mut, seeds = [b"question", question_account.authority.as_ref(), question_account.id.as_ref()], bump = question_account.bump)]
    pub question_account: Account<'info, Question>,
    // init (not init_if_needed) enforces one immutable record per wallet per question.
    #[account(init, payer = forecaster, space = 8 + Forecast::SPACE,
        seeds = [b"forecast", question_account.key().as_ref(), forecaster.key().as_ref()], bump)]
    pub forecast: Account<'info, Forecast>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ResolveQuestion<'info> {
    pub resolver: Signer<'info>,
    #[account(mut, has_one = resolver,
        seeds = [b"question", question_account.authority.as_ref(), question_account.id.as_ref()], bump = question_account.bump)]
    pub question_account: Account<'info, Question>,
}

#[account]
pub struct Question {
    pub authority: Pubkey,
    pub resolver: Pubkey,
    pub id: [u8; 32],
    pub question: String,
    pub rules_hash: [u8; 32],
    pub closes_at: i64,
    pub resolves_after: i64,
    pub outcome: u8,
    pub resolved_at: i64,
    pub evidence_hash: [u8; 32],
    pub forecast_count: u64,
    pub bump: u8,
}
impl Question {
    pub const SPACE: usize = 32 + 32 + 32 + 4 + 200 + 32 + 8 + 8 + 1 + 8 + 32 + 8 + 1;
}

#[account]
pub struct Forecast {
    pub question: Pubkey,
    pub forecaster: Pubkey,
    pub probability_bps: u16,
    pub created_at: i64,
    pub bump: u8,
}
impl Forecast { pub const SPACE: usize = 32 + 32 + 2 + 8 + 1; }

#[error_code]
pub enum RegistryError {
    #[msg("Question must be nonempty and at most 200 UTF-8 bytes")]
    InvalidQuestion,
    #[msg("Hash must not be zero")]
    InvalidHash,
    #[msg("Close must be future; resolve time must not precede close")]
    InvalidSchedule,
    #[msg("Resolver cannot be the system/default public key")]
    InvalidResolver,
    #[msg("Forecasting has closed")]
    ForecastClosed,
    #[msg("Probability must be 0 to 10000 basis points")]
    InvalidProbability,
    #[msg("Resolution is immutable")]
    AlreadyResolved,
    #[msg("Resolution is too early")]
    TooEarly,
    #[msg("Outcome must be YES, NO or VOID")]
    InvalidOutcome,
    #[msg("Counter overflow")]
    Overflow,
}
