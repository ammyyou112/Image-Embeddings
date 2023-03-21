from configparser import ConfigParser


def config(filename="database.ini", section="postgresql"):
    parser = ConfigParser()
    try:
        # read config file
        parser.read(filename)
    except Exception as e:
        raise Exception(f"Error reading {filename}: {e}")

    if not parser.has_section(section):
        raise Exception(f"{section} section not found in {filename}")

    db = dict(parser.items(section))
    return db