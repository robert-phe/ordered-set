"""
An OrderedSet is a custom MutableSet that remembers its order, so that every
entry has an index that can be looked up.

Based on a recipe originally posted to ActiveState Recipes by Raymond Hettiger,
and released under the MIT license.

Rob Speer's changes are as follows:

    - changed the content from a doubly-linked list to a regular Python list.
      Seriously, who wants O(1) deletes but O(N) lookups by index?
    - add() returns the index of the added item
    - index() just returns the index of an item
    - added a __getstate__ and __setstate__ so it can be pickled
    - added __getitem__
"""
import collections
import itertools as it

SLICE_ALL = slice(None)
__version__ = '2.0.1'


def is_iterable(obj):
    """
    Are we being asked to look up a list of things, instead of a single thing?
    We check for the `__iter__` attribute so that this can cover types that
    don't have to be known by this module, such as NumPy arrays.

    Strings, however, should be considered as atomic values to look up, not
    iterables. The same goes for tuples, since they are immutable and therefore
    valid entries.

    We don't need to check for the Python 2 `unicode` type, because it doesn't
    have an `__iter__` attribute anyway.
    """
    return hasattr(obj, '__iter__') and not isinstance(obj, str) and not isinstance(obj, tuple)


class OrderedSet(collections.MutableSet):
    """
    An OrderedSet is a custom MutableSet that remembers its order, so that
    every entry has an index that can be looked up.
    """
    def __init__(self, iterable=None):
        self.items = []
        self.map = {}
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        """
        Get the item at a given index.

        If `index` is a slice, you will get back that slice of items. If it's
        the slice [:], a copy of this object is returned.

        If `index` is an iterable, you'll get the OrderedSet of items
        corresponding to those indices. This is similar to NumPy's
        "fancy indexing".
        """
        if index == SLICE_ALL:
            return self.copy()
        elif hasattr(index, '__index__') or isinstance(index, slice):
            result = self.items[index]
            if isinstance(result, list):
                return OrderedSet(result)
            else:
                return result
        elif is_iterable(index):
            return OrderedSet([self.items[i] for i in index])
        else:
            raise TypeError(
                "Don't know how to index an OrderedSet by %r" % index)

    def copy(self):
        return OrderedSet(self)

    def __getstate__(self):
        if len(self) == 0:
            # The state can't be an empty list.
            # We need to return a truthy value, or else __setstate__ won't be run.
            #
            # This could have been done more gracefully by always putting the state
            # in a tuple, but this way is backwards- and forwards- compatible with
            # previous versions of OrderedSet.
            return (None,)
        else:
            return list(self)

    def __setstate__(self, state):
        if state == (None,):
            self.__init__([])
        else:
            self.__init__(state)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        """
        Add `key` as an item to this OrderedSet, then return its index.

        If `key` is already in the OrderedSet, return the index it already
        had.
        """
        if key not in self.map:
            self.map[key] = len(self.items)
            self.items.append(key)
        return self.map[key]
    append = add

    def update(self, sequence):
        """
        Update the set with the given iterable sequence, then return the index
        of the last element inserted.
        """
        item_index = None
        try:
            for item in sequence:
                item_index = self.add(item)
        except TypeError:
            raise ValueError('Argument needs to be an iterable, got %s' % type(sequence))
        return item_index

    def index(self, key):
        """
        Get the index of a given entry, raising an IndexError if it's not
        present.

        `key` can be an iterable of entries that is not a string, in which case
        this returns a list of indices.
        """
        if is_iterable(key):
            return [self.index(subkey) for subkey in key]
        return self.map[key]

    def pop(self):
        """
        Remove and return the last element from the set.

        Raises KeyError if the set is empty.
        """
        if not self.items:
            raise KeyError('Set is empty')

        elem = self.items[-1]
        del self.items[-1]
        del self.map[elem]
        return elem

    def discard(self, key):
        """
        Remove an element.  Do not raise an exception if absent.

        The MutableSet mixin uses this to implement the .remove() method, which
        *does* raise an error when asked to remove a non-existent item.
        """
        if key in self:
            i = self.map[key]
            del self.items[i]
            del self.map[key]
            for k, v in self.map.items():
                if v >= i:
                    self.map[k] = v - 1

    def clear(self):
        """
        Remove all items from this OrderedSet.
        """
        del self.items[:]
        self.map.clear()

    def __iter__(self):
        return iter(self.items)

    def __reversed__(self):
        return reversed(self.items)

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and self.items == other.items
        try:
            other_as_set = set(other)
        except TypeError:
            # If `other` can't be converted into a set, it's not equal.
            return False
        else:
            return set(self) == other_as_set

    def union(self, *sets):
        """
        Combines all unique items.
        Each items order is defined by its first appearance.

        Example:
            >>> self = OrderedSet.union(oset([3, 1, 4, 1, 5]), [1, 3], [2, 0])
            >>> print(self)
            OrderedSet([3, 1, 4, 5, 2, 0])
            >>> self.union([8, 9])
            OrderedSet([3, 1, 4, 5, 2, 0, 8, 9])
            >>> self | {10}
            OrderedSet([3, 1, 4, 5, 2, 0, 10])
            >>> OrderedSet.union(oset([1, 2, 3]))
            OrderedSet([1, 2, 3])
        """
        cls = self.__class__ if isinstance(self, OrderedSet) else OrderedSet
        containers = map(list, it.chain([self], sets))
        items = it.chain.from_iterable(containers)
        return cls(items)

    def intersection(self, *sets):
        """
        Returns elements in common between all sets. Order is defined only
        by the first set.

        Example:
            >>> self = OrderedSet.intersection(oset([0, 1, 2, 3]), [1, 2, 3])
            >>> print(self)
            OrderedSet([1, 2, 3])
            >>> self.intersection([2, 4, 5], [1, 2, 3, 4])
            OrderedSet([2])
            >>> OrderedSet.intersection(oset([1, 2, 3]))
            OrderedSet([1, 2, 3])
        """
        cls = self.__class__ if isinstance(self, OrderedSet) else OrderedSet
        if sets:
            common = set.intersection(*map(set, sets))
            items = (item for item in self if item in common)
        else:
            items = self
        return cls(items)

    def difference(self, *sets):
        """
        Returns all elements that are in this set but not the others.

        Example:
            >>> OrderedSet([1, 2, 3]).difference(OrderedSet([2]))
            OrderedSet([1, 3])
            >>> OrderedSet([1, 2, 3]) - OrderedSet([2])
            OrderedSet([1, 3])
        """
        cls = self.__class__
        other = set.intersection(*map(set, sets))
        return cls(item for item in self if item not in other)

    def issubset(self, other):
        """
        Report whether another set contains this set.

        Example:
            >>> OrderedSet([1, 2, 3]).issubset({1, 2})
            False
            >>> OrderedSet([1, 2, 3]).issubset({1, 2, 3, 4})
            True
            >>> OrderedSet([1, 2, 3]).issubset({1, 4, 3, 5})
            False
        """
        if len(self) > len(other):  # Fast check for obvious cases
            return False
        return all(item in other for item in self)

    def issuperset(self, other):
        """
        Report whether this set contains another set.

        Example:
            >>> OrderedSet([1, 2]).issuperset([1, 2, 3])
            False
            >>> OrderedSet([1, 2, 3, 4]).issuperset({1, 2, 3})
            True
            >>> OrderedSet([1, 4, 3, 5]).issuperset({1, 2, 3})
            False
        """
        if len(self) < len(other):  # Fast check for obvious cases
            return False
        return all(item in self for item in other)

    def symmetric_difference(self, other):
        """
        Return the symmetric difference of two sets as a new set.
        (I.e. all elements that are in exactly one of the sets.)

        Example:
            >>> self = OrderedSet([1, 4, 3, 5, 7])
            >>> other = OrderedSet([9, 7, 1, 3, 2])
            >>> self.symmetric_difference(other)
            OrderedSet([4, 5, 9, 2])
        """
        cls = self.__class__ if isinstance(self, OrderedSet) else OrderedSet
        diff1 = cls(self).difference(other)
        diff2 = cls(other).difference(self)
        return diff1.union(diff2)

    def difference_update(self, *sets):
        """
        Returns a copy of self with items from other removed

        Example:
            >>> self = OrderedSet([1, 2, 3])
            >>> self.difference_update(OrderedSet([2]))
            >>> print(self)
            OrderedSet([1, 3])
        """
        for item in it.chain.from_iterable(sets):
            self.discard(item)

    def intersection_update(self, other):
        """
        Update a set with the intersection of itself and another.
        Order depends only on the first element

        Example:
            >>> self = OrderedSet([1, 4, 3, 5, 7])
            >>> other = OrderedSet([9, 7, 1, 3, 2])
            >>> self.intersection_update(other)
            >>> print(self)
            OrderedSet([1, 3, 7])
        """
        to_remove = [item for item in self if item not in other]
        for item in to_remove:
            self.discard(item)

    def symmetric_difference_update(self, other):
        """
        Update a set with the intersection of itself and another.
        Order depends only on the first element

        Example:
            >>> self = OrderedSet([1, 4, 3, 5, 7])
            >>> other = OrderedSet([9, 7, 1, 3, 2])
            >>> self.symmetric_difference_update(other)
            >>> print(self)
            OrderedSet([4, 5, 9, 2])
        """
        cls = self.__class__ if isinstance(self, OrderedSet) else OrderedSet
        diff2 = cls(other).difference(self)
        self.difference_update(other)
        self.update(diff2)
