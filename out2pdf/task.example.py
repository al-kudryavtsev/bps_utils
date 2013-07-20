# coding: cp1251
from ac_eng import *

AIRPORT_FILE = 'C:\APTRWY.txt'

DATA_FOLDER = '.'

TASKS = [
    'Boeing 737-300 CFM56-3B-2',
    'Boeing 777-200ER Trent 884'
    ]

TARGET_FOLDERS = ['OUT_GOOD'] # None for all available

# Group many folders into one, each file per airport groups
# results of grouped folders
FOLDER_GROUP_RULES = {f: 'ALL_OPERATIVE' for f in ['OUT_DRY', 'OUT_GOOD',
    'OUT_MEDIUM', 'OUT_POOR']}

ALL_TASKS = {
    'Boeing 737-300 CFM56-3B-2': {
        'ac_eng': AC_ENG_737_300_22K,
        'takeoff': [
            'OUT_DRY',
            'OUT_GOOD',
            'OUT_MEDIUM',
            'OUT_POOR',
            'OUT__GOOD_REV_INOP',
            ],
        'landing': ['LAND_OUT_WET', 'LAND_OUT_DRY'],
    },
    'Boeing 777-200ER Trent 884': {
        'ac_eng': AC_ENG_772_TRENT884,
        'takeoff': [
            'OUT_DRY',
            'OUT_GOOD',
            'OUT_MEDIUM',
            'OUT_POOR',
            'OUT__AC_OFF',
            ],
        'landing': ['LAND_OUT_WET', 'LAND_OUT_DRY'],
    }
}

PDF_NAME_TEMPLATES = {
    'OUT_DRY': '%(code)s_%(ac_eng)s__DRY.pdf',
    'OUT_GOOD': '%(code)s_%(ac_eng)s__GOOD.pdf',
    'OUT_MEDIUM': '%(code)s_%(ac_eng)s__MEDIUM.pdf',
    'OUT_POOR': '%(code)s_%(ac_eng)s__POOR.pdf',
    'OUT__AC_OFF': '%(code)s_%(ac_eng)s__AC_OFF.pdf',
    'OUT__GOOD_REV_INOP': '%(code)s_%(ac_eng)s__GOOD_REV_INOP.pdf',
    'LAND_OUT_DRY': '%(code)s_%(ac_eng)s__LDG_DRY_DISPATCH.pdf',
    'LAND_OUT_WET': '%(code)s_%(ac_eng)s__LDG_WET_DISPATCH.pdf',
    
    'ALL_OPERATIVE': '%(code)s_%(ac_eng)s_ALL_OPERATIVE.pdf',
}
