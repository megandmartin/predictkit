"""Behavioral checks for the code-owned capability and acceptance boundary."""
from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
import unittest

from predictkit.capabilities import (VERSION, SKILL_OWNERS, all_profiles,
                                    profile_for, profile_hash, validate_role_output)
from predictkit.contracts import ROLES, canonical_hash, validate_brief
from predictkit.providers import RehearsalProvider
from predictkit.skills import ROLE_SKILLS

ROOT = Path(__file__).resolve().parents[1]
BRIEF = validate_brief(json.loads((ROOT / "examples/launchlens.json").read_text()))


def fixture(role):
    return asyncio.run(RehearsalProvider(delay=0).run(role, BRIEF, ""))[0]


def with_content(role, path, content):
    raw = fixture(role)
    next(item for item in raw["artifacts"] if item["path"] == path)["content"] = content
    return raw


def domain(market):
    return with_content("domain", "app/market.json", json.dumps(market))


def market():
    return json.loads(fixture("domain")["artifacts"][0]["content"])


def html_result(content):
    return with_content("frontend", "app/index.html", content)


def minimal_html(extra_head="", extra_body=""):
    return '<!doctype html><html lang="en"><head><title>Example</title><meta name="viewport" content="width=device-width, initial-scale=1">' + extra_head + '</head><body><main>Simulation</main>' + extra_body + '</body></html>'


class CapabilityProfileTests(unittest.TestCase):
    def test_accessible_svg_title_does_not_replace_or_duplicate_document_title(self):
        graphic='<svg viewBox="0 0 10 10" role="img"><title>Forecast history</title><path d="M0 0L10 10"/></svg>'
        source=minimal_html(extra_body=graphic)
        self.assertTrue(validate_role_output('frontend',html_result(source),BRIEF)['passed'])
        missing=source.replace('<title>Example</title>','')
        report=validate_role_output('frontend',html_result(missing),BRIEF)
        self.assertFalse(next(check for check in report['checks'] if check['id']=='html-document')['passed'])
    def test_every_runtime_role_has_profile_from_runtime_registries(self):
        self.assertEqual([profile["id"] for profile in all_profiles()], list(ROLES))
        for role, spec in ROLES.items():
            profile = profile_for(role)
            self.assertEqual(profile["output_paths"], spec["paths"])
            self.assertEqual(profile["skill_ids"], ROLE_SKILLS[role])
            self.assertEqual(profile["phase"], spec["phase"])
            self.assertEqual(profile["version"], VERSION)
            self.assertTrue(profile["can_do"] and profile["cannot_do"] and profile["example"])
            self.assertTrue(profile["review_questions"])
            self.assertTrue(all(check["kind"] == "static" for check in profile["acceptance_checks"]))
            json.dumps(profile, allow_nan=False)

    def test_input_paths_match_wave_snapshots_without_concurrent_siblings(self):
        discovery = [ROLES[role]["paths"][0] for role in ("research", "product", "architect")]
        for role in ("research", "product", "architect"):
            self.assertEqual(profile_for(role)["input_paths"], [])
        self.assertEqual(profile_for("chief")["input_paths"], discovery)
        for role in ("frontend", "domain", "submission"):
            self.assertEqual(profile_for(role)["input_paths"], discovery + ["decisions/build-memo.md"])
        self.assertEqual(len(profile_for("reviewer")["input_paths"]), 10)
        self.assertIn("app/index.html", profile_for("reviewer")["input_paths"])
        self.assertNotIn("qa/review.md", profile_for("reviewer")["input_paths"])

    def test_every_mapped_skill_has_one_primary_owner_who_loads_it(self):
        mapped = set(skill for skills in ROLE_SKILLS.values() for skill in skills)
        self.assertEqual(set(SKILL_OWNERS), mapped)
        self.assertEqual(len(SKILL_OWNERS), 8)
        for skill, role in SKILL_OWNERS.items():
            self.assertIn(skill, ROLE_SKILLS[role])
        self.assertNotIn("run-workshop", SKILL_OWNERS)
        self.assertNotIn("continue-sprint", SKILL_OWNERS)

    def test_profiles_are_defensive_copies_and_hashes_stable(self):
        expected = profile_hash("domain")
        changed = profile_for("domain")
        self.assertEqual(expected, canonical_hash(changed))
        changed["output_paths"].append("outside.txt")
        changed["can_do"].clear()
        changed["acceptance_checks"][0]["label"] = "mutated"
        self.assertEqual(profile_hash("domain"), expected)
        self.assertNotIn("outside.txt", ROLES["domain"]["paths"])
        self.assertNotEqual(profile_hash("frontend"), expected)

    def test_unknown_profile_cannot_extend_permissions(self):
        with self.assertRaises(ValueError):
            profile_for("wallet")


class RoleOutputTests(unittest.TestCase):
    def test_all_rehearsal_roles_satisfy_their_static_profiles(self):
        for role in ROLES:
            with self.subTest(role=role):
                report = validate_role_output(role, fixture(role), BRIEF)
                self.assertTrue(report["passed"], report)
                self.assertEqual([check["id"] for check in report["checks"]], [check["id"] for check in profile_for(role)["acceptance_checks"]])
                self.assertEqual(report["kind"], "role-output-checks")
                self.assertTrue(report["not_tested"])
                json.dumps(report, allow_nan=False)

    def test_invalid_ownership_fails_without_reporting_content(self):
        raw = fixture("research")
        raw["artifacts"][0] = {"path": "runtime.py", "content": "private output must not be echoed"}
        report = validate_role_output("research", raw, BRIEF)
        self.assertFalse(report["passed"])
        self.assertNotIn("private output", json.dumps(report))
        self.assertEqual(len(report["checks"]), 1)

    def test_invalid_or_malformed_results_are_reports_not_exceptions(self):
        values = [None, [], {}, {"summary": "", "artifacts": [{"path": [], "content": "x"}], "limitations": []}]
        for raw in values:
            with self.subTest(raw=raw):
                self.assertFalse(validate_role_output("research", raw, BRIEF)["passed"])
        self.assertFalse(validate_role_output("unregistered", fixture("research"), BRIEF)["passed"])

    def test_weak_markdown_is_not_misrepresented_as_semantically_verified(self):
        raw = with_content("research", "research/market.md", "Evidence pending.")
        report = validate_role_output("research", raw, BRIEF)
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["checks"]), 1)
        self.assertTrue(any("factual accuracy" in item for item in report["not_tested"]))
        self.assertTrue(profile_for("research")["review_questions"])

    def test_empty_artifacts_fail_shared_contract(self):
        self.assertFalse(validate_role_output("research", with_content("research", "research/market.md", "  "), BRIEF)["passed"])

    def test_no_output_or_brief_mutation(self):
        raw = fixture("domain")
        saved = copy.deepcopy(raw)
        brief = copy.deepcopy(BRIEF)
        validate_role_output("domain", raw, brief)
        self.assertEqual(raw, saved)
        self.assertEqual(brief, BRIEF)


class MarketAcceptanceTests(unittest.TestCase):
    def check_market(self, value):
        return validate_role_output("domain", domain(value), BRIEF)

    def test_changed_frozen_strings_are_rejected(self):
        for key in ("question", "resolution_rule", "void_policy"):
            value = market()
            value[key] += " amended"
            with self.subTest(key=key):
                report = self.check_market(value)
                self.assertFalse(report["passed"])
                self.assertFalse(next(check for check in report["checks"] if check["id"] == "market-brief")["passed"])

    def test_missing_or_wrong_type_fields_rejected(self):
        for key in ("question", "resolution_rule", "void_policy", "mode", "outcomes"):
            for wrong in (None, True, 1, {}, ""):
                value = market()
                value[key] = wrong
                with self.subTest(key=key, wrong=wrong):
                    self.assertFalse(self.check_market(value)["passed"])
            value = market()
            del value[key]
            self.assertFalse(self.check_market(value)["passed"])

    def test_mode_and_outcome_vocabulary_cannot_be_promoted(self):
        for field, wrong in (("mode", "devnet"), ("mode", "mainnet"), ("outcomes", ["NO", "YES", "VOID"]), ("outcomes", ["YES", "NO"]), ("outcomes", ["YES", "NO", "VOID", "MAYBE"])):
            value = market()
            value[field] = wrong
            with self.subTest(field=field, wrong=wrong):
                self.assertFalse(self.check_market(value)["passed"])

    def test_nonobject_json_rejected(self):
        for value in ([], True, 1, "text", None):
            with self.subTest(value=value):
                self.assertFalse(self.check_market(value)["passed"])

    def test_duplicate_keys_even_nested_rejected(self):
        for suffix in (',"mode":"offchain-simulation"}', ',"metadata":{"x":1,"x":2}}'):
            content = json.dumps(market())[:-1] + suffix
            report = validate_role_output("domain", with_content("domain", "app/market.json", content), BRIEF)
            self.assertFalse(report["passed"])
            self.assertFalse(next(check for check in report["checks"] if check["id"] == "market-json")["passed"])

    def test_nonfinite_values_even_in_additional_metadata_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
            content = json.dumps(market())[:-1] + ',"metadata":{"value":' + value + '}}'
            with self.subTest(value=value):
                report = validate_role_output("domain", with_content("domain", "app/market.json", content), BRIEF)
                self.assertFalse(report["passed"])

    def test_malformed_json_rejected(self):
        report = validate_role_output("domain", with_content("domain", "app/market.json", "{broken"), BRIEF)
        self.assertFalse(report["passed"])
        self.assertEqual(report["checks"][0]["id"], "output-contract")

    def test_finite_extra_metadata_allowed(self):
        value = {**market(), "metadata": {"draft": True, "confidence": 0.2, "count": 2, "notes": None}}
        self.assertTrue(self.check_market(value)["passed"])

    def test_missing_frozen_brief_is_not_bypassed(self):
        for brief in (None, {}, {"market_question": True}):
            with self.subTest(brief=brief):
                self.assertFalse(validate_role_output("domain", fixture("domain"), brief)["passed"])


class HTMLAcceptanceTests(unittest.TestCase):
    def check_html(self, content):
        return validate_role_output("frontend", html_result(content), BRIEF)

    def test_self_contained_document_without_template_ids_is_valid(self):
        self.assertTrue(self.check_html(minimal_html(extra_body='<p>This layout uses no required IDs.</p>'))["passed"])

    def test_document_requirements_are_observable(self):
        valid = minimal_html()
        changes = [valid.replace('<!doctype html>', ''), valid.replace(' lang="en"', ''), valid.replace('<title>Example</title>', '<title> </title>'), valid.replace('width=device-width', 'width=800'), valid.replace('</body>', ''), valid + '<html></html>', valid.replace('<head>', '').replace('</head>', ''), '<body>Simulation</body>']
        for content in changes:
            with self.subTest(content=content):
                self.assertFalse(self.check_html(content)["passed"])

    def test_remote_and_relative_fetching_attributes_rejected(self):
        values = ['<script src="https://example.test/app.js"></script>', '<script src="data:text/javascript,alert(1)"></script>', '<img src="//example.test/x.png">', '<img src="local.png">', '<link rel="stylesheet" href="/site.css">', '<form action="https://example.test/post"></form>', '<img srcset="x.png 1x, y.png 2x">', '<img srcset="data:image/png;base64,AA== 1x, https://example.test/x.png 2x">', '<svg><image href="https://example.test/x.png"></image></svg>', '<svg><use xlink:href="https://example.test/x.svg#icon"></use></svg>', '<iframe srcdoc="hello"></iframe>', '<meta http-equiv="refresh" content="0;url=https://example.test">']
        for markup in values:
            with self.subTest(markup=markup):
                self.assertFalse(self.check_html(minimal_html(extra_body=markup))["passed"])

    def test_embedded_images_and_nonfetching_link_text_are_valid(self):
        content = minimal_html(extra_body='<img src="data:image/png;base64,AA==" alt="Example"><a href="https://example.test">Source link</a><p>fetch(url) and https://example.test are text, not executed.</p>')
        self.assertTrue(self.check_html(content)["passed"])
        self.assertTrue(self.check_html(minimal_html(extra_body='<svg><use href="#local"></use></svg>'))["passed"])

    def test_css_imports_and_urls_rejected(self):
        for css in ('@import "https://example.test/a.css";', '@import url(/a.css);', 'body{background:url(https://example.test/x.png)}', 'body{background:url("/x.png")}'):
            with self.subTest(css=css):
                self.assertFalse(self.check_html(minimal_html(extra_head='<style>' + css + '</style>'))["passed"])

    def test_embedded_and_fragment_css_urls_allowed(self):
        css = 'body{background:url("data:image/png;base64,AA==")}svg{filter:url(#f)}'
        self.assertTrue(self.check_html(minimal_html(extra_head='<style>' + css + '</style>'))["passed"])

    def test_static_dynamic_and_comment_separated_imports_rejected(self):
        for js in ('import "https://example.test/a.js";', 'import foo from "https://example.test/a.js";', 'export {foo} from "https://example.test/a.js";', 'export * from "https://example.test/a.js";', 'import {x} from "https://example.test/a.js";', 'import("https://example.test/a.js");', 'import/* comment */("https://example.test/a.js");'):
            with self.subTest(js=js):
                self.assertFalse(self.check_html(minimal_html(extra_body='<script type="module">' + js + '</script>'))["passed"])

    def test_network_calls_in_script_and_handlers_rejected(self):
        for js in ('fetch("/api/status")', 'new XMLHttpRequest()', 'new WebSocket("wss://example.test")', 'new EventSource("/feed")', 'navigator.sendBeacon("/log")', 'fetch/* comment */("/api")'):
            with self.subTest(js=js):
                self.assertFalse(self.check_html(minimal_html(extra_body='<script>' + js + '</script>'))["passed"])
                self.assertFalse(self.check_html(minimal_html(extra_body='<button onclick=\'' + js + '\'>Click</button>'))["passed"])
                self.assertFalse(self.check_html(minimal_html(extra_body='<a href=\'javascript:' + js + '\'>Click</a>'))["passed"])

    def test_source_indicators_are_explicitly_not_a_network_or_security_proof(self):
        # Deliberately outside the detector's syntactic scope. The report must not
        # mistake absence of these few known patterns for a security guarantee.
        report = self.check_html(minimal_html(extra_body='<script>window["fe" + "tch"]("/api")</script>'))
        self.assertTrue(report["passed"])
        self.assertIn("does not prove", report["checks"][-1]["detail"])
        self.assertTrue(any("Obfuscated or computed" in item for item in report["not_tested"]))


if __name__ == "__main__":
    unittest.main()
