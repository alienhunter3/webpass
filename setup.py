from setuptools import find_packages, setup

setup(
    name='pywebpass',
    version='1.0.2',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'pykeepass',
        'requests',
        'systemd-logging',
        'wsgi',
    ],
)
