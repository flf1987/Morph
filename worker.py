import os
import md5
import time
import config
import struct
import subprocess
import xmlrpclib
from common import *

def recv_data_block(master_ip, master_snd_port):
    flag        = 0
    success     = 0
    block_data  = ''
    block_info  = block()

    s = socket.socket()         # Create a socket object
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024*10)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024*10)

    s.connect((master_ip, master_snd_port))

    try:
        while True:
            data = s.recv(1024*400)
            block_data = block_data + data
            if flag == 0 and len(block_data) >= struct.calcsize(block_format):
                flag = 1
                (block_info.task_id,   \
                 block_info.path_len,  \
                 block_info.file_path, \
                 block_info.block_no,  \
                 block_info.total_no,  \
                 block_info.bitrate,   \
                 block_info.width,     \
                 block_info.height,    \
                 block_info.size,      \
                 block_info.md5_val,
                 block_info.status)   = struct.unpack(block_format, block_data[0:struct.calcsize(block_format)])

            if not data:
                break


        if block_info.size == len(block_data) - struct.calcsize(block_format):
            print 'the file length is okay'
        else:
            print block_info.size
            print len(block_data) - struct.calcsize(block_format)
            print 'file length error'
            return None

        key = md5.new()
        key.update(block_data[struct.calcsize(block_format):])
        val = key.hexdigest()

        if block_info.md5_val == val:
            print 'the MD5 checksum is okay'
            path_len    = block_info.path_len
            base_name   = os.path.basename(block_info.file_path[0:path_len])
            new_path    = working_path + base_name

            block_info.file_path = new_path
            block_info.path_len  = len(new_path)


            f = open(new_path, 'wb')
            f.write(block_data[struct.calcsize(block_format):])
            f.close()
            s.send('okay')
            success = 1
        else:
            print 'md5 check fail'
            s.send('fail')
            success = 0

    except Exception, ex:
        print ex
        s.send('fail')
        success = 0

    finally:
        s.close()
        if success == 1:
            return block_info
        else:
            return None


def transcode_data(block_info):
    print 'transcode the video block into user requested block_format'
    #print block_info.task_id
    #print block_info.file_path

    dir_name        = os.path.dirname(block_info.file_path)
    base_name       = os.path.basename(block_info.file_path)
    (prefix,suffix) = os.path.splitext(base_name)
    new_path        = dir_name + '/' + prefix + '_new' + suffix

    cmd = "ffmpeg -y -i " + block_info.file_path + " -threads 4 -s 600x300 -strict -2 " + new_path

    print cmd
    os.system(cmd)

    #p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    #for line in p.stdout.readlines():
    #    print line,
    #retval = p.wait()

    #we still to check the result at here

    f       = open(new_path, 'rb')
    data    = f.read()
    f.close()

    key     = md5.new()
    key.update(data)
    md5_val = key.hexdigest()

    size    = os.path.getsize(new_path)

    block_info.file_path = new_path
    block_info.path_len  = len(new_path)
    block_info.size      = size
    block_info.md5_val   = md5_val
    block_info.status    = 0

    return block_info


def send_back_data(block_info, master_ip, master_rev_port):
    print 'send back the file:'

    try:
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024*10)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024*10)


        s.connect((master_ip, master_rev_port))

        f    = open(block_info.file_path, 'rb')
        data = f.read()
        f.close()

        pack = pack_block_info(block_info)
        block_data = pack + data
        print 'the sent back length:', len(block_data)

        sum = 0
        while True:
            cnt = s.send(block_data[sum: sum + 1024*400])
            sum = cnt + sum
            if cnt == 0:
                print 'finish sending back data:', sum
                break

        s.shutdown(gevent.socket.SHUT_WR)

        ret_msg = s.recv(10)
        print 'the return msg is:', ret_msg
        s.close()

    except Exception, ex:
        print ex
        s.close()


if __name__ == '__main__':

    master_ip       = config.master_ip
    master_rpc_port = config.master_rpc_port
    master_rev_port = config.master_rev_port
    master_snd_port = config.master_snd_port

    rpc_addr = "http://" + master_ip + ":" + master_rpc_port
    server = xmlrpclib.ServerProxy(rpc_addr)

    while True:
        num = server.get_blk_num()
        print "The current number of blocks in the master:", num
        if num == 0:
            time.sleep(1)
            continue

        block_info = recv_data_block(master_ip, master_snd_port)
        if block_info is not None:
            block_info = transcode_data(block_info)
        else:
            continue

        if block_info.status == 0:
            send_back_data(block_info, master_ip, master_rev_port)



