import json

import jsonschema
try:
    from ruamel import yaml
except ModuleNotFoundError:
    yaml = False

JSON_SCHEMA = {
    'type': 'object',
    'properties': {
        'corpus': {
            'type': 'object',
            'properties': {
                'directory': {'type': 'string'},
                'directories': {
                    'type': 'array',
                    'items': {'type': 'string'}
                },
                'version': {'type': 'string'},  # text or lemma
                'connections': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},  # database name; path to CSV file
                            'encoding': {'type': 'string'},  # for CSV file
                            'driver': {'type': 'string'},
                            'server': {'type': 'string'},
                            'database': {'type': 'string'},
                            'name_col': {'type': 'string'},
                            'text_col': {'type': 'string'}
                        }
                    }
                },
            }
        },
        'annotation': {
            'type': 'object',
            'properties': {
                'file': {'type': 'string'}
            }
        },
        'annotations': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string'}
                }
            }
        },
        'output': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'kind': {'type': 'string'},  # sql, csv, etc.
                'path': {'type': 'string'},
                'driver': {'type': 'string'},
                'server': {'type': 'string'},
                'database': {'type': 'string'},
                'ignore': {'type': 'boolean'},
                'encoding': {'type': 'string'},
            }
        },
        'select': {
            'type': 'object',
            'properties': {
                'start': {'type': 'number'},
                'end': {'type': 'number'},
                'encoding': {'type': 'string'},
                'filenames': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        },
        'algorithm': {
            'type': 'object',
            'names': {
                'type': 'array',
                'items': {'type': 'string'}
            }
        },
        'loginfo': {
            'type': 'object',
            'properties': {
                'directory': {'type': 'string'},
                'ignore': {'type': 'boolean'},
                'encoding': {'type': 'string'},
                'kind': {'type': 'string'},
            }
        },
        'skipinfo': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string'},
                'rebuild': {'type': 'boolean'},
                'ignore': {'type': 'boolean'},
            }
        },
        'logger': {
            'type': 'object',
            'properties': {
                'verbose': {'type': 'boolean'}
            }
        }
    }
}


def myexec(code):
    import warnings
    warnings.warn('Executing python external file: only do this if you trust it')
    import sys
    from io import StringIO
    temp_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        # try if this is a expression
        ret = eval(code)
        result = sys.stdout.getvalue()
        if ret:
            result = result + ret
    except:
        try:
            exec(code)
        except:
            # you can use <traceback> module here
            import traceback
            buf = StringIO()
            traceback.print_exc(file=buf)
            error = buf.getvalue()
            raise ValueError(error)
        else:
            result = sys.stdout.getvalue()
    sys.stdout = temp_stdout
    return result


def get_config(path):
    with open(path) as fh:
        if path.endswith('json'):
            return json.load(fh)
        elif path.endswith('yaml') and yaml:
            return yaml.load(fh)
        elif path.endswith('py'):
            return eval(myexec(fh.read()))
        else:
            raise ValueError('Unrecognized configuration file type: {}'.format(path.split('.')[-1]))


def validate_config(path):
    conf = get_config(path)
    jsonschema.validate(conf, JSON_SCHEMA)
    return conf
