import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
import live_sync as ls


class TitleTests(unittest.TestCase):
    def test_parse_variants(self):
        for raw, want in [
            ("GTA 6 - Chapter 1 | Clear Skies", (1, "Clear Skies")),
            ("GTA 6 | Chapter 1 | Island Dreams", (1, "Island Dreams")),
            ("GTA 6 - Chapter 3 |Dealer's choice", (3, "Dealer's choice")),
            ("gta 6 – chapter 2 | Moses ", (2, "Moses")),
        ]:
            self.assertEqual(ls.parse_title(raw), want, raw)

    def test_parse_rejects_other(self):
        for raw in ["Cleopatra Unveiled", "GTA 6 | Gameplay 1 | Prologue", "", None]:
            self.assertIsNone(ls.parse_title(raw))

    def test_build_title_clean_and_short(self):
        t = ls.build_title(2, "Slam Dunk")
        self.assertEqual(t, "GTA 6 Walkthrough - Chapter 2: Slam Dunk | PS5 Gameplay")
        self.assertTrue(ls.is_clean(t))
        self.assertLessEqual(len(ls.build_title(1, "x" * 200)), 100)

    def test_duration(self):
        self.assertEqual(ls.duration_minutes("PT16M48S"), 17)
        self.assertEqual(ls.duration_minutes("PT1H9M5S"), 69)
        self.assertEqual(ls.duration_minutes("garbage"), 0)


class DescriptionTests(unittest.TestCase):
    def test_keeps_owner_text(self):
        d = ls.build_description(1, "Swamped", 20, existing="my own note")
        self.assertIn("my own note", d)
        self.assertTrue(d.startswith(ls.MARKER))

    def test_idempotent_on_own_text(self):
        first = ls.build_description(1, "Swamped", 20)
        self.assertNotIn("---", ls.build_description(1, "Swamped", 20, existing=first))


class FrameTests(unittest.TestCase):
    def test_black_and_flat_rejected(self):
        self.assertFalse(ls.frame_ok(Image.new("RGB", (640, 360), (0, 0, 0))))
        self.assertFalse(ls.frame_ok(Image.new("RGB", (640, 360), (20, 40, 255))))

    def test_letterbox_stripped(self):
        im = Image.new("RGB", (640, 480), (0, 0, 0))
        im.paste(Image.effect_noise((640, 320), 80).convert("RGB"), (0, 80))
        self.assertEqual(ls.strip_letterbox(im).size, (640, 320))

    def test_render_size(self):
        frame = Image.effect_noise((1280, 720), 60).convert("RGB")
        self.assertEqual(ls.render_thumbnail(frame, 2, "Twist, Wrist, Smash, Grab").size, (1280, 720))


class WorkSelectionTests(unittest.TestCase):
    def vid(self, i, title, live="none", privacy="public"):
        return {"id": i, "snippet": {"title": title, "publishedAt": "2026-11-24T00:00:00Z", "liveBroadcastContent": live},
                "status": {"privacyStatus": privacy}, "contentDetails": {"duration": "PT10M"}}

    def test_picks_only_new_finished_gta_streams(self):
        vs = [self.vid("a", "GTA 6 - Chapter 1 | New One"),
              self.vid("b", "GTA 6 Walkthrough - Chapter 1: Done | PS5 Gameplay"),
              self.vid("c", "GTA 6 - Chapter 2 | Still Live", live="live"),
              self.vid("d", "GTA 6 - Chapter 2 | Secret", privacy="private"),
              self.vid("e", "Cleopatra Unveiled")]
        self.assertEqual([w[0]["id"] for w in ls.pick_work(vs, {"videos": {}})], ["a"])

    def test_resumes_unfinished_steps_after_title_changed(self):
        v = self.vid("a", "GTA 6 Walkthrough - Chapter 1: New One | PS5 Gameplay")
        st = {"videos": {"a": {"chapter": 1, "mission": "New One",
                               "steps": {"metadata": True, "playlist": True, "thumbnail": False}}}}
        self.assertEqual([w[1:] for w in ls.pick_work([v], st)], [(1, "New One")])


if __name__ == "__main__":
    unittest.main()
