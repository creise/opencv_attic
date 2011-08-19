import sys, re, os.path
from xml.dom.minidom import parse

class TestInfo(object):

    def __init__(self, xmlnode):
        self.fixture = xmlnode.getAttribute("classname")
        self.name = xmlnode.getAttribute("name")
        self.value_param = xmlnode.getAttribute("value_param")
        self.type_param = xmlnode.getAttribute("type_param")
        self.name = xmlnode.getAttribute("name")
        if xmlnode.getElementsByTagName("failure"):
            self.status = "failed"
        else:
            self.status = xmlnode.getAttribute("status")
        if self.name.startswith("DISABLED_"):
            self.status = "disabled"
            self.fixture = self.fixture.replace("DISABLED_", "")
            self.name = self.name.replace("DISABLED_", "")

    def dump(self):
        print "%s -> %s" % (str(self), self.status)

    def __str__(self):
        return '::'.join(filter(None, [self.fixture, self.type_param, self.value_param]))

    def __cmp__(self, other):
        r = cmp(self.fixture, other.fixture);
        if r != 0:
            return r
        if self.type_param:
            if other.type_param:
                r = cmp(self.type_param, other.type_param);
                if r != 0:
                     return r
            else:
                return -1
        else:
            if other.type_param:
                return 1
        if self.value_param:
            if other.value_param:
                r = cmp(self.value_param, other.value_param);
                if r != 0:
                     return r
            else:
                return -1
        else:
            if other.value_param:
                return 1
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage:\n", os.path.basename(sys.argv[0]), "<log_name>.xml"
        exit(0)

    tests = []

    log = parse(sys.argv[1])
    for case in log.getElementsByTagName("testcase"):
        tests.append(TestInfo(case))

    for t in sorted(tests):
        t.dump()