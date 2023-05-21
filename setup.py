from setuptools import find_packages, setup

setup(
    name='pywebpass',
    version='1.3.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'pykeepass',
        'requests',
        'systemd-logging',
    ],
    entry_points={
        'console_scripts': ['webpass-client=pywebpass.client.command:main'],
    },
 )
