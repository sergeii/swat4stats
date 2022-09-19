from django.contrib.staticfiles import storage


class ManifestStaticFilesStorage(storage.ManifestStaticFilesStorage):
    # don't hash assets referenced in css and js files
    patterns = ()
