def on_starting(server):
    from main import start_mqtt
    start_mqtt()


def post_fork(server, worker):
    # main's startup queries run in the master, so each forked worker inherits the master's pooled
    # connection. Two processes on one socket corrupt each other's queries; forget it without closing it.
    from configs.database import engine
    engine.dispose(close=False)


timeout = 300
