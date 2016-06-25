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
    """Unpacks the specified volume(s) into the given destdir.

       Arguments:
       sourcefile -- volume to unpack, or directory containing volumes to unpack
       destdir --  the directory to unpack into

       Returns the abs path to each unpacked volume.

    """
    assert os.path.exists(sourcefile), "sourcefile must exist"
    assert os.path.isdir(destdir), " destdir must be a directory"
    root_dirs = []
    for file in files(sourcefile):
        volumename = get_volumename(file)
        xdftool([file, "unpack", destdir], quiet=True)
        root_dir = os.path.join(destdir, volumename)
        assert os.path.isdir(root_dir)
        root_dirs.append(root_dir)
    return root_dirs if os.path.isdir(sourcefile) else root_dirs[0]

def list(volumepath, quiet=False):
    """Runs xdftool's list command, returns the output."""
    return xdftool([volumepath, "list"], quiet)

def get_volumename(volumepath):
    output = list(volumepath, quiet=True)
    return output.split("VOLUME")[0].strip()

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

def pack_hdf(srcdir, destimage, sizeMb):
    xdftool([destimage, "pack", srcdir, "size=%iMi" % sizeMb])

def files(sourcefile):
    return \
        [os.path.join(sourcefile, f) \
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
        seq_file.write(content)

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

def xdftool(args, quiet=False):
    import subprocess
    cmd = ["xdftool"] + [str(a) for a in args]
    if not quiet:
        print cmd
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output = p.communicate()[0]
    error = p.poll() != 0
    if not quiet or error:
        print output
    if error:
        sys.exit(1)
    return output

def join_mkdir(path, dir):
    p = os.path.join(path, dir)
    if (not os.path.exists(p)):
        os.mkdir(p)
    return p

class t_dir:
    def __enter__(self):
        self.tempdir = tempfile.mkdtemp("hdfsetup")
        return self.tempdir
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tempdir)

class StartupSequenceBuilder:
    def __init__(self):
        self.lines = []
        
    def assign(self, src, dest):
        if not src.endswith(":"):
            src = "%s:" % src
        if not dest.startswith("dh0:"):
            dest = "dh0:%s" % dest
        if " " in src:
            src = '"%s"' % src
        if " " in dest:
            dest = '"%s"' % dest
        self.lines.append("assign %s %s" % (src, dest))

    def echo(self, message, extraLine=True):
        self.lines.append('echo "%s"' % message)
        if extraLine:
            self.lines.append('echo ""')

    def addLine(self, line):
        self.lines.append("%s\n" % line)

    def build(self):
        return "%s\n" % str(self)

    def __str__(self):
        return "\n".join(self.lines)
    
if __name__ == "__main__":
    import config
    assert os.path.isfile(config.cadf), "config.cadf must be a valid file"
    assert os.path.isdir(config.adfdir), "config.adfdir must be a directory"
    assert config.desthdf is not None, "config.desthdf must be set"
    assert not os.path.isfile(config.desthdf),  "config.desthdf exists [%s]" % config.desthdf

    tempdir = "/tmp/hdfmk"

    if os.path.exists(tempdir):
        shutil.rmtree(tempdir)
    os.mkdir(tempdir)

    # name of dir adf(s) are in
    unpack_root = os.path.split(config.adfdir)[1]

    volume_dirs = unpack(config.adfdir, join_mkdir(tempdir, unpack_root))

    sb = StartupSequenceBuilder()
    for vdir in volume_dirs:
        src = os.path.split(vdir)[1]
        dest = os.path.join(unpack_root, src)
        sb.assign(src, dest)
    sb.addLine('cd "monkey2 disk 1:"')
    #sb.addLine('monkey2')

    add_startup_sequence(sb.build(), tempdir)
    build_c_dir(config.cadf, tempdir)
    pack_hdf(tempdir, config.desthdf, 20)
