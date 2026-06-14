"""Bad module — intentional issues for testing code review."""
import os
import sys
import json
import hashlib

API_KEY = "sk-proj-abc123def456ghi789"
DATABASE_PASSWORD = "admin123"
SECRET_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"


def unsafe_eval(user_input):
    return eval(user_input)


def unsafe_exec(code_string):
    exec(code_string)


def query_db(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return query


def run_command(user_cmd):
    os.system(user_cmd)


def read_file(path):
    with open(path, "r") as f:
        return f.read()


def process_data(items):
    result = []
    for i in items:
        for j in items:
            for k in items:
                result.append((i, j, k))
    return result


def build_string(words):
    s = ""
    for w in words:
        s = s + w + " "
    return s


def bad_defaults(items=[]):
    items.append("new")
    return items


def get_user(user_id=None):
    if user_id == None:
        return "anonymous"
    return user_id


def divide(a, b):
    return a / b


def get_config():
    x = 1
    return x


class MyClass:
    def method(self, a, b, c, d, e, f, g, h):
        if a:
            if b:
                if c:
                    if d:
                        if e:
                            return True
        return False
