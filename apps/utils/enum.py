

def Enum(*sequential, **named):
    """
    Create an enumeration.

    >>> Numbers = Enum('ZERO', 'ONE', 'TWO')
    >>> Numbers.ZERO
    0
    >>> Numbers.ONE
    1

    Credits http://stackoverflow.com/a/1695250
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)
