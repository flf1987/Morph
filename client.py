import config
from common import *
from xmlrpclib import ServerProxy

if __name__ == "__main__":

    master_ip       = config.master_ip
    master_rpc_port = config.master_rpc_port
    rpc_addr = "http://" + master_ip + ":" + master_rpc_port
    server = ServerProxy(rpc_addr)

    #please replace it with the program command line
    file_path = '/home/guanyu/Videos/yanjingshe_2.mp4'
    width     = "%04d" % int("400")
    height    = "%04d" % int("400")

    ret = server.add_trans_task(file_path, "", width, height)
