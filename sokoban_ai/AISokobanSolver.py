from searchFunctions import *
import asyncio
import bisect
from mapa import Tiles
from mapa import Map
from copy import deepcopy

class SearchNode:
    def __init__(self, pos, parent=None, directions=(0,0), path="", strategy='bfs'):
        #position of the box that is going to be pushed
        self.pos = pos
        #direction of the box push
        self.directions = directions
        #parent state
        self.parent = parent
        self.heuristic = 0
        self.cost=0
        self.depth = 0
        self.final_path = ""
        self.strategy = strategy
        
        if parent is not None:
            self.depth = self.parent.depth + 1
            self.path = path
            self.cost=len(path) + self.parent.cost
            self.final_path = f'{self.parent.final_path}{self.path}'
            self.cost = self.parent.cost + len(path)
            #list of parent boxes without the box being pushed
            lst_boxes={box for box in self.parent.boxes if box != self.pos}
            #adding the new position of the pushed box
            lst_boxes.add((pos[0] + directions[0], pos[1] + directions[1]))
            self.boxes = lst_boxes
        else:
            self.depth = 0
            self.cost = 0
            self.final_path = ""
            self.heuristic = 0 

    def setHeuristic(self, storages):
        self.heuristic = greedy_heur(self, storages)

    def __str__(self):
        return  "(" + str(self.pos) + ", " + str(self.directions) + ")"

    def __lt__(self, other):
        if self.strategy == 'bfs':
            return self.depth  <  other.depth
        elif self.strategy == 'a*':
            return self.heuristic*2 + self.depth + self.cost < other.heuristic*2 + other.depth + other.cost
        elif self.strategy == 'greedy':
            return self.heuristic*2 + self.depth/3 < other.heuristic*2 + other.depth/3



class TreeSearch:
    def __init__(self, mapa, level):
        self.level = level
        #initial strategy to solving levels
        self.strategy = 'bfs'
        self.change_strategy = True
        
        self.map = mapa
        self.hor_tiles, self.ver_tiles = self.map.size
        self.storages = set(mapa.filter_tiles([Tiles.GOAL, Tiles.MAN_ON_GOAL, Tiles.BOX_ON_GOAL]))
        self.storages_hash = hash(frozenset(self.storages))
        
        self.root = SearchNode(mapa.keeper)
        self.root.boxes = mapa.boxes
        #deque of nodes to explore with the root
        self.open_nodes = deque([])
        self.open_nodes.append(self.root)

        #matrix of deadsquares
        self.deadsquares = self.simple_deadlock()
        #matrix of all reachable positions by the keeper without taking in consideration the boxes
        self.reachable_area = initial_reachable_area(self.root.pos, mapa)
        # #dictionary with storage as a key and a matrix with all the distances to this storage
        # self.heuristic_stor = calc_pos_heuristic(self.storages, self.map, self.deadsquares)
        #backtrack that stores hashes of boxes and a list of the keepers' positions
        self.backtrack_pos = {hash(frozenset(self.root.boxes)): [self.root.pos]}
        self.non_terminals = 0

    def completed(self, hash_boxes):
        """
        @param hash_boxes: a hash of the set of the boxes current positions
        Returns a boolean value, if the hash of the storages equals  the hash passed as parameter then the map is completed
        """
        return self.storages_hash == hash_boxes

    #to retrieve all deadsquares we need to check whether a simple deadlock may occur or not
    def simple_deadlock(self):
        """
        Function that fills an bidimensional array with 1's if the player can reach a position
        or leave it at value 0 if it is a simple deadlock
        """
        def recursive(cur):
            """
            We start this minimal Breadth first search on the coordinates of each storage.
            If a position is blocked vertically and horizontally by a Wall(Identified by 0b1000), then that any push of a box
            to that position results in a Simple Deadlock. Since any wall is Identified by the constant value "8" , doing the AND 
            bitwise operation can check if the position is a Wall : 1*2³ + 0*2² + ...
            """
            x, y = cur
            #avoid going to the same position more than once
            if vis_geral[y][x] or self.map.get_tile(cur) & 0b1000:
                return

            vis_geral[y][x] = 1

            if 0 < y + 2 < ver_tiles and not (map.get_tile((x, y + 2)) & 0b1000):
                recursive((x, y + 1))
            if 0 < x + 2 < hor_tiles and not (map.get_tile((x + 2, y)) & 0b1000):
                recursive((x + 1, y))
            if 0 < y - 2 < ver_tiles and not (map.get_tile((x, y - 2)) & 0b1000):
                recursive((x, y - 1))
            if 0 < x - 2 < hor_tiles and not (map.get_tile((x - 2, y)) & 0b1000):
                recursive((x - 1, y))
            return

        map = self.map
        hor_tiles = self.hor_tiles
        ver_tiles = self.ver_tiles
        #Initialization of the bidimensional array
        vis_geral = [[0] * hor_tiles for _ in range(ver_tiles)]

        for storage in self.storages:
            recursive(storage)

        return vis_geral


    def check_backtrack(self, node, key):
        """
        @param node: a node object of the class Node
        @param key: a hash of the boxes positions 
        Check if the next push was already visited, we keep a dictionary with the states we've already been
        as a key, the value is a list of the keepers' positions.
        Returns a boolean value, False if we already been throug this State, or True in the other scenario
        """
        keeper = node.pos
        backtrack_pos = self.backtrack_pos

        if key in backtrack_pos:
            if any(bfs(keeper, (dx, dy), self.map, node.boxes) is not None for dx, dy in backtrack_pos[key]):
                return False
            backtrack_pos[key].append(keeper)
        else:
            backtrack_pos[key] = deque([keeper])
        return True


    async def search(self):
        """
        Main search function where it is popped one node of the open nodes queue.
        According to the current number of non-terminal nodes and terminal nodes, we may change
        the heuristic-based strategy that we will be using to "order" the nodes in this queue
        """
        started_astar = False
        while self.open_nodes != []:
            await asyncio.sleep(0)
            node = self.open_nodes.popleft()
            self.non_terminals += 1
            if self.change_strategy:
                if not started_astar:
                    if 7000 <= self.non_terminals <= 12000:
                        self.strategy = "a*"
                        started_astar = True
                elif 12000 < self.non_terminals:
                    self.strategy = "greedy"
                    self.change_strategy=False

            poss_pushes, completed = self.get_pushes(node)
            
            if not completed:
                #it the current state has not every box in a goal then we will expand the remaining nodes in the queue
                self.add_to_open(poss_pushes, self.open_nodes)
            else:
                #we get the final_path to achieve the solution of the level stored as an attribute of the Node
                node = poss_pushes.pop(0)
                print(self.level)
                print(node.final_path)
                print("steps",len(node.final_path))
                print("depth",node.depth)
                print("non_terminals", self.non_terminals)
                return node.final_path

    def get_pushes(self, node):
        '''
        Calculates the pushes that can be added to the list of open nodes.
        In order to do that, iterate through each box and finding, for each action, the possible pushes 
        '''
        
        pushes = deque([])

        #call the function that gets a bidimensional array with the reachable positions by the keeper, in the current state
        node.reach_pos = reachable_positions(node.pos, self.map, node.boxes)
        #the boxes that we will iterate will be returned by the function find_coral_boxes
        for x, y in self.find_coral_boxes(node.reach_pos, node.boxes, self.storages, self.map, self.deadsquares):
            for dx, dy, d in [(-1, 0, "a"), (0, 1, "s"), (1, 0, "d"), (0, -1, "w")]:
                if (
                    node.reach_pos[y-dy][x-dx] #check if the keeper can reach the position to make this push
                    and not self.map._map[y + dy][x + dx] & 0b1000 #avoid pushing towards a wall
                    and not (x+dx, y+dy) in node.boxes #avoid pushing towards a box
                    and self.deadsquares[y+dy][x+dx]): #avoid pushing to a deadsquare

                    #call to the function that returns the path that the keeper has to do in order to do this push
                    #if the path is None then this push is not possible
                    path = bfs(node.pos,(x-dx, y-dy), self.map, node.boxes)
                    if path is None:
                        continue
                    #create a node
                    temp_node = SearchNode((x,y), node, (dx,dy), f'{path}{d}', self.strategy)

                    hash_boxes = hash(frozenset(temp_node.boxes))
                    
                    #check if map is already completed
                    if self.completed(hash_boxes):
                        return [temp_node], True
                    #verify if we have been through this state and this push does not result in a freeze deadlock
                    if (self.check_backtrack(temp_node, hash_boxes)
                        and not self.freeze_deadlock((x + dx, y + dy), temp_node.boxes, self.storages, self.map, self.deadsquares)):
                        temp_node.setHeuristic(self.storages)
                        #all verifications done, we can now append the node to the queue of open nodes.
                        pushes.append(temp_node)

        return pushes, False

    def find_coral_boxes(self, reach_pos, boxes, storages, map, deadsquares):
        '''
        Returns boxes that are on the edges of a Pi-corral or all boxes if there isn't a Pi-corral (also works with multi-room Pi-corrals).
        '''
        coral_pos_set = set()
        ver_tiles = self.ver_tiles
        hor_tiles = self.hor_tiles

        #find corrals by comparing if a position (that doesn't have a box) was reachable
        #on the initial state of the level and on this node state it's not
        coral_pos_set = {(x,y) for y in range(ver_tiles) for x in range(hor_tiles) if not reach_pos[y][x]  
                        and self.reachable_area[y][x]
                        and (x,y) not in boxes}

        boxes_coral = set()
        vis = set()
    
        new_push_boxes = {box for box in boxes}

        #needs to be a list since it will append values during the iteration to the list
        coral_pos_lst = list(coral_pos_set)

        #check if there's a box around a corral position
        for x, y in coral_pos_lst:
            for dx,dy, d in [(-1, 0, "a"), (0, 1, "s"), (1, 0, "d"), (0, -1, "w")]:
                xx = x + dx
                yy = y + dy
                if (xx, yy) in vis:
                    continue

                vis.add((x + dx, y + dy))

                #box around the corral
                if (xx, yy) in boxes:
                    pushes = []
                    #this list of box simulates a push since all its needed are the boxes
                    new_push_boxes.remove((xx, yy))
                    # calculate all pushes for this box
                    for dxx, dyy, dd in [(-1, 0, "a"), (0, 1, "s"), (1, 0, "d"), (0, -1, "w")]:
                        push_x = xx + dxx
                        push_y = yy + dyy
                        #keeper can reach the position to make this push
                        if reach_pos[push_y][push_x]:
                            #check for walls, deadsquares and boxes
                            if (not map._map[yy + dyy][xx + dxx] & 0b1000
                                and deadsquares[yy + dyy][xx + dxx]
                                and (push_x, push_y) not in new_push_boxes):
                                
                                new_push_boxes.add((push_x, push_y))
                                #check if this solves the level
                                if self.completed(hash(frozenset(new_push_boxes))):
                                    return boxes
                                #check for freeze deadlocks
                                if not self.freeze_deadlock((push_x, push_y), new_push_boxes, storages, map, deadsquares):
                                    #if the push is to the outside of the corral, then this is not a Pi-corral
                                    #and it should return all boxes
                                    if (push_x, push_y) not in coral_pos_set:
                                        return boxes
                                
                                new_push_boxes.remove((push_x, push_y))
                    # If it's a box, add itself to check positions around
                    # because it may be getting blocked by other boxes
                    # that may have pushes that unblock it
                    # this part is what solves multi-room Pi-corrals
                    coral_pos_lst.append((xx, yy))
                    coral_pos_set.add((xx, yy))
                    boxes_coral.add((xx, yy))
                    new_push_boxes.add((xx, yy))

        
        if len(boxes_coral) > 0:
            # if these two conditions check, then it's a Pi-corral
            # and we can prune pushes of other boxes not part of the Pi-corral:
            # atleast one box of the coral not in a goal
            # atleast one goal of the coral doesn't have a box
            if (not all( box in storages for box in boxes_coral )
                or any( ( pos in storages ) and ( not pos in boxes ) for pos in coral_pos_set ) ):
                return boxes_coral

        return boxes



    def freeze_deadlock(self, pos, boxes, storages, map, deadsquares):
        """
        Function that calculates if a push results in a freeze deadlock
        
        @param pos: the new  possible position of the box after a push
        @param boxes: the boxes positions after this possible push
        
        Returns a boolean value according if there's a freeze deadlock or not
        """
        def recursive(x, y, visited_box):
            """
            verify if there is the presence of a freeze deadlock, which means that one or more boxes that are immovable.
            The only time that boxes can be immovable and not result in a deadlock is if all of them are all on a goal position 
            """
            if (x, y) in visited_box:
                return True
            #add another visited box
            visited_box.add((x,y))
            blocked_x = False
            blocked_y = False
            #verify if is is a simple deadlock near the current position on the x axis, simple deadlocks make boxes "frozen" too
            if not deadsquares[y][x+1] and not deadsquares[y][x-1]:
                blocked_x = True
            #check if is blocked in the x axis by a wall(different from simple deadlocks!those are blocked in BOTH axis by a wall)    
            elif map.get_tile((x+1, y)) & 0b1000 or map.get_tile((x-1, y)) & 0b1000:
                blocked_x = True
            #the same of the y axis
            if not deadsquares[y+1][x] and not deadsquares[y-1][x]:
                blocked_y = True
            elif map.get_tile((x, y+1)) & 0b1000 or map.get_tile((x, y-1)) & 0b1000:
                blocked_y = True


            #both axis blocked , box  is freezed
            if blocked_x and blocked_y:
                return True
            
            #verify if around this box on the y axis, is another box, if so then we do the same for the box, a recursive call
            if not blocked_y:
                for dy in [-1, 1]:
                    if (x, y + dy) in boxes:
                        blocked_y = recursive(x, y+dy, visited_box)
                        if blocked_y:
                            break
                if not blocked_y:
                    return False
                elif blocked_x:
                    return True
            # same for the x axis
            if not blocked_x:
                for dx in [-1, 1]:
                    if (x + dx, y) in boxes:
                        blocked_x = recursive(x+dx, y, visited_box)
                        if blocked_x:
                            break

            return blocked_x

        visited_box=set()
        x, y = pos
        
        if not recursive(x, y, visited_box):
            return False
        #if the recursive call verified that there is a freeze deadlock, then we still need to check if all visited boxes are in a goal position,
        if all(box in storages for box in visited_box):
            #if thats the case we need to check around the goal for another boxes that we have not visited since the recursive function
            #returns as soon as one box is blocked, maybe these are not on goal
            box_list = list(visited_box)
            for box in box_list:
                for dx, dy, d in [(-1, 0, "a"), (0, 1, "s"), (1, 0, "d"), (0, -1, "w")]:
                    if (box[0] + dx, box[1] + dy) in boxes and (box[0] + dx, box[1] + dy) not in storages:
                        if not recursive(box[0] + dx, box[1] + dy, visited_box):
                            return False
            return not all(box in storages for box in visited_box)
        return True


    def add_to_open(self, pushes, open_nodes):
        '''
        @param pushes- the valid new  pushes for this node's state
        Places the pushes one by one maintaining always the order.
        '''
        for push in pushes:
            #we do not need to sort all list, only put in the right place each push, therefore we use the bisect module
            bisect.insort( open_nodes, push )