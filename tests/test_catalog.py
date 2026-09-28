"""Catalog boundaries: actual instructions, deterministic hashes, no private reads."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from predictkit.catalog import ROOT, MAX_PROMPT_BYTES, build_catalog
from predictkit.contracts import ROLES
from predictkit.skills import ROLE_SKILLS, load_skills


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for folder in ("agents", "skills"):
            shutil.copytree(ROOT / folder, self.root / folder)

    def tearDown(self):
        self.temporary.cleanup()

    def test_roles_match_runtime_and_full_prompt_files(self):
        catalog = build_catalog(self.root)
        self.assertEqual([r["id"] for r in catalog["roles"]], list(ROLES))
        for role in catalog["roles"]:
            with self.subTest(role=role["id"]):
                self.assertEqual(role["title"], ROLES[role["id"]]["name"])
                self.assertEqual(role["outputs"], ROLES[role["id"]]["paths"])
                self.assertEqual(role["skills"], ROLE_SKILLS[role["id"]])
                self.assertEqual(role["role_content"], (self.root / role["role_path"]).read_text())
                self.assertIn(role["summary"], role["role_content"])

    def test_skills_match_actual_provider_loader_and_hashes(self):
        catalog = build_catalog(self.root)
        skills = {s["id"]: s for s in catalog["skills"]}
        self.assertEqual(len(skills), 8)
        for role in ROLES:
            prompt, records = load_skills(role, self.root)
            for identifier, record in zip(ROLE_SKILLS[role], records):
                entry = skills[identifier]
                self.assertIn(entry["content"], prompt)
                self.assertEqual(entry["path"], record["path"])
                self.assertEqual(entry["sha256"], record["sha256"])
                self.assertEqual(entry["sha256"], hashlib.sha256((self.root / entry["path"]).read_bytes()).hexdigest())
                self.assertTrue(entry["description"])

    def test_operator_guides_are_explicitly_separate_from_loaded_skills(self):
        catalog = build_catalog(self.root)
        guides = {s["id"] for s in catalog["operator_guides"]}
        loaded = {s["id"] for s in catalog["skills"]}
        self.assertEqual(guides, {"run-workshop", "continue-sprint"})
        self.assertFalse(guides & loaded)
        self.assertEqual(len(guides | loaded), 10)

    def test_dependencies_match_fixed_scheduler_waves(self):
        roles = {r["id"]: r for r in build_catalog(self.root)["roles"]}
        for role in ("research", "product", "architect"):
            self.assertEqual(roles[role]["depends_on"], [])
        self.assertEqual(roles["chief"]["depends_on"], ["research", "product", "architect"])
        for role in ("frontend", "domain", "submission"):
            self.assertEqual(roles[role]["depends_on"], ["chief"])
        self.assertEqual(roles["reviewer"]["depends_on"], ["frontend", "domain", "submission"])

    def test_deterministic_serializable_catalog_and_content_change_hash(self):
        first = build_catalog(self.root)
        self.assertEqual(json.dumps(first), json.dumps(build_catalog(self.root)))
        skill = first["skills"][0]
        path = self.root / skill["path"]
        path.write_text(path.read_text() + "\nReviewed local change.\n")
        updated = next(s for s in build_catalog(self.root)["skills"] if s["id"] == skill["id"])
        self.assertNotEqual(skill["sha256"], updated["sha256"])

    def test_no_environment_run_files_or_unmapped_skills_are_exposed(self):
        secret = "CATALOG_PRIVATE_SENTINEL_NOT_A_REAL_KEY"
        (self.root / ".env").write_text(secret)
        (self.root / ".local").mkdir()
        (self.root / ".local/private-brief.json").write_text(secret)
        (self.root / "skills/unmapped").mkdir()
        (self.root / "skills/unmapped/SKILL.md").write_text(secret)
        with patch.dict("os.environ", {"OPENAI_API_KEY": secret}):
            result = json.dumps(build_catalog(self.root))
        self.assertNotIn(secret, result)
        self.assertNotIn("skills/unmapped", result)
        self.assertNotIn(str(self.root), result)

    def test_skill_file_symlink_is_rejected(self):
        path = self.root / "skills/frame-opportunity/SKILL.md"
        path.unlink()
        path.symlink_to(self.root / "agents/chief.md")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build_catalog(self.root)

    def test_role_file_symlink_is_rejected(self):
        path = self.root / "agents/research.md"
        path.unlink()
        path.symlink_to(self.root / "agents/chief.md")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build_catalog(self.root)

    def test_skill_directory_symlink_is_rejected_even_within_root(self):
        path = self.root / "skills/frame-opportunity"
        alternate = self.root / "skills/alternate"
        path.rename(alternate)
        path.symlink_to(alternate, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build_catalog(self.root)

    def test_operator_guide_symlink_is_rejected(self):
        path = self.root / "skills/run-workshop/SKILL.md"
        path.unlink()
        path.symlink_to(self.root / "agents/chief.md")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build_catalog(self.root)

    def test_missing_or_oversized_prompt_fails_closed(self):
        path = self.root / "agents/research.md"
        for content in (None, "a" * (MAX_PROMPT_BYTES + 1)):
            if content is None:
                path.unlink()
            else:
                path.write_text(content)
            with self.assertRaises(ValueError):
                build_catalog(self.root)

    def test_invalid_metadata_fails_closed(self):
        path = self.root / "skills/frame-opportunity/SKILL.md"
        path.write_text("---\nname: wrong-name\ndescription: Wrong metadata.\n---\n# Prompt\n")
        with self.assertRaisesRegex(ValueError, "metadata invalid"):
            build_catalog(self.root)

    def test_modes_do_not_claim_native_workers_tools_or_default_live_model(self):
        catalog = build_catalog(self.root)
        modes = {m["id"]: m for m in catalog["runtime_modes"]}
        self.assertEqual(set(modes), {"rehearsal", "openai"})
        self.assertFalse(modes["rehearsal"]["uses_ai"])
        self.assertTrue(modes["openai"]["uses_ai"])
        self.assertTrue(all(m["tools"] == [] for m in modes.values()))
        self.assertIn("explicitly configured", modes["openai"]["model_selection"])


if __name__ == "__main__":
    unittest.main()
