"""The campaign's own script (campaign_script.txt, both games): its top-level pieces between `script` and
`end_script` - a monitor (monitor_event / monitor_conditions ... end_monitor), a while / if block, or one line
(declare_counter, a command) - with the comments right above each, so a modder can see them and take any out (one,
the picked ones, or all). The `script` / `end_script` frame always stays: the game still finds the file it was told
to read."""

from .textio import strip_comment, tokens

OPENS = {"monitor_event": "end_monitor", "monitor_conditions": "end_monitor", "while": "end_while", "if": "end_if"}
CLOSES = set(OPENS.values())


def path_of(mod, campaign):
    return mod.in_campaign(campaign, "campaign_script.txt")


def read(f):
    """[{'id', 'kind', 'first', 'span': (a, b), 'lines'}] - the pieces in file order; id = 'kind@line' (1-based)."""
    texts = f.texts()
    start = next((i for i, l in enumerate(texts) if tokens(l)[:1] == ["script"]), None)
    if start is None:
        return []
    end = next((i for i in range(len(texts) - 1, start, -1) if tokens(texts[i])[:1] == ["end_script"]), len(texts))
    out, i, notes = [], start + 1, None
    while i < end:
        t = tokens(texts[i])
        if not t:
            if not texts[i].strip():
                notes = None                            # a blank line parts a comment from what follows
            elif notes is None:
                notes = i                               # a comment right above the next piece goes with it
            i += 1
            continue
        a = notes if notes is not None else i
        notes = None
        if t[0] in OPENS:
            depth, j = 0, i
            while j < end:
                w = tokens(texts[j])[:1]
                if w and w[0] in OPENS:
                    depth += 1
                elif w and w[0] in CLOSES:
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            b = min(j + 1, end)
        else:
            b = i + 1
        out.append({"id": "%s@%d" % (t[0], i + 1), "kind": t[0], "first": strip_comment(texts[i]).strip(),
                    "span": (a, b), "lines": b - a})
        i = b
    return out


def plan_remove(plan, path, ids):
    """The pieces named (ids of read) taken out of campaign_script.txt, the blank lines after each with it; the
    script / end_script frame kept. Returns how many."""
    f = plan.edit(path)
    gone = [p for p in read(f) if p["id"] in set(ids)]
    for p in sorted(gone, key=lambda p: -p["span"][0]):     # from the end: the earlier lines keep their place
        a, b = p["span"]
        while b < len(f) and not f.text(b).strip():
            b += 1
        f.delete(a, b)
    if gone:
        plan.note(f, "%d piece(s) of the campaign script taken out: %s" % (
            len(gone), ", ".join(p["first"][:40] for p in gone[:5]) + (" ..." if len(gone) > 5 else "")))
    return len(gone)
