#!/usr/bin/env python
"""
Given a root directory, recurse in it and find all the duplicate
files, files that have the same contents, but not necessarily the
same filename.
"""

# created by David Mertz and Martin Blais
#
# This code is released as CC-0
# http://creativecommons.org/publicdomain/zero/1.0/

from pydantic import ValidationError
from pydantic.dataclasses import dataclass
from sys import maxsize, stderr
import optparse
from os import readlink, cpu_count, scandir, PathLike
from os.path import islink, abspath, isdir
from fnmatch import fnmatch
from hashlib import sha1
from itertools import groupby
from operator import attrgetter
import multiprocessing.pool
from multiprocessing import Pool
from typing import Iterator, Iterable, Any


# Keep together associated file information
@dataclass
class Finfo:
    path: str
    size: int
    inode: int


@dataclass
class HashRecord:
    digest: str
    finfo: Finfo


# Keep stats on hashes performed and avoided
hashes_calculated, hashes_skipped = 0, 0


def main() -> None:
    parser = optparse.OptionParser(__doc__.strip())
    parser.add_option(
        "-M",
        "--max-size",
        type="int",
        default=maxsize,
        help="Ignore files larger than MAX_SIZE",
    )
    parser.add_option(
        "-m",
        "--min-size",
        type="int",
        default=1,
        help="Ignore files smaller than MIN_SIZE",
    )
    parser.add_option(
        "-l",
        "--enable-symlinks",
        action="store_true",
        default=False,
        help="Include symlinks in duplication report",
    )
    parser.add_option(
        "-g",
        "--glob",
        type="str",
        default="*",
        help="Limit matches to glob pattern",
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Display progress information on STDERR",
    )
    opts, args = parser.parse_args()
    if not args:
        parser.error("You must specify directories to search.")

    find_duplicates(args, opts)


def scan_files(args: Iterable[str | PathLike[Any]], opts) -> Iterator[Finfo]:
    for dir in args:
        if isdir(dir):
            for entry in scandir(dir):
                if entry.is_dir(follow_symlinks=opts.enable_symlinks):
                    yield from scan_files([entry.path], opts)
                elif entry.is_file(follow_symlinks=opts.enable_symlinks):
                    if fnmatch(entry.name, opts.glob):
                        try:
                            path = entry.path
                            size = entry.stat().st_size
                            inode = entry.inode()
                            yield Finfo(path, size, inode)
                        except FileNotFoundError as err:
                            if opts.verbose:
                                print(err, file=stderr)


# NOTE: return is now a more structured dataclass
def hash_content(finfo: Finfo) -> HashRecord:
    try:
        with open(finfo.path, "rb") as fh:
            content = fh.read()
            return HashRecord(sha1(content).hexdigest(), finfo)
    except IOError as s:
        print(s, file=stderr)
        return HashRecord("_ERROR", finfo)


def parallel_hash(
    finfos: list[Finfo], pool: multiprocessing.pool.Pool
) -> list[HashRecord]:
    global hashes_calculated, hashes_skipped
    # Might have exclusively paths of this size with same inode
    if len({finfo.inode for finfo in finfos}) == 1:
        inode = finfos[0].inode  # Any finfo will do
        hashes = [HashRecord(f"<INODE {inode}>", finfo) for finfo in finfos]
        hashes_skipped += len(finfos)
        return hashes

    # Otherwise, split up the inodes with one versus several paths
    unique_inodes = [f[0] for _, f in group_by_key(finfos, "inode") if len(f) == 1]
    dup_inodes = [f for _, f in group_by_key(finfos, key="inode") if len(f) > 1]

    # Use the pool to parallelize distinct inodes
    hashes = pool.map(hash_content, unique_inodes)
    hashes_calculated += len(hashes)
    if not dup_inodes:  # No dup inodes to handle below
        return hashes

    # Might add to hashes if we have hardlink sets
    # Note: there COULD be many such inode sets, which are calculated
    #     serially.  However, the performance difference between serial
    #     and parallel is so small that it matters little.
    for dup_inode in dup_inodes:
        hash_record = hash_content(dup_inode[0])
        hashes_calculated += 1
        hashes_skipped -= 1  # Will add back in loop
        for finfo in dup_inode:
            hashes.append(HashRecord(hash_record.digest, finfo))
            hashes_skipped += 1

    return hashes


def group_by_key(
    records: Iterable[object],
    key: str,
    reverse: bool = True,
) -> Iterator[tuple[Any, list]]:
    """Combine records by common value in position (default first)

    This function is passed an interable each of whose values is a tuple;
    it yields a sequence of tuples whose first element is the identical
    key-position element from the original pairs, and whose second element
    is a list of tail elements corresponding to the same key element:

      >>> Thing = namedtuple('Thing', 'order name value')
      >>> things = [Thing(1, "foo", 17),
      ...           Thing(1, "bar", 119),
      ...           Thing(2, "baz", 43)]
      >>> list(group_by_key(things, "order", reverse=False))
      [(1, [Thing(order=1, name='foo', value=17),
            Thing(order=1, name='bar', value=119)]),
      (2, [Thing(order=2, name='baz', value=43)])]

    By default, groups are arranged from largest to smallest key value.

    By passing a val_type argument, the groups may be cast into a whatever
    special type is needed, initialized by the tuple of arguments.
    """
    records = sorted(records, key=attrgetter(key), reverse=reverse)
    for idx, vals in groupby(records, attrgetter(key)):
        yield (idx, list(vals))


def get_path_infos(
    dirs: Iterable[str | PathLike[Any]], opts: optparse.Values
) -> Iterator[Finfo]:
    "Yield a sequence of Finfo objects"
    count = 0
    for finfo in scan_files(dirs, opts):
        if opts.min_size <= finfo.size <= opts.max_size:
            count += 1
            yield finfo
    if opts.verbose:
        print(f"Looked up  {count:,} file sizes", file=stderr)


def find_duplicates(dirs: Iterable[str | PathLike[Any]], opts: optparse.Values) -> None:
    "Find the duplicate files in the given root directory."
    # NOTE: this is a kludge to make mypy happy.  None is a *possible* return
    # value for cpu_count(), but it will not happy on common architectures
    n_cpus = cpu_count() or 2
    # Need process pool
    pool = Pool(processes=int(n_cpus * 0.75))
    distincts = 0
    npaths = 0

    # Loop over the path records
    paths = get_path_infos(dirs, opts)
    for sz, finfos in group_by_key(paths, "size"):
        # We have accumulated some dups that need to be printed
        if len(finfos) > 1:
            hashes = parallel_hash(finfos, pool=pool)
            for hash, vals in group_by_key(hashes, "digest"):
                if len(vals) > 1:
                    distincts += 1
                    print("Size:", sz, "| SHA1:", hash)
                    for hashrecord in vals:
                        npaths += 1
                        if islink(hashrecord.finfo.path):
                            ln = "-> " + readlink(hashrecord.finfo.path)
                            print(" ", abspath(hashrecord.finfo.path), ln)
                        else:
                            print(" ", abspath(hashrecord.finfo.path))

    if opts.verbose:
        print(f"Found      {distincts:,} duplicatation sets", file=stderr)
        print(f"Found      {npaths:,} paths within sets", file=stderr)
        print(f"Calculated {hashes_calculated:,} SHA1 hashes", file=stderr)
        print(f"Short-cut  {hashes_skipped:,} hard links", file=stderr)


if __name__ == "__main__":
    try:
        main()
    except ValidationError as e:
        print(e.json())
        raise
