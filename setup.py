
from distutils.core import setup

with open('VERSION') as f:
    version = f.read().rstrip('\n')

setup (name='vamos',
       version=version,
       package_dir={'vamos': 'python/vamos'},
       packages=['vamos',
                 'vamos.rsf2model',
                 'vamos.golem',
                 'vamos.vampyr',
                 'vamos.busyfix'
                 ],
       scripts=['python/golem',
                'python/rsf2model',
                'python/undertaker-kconfigpp',
                'python/vampyr',
                'python/busyfix',
                ],
       )

setup (name='kbuildparse',
       version=version,
       package_dir={'kbuildparse': 'python/kbuildparse'},
       packages=['kbuildparse',
                 'kbuildparse.linux',
                 'kbuildparse.coreboot',
                 'kbuildparse.busybox',
                 ],
       scripts=['python/minigolem',
                ],
       )
