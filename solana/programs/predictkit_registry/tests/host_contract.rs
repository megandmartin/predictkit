//! Compiled host serialization checks. These do not execute Solana instructions,
//! invoke account constraints, advance a validator clock, or prove PDA ownership.
use anchor_lang::{prelude::Pubkey, AccountDeserialize, AccountSerialize, Discriminator, InstructionData, ToAccountMetas};
use predictkit_registry::{accounts, instruction, Forecast, Question};

fn key(byte: u8) -> Pubkey { Pubkey::new_from_array([byte; 32]) }

#[test]
fn generated_discriminators_match_handwritten_client_conventions() {
    assert_eq!(Question::DISCRIMINATOR, &[111, 22, 150, 220, 181, 122, 118, 127]);
    assert_eq!(Forecast::DISCRIMINATOR, &[249, 253, 125, 195, 175, 165, 123, 36]);
    assert_eq!(instruction::CreateQuestion::DISCRIMINATOR, &[222, 74, 49, 30, 160, 220, 179, 27]);
    assert_eq!(instruction::SubmitForecast::DISCRIMINATOR, &[198, 148, 116, 0, 89, 239, 189, 90]);
    assert_eq!(instruction::ResolveQuestion::DISCRIMINATOR, &[52, 32, 224, 179, 180, 8, 0, 246]);
}

#[test]
fn compiled_instruction_serialization_matches_client_field_order() {
    let create = instruction::CreateQuestion {
        id: [1; 32], question: "Ship?".into(), rules_hash: [2; 32],
        closes_at: 200, resolves_after: 300, resolver: key(8),
    }.data();
    let mut expected = vec![222, 74, 49, 30, 160, 220, 179, 27];
    expected.extend_from_slice(&[1; 32]);
    expected.extend_from_slice(&5u32.to_le_bytes());
    expected.extend_from_slice(b"Ship?");
    expected.extend_from_slice(&[2; 32]);
    expected.extend_from_slice(&200i64.to_le_bytes());
    expected.extend_from_slice(&300i64.to_le_bytes());
    expected.extend_from_slice(&[8; 32]);
    assert_eq!(create, expected);
    for bps in [0u16, 1, 9999, 10000] {
        let encoded = instruction::SubmitForecast { probability_bps: bps }.data();
        assert_eq!(encoded.len(), 10);
        assert_eq!(&encoded[8..], &bps.to_le_bytes());
    }
    for outcome in 1..=3u8 {
        let encoded = instruction::ResolveQuestion { outcome, evidence_hash: [3; 32] }.data();
        assert_eq!(encoded.len(), 41);
        assert_eq!(encoded[8], outcome);
        assert_eq!(&encoded[9..], &[3; 32]);
    }
}

#[test]
fn question_account_uses_utf8_bytes_and_declared_allocation() {
    for question in ["Ship?".to_owned(), "界".repeat(66) + "ab"] {
        let q = Question {
            authority: key(7), resolver: key(8), id: [5; 32], question: question.clone(),
            rules_hash: [2; 32], closes_at: 200, resolves_after: 300, outcome: 1,
            resolved_at: 301, evidence_hash: [3; 32], forecast_count: 9, bump: 254,
        };
        let mut bytes = Vec::new();
        q.try_serialize(&mut bytes).unwrap();
        assert_eq!(Question::SPACE, 398);
        assert_eq!(bytes.len(), 206 + question.len());
        assert_eq!(&bytes[104..108], &(question.len() as u32).to_le_bytes());
        assert_eq!(&bytes[108..108 + question.len()], question.as_bytes());
        bytes.resize(8 + Question::SPACE, 0);
        let decoded = Question::try_deserialize(&mut bytes.as_slice()).unwrap();
        assert_eq!(decoded.question, question);
        assert_eq!(decoded.authority, key(7));
        assert_eq!(decoded.resolver, key(8));
        assert_eq!(decoded.outcome, 1);
        assert_eq!(decoded.forecast_count, 9);
        assert_eq!(decoded.bump, 254);
    }
}

#[test]
fn forecast_account_layout_matches_declared_space() {
    let f = Forecast { question: key(1), forecaster: key(2), probability_bps: 10000, created_at: 123, bump: 253 };
    let mut bytes = Vec::new();
    f.try_serialize(&mut bytes).unwrap();
    assert_eq!(Forecast::SPACE, 75);
    assert_eq!(bytes.len(), 83);
    assert_eq!(&bytes[8..40], &[1; 32]);
    assert_eq!(&bytes[40..72], &[2; 32]);
    assert_eq!(&bytes[72..74], &10000u16.to_le_bytes());
    assert_eq!(&bytes[74..82], &123i64.to_le_bytes());
    assert_eq!(bytes[82], 253);
}

#[test]
fn generated_account_order_signers_and_writable_flags_match_client() {
    let create = accounts::CreateQuestion { authority: key(1), question_account: key(2), system_program: key(3) }.to_account_metas(None);
    let forecast = accounts::SubmitForecast { forecaster: key(1), question_account: key(2), forecast: key(3), system_program: key(4) }.to_account_metas(None);
    let resolve = accounts::ResolveQuestion { resolver: key(1), question_account: key(2) }.to_account_metas(None);
    for (actual, expected) in [
        (create, vec![(1, true, true), (2, false, true), (3, false, false)]),
        (forecast, vec![(1, true, true), (2, false, true), (3, false, true), (4, false, false)]),
        (resolve, vec![(1, true, false), (2, false, true)]),
    ] {
        assert_eq!(actual.len(), expected.len());
        for (a, (byte, signer, writable)) in actual.iter().zip(expected) {
            assert_eq!((a.pubkey, a.is_signer, a.is_writable), (key(byte), signer, writable));
        }
    }
}
