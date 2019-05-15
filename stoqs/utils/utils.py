# A collection of various utility functions
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# An epoch good for time axis labels - OceanSITES uses 1 Jan 1950
EPOCH_STRING = '1950-01-01'
EPOCH_DATETIME = datetime(1950, 1, 1)

def round_to_n(x, n):
    '''
    Round to n significant digits
    '''
    if n < 1:
        raise ValueError("number of significant digits must be >= 1")

    if type(x) in (list, tuple):
        rounded_list = []
        for xi in x:
            # Use %e format to get the n most significant digits, as a string.
            format = "%." + str(n-1) + "e"
            as_string = format % xi
            rounded_list.append(float(as_string))
        
        return rounded_list

    else:
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
    if 'get_actual_count' in kwargs:
        if kwargs['get_actual_count']:
            get_actual_count_state = True

    return get_actual_count_state

def getShow_Sigmat_Parameter_Values(kwargs):
    '''
    return state of showsigmatparametervalues checkbox from query UI
    '''
    show_sigmat_parameter_values_state = False
    if 'showsigmatparametervalues' in kwargs:
        if kwargs['showsigmatparametervalues']:
            show_sigmat_parameter_values_state = True

    return show_sigmat_parameter_values_state

def getShow_StandardName_Parameter_Values(kwargs):
    '''
    return state of showstandardnameparametervalues checkbox from query UI
    '''
    show_standardname_parameter_values_state = False
    if 'showstandardnameparametervalues' in kwargs:
        if kwargs['showstandardnameparametervalues']:
            show_standardname_parameter_values_state = True

    return show_standardname_parameter_values_state

def getShow_All_Parameter_Values(kwargs):
    '''
    return state of showallparametervalues checkbox from query UI
    '''
    show_all_parameter_values_state = False
    if 'showallparametervalues' in kwargs:
        if kwargs['showallparametervalues']:
            show_all_parameter_values_state = True

    return show_all_parameter_values_state

def getShow_Parameter_Platform_Data(kwargs):
    '''
    return state of Show data checkbox from query UI
    '''
    show_parameter_platform_data_state = False
    if 'showparameterplatformdata' in kwargs:
        if kwargs['showparameterplatformdata']:
            show_parameter_platform_data_state = True

    return show_parameter_platform_data_state

#
# General utility methods called by STOQSQueryManager, MPQuery, etc.
#

def getParameterGroups(dbAlias, parameter=None):
    '''
    Return list of ParameterGroups that parameter belongs to
    '''
    from stoqs.models import ParameterGroupParameter

    qs = ParameterGroupParameter.objects.using(dbAlias).values_list('parametergroup__name', flat=True)
    if parameter:
        qs = qs.filter(parameter=parameter)

    return qs


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

def pearsonr(x, y):
    '''
    See http://stackoverflow.com/questions/3949226/calculating-pearson-correlation-and-significance-in-python and
    http://shop.oreilly.com/product/9780596529321.do
    '''
    # Assume len(x) == len(y)
    n = len(x)
    sum_x = float(sum(x))
    sum_y = float(sum(y))
    sum_x_sq = sum([pow(x, 2) for x in x])
    sum_y_sq = sum([pow(x, 2) for x in y])
    psum = sum(map(lambda x, y: x * y, x, y))
    num = psum - (sum_x * sum_y/n)
    den = pow((sum_x_sq - pow(sum_x, 2) / n) * (sum_y_sq - pow(sum_y, 2) / n), 0.5)
    if den == 0: return 0
    return num / den

def find_matching_char(s, c1, c2):
    '''To use to find for example matching c1='(' and c2=')' in string s
    '''
    pos = 0
    if c1 not in s:
        return 

    start_checking = False
    for i, c in enumerate(s):
        if c == c1:
            pos += 1
            start_checking = True
        if c == c2:
            pos -= 1
        if start_checking:
            if pos == 0:
                return i + 1

def find_parens(s):
    '''Cribbed from https://stackoverflow.com/questions/29991917/indices-of-matching-parentheses-in-python
    Returns hash where keys are opening parens and values are the closing parens.
    '''
    toret = {}
    pstack = []

    for i, c in enumerate(s):
        if c == '(':
            pstack.append(i)
        elif c == ')':
            if len(pstack) == 0:
                logger.debug("No matching opening parens at: " + str(i))
                return toret

            toret[pstack.pop()] = i

    if len(pstack) > 0:
        logger.debug("No matching closing parens at: " + str(pstack.pop()))
        return toret

    return toret

def _quote_ins(FIND_INS, pgq, all_ins, INSTR, incount, in_match):
    # Build up the new SQL by appending modified IN clauses and intermediate (trailing) content
    matched_ins = FIND_INS.match(pgq[in_match.start():]).groups()[0]    # Could contain multiple INs, find_parens() fixes this
    parens_hash = find_parens(matched_ins)                              # Get start and end indices for inside parens: IN (xxx)

    # Need to unqote/quote the IN values for Postgres
    # The 0 key's value is the matching paren, pull contents of the IN, wrapping it with parens
    in_content = matched_ins[1:parens_hash[0]]
    # Capture intermediate and trailing SQL between the ' IN ' clauses 
    try:
        end_index = all_ins[incount+1].start() - len(INSTR) - all_ins[incount].end() + parens_hash[0] + 1
        trailing_content = matched_ins[parens_hash[0]:end_index]
    except IndexError:
        # Likely all_ins[incount+1] has failed on last in_match instance
        trailing_content = matched_ins[parens_hash[0]:]
    new_items = []
    if ',' in matched_ins:
        # Handle multiple items in the IN clause
        for item in in_content.split(','):
            item = item.replace("'", "")        # Remove QUOTE_DATES quotes
            new_items.append(f"'{item.lstrip()}'")
    else: 
        new_items.append(f"'{in_content.lstrip()}'")

    if new_items:
        quoted_in = f"{INSTR}({', '.join(new_items)}" + trailing_content
    else:
        raise ValueError(f"Did not get any new_items from IN in {matched_ins}")

    return quoted_in

def postgresifySQL(query, pointFlag=False, translateGeom=False, sampleFlag=False):
    '''
    Given a generic database agnostic Django query string modify it using regular expressions to work
    on a PostgreSQL server.  If pointFlag is True then use the mappoint field for geom.  If translateGeom
    is True then translate .geom to latitude and longitude columns.
    '''
    import re

    # Get text of query to quotify for Postgresql
    pgq = str(query)

    # Remove double quotes from around all table and colum names
    pgq = pgq.replace('"', '')

    if not sampleFlag:
        # Add aliases for geom and gid - Activity
        pgq = pgq.replace('stoqs_activity.id', 'stoqs_activity.id as gid', 1)
        pgq = pgq.replace('= stoqs_activity.id as gid', '= stoqs_activity.id', 1)           # Fixes problem with above being applied to Sample query join
        if pointFlag:
            pgq = pgq.replace('stoqs_activity.mappoint', 'stoqs_activity.mappoint as geom')
        else:
            pgq = pgq.replace('stoqs_activity.maptrack', 'stoqs_activity.maptrack as geom')
    else:
        # Add aliases for geom and gid - Sample
        pgq = pgq.replace('stoqs_sample.id', 'stoqs_sample.id as gid', 1)
        pgq = pgq.replace('stoqs_sample.geom', 'stoqs_sample.geom as geom')

    if translateGeom:
        pgq = pgq.replace('stoqs_measurement.geom', 'ST_X(stoqs_measurement.geom) as longitude, ST_Y(stoqs_measurement.geom) as latitude')
    
    # Quotify simple things that need quotes
    QUOTE_NAMEEQUALS = re.compile('name\s+=\s+(?P<argument>[^\)\s)]+)')
    QUOTE_DATES = re.compile('(?P<argument>\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)')

    pgq = QUOTE_NAMEEQUALS.sub(r"name = '\1'", pgq)
    pgq = QUOTE_DATES.sub(r"'\1'", pgq)

    # The IN ( ... ) clauses require special treatment: an IN SELECT subquery needs no quoting, only string values need quotes, and numbers need no quotes
    FIND_INS = re.compile('\sIN\s(?P<argument>.+)')
    INSTR = ' IN '
    all_ins = [ai for ai in re.finditer(INSTR, pgq)]
    items = ''
    try:
        new_pgq = pgq[:all_ins[0].start()]
    except IndexError:
        # Likely no INSTR string found
        new_pgq = pgq

    # Test for presence of a 'SELECT' in any part of the INs matched - as happens for Sample location queries
    has_select = False
    for in_match in all_ins:
        matched_ins = FIND_INS.match(pgq[in_match.start():]).groups()[0]
        if 'SELECT' in matched_ins:
            has_select = True
            all_inner_ins = [ai for ai in re.finditer(INSTR, matched_ins)]
            new_pgq += f"{INSTR}{matched_ins[:all_inner_ins[0].start()]}"
            for incount, inner_in_match in enumerate(all_inner_ins):
                new_pgq += _quote_ins(FIND_INS, matched_ins, all_inner_ins, INSTR, incount, inner_in_match)
                break
    
    if not has_select:
        for incount, in_match in enumerate(all_ins):
            new_pgq += _quote_ins(FIND_INS, pgq, all_ins, INSTR, incount, in_match)

    # Remove all '::bytea' added to the geom fields - and cleanup any mistakes 
    new_pgq = new_pgq.replace(r'::bytea', r'')
    new_pgq = new_pgq.replace(r' IN IN ', r' IN ')
    new_pgq = new_pgq.replace(r' IN  IN', r' IN ')

    return new_pgq

def spiciness(t,s):
    """
    Return spiciness as defined by Flament (2002).
    see : http://www.satlab.hawaii.edu/spice/spice.html
    ref : A state variable for characterizing water masses and their 
          diffusive stability: spiciness. Progress in Oceanography
          Volume 54, 2002, Pages 493-501. 
    test : spice(p=0,T=15,S=33)=0.54458641375
    NB : only for valid p = 0 
    """
    B = numpy.zeros((7,6))
    B[1,1] = 0
    B[1,2] = 7.7442e-001
    B[1,3] = -5.85e-003
    B[1,4] = -9.84e-004
    B[1,5] = -2.06e-004

    B[2,1] = 5.1655e-002
    B[2,2] = 2.034e-003
    B[2,3] = -2.742e-004
    B[2,4] = -8.5e-006
    B[2,5] = 1.36e-005

    B[3,1] = 6.64783e-003
    B[3,2] = -2.4681e-004
    B[3,3] = -1.428e-005
    B[3,4] = 3.337e-005
    B[3,5] = 7.894e-006

    B[4,1] = -5.4023e-005
    B[4,2] = 7.326e-006
    B[4,3] = 7.0036e-006
    B[4,4] = -3.0412e-006
    B[4,5] = -1.0853e-006
 
    B[5,1] = 3.949e-007
    B[5,2] = -3.029e-008
    B[5,3] = -3.8209e-007
    B[5,4] = 1.0012e-007
    B[5,5] = 4.7133e-008

    B[6,1] = -6.36e-010
    B[6,2] = -1.309e-009
    B[6,3] = 6.048e-009
    B[6,4] = -1.1409e-009
    B[6,5] = -6.676e-010
    # 
    t = numpy.array(t)
    s = numpy.array(s)
    #
    coefs = B[1:7,1:6]
    sp = numpy.zeros(t.shape)
    ss = s - 35.
    bigT = numpy.ones(t.shape)
    for i in range(6):
        bigS = numpy.ones(t.shape)
        for j in range(5):
            sp+= coefs[i,j]*bigT*bigS
            bigS*= ss
        bigT*=t
    return sp

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = list(map(math.radians, [lon1, lat1, lon2, lat2]))

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 

    # 6367 km is the radius of the Earth
    km = 6367 * c
    return km 

if __name__ == "__main__":
    import doctest
    doctest.testmod()

