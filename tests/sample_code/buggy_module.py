"""Bug test module — intentional bugs for testing detection."""


def missing_return_value(x):
    if x > 0:
        return "positive"
    if x < 0:
        return "negative"


def variable_before_assignment():
    print(y)
    y = 10


def infinite_loop():
    i = 0
    while i < 10:
        if i == 5:
            continue
        i += 1


def wrong_comparison(x):
    if x = 5:
        return True
    return False


def shadowed_builtin():
    list = [1, 2, 3]
    return list


def none_dereference(data):
    result = None
    for item in data:
        result = item
    return result.upper()


def unreachable_code():
    return True
    print("This will never execute")


class Broken:
    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value

    def set_value(self, new_value):
        self.value = new_value

    def reset(self):
        self.value = None
