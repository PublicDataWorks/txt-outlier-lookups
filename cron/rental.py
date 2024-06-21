from subprocess import PIPE, Popen


def fetch_data():
    try:
        Popen(["./rental.sh"], shell=True, stdin=PIPE, stderr=PIPE)
    except Exception as e:
        print(e)
