import functools
import re
from reps import TAKEOFF_OPS, LANDING_OPS

NEW_PAGE = 0
INVERT_COLORS = 1
REMOVE_LINE = 2

class TextProcessor(object):
    
    def __init__(self, operations):
        self._ops = {}
        for ac_eng, tops in operations.iteritems():
            _tops = {}
            for rex, op in tops.iteritems():
                _tops[re.compile(rex)] = \
                    (getattr(self, "_" + op[0]),) + tuple(op[1:]) \
                        if len(op) > 1 else (getattr(self, "_" + op[0]),)
            self._ops[ac_eng] = _tops
        self._match_func_partial = functools.partial(self._process_match, self)

    def _op_replace(self, match, replacement):
        #print "REPLACE '%s' with '%s'" % (match.group(),replacement)
        return replacement
    
    def _op_invert_colors(self, match):
        return self._op_replace_invert_colors(match, match.group())
        
    def _op_replace_invert_colors(self, match, replacement):
        s = match.span()
        ls = replacement.lstrip()
        rs = ls.rstrip()
        off = s[1] - len(ls)
        
        self._metadata.append((self._line_num, off, off + len(rs), INVERT_COLORS))
        return replacement
    
    def _op_remove_line(self, match):
        #print "REMOVE_LINE '%s'" % match.group()
        self._metadata.append((self._line_num, 0, 0, REMOVE_LINE))
        return ""

    def _op_newpage(self, match):
        self._metadata.append((self._line_num, 0, 0, NEW_PAGE))
        return ""

    def _process_match(self, match):
        op = self._tops[self._pattern]
        
        #print op
        if len(op) > 1:
            return op[0](match, *op[1:])
        return op[0](match)


    def process_lines(self, lines, ac_eng):
        tops = self._ops[ac_eng]
        
        self._ac_eng = ac_eng
        self._tops = tops
        self._metadata = []
        
        for i, l in enumerate(lines):
            self._line_num = i
            for pattern in tops.keys():
                self._pattern = pattern
                l, cnt = pattern.subn(self._process_match, l)
                #if cnt > 0:
                #    print "Replaced %d! '%s'" % (cnt, l)
                lines[i] = l
        return self._metadata


TAKEOFF_PROCESSOR = TextProcessor(TAKEOFF_OPS)
LANDING_PROCESSOR = TextProcessor(LANDING_OPS)


def _extract_pages(lines, metadata):
    per_page = []
    start = -1
    for (ln, s, e, type) in metadata:
        if type == NEW_PAGE:
            if start != -1:
                per_page.append(lines[start:ln])
            start = ln
    per_page.append(lines[start:])
    
    return per_page


def preprocess(lines, ac_eng, is_takeoff):
    # Delete 1st page
    i = 0
    while i < len(lines):
        if lines[i].startswith("\f"): break
        i += 1
    lines = lines[i:]

    # Do required operations
    if is_takeoff:
        metadata = TAKEOFF_PROCESSOR.process_lines(lines, ac_eng)
    else:
        metadata = LANDING_PROCESSOR.process_lines(lines, ac_eng)

    # Group lines into pages
    paged_lines = _extract_pages(lines, metadata)
    
    return paged_lines


def _test():
    import sys
    from ac_eng import *
    
    lines = open("CYOW.out", "r").readlines()
    res = preprocess(lines, AC_ENG_737_800W_27_26K, True)
    for page in res:
        print "NEW PAGE\n"
        sys.stdout.writelines(page)

if __name__ == '__main__':
    _test()