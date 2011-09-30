


class Service(object):

    name = None
    running = 0

    def start(self):
        self.running = 1

    def stop(self):
        self.running = 0


class ServiceCollection(Service):

    def __self__(self):
        self.services = []

    def __iter__(self):
        return iter(self.services)

    def start(self):
        Service.start(self)
        for service in self:
            self.start()

    def stop(self):
        Service.stop(self)
        services = list(self)
        services.reverse()
        for service in services:
            service.stop() #this can block if the service stop needs to do
                           #things like save data or something
