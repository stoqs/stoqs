import sys
import math
import numpy as np
from netCDF4 import Dataset

def convert_to_xyz(filename):
	print("Reading data")
	dataset = None

	with open(filename, "rb") as file:
		data = file.read()
		dataset = Dataset(filename, mode="r", memory=data)

	if not dataset:
		raise ValueError("Failed to read dataset file")

	print(dataset)

	x_size = dataset.variables["dimension"][0]
	y_size = dataset.variables["dimension"][1]
	z_values = dataset.variables["z"]

	print("allocating array")
	points = np.empty(z_values.shape[0], dtype=object)

	print("[0]:", points[0])
	points_index = 0

	print("Reading data")
	for x in range(x_size):
		print("{} / {}".format(x + 1, x_size))
		for y in range(y_size):
			z_index = x + y * x_size
			z = z_values[z_index].data

			if not math.isnan(z):
				points[points_index] = (x, y, z)
				points_index += 1

	return points, points_index

if __name__ == "__main__":
	filename = "./bathymetry.grd"
	points, size = convert_to_xyz(filename)
	print(points)
