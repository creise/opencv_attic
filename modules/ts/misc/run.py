import testlog_parser, sys, os, platform, xml, re, tempfile, glob, datetime, getpass
from optparse import OptionParser
from subprocess import Popen, PIPE

hostos = os.name # 'nt', 'posix'
hostmachine = platform.machine() # 'x86', 'AMD64', 'x86_64'
nameprefix = "opencv_perf_"


parse_patterns = (
  {'name': "has_perf_tests",     'default': "OFF",      'pattern': re.compile("^BUILD_PERF_TESTS:BOOL=(ON)$")},
  {'name': "cmake_home",         'default': None,       'pattern': re.compile("^CMAKE_HOME_DIRECTORY:INTERNAL=(.+)$")},
  {'name': "opencv_home",        'default': None,       'pattern': re.compile("^OpenCV_SOURCE_DIR:STATIC=(.+)$")},
  {'name': "tests_dir",          'default': None,       'pattern': re.compile("^EXECUTABLE_OUTPUT_PATH:PATH=(.+)$")},
  {'name': "build_type",         'default': "Release",  'pattern': re.compile("^CMAKE_BUILD_TYPE:STRING=(.*)$")},
  {'name': "svnversion_path",    'default': None,       'pattern': re.compile("^SVNVERSION_PATH:FILEPATH=(.*)$")},
  {'name': "cxx_flags",          'default': None,       'pattern': re.compile("^CMAKE_CXX_FLAGS:STRING=(.*)$")},
  {'name': "cxx_flags_debug",    'default': None,       'pattern': re.compile("^CMAKE_CXX_FLAGS_DEBUG:STRING=(.*)$")},
  {'name': "cxx_flags_release",  'default': None,       'pattern': re.compile("^CMAKE_CXX_FLAGS_RELEASE:STRING=(.*)$")},
  {'name': "ndk_path",           'default': None,       'pattern': re.compile("^ANDROID_NDK(?:_TOOLCHAIN_ROOT)?:PATH=(.*)$")},
  {'name': "arm_target",         'default': None,       'pattern': re.compile("^ARM_TARGET:INTERNAL=(.*)$")},
  {'name': "android_executable", 'default': None,       'pattern': re.compile("^ANDROID_EXECUTABLE:FILEPATH=(.*android.*)$")},
  {'name': "is_x64",             'default': "OFF",      'pattern': re.compile("^CUDA_64_BIT_DEVICE_CODE:BOOL=(ON)$")},#ugly(
  {'name': "cmake_generator",    'default': None,       'pattern': re.compile("^CMAKE_GENERATOR:INTERNAL=(.+)$")},
)

class RunInfo(object):
    def __init__(self, path):
        self.path = path
        self.error = None
        for p in parse_patterns:
            setattr(self, p["name"], p["default"])
        cachefile = open(os.path.join(path, "CMakeCache.txt"), "rt")
        try:
            for l in cachefile.readlines():
                ll = l.strip()
                if not ll or ll.startswith("#"):
                    continue
                for p in parse_patterns:
                    match = p["pattern"].match(ll)
                    if match:
                        value = match.groups()[0]
                        if value and not value.endswith("-NOTFOUND"):
                            setattr(self, p["name"], value)
        except:
            pass
        cachefile.close()
        # add path to adb
        if self.android_executable:
            self.adb = os.path.join(os.path.dirname(os.path.dirname(self.android_executable)), ("platform-tools/adb","platform-tools/adb.exe")[hostos == 'nt'])
        else:
            self.adb = None
        # detect target platform    
        if self.android_executable or self.arm_target or self.ndk_path:
            self.targetos = "android"
        else:
            self.targetos = hostos
        # fix has_perf_tests param
        self.has_perf_tests = self.has_perf_tests == "ON"
        # fix is_x64 flag
        self.is_x64 = self.is_x64 == "ON"
        # detect target arch
        if self.targetos == "android":
            self.targetarch = "arm"
        elif self.is_x64 and hostmachine in ["AMD64", "x86_64"]:
            self.targetarch = "x64"
        elif hostmachine in ["x86", "AMD64", "x86_64"]:
            self.targetarch = "x86"
        else:
            self.targetarch = "unknown"
            
        # fix test path
        if "Visual Studio" in self.cmake_generator:
            self.tests_dir = os.path.join(self.tests_dir, self.build_type)
            
        self.hardware = None
        
        self.getSvnVersion(self.cmake_home, "cmake_home_svn")
        if self.opencv_home == self.cmake_home:
            self.opencv_home_svn = self.cmake_home_svn
        else:
            self.getSvnVersion(self.opencv_home, "opencv_home_svn")
            
        self.tests = self.getAvailableTestApps()
        
    def getSvnVersion(self, path, name):
        if not self.has_perf_tests or not self.svnversion_path or not os.path.isdir(path):
            if not self.svnversion_path and hostos == 'nt':
                self.tryGetSvnVersionWithTortoise(path, name)
            else:
                setattr(self, name, None)
            return
        svnprocess = Popen([self.svnversion_path, "-n", path], stdout=PIPE, stderr=PIPE)
        output = svnprocess.communicate()
        setattr(self, name, output[0])
        
    def tryGetSvnVersionWithTortoise(self, path, name):
        try:
            wcrev = "SubWCRev.exe"
            dir = tempfile.mkdtemp()
            #print dir
            tmpfilename = os.path.join(dir, "svn.tmp")
            tmpfilename2 = os.path.join(dir, "svn_out.tmp")
            tmpfile = open(tmpfilename, "w")
            tmpfile.write("$WCRANGE$$WCMODS?M:$")
            tmpfile.close();
            wcrevprocess = Popen([wcrev, path, tmpfilename, tmpfilename2, "-f"], stdout=PIPE, stderr=PIPE)
            output = wcrevprocess.communicate()
            if "is not a working copy" in output[0]:
                version = "exported"
            else:
                tmpfile = open(tmpfilename2, "r")
                version = tmpfile.read()
                tmpfile.close()
            setattr(self, name, version)
        except:
            setattr(self, name, None)
        finally:
            if dir:
                import shutil
                shutil.rmtree(dir)
                
    def getAvailableTestApps(self):
        if self.tests_dir and os.path.isdir(self.tests_dir):
            files = glob.glob(os.path.join(self.tests_dir, nameprefix + "*"))
            if self.targetos == hostos:
                files = [f for f in files if os.access(f, os.X_OK)]
            return files
        return []
    
    def getLogName(self, app, timestamp):
        app = os.path.basename(app)
        if app.endswith(".exe"):
            app = app[:-4]
        if app.startswith(nameprefix):
            app = app[len(nameprefix):]
        if self.opencv_home_svn:
            if self.cmake_home_svn == self.opencv_home_svn:
                rev = self.cmake_home_svn
            else:
                rev = self.cmake_home_svn + "-" + self.opencv_home_svn
        else:
            rev = None
        if rev:
            rev = rev.replace(":","to") + "_" 
        else:
            rev = ""
        if self.hardware:
            hw = str(self.hardware).replace(" ", "_") + "_"
        else:
            hw = ""
        return "%s_%s_%s_%s%s%s.xml" %(app, self.targetos, self.targetarch, hw, rev, timestamp.strftime("%Y%m%dT%H%M%S"))
        
    def getTest(self, name):
        for t in self.tests:
            if t == name:
                return t
            fname = os.path.basename(t)
            if fname == name:
                return t
            if fname.endswith(".exe"):
                fname = fname[:-4]
            if fname == name:
                return t
            if fname.startswith(nameprefix):
                fname = fname[len(nameprefix):]
            if fname == name:
                return t
        return None
    
    def runAdb(self, *args):
        cmd = [self.adb]
        cmd.extend(args)
        adbprocess = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output = adbprocess.communicate()
        if not output[1]:
            return output[0]
        self.error = output[1]
        print self.error
        return None
    
    def isRunnable(self):
        if not self.has_perf_tests or not self.tests:
            self.error = "Performance tests are not built (at %s)" % self.path
            return False
        if self.targetarch == "x64" and hostmachine == "x86":
            self.error = "Target architecture is incompatible with current platform (at %s)" % self.path
            return False
        if self.targetos == "android":
            if not self.adb or not os.path.isfile(self.adb) or not os.access(self.adb, os.X_OK):
                self.error = "Could not find adb executable (at %s)" % self.path
                return False
            adb_res = self.runAdb("devices")
            if not adb_res:
                self.error = "Could not run adb command: %s (at %s)" % (self.error, self.path)
                return False
            connected_devices = len(re.findall(r"^[^ \t]+[ \t]+device$", adb_res, re.MULTILINE))
            if connected_devices == 0:
                self.error = "No Android device connected (at %s)" % self.path
                return False
            if connected_devices > 1:
                self.error = "Too many (%s) devices are connected. Single device is required. (at %s)" % (connected_devices, self.path)
                return False
            if "armeabi-v7a" in self.arm_target:
                adb_res = self.runAdb("shell", "cat /proc/cpuinfo")
                if not adb_res:
                    self.error = "Could not get info about Android platform: %s (at %s)" % (self.error, self.path)
                    return False
                if "ARMv7" not in adb_res:
                    self.error = "Android device does not support ARMv7 commands, but tests are built for armeabi-v7a (at %s)" % self.path
                    return False
                if "NEON" in self.arm_target and "neon" not in adb_res:
                    self.error = "Android device has no NEON, but tests are built for %s (at %s)" % (self.arm_target, self.path)
                    return False
                hw = re.search(r"^Hardware[ \t]*:[ \t]*(.*?)$", adb_res, re.MULTILINE)
                if hw:
                    self.hardware = hw.groups()[0].strip()
        return True
    
    def runTest(self, path, workingDir, _stdout, _stderr, args = []):
        if self.error:
            return
        args = args[:]
        timestamp = datetime.datetime.now()
        logfile = self.getLogName(path, timestamp)
        
        userlog = [a for a in args if a.startswith("--gtest_output=")]
        if len(userlog) == 0:
            args.append("--gtest_output=xml:" + logfile)
        else:
            logfile = userlog[userlog[0].find(":")+1:]
        
        if self.targetos == "android":
            uname = getpass.getuser()
            print uname
            pass
        else:
            cmd = [os.path.abspath(path)]
            cmd.extend(args)
            print >> _stderr, "Running:", " ".join(cmd) 
            testprocess = Popen(cmd, stdout=_stdout, stderr=_stderr, cwd = workingDir)
            testprocess.communicate()
            
    def runTests(self, tests, _stdout, _stderr, workingDir, args = []):
        if self.error:
            return
        if not tests:
            tests = self.tests
        for test in tests:
            t = self.getTest(test)
            if t:
                self.runTest(t, workingDir, _stdout, _stderr, args)
            else:
                print >> _stderr, "Test \"%s\" is not found in %s" % (test, self.tests_dir)

if __name__ == "__main__":
    test_args = [a for a in sys.argv if a.startswith("--perf_") or a.startswith("--gtest_")]
    argv =      [a for a in sys.argv if not(a.startswith("--perf_") or a.startswith("--gtest_"))]
    
    parser = OptionParser()
    parser.add_option("-t", "--tests", dest="tests", help="comma-separated list of modules to test", metavar="SUITS", default="")
    parser.add_option("-w", "--cwd", dest="cwd", help="working directory for tests", metavar="PATH", default=".")
    (options, args) = parser.parse_args(argv)
    
    run_args = []
    
    for path in args:
        path = os.path.abspath(path)
        while (True):
            if os.path.isdir(path) and os.path.isfile(os.path.join(path, "CMakeCache.txt")):
                run_args.append(path)
                break
            npath = os.path.dirname(path)
            if npath == path:
                break
            path = npath
    
    if len(run_args) == 0:
        print >> sys.stderr, "Usage:\n", os.path.basename(sys.argv[0]), "<build_path>"
        exit(1)
        
    tests = [s.strip() for s in options.tests.split(",") if s]
    for i in range(len(tests)):
        name = tests[i]
        if not name.startswith(nameprefix):
            tests[i] = nameprefix + name
            
    if len(tests) != 1 or len(run_args) != 1:
        #remove --gtest_output from params
        test_args = [a for a in test_args if not a.startswith("--gtest_output=")]
    
    for path in run_args:
        info = RunInfo(path)
        #print vars(info),"\n"
        if not info.isRunnable():
            print >> sys.stderr, "Error:", info.error
        else:
            info.runTests(tests, sys.stdout, sys.stderr, options.cwd, test_args)
