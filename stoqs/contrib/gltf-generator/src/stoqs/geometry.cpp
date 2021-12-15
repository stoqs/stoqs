#include <stoqs/geometry.h>

// standard library
#include <math.h>

#define EARTH_RADIUS_M 6371000.0

namespace stoqs
{
	Geometry::Geometry(const Bathymetry& bathymetry, const Options& options) :
	_vertices(get_vertices(bathymetry, options.exaggeration())),
	_triangles(get_triangles(_vertices))
	{}

	double Geometry::to_radians(double degrees)
	{
		return degrees * (3.1415926535 / 180.0);
	}

	double Geometry::get_longitude(const Bathymetry& bathymetry, size_t x)
	{
		return bathymetry.longitude_min() + bathymetry.longitude_spacing() * (double)x;
	}

	double Geometry::get_latitude(const Bathymetry& bathymetry, size_t y)
	{
		return bathymetry.latitude_min() + bathymetry.latitude_spacing() * (double)y;
	}

	Vertex Geometry::get_earth_centered_vertex(double longitude, double latitude, double altitude, uint32_t id)
	{
		double phi = to_radians(latitude);
		double theta = to_radians(longitude);

		double cos_phi = cos(phi);
		double cos_theta = cos(theta);
		double sin_phi = sin(phi);
		double sin_theta = sin(theta);
		double rho = EARTH_RADIUS_M + altitude;

		// this assumes z is up
		float x = rho * cos_phi * cos_theta;
		float y = rho * cos_phi * sin_theta;
		float z = rho * sin_phi;

		// gltf assumes y is up
		return Vertex(x, z, y, id);
	}

	Matrix<Vertex> Geometry::get_vertices(const Bathymetry& bathymetry, double vertical_exaggeration)
	{
		Matrix<Vertex> out(bathymetry.size_x(), bathymetry.size_y());
		const auto& altitudes = bathymetry.altitudes();
		uint32_t vertex_id = 1;

		for (size_t y = 0; y < altitudes.size_y(); ++y)
		{
			for (size_t x = 0; x < altitudes.size_x(); ++x)
			{
				float altitude = altitudes.at(x, y);

				if (!std::isnan(altitude))
				{
					double longitude = get_longitude(bathymetry, x);
					double latitude = get_latitude(bathymetry, y);
					double adjusted_altitude = (double)altitude * vertical_exaggeration;
					
					out.at(x, y) = get_earth_centered_vertex(longitude, latitude, adjusted_altitude, vertex_id++);
				}
			}
		}

		return out;
	}

	std::vector<Triangle> Geometry::get_triangles(const Matrix<Vertex>& vertices)
	{
		size_t end_y = vertices.size_y() - 1;
		size_t end_x = vertices.size_x() - 1;
		size_t max_triangle_count = 2 * end_x * end_y;

		std::vector<Triangle> out;

		out.reserve(max_triangle_count);
			
		for (size_t y = 0; y < end_y; ++y)
		{
			for (size_t x = 0; x < end_x; ++x)
			{
				const auto& bottom_left = vertices.at(x, y);
				const auto& bottom_right = vertices.at(x + 1, y);
				const auto& top_left = vertices.at(x, y + 1);
				const auto& top_right = vertices.at(x + 1, y + 1);
				
				if (bottom_left.is_valid() && top_right.is_valid())
				{
					if (top_left.is_valid())
						out.emplace_back(Triangle {
							bottom_left.index(),
							top_left.index(),
							top_right.index()
						});
					
					if (bottom_right.is_valid())
						out.emplace_back(Triangle {
							bottom_left.index(),
							top_right.index(),
							bottom_right.index()
						});
				}
				else if (bottom_right.is_valid() && top_left.is_valid())
				{
					if (bottom_left.is_valid())
						out.emplace_back(Triangle {
							bottom_right.index(),
							bottom_left.index(),
							top_left.index()
						});
					
					if (top_right.is_valid())
						out.emplace_back(Triangle {
							bottom_right.index(),
							top_left.index(),
							top_right.index()
						});
				}
			}
		}

		return out;
	}
}
