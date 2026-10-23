"""Edit faction's texts (edit._texts): a string the mod lacks is added only when it holds words - an empty box is no
string (tester 2026-10-23: Apply on Medieval II wrote an empty {EGYPT_DESCR} - its greyed tooltip box sends "")."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from campaign_editor.edit import edit                          # noqa: E402
from campaign_editor.minimod import make as make_minimod, write  # noqa: E402
from campaign_editor.moddata import ModData                    # noqa: E402

TEXTS = "{ALPHA}\t\tAlphan Kingdom\n{EMT_ALPHA_SPY}\t\tAlphan Spy\n"


class EmptyTextTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.d = make_minimod(self.root)
        write(os.path.join(self.d, "text", "expanded_bi.txt"), TEXTS, utf16=True)   # no {ALPHA_DESCR}, no long one

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_empty_boxes_add_no_string(self):
        plan = edit(ModData(self.root), "test", "alpha", {"description": "", "long_description": "", "denari": 7})
        self.assertFalse([p for p in plan.changed_files() if "text" in p.replace("\\", "/").split("/")], plan.notes)
        self.assertFalse([n for _, n in plan.notes if "_DESCR" in n], plan.notes)

    def test_typed_text_still_added(self):
        plan = edit(ModData(self.root), "test", "alpha", {"description": "Alphans ride"})
        self.assertTrue([n for _, n in plan.notes if "ALPHA_DESCR added" in n], plan.notes)


if __name__ == "__main__":
    unittest.main()
