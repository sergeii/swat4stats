import os


def env(name, default):
    return os.environ.get(name, default)
