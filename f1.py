import sys
from geopy.distance import geodesic

cities = [
    # 0 latitude, 1 longitude, 2 continent, 3 name, 4 harbour
    # Oceania
    (-37.6733, 144.8433, "Oceania", "Melbourne", "no"),

    # Asia
    (1.2914, 103.8640, "Asia", "Singapore", "harbour"),
    (26.0325, 50.5100, "Asia", "Sakhir", "harbour"),
    (21.4225, 39.8262, "Asia", "Jeddah", "no"),
    (34.8431, 136.5419, "Asia", "Suzuka", "no"),
    (31.2001, 121.6057, "Asia", "Shanghai", "harbour"),
    (25.3436, 51.4367, "Asia", "Lusail", "harbour"),
    (24.4672, 54.6031, "Asia", "Yas Marina", "harbour"),
    (40.3723, 49.8532, "Asia", "Baku", "harbour"),

    # Europe
    (44.3439, 11.7167, "Europe", "Imola", "no"),
    (43.7333, 7.4167, "Europe", "Monaco", "harbour"),
    (41.5704, 2.2590, "Europe", "Barcelona", "harbour"),
    (47.2197, 14.7647, "Europe", "Spielberg", "no"),
    (51.0379, -1.7812, "Europe", "Silverstone", "no"),
    (47.5831, 19.2525, "Europe", "Budapest", "no"),
    (50.4372, 5.9714, "Europe", "Spa", "no"),
    (52.3842, 4.5456, "Europe", "Zandvoort", "harbour"),
    (45.6156, 9.2811, "Europe", "Monza", "no"),

    # North America
    (25.7617, -80.1918, "North America", "Miami", "harbour"),
    (30.1380, -97.6357, "North America", "Austin", "no"),
    (19.4042, -99.0907, "North America", "Mexico City", "no"),
    (45.4572, -73.7516, "North America", "Montreal", "no"),
    (36.1699, -115.1398, "North America", "Las Vegas", "no"),

    # South America
    (-23.5505, -46.6333, "South America", "Sao-Paolo", "no"),
]


def getTime(distance, mode):
    if mode == "Truck":
        time = distance / 60
    elif mode == "Train":
        time = distance / 70
    elif mode == "Ship":
        time = distance / 20
    elif mode == "Plane":
        time = distance / 930
    else:
        raise Exception(f"getTime: invalid mode {mode}")
    return time


def getEffectiveTime(time):
    # less than 3 days => 1 week (3 days transit + 4 days event)
    # more than 3 days && less than 10 days => 2 weeks (10 days transit + 4 days event)
    # more than 10 days && less than 17 => 3 weeks (17 days transit + 4 days event)
    # more than 17 days && less than 24 => 4 weeks (24 days transit + 4 days event)
    # and so on
    time_incl_event = time + (4 * 24)
    weeks = time_incl_event // (7 * 24) + 1
    return weeks * 7 * 24


def getEmission(distance, mode):
    if mode == "Truck":
        emission = distance * 0.105
    elif mode == "Train":
        emission = distance * 0.065
    elif mode == "Ship":
        emission = distance * 0.025
    elif mode == "Plane":
        emission = distance * 0.5
    else:
        raise Exception("getEmission: invalid mode ${mode}")
    return emission


class Edge:
    def __init__(self, start, end, distance, mode, emission, time, time_in_transport):
        self.start = start  # end city Node
        self.end = end  # end city Node
        self.distance = distance
        self.mode = mode  # "Ship", "Train", "Truck", "Plane"
        self.emission = emission
        self.time = time
        self.time_in_transport = time_in_transport

    def __str__(self) -> str:
        return f"{self.end.name} {self.distance} {self.mode} {self.emission} {self.time} {self.time_in_transport}"


class Node:
    def __init__(self, name, continent, harbour):
        self.name = name
        self.continent = continent
        self.harbour = harbour
        self.edges = []

    def add_edge(self, end, distance, mode, emission, time, time_in_transport):
        self.edges.append(
            Edge(self, end, distance, mode, emission, time, time_in_transport))


class CalculatedRoute:
    def __init__(self, best_route, edges, emission, duration, distance, time_in_transport) -> None:
        self.best_route = best_route
        self.edges = edges
        self.emission = emission
        self.duration = duration
        self.distance = distance
        self.time_in_transport = time_in_transport

# air connection always available
# ship connections available if both have harbor
# train connections available if both are in the same continent (ie. for simplification Europe<->Asia is not connected by train)


print("============ Initiate nodes (cities) ==============")

max_time_in_transit = 180 * 24  # year in hours
continents_to_cities = {}
all_cities = {}

# Create nodes
for city in cities:
    continent = city[2]
    city_name = city[3]
    harbour = city[4]
    if continent not in continents_to_cities:
        continents_to_cities[continent] = {}
    city_node = Node(city_name, continent, harbour)
    continents_to_cities[continent][city_name] = city_node
    all_cities[city_name] = city_node

print("============ Initiate edges (city connections) ==============")

# add edges
for from_city in cities:
    for to_city in cities:
        from_city_name = from_city[3]
        to_city_name = to_city[3]
        if from_city_name != to_city_name:
            from_city_gps = (from_city[0], from_city[1])
            to_city_gps = (to_city[0], to_city[1])
            distance = geodesic(from_city_gps, to_city_gps).kilometers
            # for mode in ["Plane", "Train", "Truck",  "Ship"]:
            # NOTE: removed Truck mode, because Train has got the same connectivity, higher speed and lower emissions
            for mode in ["Plane", "Train", "Ship"]:
                from_city_harbour = from_city[4]
                to_city_harbour = to_city[4]
                if mode == "Ship" and (from_city_harbour == "no" or to_city_harbour == "no"):
                    # one of the cities does not have a harbour
                    continue
                from_city_continent = from_city[2]
                to_city_continent = to_city[2]
                if (mode == "Train" or mode == "Truck") and from_city_continent != to_city_continent:
                    # cities are not in the same continent
                    # NOTE: maybe allow Europe<->Asia for train and truck ?
                    continue
                emission = getEmission(distance, mode)
                time_in_transport = getTime(distance, mode)
                time = getEffectiveTime(time_in_transport)
                all_cities[from_city_name].add_edge(
                    all_cities[to_city_name], distance, mode, emission, time, time_in_transport)

print("============ Print nodes and edges ==============")

# print all nodes and their edges
for node in all_cities:
    value = all_cities[node]
    print(node, value.continent, value.harbour)
    for edge in value.edges:
        print("  =>", edge.start.name, "->", edge.end.name,
              edge.mode, edge.distance, edge.emission, edge.time, edge.time_in_transport)

continents_from_to = {}

print("============ Pre-calculate continents ==============")


def calculate_lowest_emission(continent, cities_names, route, edges, duration, emission, distance, time_in_transport, in_edge):
    global continents_from_to
    if duration > max_time_in_transit:
        # optimization: limit how much time we spend in one
        return
    if len(route) > 1 and continents_from_to[continent][route[0]][route[-1]].emission < emission:
        return
    if len(cities_names) == 1:
        if continents_from_to[continent][route[0]][cities_names[0]].emission > emission:
            continents_from_to[continent][route[0]][cities_names[0]] = CalculatedRoute(
                route + [in_edge.end.name], edges + [in_edge], emission +
                in_edge.emission, duration + in_edge.time,
                distance + in_edge.distance, time_in_transport + in_edge.time_in_transport)
        return
    for ix, city_name in enumerate(cities_names):
        remaining = cities_names.copy()
        remaining.pop(ix)
        select_edges = [
            item for item in all_cities[city_name].edges if item.end.continent == continent and (in_edge is None or in_edge.end.name == city_name)]
        for edge in select_edges:
            if edge.mode != "Plane" and edge.end.name not in route:
                if in_edge is None:
                    calculate_lowest_emission(continent, remaining, route + [city_name], edges,
                                              duration, emission,
                                              distance, time_in_transport, edge)
                else:
                    calculate_lowest_emission(continent, remaining, route + [city_name], edges + [in_edge], duration + in_edge.time,
                                              emission + in_edge.emission, distance + in_edge.distance, time_in_transport + in_edge.time_in_transport, edge)


def calculate_lowest_emission_start(continent):
    calculate_lowest_emission(
        continent, list(continents_to_cities[continent].keys()), [], [], 0, 0, 0, 0, None)


# pre-calculate continents
for continent in continents_to_cities:
    cities = continents_to_cities[continent]
    continents_from_to[continent] = {}
    for start in cities:
        continents_from_to[continent][start] = {}
        if (len(cities) == 1):
            continents_from_to[continent][start][start] = CalculatedRoute(
                [], [], 0, 0, 0, 0)
        else:
            for end in cities:
                if start != end:
                    continents_from_to[continent][start][end] = CalculatedRoute(
                        [], [], sys.maxsize, 0, 0, 0)
    if (len(cities) > 1):
        print("pre-calculate continents", continent, cities)
        calculate_lowest_emission_start(continent)

print("============ Print pre-calculated continents ==============")

# print pre-calculated continents
for continent in continents_from_to:
    for start in continents_from_to[continent]:
        for end in continents_from_to[continent][start]:
            print(continent, start, end, continents_from_to[continent][start][end].best_route,
                  continents_from_to[continent][start][end].distance,
                  continents_from_to[continent][start][end].emission, continents_from_to[continent][start][end].duration,
                  continents_from_to[continent][start][end].time_in_transport)
            for edge in continents_from_to[continent][start][end].edges:
                print("  =>", edge.start.name, "->", edge.end.name,
                      edge.mode, edge.distance, edge.emission,
                      edge.time, edge.time_in_transport)

print("============ calculate whole trip ==============")

final_route = []
final_emission = sys.maxsize
final_duration = 0
final_edges = []
final_distance = 0
final_time_in_transport = 0


def whole_trip(from_continent, from_city, visited_continent, route, emission, duration, edges, distance, time_in_transport):
    global final_route
    global final_emission
    global final_duration
    global final_edges
    global final_distance
    global final_time_in_transport
    for end_city in continents_to_cities[from_continent]:
        if len(continents_to_cities[from_continent]) == 1 or from_city != end_city:
            if len(visited_continent) == len(continents_to_cities):
                emission2 = emission + \
                    continents_from_to[from_continent][from_city][end_city].emission
                duration2 = duration + \
                    continents_from_to[from_continent][from_city][end_city].duration
                route2 = route + ["CONTINENT:", from_city, end_city]
                edges2 = edges + \
                    continents_from_to[from_continent][from_city][end_city].edges
                distance2 = distance + \
                    continents_from_to[from_continent][from_city][end_city].distance
                time_in_transport2 = time_in_transport + \
                    continents_from_to[from_continent][from_city][end_city].time_in_transport
                if emission < final_emission:
                    final_emission = emission2
                    final_route = route2
                    final_duration = duration2
                    final_edges = edges2
                    final_distance = distance2
                    final_time_in_transport = time_in_transport2
                    print("New best route found", final_route,
                          final_emission, final_duration, final_time_in_transport)
            else:
                for edge in continents_to_cities[from_continent][end_city].edges:
                    if edge.end.continent not in visited_continent:
                        emission3 = emission + \
                            continents_from_to[from_continent][from_city][end_city].emission
                        duration3 = duration + \
                            continents_from_to[from_continent][from_city][end_city].duration
                        route3 = route + ["CONTINENT:", from_city, end_city]
                        edges3 = edges + \
                            continents_from_to[from_continent][from_city][end_city].edges
                        distance3 = distance + \
                            continents_from_to[from_continent][from_city][end_city].distance
                        time_in_transport3 = time_in_transport + \
                            continents_from_to[from_continent][from_city][end_city].time_in_transport
                        whole_trip(edge.end.continent, edge.end.name, visited_continent + [edge.end.continent], route3 + [
                            "BETWEEN:", end_city, edge.end.name], emission3 + edge.emission, duration3 + edge.time, edges3 + [edge], distance3 + edge.distance, time_in_transport3 + edge.time_in_transport)


whole_trip("Oceania", "Melbourne", ["Oceania"], [], 0, 0, [], 0, 0)

print("============ Result ==============")

total_emission = 0
total_time_in_transport = 0
total_duration = 0
total_distance = 0

print(
    f"Final best route found. Emission:{final_emission} duration:{final_duration} hours time_in_transport:{final_time_in_transport} hours distance:{final_distance} km")
print("Route: city, distance, mode, emission, time")
print("  => city:Melbourne")
for edge in final_edges:
    print(f"  => city:{edge.start.name}->{edge.end.name}, distance:{edge.distance}km by {edge.mode} emissions:{edge.emission} duration:{edge.time} hours time_in_transport:{edge.time_in_transport} hours")
    total_emission += edge.emission
    total_time_in_transport += edge.time_in_transport
    total_duration += edge.time
    total_distance += edge.distance

print(
    f"[CHECK] Total: Emission:{total_emission} duration:{total_duration} hours time_in_transport:{total_time_in_transport} hours distance:{total_distance} km")