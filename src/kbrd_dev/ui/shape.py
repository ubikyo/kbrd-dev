from math import hypot


def rounded_polygon(points, radius, segments=4):
    rounded = []
    count = len(points)

    for index, current in enumerate(points):
        previous = points[index - 1]
        following = points[(index + 1) % count]
        previous_length = hypot(
            previous[0] - current[0],
            previous[1] - current[1],
        )
        following_length = hypot(
            following[0] - current[0],
            following[1] - current[1],
        )
        distance = min(radius, previous_length / 2, following_length / 2)
        start = (
            current[0] + (previous[0] - current[0]) * distance / previous_length,
            current[1] + (previous[1] - current[1]) * distance / previous_length,
        )
        end = (
            current[0] + (following[0] - current[0]) * distance / following_length,
            current[1] + (following[1] - current[1]) * distance / following_length,
        )

        for step in range(segments + 1):
            position = step / segments
            inverse = 1 - position
            rounded.append((
                inverse * inverse * start[0]
                + 2 * inverse * position * current[0]
                + position * position * end[0],
                inverse * inverse * start[1]
                + 2 * inverse * position * current[1]
                + position * position * end[1],
            ))

    return rounded


def triangulate(points):
    remaining = list(range(len(points)))
    triangles = []
    orientation = 1 if _area(points) > 0 else -1

    while len(remaining) > 3:
        for position, current in enumerate(remaining):
            previous = remaining[position - 1]
            following = remaining[(position + 1) % len(remaining)]
            if orientation * _cross(
                points[previous],
                points[current],
                points[following],
            ) <= 1e-9:
                continue
            if any(
                _inside_triangle(
                    points[candidate],
                    points[previous],
                    points[current],
                    points[following],
                )
                for candidate in remaining
                if candidate not in (previous, current, following)
            ):
                continue

            triangles.extend((previous, current, following))
            del remaining[position]
            break
        else:
            raise ValueError("unable to triangulate polygon")

    triangles.extend(remaining)
    return triangles


def _area(points):
    return sum(
        x * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * y
        for index, (x, y) in enumerate(points)
    ) / 2


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _inside_triangle(point, a, b, c):
    crosses = (
        _cross(a, b, point),
        _cross(b, c, point),
        _cross(c, a, point),
    )
    return not (any(value < -1e-9 for value in crosses) and any(
        value > 1e-9 for value in crosses
    ))
