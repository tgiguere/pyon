
from pyon.net import messaging





class Container(object):

    def start(self):
        """
        """

    def stop(self):
        """
        """










def makeNode(config):
    """
    blocking construction and connection of node
    """
    log.debug("In makeNode")
    node = messaging.NodeB()
    messagingParams = config.server.amqp
    log.debug("messagingParams: %s" % str(messagingParams))
    credentials = messaging.PlainCredentials(messagingParams["username"], messagingParams["password"])
    conn_parameters = messaging.ConnectionParameters(host=messagingParams["host"], virtual_host=messagingParams["vhost"], port=messagingParams["port"], credentials=credentials)
    connection = messaging.SelectConnection(conn_parameters , node.on_connection_open)
    ioloop_process = gevent.spawn(ioloop, connection)
    #ioloop_process = gevent.spawn(connection.ioloop.start)
    node.ready.wait()
    return node, ioloop_process
 
