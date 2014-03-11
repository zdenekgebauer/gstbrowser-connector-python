from distutils.core import setup

setup(
    name='filebrowser-connector-python',
    version='0.01',
    packages=['connector', 'gstbrowser'],
    url='https://github.com/zdenekgebauer/gstbrowser-connector-python',
    license='WTFPL',
    author='Zdenek Gebauer',
    author_email='zdenek.gebauer@gmail.com',
    description='server connector for gstbrowser'
    long_description=read('README.rst'),
    platforms=['OS Independent'],
    packages=[
        'gstbrowser',
        'connector',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
    ],
)
