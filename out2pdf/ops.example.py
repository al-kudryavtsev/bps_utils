from ac_eng import *
import re


# Escape all strings containing unused regexp metacharacters
_ = re.escape


# Aircraft-engine specific operations (takeoff)
TAKEOFF_OPS = {}
TAKEOFF_OPS[AC_ENG_737_300_22K] = {
    "MAX BRAKE RELEASE WT MUST NOT EXCEED MAX CERT TAKEOFF WT OF[ ]*[1-9][0-9]* KG": ("op_remove_line",),
}

TAKEOFF_OPS[AC_ENG_772_TRENT884] = {
    "MAX BRAKE RELEASE WT MUST NOT EXCEED MAX CERT TAKEOFF WT OF[ ]*[1-9][0-9]* KG": ("op_remove_line",),
    _("JUST STRING WITH REGEXP METACHARACTER .*[]"): ("op_replace", "ANOTHER STRING"),
}


# Aircraft-engine specific operations (landing)
LANDING_OPS = {}
LANDING_OPS[AC_ENG_737_300_22K] = {
    "Landing weight must not exceed[ ]*[1-9][0-9]* KG": ("op_remove_line",),
}

LANDING_OPS[AC_ENG_772_TRENT884] = LANDING_OPS[AC_ENG_737_300_22K]
