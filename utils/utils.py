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

#
# Methods that return checkbox selections made on the UI, called by STOQSQueryManager and MPQuery
#
def getGet_Actual_Count(kwargs):
    '''
    return state of Get Actual Count checkbox from query UI
    '''
    get_actual_count_state = False
    if kwargs.has_key('get_actual_count'):
        if kwargs['get_actual_count']:
            get_actual_count_state = True

    return get_actual_count_state

def getShow_Sigmat_Parameter_Values(kwargs):
    '''
    return state of showsigmatparametervalues checkbox from query UI
    '''
    show_sigmat_parameter_values_state = False
    if kwargs.has_key('showsigmatparametervalues'):
        if kwargs['showsigmatparametervalues']:
            show_sigmat_parameter_values_state = True

    return show_sigmat_parameter_values_state

def getShow_StandardName_Parameter_Values(kwargs):
    '''
    return state of showstandardnameparametervalues checkbox from query UI
    '''
    show_standardname_parameter_values_state = False
    if kwargs.has_key('showstandardnameparametervalues'):
        if kwargs['showstandardnameparametervalues']:
            show_standardname_parameter_values_state = True

    return show_standardname_parameter_values_state

def getShow_All_Parameter_Values(kwargs):
    '''
    return state of showallparametervalues checkbox from query UI
    '''
    show_all_parameter_values_state = False
    if kwargs.has_key('showallparametervalues'):
        if kwargs['showallparametervalues']:
            show_all_parameter_values_state = True

    return show_all_parameter_values_state

def getDisplay_Parameter_Platform_Data(kwargs):
    '''
    return state of Display Parameter-Platform data checkbox from quiry UI
    '''
    display_parameter_platform_data_state = False
    if kwargs.has_key('displayparameterplatformdata'):
        if kwargs['displayparameterplatformdata']:
            display_parameter_platform_data_state = True

    return display_parameter_platform_data_state


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

def postgresifySQL(query, pointFlag=False):
    '''
    Given a generic database agnostic Django query string modify it using regular expressions to work
    on a PostgreSQL server.  If pointFlag is True then use the mappoint field for geom.
    '''
    import re

    # Get text of query to quotify for Postgresql
    q = str(query)

    # Remove double quotes from around all table and colum names
    q = q.replace('"', '')

    # Add aliases for geom and gid - Activity
    q = q.replace('stoqs_activity.id', 'stoqs_activity.id as gid', 1)
    q = q.replace('= stoqs_activity.id as gid', '= stoqs_activity.id', 1)           # Fixes problem with above being applied to Sample query join

    if pointFlag:
        q = q.replace('stoqs_activity.mappoint', 'stoqs_activity.mappoint as geom')
    else:
        q = q.replace('stoqs_activity.maptrack', 'stoqs_activity.maptrack as geom')

    q = q.replace('stoqs_measurement.geom', 'ST_X(stoqs_measurement.geom) as longitude, ST_Y(stoqs_measurement.geom) as latitude')
    # Add aliases for geom and gid - Sample
    q = q.replace('stoqs_sample.id', 'stoqs_sample.id as gid', 1)
    q = q.replace('stoqs_sample.geom', 'stoqs_sample.geom as geom')

    # Quotify things that need quotes
    QUOTE_NAMEEQUALS = re.compile('name\s+=\s+(?P<argument>\S+)')
    QUOTE_DATES = re.compile('(?P<argument>\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)')
    QUOTE_INS = re.compile('IN\s+\((?P<argument>[^\)]+)\)')

    q = QUOTE_NAMEEQUALS.sub(r"name = '\1'", q)
    q = QUOTE_DATES.sub(r"'\1'", q)
    q = QUOTE_INS.sub(r"IN ('\1')", q)

    return q

if __name__ == "__main__":
    import doctest
    doctest.testmod()

