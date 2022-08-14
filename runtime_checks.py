#!/usr/bin/env python
from finddups3 import Pool, Finfo, parallel_hash, ValidationError

pool = Pool(8)

fileGroups = [
    [
        ("finddups.py", 7188, 8269401),
        ("finddups2.py", 8037, 8269470),
        ("finddups2a.py", 7866, 8269464),
        ("finddups3.py", 8061, 8269341),
        ("finddups4.py", 8085, 8269452),
    ],
    [
        ("finddups.py", 7188, 8269401),
        ("finddups2.py", 8037, 8269470),
        ("finddups2a.py", 7866, None),
        ("finddups3.py", 8061, 8269341),
    ],
    [
        ("finddups.py", 7188, 8269401),
        ("finddups2.py", 8037, 8269470),
        ("finddups2a.py", 7866, 8269464),
    ],
]

for ngroup, group in enumerate(fileGroups):
    try:
        files = [Finfo(*tup) for tup in group]
        for hash_info in parallel_hash(files, pool):
            print(hash_info.digest, hash_info.finfo.path)
    except ValidationError as e:
        print(f"Problem detected with file group {ngroup+1}")
        print(e)
    print("-" * 79)
