import os
import sys

def we_are_frozen():
    return hasattr(sys, "frozen")

def module_path():
    encoding = sys.getfilesystemencoding()
    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable, encoding))
    else:
        return os.path.abspath(os.path.dirname(__file__))
    
if __name__ == '__main__':
    print module_path()
