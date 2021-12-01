import struct
import operator
from gltflib import (
    GLTF, GLTFModel, Asset, Scene, Node, Mesh, Primitive, Attributes, Buffer, BufferView, Accessor, AccessorType,
    BufferTarget, ComponentType, GLBResource, FileResource)

vertices = [
    (-0.5, 0, -0.5),
    (-0.5, 0, 0.5),
    (0.5, 0, -0.5),
    (0.5, 0, -0.5),
    (0.5, 0, 0.5),
    (-0.5, 0, 0.5),
    (-0.5, 1, -0.5),
    (-0.5, 1, 0.5),
    (0.5, 1, -0.5),
    (0.5, 1, -0.5),
    (0.5, 1, 0.5),
    (-0.5, 1, 0.5),
    (0.5, 0, -0.5),
    (0.5, 1, -0.5),
    (0.5, 0, 0.5),
    (0.5, 0, 0.5),
    (0.5, 1, 0.5),
    (0.5, 1, -0.5),
    (-0.5, 0, -0.5),
    (-0.5, 1, -0.5),
    (-0.5, 0, 0.5),
    (-0.5, 0, 0.5),
    (-0.5, 1, 0.5),
    (-0.5, 1, -0.5),
    (-0.5, 0, -0.5),
    (-0.5, 1, -0.5),
    (0.5, 1, -0.5),
    (-0.5, 0, -0.5),
    (0.5, 0, -0.5),
    (0.5, 1, -0.5),
    (-0.5, 0, 0.5),
    (-0.5, 1, 0.5),
    (0.5, 1, 0.5),
    (-0.5, 0, 0.5),
    (0.5, 0, 0.5),
    (0.5, 1, 0.5)
]

vertex_bytearray = bytearray()
for vertex in vertices:
    for value in vertex:
        vertex_bytearray.extend(struct.pack('f', value))
bytelen = len(vertex_bytearray)
mins = [min([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]
maxs = [max([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]
model = GLTFModel(
    asset=Asset(version='2.0'),
    scenes=[Scene(nodes=[0])],
    nodes=[Node(mesh=0)],
    meshes=[Mesh(primitives=[Primitive(attributes=Attributes(POSITION=0))])],
    buffers=[Buffer(byteLength=bytelen, uri='vertices.bin')],
    bufferViews=[BufferView(buffer=0, byteOffset=0, byteLength=bytelen, target=BufferTarget.ARRAY_BUFFER.value)],
    accessors=[Accessor(bufferView=0, byteOffset=0, componentType=ComponentType.FLOAT.value, count=len(vertices),
                        type=AccessorType.VEC3.value, min=mins, max=maxs)]
)

resource = FileResource('vertices.bin', data=vertex_bytearray)
gltf = GLTF(model=model, resources=[resource])
gltf.export('square.gltf')
