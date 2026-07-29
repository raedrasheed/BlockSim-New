# Event.py

import heapq
from InputsConfig import InputsConfig as p  # kept for compatibility (even if unused)


class Event(object):
    """ Defines the Event.

        :param str type: the event type (block creation or block reception)
        :param int node: the id of the node that the event belongs to
        :param float time: the simulation time in which the event will be executed at
        :param obj block: the event content "block" to be generated or received
    """
    def __init__(self, type, node, time, block, meta=None):
        self.type = type
        self.node = node
        self.time = float(time)
        self.block = block

        # Stage 3: optional immutable event-identity metadata (EventIdentity).
        # Default None keeps all non-PoCol models unaffected.
        self.meta = meta

        # tie-breaker sequence number assigned by Queue.add_event
        self._seq = 0

    def __lt__(self, other):
        # heapq needs comparable items
        if self.time != other.time:
            return self.time < other.time
        return self._seq < other._seq


class Queue:
    event_list = []          # now this list is maintained as a MIN-HEAP
    _seq_counter = 0

    @staticmethod
    def add_event(event):
        # Assign a unique increasing sequence for stable ordering when times are equal
        event._seq = Queue._seq_counter
        Queue._seq_counter += 1
        heapq.heappush(Queue.event_list, event)

    @staticmethod
    def remove_event(event):
        # Original code deleted the earliest event (index 0), ignoring the argument.
        # Keep same behavior: pop earliest from heap.
        if Queue.event_list:
            heapq.heappop(Queue.event_list)

    @staticmethod
    def get_next_event():
        # Return earliest event WITHOUT removing it (same behavior as before)
        if not Queue.event_list:
            return None
        return Queue.event_list[0]

    @staticmethod
    def size():
        return len(Queue.event_list)

    @staticmethod
    def isEmpty():
        return len(Queue.event_list) == 0
