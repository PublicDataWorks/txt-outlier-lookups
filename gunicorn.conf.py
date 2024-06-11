def post_worker_init(worker):
    from main import start_mqtt
    start_mqtt()
