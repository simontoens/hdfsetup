#!/usr/bin/python

"""
This code mostly wraps xdftool and chains xdftool commands.
xdftool must be property installed.
See http://lallafa.de/blog/amiga-projects/amitools/xdftool
"""

import distutils.dir_util
import os
import shutil
import subprocess
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
    xdftool([destimage, "pack", srcdir, "size=%iMi" % sizeMb], quiet=True)

def files(sourcefile):
    return \
        [os.path.join(sourcefile, f) \
        for f in os.listdir(sourcefile) \
        if f.lower().endswith(".adf")] \
        if os.path.isdir(sourcefile) else [sourcefile]

def augment_c_dir(c_dir_adf, destdir):
    command_list = ["type", "dir", "cd", "echo", "assign", "info", "wait"]
    cdir = join_mkdir(destdir, "c")
    with temp_dir() as tempdir:
        unpack(c_dir_adf, tempdir)
        adfdir = getdirectory(tempdir)
        for f in [os.path.join(adfdir, "c", cmd) for cmd in command_list]:
            shutil.copy(f, cdir)
    return cdir

def add_startup_sequence(content, destdir, quiet=True):
    sdir = join_mkdir(destdir, "s")
    seq = os.path.join(sdir, "startup-sequence")
    if not quiet:
        print "startup-sequence:"
        print content
    with open(seq, "w") as seq_file:
        seq_file.write(content)

def getdirectory(dirpath):
    """Returns the abs path of the first directory found that is a child of the given dirpath."""
    for f in os.listdir(dirpath):
        abspath = os.path.join(dirpath, f)
        if os.path.isdir(abspath):
            return abspath
        
def rm_xdftool_md(dirpath):
    paths = [os.path.join(dirpath, f) for f in os.listdir(dirpath) if os.path.splitext(f)[1] in (".xdfmeta", ".blkdev")]
    for p in paths:
        os.remove(p)

def xdftool(args, quiet=False):
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

def get_size_bytes(start_dirpath):
    total_size_bytes = 0
    for dirpath, dirnames, filenames in os.walk(start_dirpath):
        for f in filenames:
            total_size_bytes += os.path.getsize(os.path.join(dirpath, f))
    return total_size_bytes

def get_hdf_size_mb(destdir):
    size_bytes = get_size_bytes(destdir)
    size_mb = size_bytes / (1000 * 1000) # too small when using 1024 * 1024
    size_mb += (size_mb * 0.3) # leave 30% of hdf free ...
    size_mb = round(size_mb) #  ... but make it a nice round number
    return size_mb

class temp_dir:
    def __enter__(self):
        self.tempdir = tempfile.mkdtemp("hdfsetup")
        return self.tempdir
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tempdir)

class BatchFileBuilder:
    def __init__(self):
        self._lines = []
        
    def assign(self, src, dest):
        if not src.endswith(":"):
            src = "%s:" % src
        if not dest.startswith("dh0:"):
            dest = "dh0:%s" % dest
        self._lines.append('assign %s %s' % (self._esc(src), self._esc(dest)))

    def info(self):
        self._lines.append("info")

    def cd(self, path):
        self._lines.append('cd %s' % self._esc(path))

    def comment(self, comment=None):
        line = ";"
        if comment is not None:
            line = "%s %s" % (line, comment)
        self._lines.append(line)

    def echo(self, message=""):
        self._lines.append('echo "%s"' % message)
        
    def execute(self, path):
        self._lines.append('execute %s' % self._esc(path))

    def wait(self, numSeconds=1):
        self._lines.append('wait %i secs' % numSeconds)

    def addLine(self, line):
        self._lines.append("%s\n" % line)

    def addContent(self, content):
        for line in content.split("\n"):
            line = line.replace("df0:", "")
            self._lines.append(line)

    def build(self):
        return "%s\n" % str(self)

    def __str__(self):
        return "\n".join(self._lines)

    def _esc(self, path):
        return '"%s"' % path if " " in path else path
    
if __name__ == "__main__":
    import config
    assert os.path.isfile(config.cadf), "config.cadf must be a valid file"
    assert os.path.isdir(config.adfdir), "config.adfdir must be a directory"
    assert config.desthdf is not None, "config.desthdf must be set"
    assert not os.path.isfile(config.desthdf),  "config.desthdf exists [%s]" % config.desthdf

    # name of dir adf(s) are in
    unpack_root_name = os.path.split(config.adfdir)[1]

    with temp_dir() as tempdir:
        assert len(os.listdir(tempdir)) == 0
        # when creating the hdf file, the volume name comes from the
        # top-level directory name being packed
        volumename = os.path.split(config.desthdf)[1]
        if '.' in volumename:
            volumename = os.path.splitext(volumename)[0]
        tempdir = join_mkdir(tempdir, volumename)

        # put files into a subdirectory in the hdf filesystem
        unpack_root = join_mkdir(tempdir, unpack_root_name)

        volume_dirs = unpack(config.adfdir, unpack_root)

        for vdir in volume_dirs:
            distutils.dir_util.copy_tree(vdir, unpack_root)
            shutil.rmtree(vdir)
        rm_xdftool_md(unpack_root)

        cdir = os.path.join(unpack_root, "c")
        if os.path.exists(cdir):
            root_cdir = os.path.join(tempdir, "c")
            os.mkdir(root_cdir)
            distutils.dir_util.copy_tree(cdir, root_cdir)

        startSeqBuilder = BatchFileBuilder()
        startSeqBuilder.comment("-------------------------------------------")
        startSeqBuilder.comment("| Generated by hdfsetup                   |") 
        startSeqBuilder.comment("| https://github.com/simontoens/hdfsetup  |")
        startSeqBuilder.comment("-------------------------------------------")
        startSeqBuilder.comment()
        startSeqBuilder.info()
        startSeqBuilder.wait()
        startSeqBuilder.cd(unpack_root_name)
        startSeqBuilder.comment("start of original startup-sequence")
        with open(os.path.join(unpack_root, "s", "startup-sequence")) as f:
            startSeqBuilder.addContent(f.read())

        add_startup_sequence(startSeqBuilder.build(), tempdir, quiet=False)
        augment_c_dir(config.cadf, tempdir)
        pack_hdf(tempdir, config.desthdf, get_hdf_size_mb(tempdir))
