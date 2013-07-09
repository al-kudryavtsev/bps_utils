import re
from reps import TAKEOFF_REPLACEMENTS, LANDING_REPLACEMENTS


def _prepare_replacements(replacements):
    regexps = {}
    for ac_eng, reps in replacements.iteritems():
        reps_escaped = dict((re.escape(k), v) for k, v in reps.iteritems())
        pattern = re.compile("|".join(reps_escaped.keys()))
        regexps[ac_eng] = (reps_escaped, pattern)
    return regexps


TAKEOFF_REGEXPS = _prepare_replacements(TAKEOFF_REPLACEMENTS)
LANDING_REGEXPS = _prepare_replacements(LANDING_REPLACEMENTS)


def _do_replacements(lines, ac_eng, regexps):
    for i, l in enumerate(lines):
        lines[i] = regexps[ac_eng][1].sub(
            lambda m: regexps[ac_eng][0][re.escape(m.group(0))], l)


def _extract_pages(lines):
    per_page = []
    start = -1
    for i, l in enumerate(lines):
        if l.startswith("\f"):
            lines[i] = lines[i][1:]
            if start != -1:
                per_page.append(lines[start:i])
            start = i
    per_page.append(lines[start:])
    return per_page


def preprocess(lines, ac_eng, is_takeoff):
    new_lines = []
    # Delete 1st page
    i = 0
    while i < len(lines):
        if lines[i].startswith("\f"): break
        i += 1
    new_lines = lines[i:]

    # Make replacements
    if is_takeoff:
        _do_replacements(new_lines, ac_eng, TAKEOFF_REGEXPS)
    else:
        _do_replacements(new_lines, ac_eng, LANDING_REGEXPS)

    # Group lines into pages
    paged_lines = _extract_pages(new_lines)
    
    return paged_lines


def _test():
    import sys
    lines = open("OUT_DRY/CYOW.out", "r").readlines()
    res = preprocess(lines, "772ER")
    print res[0]
    for page in res[1]:
        print "NEW PAGE\n"
        sys.stdout.writelines(page)
