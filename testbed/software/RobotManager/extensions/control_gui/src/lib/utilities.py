def check_for_spaces(string):
    return ' ' in string


def split_path(path):
    # Remove any leading/trailing slashes
    path = path.strip('/')
    parts = path.split('/')

    if not parts or parts[0] == '':
        return '', ''

    first = parts[0]
    remainder = '/'.join(parts[1:])
    return first, remainder


def strip_id(path, target_id) -> str | None:
    # Ensure no leading or trailing slashes
    path = path.strip('/')
    parts = path.split('/')

    try:
        index = parts.index(target_id)
        return '/'.join(parts[index + 1:])
    except ValueError:
        # target_id not found
        return None


if __name__ == '__main__':
    path1 = 'id1/id2/id3'
    print(split_path(path1))

    print(strip_id(path1, 'id1'))

    print(split_path('/'))
    print(split_path('/id1'))
