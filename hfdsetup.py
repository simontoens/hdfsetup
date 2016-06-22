#!/usr/bin/python

"""
This code mostly wraps xdftool and chains xdftool commands.
xdftool must be property installed.
See http://lallafa.de/blog/amiga-projects/amitools/xdftool
"""

import os
import shutil
import sys
import tempfile

def unpack(sourcefile, destdir):
    """Unpacks the specified adf into the given destdir.

       Arguments:
       sourcefile -- adf to unpack, or directory containing adfs to unpack
       destdir --  the directory to unpack into

    """
    assert os.path.exists(sourcefile), "sourcefile must exist"
    assert os.path.isdir(destdir), " destdir must be a directory"
    for file in files(sourcefile):
        xdftool([file, "unpack", destdir])

def list(path):
    """Runs xdftool's list command and returns the output."""
    xdftool([path, "list"])

def create_adf(filename, destdir):
    imagepath = os.path.join(destdir, filename)
    diskname = os.path.splitext(filename)[0]
    xdftool([imagepath, "format", diskname.capitalize(), "+", "boot", "install"])
    return imagepath

def create_hdf(filename, size_mb, destdir):
    imagepath = os.path.join(destdir, filename)
    diskname = os.path.splitext(filename)[0]
    xdftool([imagepath, "create", "format", diskname.capitalize(), "size=%sMi" % size_mb, "+", "boot", "install"])
    return imagepath

def pack_hdf(srcdir, destimage):
    xdftool([destimage, "pack", srcdir, "size=10Mi"])

def files(sourcefile):
    return \
        ['"%s"' % os.path.join(sourcefile, f) \
        for f in os.listdir(sourcefile) \
        if f.lower().endswith(".adf")] \
        if os.path.isdir(sourcefile) else [sourcefile]

def build_c_dir(c_dir_adf, destdir, command_list=["type", "dir", "cd", "echo", "assign"]):
    cdir = safe_mkdir("c", destdir)
    with t_dir() as tempdir:
        unpack(c_dir_adf, tempdir)
        adfdir = getdirectory(tempdir)
        for f in [os.path.join(adfdir, "c", cmd) for cmd in command_list]:
            shutil.copy(f, cdir)
    return cdir

def add_startup_sequence(content, destdir):
    sdir = safe_mkdir("s", destdir)
    seq = os.path.join(sdir, "startup-sequence")
    with open(seq, "w") as seq_file:
        seq_file.write("%s\n" % content)

def safe_mkdir(dirname, destdir):
    destdir = os.path.join(destdir, dirname)
    if not os.path.exists(destdir):
        os.mkdir(destdir)
    return destdir

def getdirectory(dirpath):
    """Returns the abs path of the first directory found that is a child of the given dirpath."""
    for f in os.listdir(dirpath):
        abspath = os.path.join(dirpath, f)
        if os.path.isdir(abspath):
            return abspath

def xdftool(args):
    cmd = 'xdftool ' + " ".join([str(a) for a in args])
    status = os.system(cmd)
    print cmd
    if status == 0:
        print "...Ok"
    else:
        print "...Failed, aborting"
        sys.exit(1)

class t_dir:
    def __enter__(self):
        self.tempdir = tempfile.mkdtemp("hdfsetup")
        return self.tempdir
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tempdir)
    
if __name__ == "__main__":
    # setup
    cadf = "cadf.adf"; # path to adf with a c dir that has common comamnds
    tempdir = "/tmp/hdfmk"
    desthdf = "./test.hdf"
    
    if os.path.exists(tempdir):
        shutil.rmtree(tempdir)
    os.mkdir(tempdir)

    build_c_dir(cadf, tempdir)
    add_startup_sequence('echo "This is a an HDF"', tempdir)
    pack_hdf(tempdir, desthdf)
    list(desthdf)
