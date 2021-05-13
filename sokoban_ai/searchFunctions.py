from collections import deque

def bfs(start, end, map, boxes):
	"""
	Function that does the Breadth first search
	@params start,end : represent both starting and ending position to do this search
	@param map : map object that representes the current state
	@param boxes: a set with the position of the boxes
	Returns a string with the path, if it was possible to reach the "end" position or else None
	if that's not possible
	"""
	hor_tiles, ver_tiles = map.size
	vis = [[0] * hor_tiles for _ in range(ver_tiles)]
	queue = deque([])
	queue.append((start[0], start[1], ""))

	while queue:
		x, y, path = queue.popleft()
		
		if vis[y][x] or map._map[y][x] & 0b1000 or (x,y) in boxes:
			continue

		vis[y][x] = 1

		if (x, y) == end:
			return path

		if 0 < y - 1 < ver_tiles:
			queue.append((x, y - 1, path + "w"))
		if 0 < x - 1 < hor_tiles:
			queue.append((x - 1, y, path + "a"))
		if 0 < y + 1 < ver_tiles:
			queue.append((x, y + 1, path + "s"))
		if 0 < x + 1 < hor_tiles:
			queue.append((x + 1, y, path + "d"))

	return None


def initial_reachable_area(start, map):
	"""
	@param start: the starting position
	@param map: map object that representes the current state
	Returns a bi-dimensional array with the visited positions of the INITIAL State,
	we only take into account if there's a wall. If the position is visited, then it's marked with  a 1.
	"""
	hor_tiles, ver_tiles = map.size
	vis = [[0] * hor_tiles for _ in range(ver_tiles)]
	queue = deque([])
	queue.append((start[0], start[1]))

	while queue:
		x, y = queue.popleft()

		if vis[y][x] or map._map[y][x] & 0b1000:
			continue

		vis[y][x] = 1

		if 0 < y - 1 < ver_tiles:
			queue.append((x, y - 1))
		if 0 < x - 1 < hor_tiles:
			queue.append((x - 1, y))
		if 0 < y + 1 < ver_tiles:
			queue.append((x, y + 1))
		if 0 < x + 1 < hor_tiles:
			queue.append((x + 1, y))

	return vis

def reachable_positions(start, map, boxes):
	"""
	@param start: the starting position
	@param map: map object that representes the current state
	Returns a bi-dimensional array with the visited positions of the CURRENT State,
	we take into account not only  if there's a wall but also the boxes. Marks with a 1 a visited position
	"""
	hor_tiles, ver_tiles = map.size
	vis = [[0] * hor_tiles for _ in range(ver_tiles)]
	queue = deque([])
	queue.append((start[0], start[1]))

	while queue:
		x, y = queue.popleft()
		
		if vis[y][x] or map._map[y][x] & 0b1000 or (x,y) in boxes:
			continue

		vis[y][x] = 1

		if 0 < y - 1 < ver_tiles:
			queue.append((x, y - 1))
		if 0 < x - 1 < hor_tiles:
			queue.append((x - 1, y))
		if 0 < y + 1 < ver_tiles:
			queue.append((x, y + 1))
		if 0 < x + 1 < hor_tiles:
			queue.append((x + 1, y))

	return vis


def manhattan(p1, p2):
	"""
	@param p1 : a tuple with the coords of a position 
	@param p2 : another tuple with the coords of another position
	Return manhattan distance between 2 points.
	"""
	return abs( p1[0] - p2[0]) + abs(p1[1] - p2[1] )

def euclidian(p1,p2):
	"""
	@param p1 : a tuple with the coords of a position 
	@param p2 : another tuple with the coords of another position
	Return euclidian distance between 2 points.
	"""
	return hypot( p1[0] - p2[0], p1[1] - p2[1] )

def greedy_heur(node, storages):
	"""
	@param node : an object of the Node class
	@param storages: a set with the coords of the goal positions
	"""
	heur = 0
	assigned_boxes = set()
	for storage in storages:
		min_box, minimum = 0, 1000
		for box in node.boxes:
			if box not in assigned_boxes:
				cost = manhattan(box, storage)
				if  cost < minimum:
					min_box, minimum = box, cost
		assigned_boxes.add(min_box)
		heur += minimum

	return heur