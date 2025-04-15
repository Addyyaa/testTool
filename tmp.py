int = 213627378335744


def convert_to_tb(data):
    return data / 1024 / 1024 / 1024 / 1024


g = convert_to_tb(int)
print(g)
