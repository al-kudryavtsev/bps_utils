import functools
import re
from ops import TAKEOFF_OPS, LANDING_OPS

class MetaTag(object):
    NEW_PAGE = 0
    INVERT_COLORS = 1
    REMOVE_LINE = 2
    REPLACE = 3
    UNDERLINE = 4
    LARGE_FONT = 5
    FRAME = 6

class PreprocessException(Exception):
    pass

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

    # Update metadata with new element
    # If we already have element for current line, insert new one into right position
    # Offset is required to update start/end of tail elements if line len changes
    def _metadata_update(self, start, length, tag, offset=0):
        items = self._metadata.get(self._line_num, None)
        end = start + length
        
        #print (self._line_num, start, end, tag, offset)
        if items is None:
            self._metadata[self._line_num] = [[start, length, tag]]
        else:
            for n, item in enumerate(items):
                if end <= item[0] + offset:
                    items.insert(n, [start, length, tag])
                    for i in range(n + 1, len(items)):
                        items[i][0] += offset
                    break
                if start < item[0] + item[1] + offset:
                    raise PreprocessException("File '%s', line %d: cannot add "
                        "overlapping operation at range [%d, %d], "
                        "offset %d.\n" % (self._data_fname, self._line_num,
                            start, end, offset))
                if n == len(items) - 1:
                    items.append([start, length, tag])
                    break
        #print self._metadata[self._line_num]
        
    def _op_replace(self, match, replacement):
        self._metadata_update(match.start(), len(replacement),
            MetaTag.REPLACE, offset=len(replacement) - len(match.group()))
        return replacement
    
    def _op_invert_colors(self, match):
        return self._op_replace_invert_colors(match, match.group())
        
    def _op_replace_invert_colors(self, match, replacement):
        s = match.span()
        ls = replacement.lstrip()
        rs = ls.rstrip()
        off = s[1] - len(ls)
        delta_offset = len(replacement) - (s[1] - s[0])
        self._metadata_update(off, len(rs), MetaTag.INVERT_COLORS,
            offset=delta_offset)
        return replacement

    def _op_replace_invert_colors_range(self, match, replacement, start, end):
        s = match.span()
        delta_offset = len(replacement) - (s[1] - s[0])
        self._metadata_update(s[0] + start, end - start, MetaTag.INVERT_COLORS,
            offset=delta_offset)
        return replacement

    def _op_underline(self, match):
        self._metadata_update(match.start(), match.end() - match.start(),
            MetaTag.UNDERLINE)
        return match.group()
    
    def _op_flaps_and_aircond(self, match):
        replacement = match.group()
        if match.group('flaps') is not None:
            self._metadata_update(match.start('flaps'), match.end('flaps') -
                match.start('flaps'), MetaTag.LARGE_FONT)
        city = match.group('city')
        city_off = match.start('city')
        replacement = replacement[:city_off - 2] + city
        
        ac = match.group('ac')
        if ac == 'AIR COND OFF':
            self._metadata_update(match.start('ac'), match.end('ac') -
                match.start('ac'), MetaTag.INVERT_COLORS)
        return replacement.rstrip()
        
    def _op_remove_line(self, match):
        self._metadata_update(0, 0, MetaTag.REMOVE_LINE)
        return ""

    def _op_newpage(self, match):
        # Newpage detected by form feed thus offset is -1
        self._metadata_update(0, 0, MetaTag.NEW_PAGE, offset=-1)
        return match.group()[1:]

    def _process_match(self, match):
        op = self._tops[self._pattern]
        
        if len(op) > 1:
            return op[0](match, *op[1:])
        return op[0](match)


    def _gen_newpage_re(self, apt_code):
        cache = self._apt_code_re_cache = getattr(self,
            "_apt_code_re_cache", {})
        
        rex = "\\f.*%s$" % apt_code
        
        if not apt_code in cache:
            cache[apt_code] = re.compile(rex)

        return cache[apt_code]


    def _check_has_pages(self):
        for ln, meta in self._metadata.iteritems():
            for (start, end, tag) in meta:
                if tag == MetaTag.NEW_PAGE:
                    return True
        return False


    def process_lines(self, lines, ac_eng, data_fname, apt_code):
        tops = self._ops[ac_eng]
        
        self._data_fname = data_fname
        self._ac_eng = ac_eng
        self._tops = tops
        self._metadata = {}
        tops[self._gen_newpage_re(apt_code)] = (self._op_newpage,)
        
        for i, l in enumerate(lines):
            l = l.rstrip()
            self._line_num = i
            for pattern in tops.keys():
                self._pattern = pattern
                l, cnt = pattern.subn(self._process_match, l)
                lines[i] = l
                
        if self._check_has_pages() is False:
            raise PreprocessException("File '%s': no valid pages found.\n" %
                self._data_fname)
        return self._metadata


TAKEOFF_PROCESSOR = TextProcessor(TAKEOFF_OPS)
LANDING_PROCESSOR = TextProcessor(LANDING_OPS)


def preprocess(data_fname, ac_eng, apt_code, is_takeoff):

    with open(data_fname, 'r') as f:
        lines = [unicode(l, 'cp1251') for l in f.readlines()]

    # Delete 1st page
    i = 0
    while i < len(lines):
        if lines[i].startswith("\f"): break
        i += 1
    lines = lines[i:]

    # Do required operations
    if is_takeoff:
        metadata = TAKEOFF_PROCESSOR.process_lines(lines, ac_eng, data_fname, apt_code)
    else:
        metadata = LANDING_PROCESSOR.process_lines(lines, ac_eng, data_fname, apt_code)
    return (lines, metadata)


def _test():
    res, meta = preprocess("CYOW.out", AC_ENG_737_800W_27_26K, "CYOW", True)
    for i, line in enumerate(res):
        if i in meta:
            sys.stdout.write("META[%s]" % str(meta[i]))
        sys.stdout.write(line)

if __name__ == '__main__':
    import sys
    from ac_eng import *
    _test()
