import collections

def format_scores(coordinates):
    """ The score variable from tf call slightly varies as its a float value ex: .2323121204 vs .232392830. 
    This function will format the score to be 2 decimal points.
    """    
    for k, v in coordinates.items():
        i = 0
        for each in coordinates[k]:
            coordinates[k][i]['score'] = float(format(coordinates[k][i]['score'], '.2f'))
            i += 1
    coorindates = collections.OrderedDict(sorted(coordinates.items()))
    return coordinates
