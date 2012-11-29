# A collection of various utility functions

def round_to_n(x, n):
    '''
    reound to n significant digits
    '''
    if n < 1:
        raise ValueError("number of significant digits must be >= 1")
    # Use %e format to get the n most significant digits, as a string.
    format = "%." + str(n-1) + "e"
    as_string = format % x
    return float(as_string)

def addAttributeToListItems(list_to_modify, name, value):
    '''
    For each item in list_to_modify, add new attribute name with value value.
    Useful for modyfying a django queryset before passing to a template.
    '''
    new_list = []
    for item in list_to_modify:
        new_item = item
        new_item.__setattr__(name, value)
        new_list.append(new_item)

    return new_list


## {{{ http://code.activestate.com/recipes/511478/ (r1)
import math
import numpy
import functools

def percentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1

# median is 50th percentile.
median = functools.partial(percentile, percent=0.5)

## end of http://code.activestate.com/recipes/511478/ }}}

def mode(N):
    '''
    Create some bins based on the min and max of the list/array in N
    compute the histogram and then the mode of the data in N.  
    Return the edge, which is clo.
    '''
    numbins = 100
    var = numpy.array(N)
    bins = numpy.linspace(var.min(), var.max(), numbins)
    hist, bin_edges = numpy.histogram(var, bins)
    index = numpy.argmax(hist)
    if index == 0:
        return bin_edges[index]
    else:
        return (bin_edges[index] + bin_edges[index-1]) / 2.0

    


# pure-Python Douglas-Peucker line simplification/generalization
#
# this code was written by Schuyler Erle <schuyler@nocat.net> and is
#   made available in the public domain.
#
# the code was ported from a freely-licensed example at
#   http://www.3dsoftware.com/Cartography/Programming/PolyLineReduction/
#
# the original page is no longer available, but is mirrored at
#   http://www.mappinghacks.com/code/PolyLineReduction/

"""

>>> line = [(0,0),(1,0),(2,0),(2,1),(2,2),(1,2),(0,2),(0,1),(0,0)]
>>> simplify_points(line, 1.0)
[(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]

>>> line = [(0,0),(0.5,0.5),(1,0),(1.25,-0.25),(1.5,.5)]
>>> simplify_points(line, 0.25)
[(0, 0), (0.5, 0.5), (1.25, -0.25), (1.5, 0.5)]

"""

def simplify_points (pts, tolerance): 
    anchor  = 0
    floater = len(pts) - 1
    stack   = []
    keep    = set()

    stack.append((anchor, floater))  
    while stack:
        anchor, floater = stack.pop()
      
        # initialize line segment
        if pts[floater] != pts[anchor]:
            anchorX = float(pts[floater][0] - pts[anchor][0])
            anchorY = float(pts[floater][1] - pts[anchor][1])
            seg_len = math.sqrt(anchorX ** 2 + anchorY ** 2)
            # get the unit vector
            anchorX /= seg_len
            anchorY /= seg_len
        else:
            anchorX = anchorY = seg_len = 0.0
    
        # inner loop:
        max_dist = 0.0
        farthest = anchor + 1
        for i in range(anchor + 1, floater):
            dist_to_seg = 0.0
            # compare to anchor
            vecX = float(pts[i][0] - pts[anchor][0])
            vecY = float(pts[i][1] - pts[anchor][1])
            seg_len = math.sqrt( vecX ** 2 + vecY ** 2 )
            # dot product:
            proj = vecX * anchorX + vecY * anchorY
            if proj < 0.0:
                dist_to_seg = seg_len
            else: 
                # compare to floater
                vecX = float(pts[i][0] - pts[floater][0])
                vecY = float(pts[i][1] - pts[floater][1])
                seg_len = math.sqrt( vecX ** 2 + vecY ** 2 )
                # dot product:
                proj = vecX * (-anchorX) + vecY * (-anchorY)
                if proj < 0.0:
                    dist_to_seg = seg_len
                else:  # calculate perpendicular distance to line (pythagorean theorem):
                    dist_to_seg = math.sqrt(abs(seg_len ** 2 - proj ** 2))
                if max_dist < dist_to_seg:
                    max_dist = dist_to_seg
                    farthest = i

        if max_dist <= tolerance: # use line segment
            keep.add(anchor)
            keep.add(floater)
        else:
            stack.append((anchor, farthest))
            stack.append((farthest, floater))

    keep = list(keep)
    keep.sort()
    # Change from original code: add the index from the original line in the return
    return [(pts[i] + (i,)) for i in keep]

if __name__ == "__main__":
    import doctest
    doctest.testmod()

