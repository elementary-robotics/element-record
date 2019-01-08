#
# record.py
#   Simple recorder and viewer element
#
from atom import Element
from atom.messages import Response

def hello_cmd(data):
    print(data)
    return Response(data + " world", serialize=True)

if __name__ == '__main__':
    elem = Element("record")
    elem.command_add("hello", hello_cmd, timeout=1000, deserialize=True)
    elem.command_loop()
