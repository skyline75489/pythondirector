
from distutils.core import setup

setup(
    name = "pydirector", 
    version = "0.0.2",
    description = "Python Director TCP load balancer.",
    author = "Anthony Baxter",
    author_email = "anthony@interlink.com.au",
    url = 'http://sourceforge.net/projects/pythondirector/',
    packages = ['pydirector'],
    scripts = ['pydir.py'],
)

