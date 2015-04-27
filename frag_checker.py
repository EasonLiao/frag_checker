#!/usr/bin/python

''' A simle wrapper on command debugfs to help you inspect file fragmentation. '''

import argparse
import re
import sys
import os
from subprocess import check_output
import subprocess
import tempfile

parser = argparse.ArgumentParser(description="Fragmentation checker")
parser.add_argument("--dir", type=str, help="The directory you want to check.")
parser.add_argument("--file", "-f", type=str, help="The file you want to check.")
# parser.add_argument("--verbose", "-v", type=str, help="Not only print number of contiguous blocks but also detailed information.")
parser.add_argument("--filter", type=int, default=0, help="Only show files which have more than <filter> contiguous blocks.")

args = parser.parse_args()
n_pattern = re.compile("(.*): (\d+) contiguous extents")
black_hole = open(os.devnull, 'w')

def find_mount_info(path):
  assert os.path.exists(path), "Path not exist!"
  out = check_output(["df", path])
  lines = out.split('\n')[1]
  cols = lines.split()
  device, mount_point = cols[0], cols[5]
  return device, mount_point

def get_num_contiguous_blocks(dev_name, rel_path):
    # Return number of contiguous blocks for a given path.
    output = check_output(["debugfs", dev_name, "-R", "filefrag %s" % rel_path], stderr=black_hole)
    mo = re.match(n_pattern, output)
    assert mo is not None, "Failed to match output of debugfs."
    n_blocks = mo.group(2)
    return int(n_blocks)

def generate_code(f, rel_path, all_files):
    f.write("cd %s\n" % rel_path)
    for f_path in all_files:
        f.write("filefrag %s\n" % f_path)
    f.write("quit\n")
    # Must flush!
    f.flush()

def walk_directory(dev_name, rel_path, mount_point):
    all_files = []
    dir_path = os.path.join(mount_point, rel_path)
    # List all the files under dir_path.
    for item in os.listdir(dir_path):
        if os.path.isfile(os.path.join(dir_path, item)):
            all_files.append(item)

    # Create a temporary file to store generated code for debugfs.
    code_file = tempfile.NamedTemporaryFile(delete=False)
    generate_code(code_file, rel_path, all_files)

    # Execute debugfs with generated code.
    cmds = ["debugfs", "-f", code_file.name, dev_name]
    output = check_output(cmds, stderr=black_hole)

    # Break output of debugfs into lines.
    lines = output.split('\n')
    results = []
    for line in lines:
        mo = re.match(n_pattern, line)
        if mo is not None:
            results.append((mo.group(1), int(mo.group(2))))
    return results

def show_results(results):
    total_blocks  = 0
    total_files = len(results)
    for result in results:
        total_blocks += result[1]
        if result[1] >= args.filter:
            print("%s: %d" % result)
    print("Total files: %d, total contiguous blocks: %d" % (total_files, total_blocks))

def main():
    if args.dir == None and args.file == None:
        print("You must specify at least one directory or file to check.")
        return

    if args.dir != None:
        # Convert relpath to abspath.
        path = os.path.abspath(args.dir)
        dev_name, mount_point = find_mount_info(path)
        rel_path = os.path.relpath(path, start=mount_point)
        results = walk_directory(dev_name, rel_path, mount_point)
        show_results(results)
    else:
        # Convert relpath to abspath.
        path = os.path.abspath(args.file)
        dev_name, mount_point = find_mount_info(path)
        rel_path = os.path.relpath(path, start=mount_point)
        results = [(path, get_num_contiguous_blocks(dev_name, rel_path))]
        show_results(results)

if __name__ == "__main__":
    main()
