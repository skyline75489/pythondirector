
from distutils.core import setup

from pydirector import Version

setup(
    name = "pydirector", 
    version = Version, 
    description = "Python Director - TCP load balancer.",
    author = "Anthony Baxter",
    author_email = "anthony@interlink.com.au",
    url = 'http://sourceforge.net/projects/pythondirector/',
    packages = ['pydirector'],
    scripts = ['pydir.py'],
)

