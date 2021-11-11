#!/usr/bin/env python
'''
Validate conversion between quaternions and euler angles.

Usage: testEuler.py rxyz 10

See: http://matthew-brett.github.io/transforms3d/reference/transforms3d.euler.html
'''

import sys
import numpy as np
from euclid import Quaternion, Vector3
from transforms3d.euler import quat2euler, euler2quat
from transforms3d.taitbryan import quat2euler as tb_quat2euler
from transforms3d.taitbryan import euler2quat as tb_euler2quat

try:
    axes_order = sys.argv[1] or 'szxy'
except IndexError:
    axes_order = 'szxy'

try:
    n_angles = sys.argv[2] or 5
except IndexError:
    n_angles = 5

# Define quaternion rotations about X, Y, and Z axes
qxs = [ Quaternion.new_rotate_axis(a, Vector3(1, 0, 0)) for a in np.linspace(0, np.pi, n_angles) ]
qys = [ Quaternion.new_rotate_axis(a, Vector3(0, 1, 0)) for a in np.linspace(0, np.pi, n_angles) ]
qzs = [ Quaternion.new_rotate_axis(a, Vector3(0, 0, 1)) for a in np.linspace(0, np.pi, n_angles) ]


print("Successive rotations about X, Y, and Z axes as converted to Euler angles using Quaternion.get_euler() [same as axes='szxy']")
print('X: {}').format([ q.get_euler() for q in qxs ])
print('Y: {}').format([ q.get_euler() for q in qys ])
print('Z: {}').format([ q.get_euler() for q in qzs ])

print("Successive rotations about X, Y, and Z axes as converted to Euler angles using quat2euler(), axes='{}'").format(axes_order)
print('X: {}').format([ quat2euler((q.w, q.x, q.y, q.z), axes=axes_order)  for q in qxs ])
print('Y: {}').format([ quat2euler((q.w, q.x, q.y, q.z), axes=axes_order)  for q in qys ])
print('Z: {}').format([ quat2euler((q.w, q.x, q.y, q.z), axes=axes_order)  for q in qzs ])

print("Successive rotations about X, Y, and Z axes as converted to Euler angles using tb_quat2euler(), [same as axes='szyx'")
print('X: {}').format([ tb_quat2euler((q.w, q.x, q.y, q.z))  for q in qxs ])
print('Y: {}').format([ tb_quat2euler((q.w, q.x, q.y, q.z))  for q in qys ])
print('Z: {}').format([ tb_quat2euler((q.w, q.x, q.y, q.z))  for q in qzs ])

print('\nGenerating quaterion rotations using euler2quat()...')
qtxs = [ euler2quat(a, 0, 0, axes=axes_order) for a in np.linspace(0, np.pi, n_angles) ]
qtys = [ euler2quat(0, a, 0, axes=axes_order) for a in np.linspace(0, np.pi, n_angles) ]
qtzs = [ euler2quat(0, 0, a, axes=axes_order) for a in np.linspace(0, np.pi, n_angles) ]

print("Successive rotations about X, Y, and Z axes as converted to Euler angles using quat2euler(), [same as axes='sxyz'").format(axes_order)
print('X: {}').format([ quat2euler(q, axes=axes_order)  for q in qtxs ])
print('Y: {}').format([ quat2euler(q, axes=axes_order)  for q in qtys ])
print('Z: {}').format([ quat2euler(q, axes=axes_order)  for q in qtzs ])

print("\nIt seems that there is a 'gimbol lock' problem where instead of '0.0's we are getting +/- 3.141592 values.")
