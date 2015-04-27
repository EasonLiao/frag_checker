#!/usr/bin/python

''' A simle wrapper on command debugfs to help you inspect file fragmentation. '''

import argparse
import re
import os
from subprocess import check_call, check_output
import subprocess

parser = argparse.ArgumentParser(description="Fragmentation checker")
parser.add_argument("--device", "-d", type=str, required=True, help="The device containting the file system.")
parser.add_argument("--dir", type=str, help="The directory you want to check.")
parser.add_argument("--file", "-f", type=str, help="The file you want to check.")
parser.add_argument("--verbose", "-v", type=str, help="Not only print number of contiguous blocks but also detailed information.")
parser.add_argument("--filter", type=int, default=0, help="Only show files which have more than <filter> contiguous blocks.")

args = parser.parse_args()
n_pattern = re.compile(".*: (\d+) contiguous extents")
black_hole = open(os.devnull, 'w')

def get_num_contiguous_blocks(path):
    # Return number of contiguous blocks for a given path.
    output = check_output(["debugfs", args.device, "-R", "filefrag %s" % path], stderr=black_hole)
    mo = re.match(n_pattern, output)
    assert mo is not None, "Failed to match output of debugfs."
    n_blocks = mo.group(1)
    return int(n_blocks)

def walk_directory(path):
    # Get info for all the files under directory path or its subdirectories.
    results = []
    for root, _, files in os.walk(path):
        for f in files:
            full_path = os.path.join(root, f)
            results.append((full_path, get_num_contiguous_blocks(full_path)))

    return results

def show_results(results):
    for result in results:
        print("%s: %d" % result)

def main():
    if args.dir == None and args.file == None:
        print("You must specify at least one directory or file to check.")
        return

    if args.dir != None:
        # Convert relpath to abspath.
        path = os.path.abspath(args.dir)
        results = walk_directory(path)
        show_results(filter(lambda x: x[1] >= args.filter, results))
    else:
        # Convert relpath to abspath.
        path = os.path.abspath(args.file)
        results = [(path, get_num_contiguous_blocks(path))]
        show_results(results)

if __name__ == "__main__":
    main()
