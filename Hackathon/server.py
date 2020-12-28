#!/usr/bin/env python3
import struct
import socket
import threading
import time
import logging
import traceback

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

SUBNET = '10.0.0.255'
UDP_PORT = 13117
LOCAL_HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
TCP_PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
num_of_clients = 0
waiting_semaphore = threading.Semaphore(0) # as number of clients
VictoryPrint = ""
WelcomePrint = ""
b_startgame = False
clients_wait = threading.Event()



def start_game(db):
  #  logging.debug('Starting game !')
    global WelcomePrint, b_startgame, VictoryPrint, clients_wait
    winner = 0
    WelcomePrint = "Welcome to Keyboard Spamming Battle Royale.\n"
    for group_id in db.keys():
        WelcomePrint += f"Group{group_id}:\n==\n"
        for name in db[group_id].keys():
            WelcomePrint += f"{name}\n"
    print(WelcomePrint)
    clients_wait.set()
    time.sleep(10)
    clients_wait.clear()
    b_startgame = False
    real_num_of_client = len(db[1].keys()) + len(db[2].keys())
    while num_of_clients != real_num_of_client:
        if real_num_of_client == 0:
            print("None clients")
            return
        check_change = len(db[1].keys()) + len(db[2].keys())
        if real_num_of_client != check_change:
            real_num_of_client = check_change
    logging.debug('game finished. calculating results')
    score_group_1 = sum(list(db[1].values()))
    score_group_2 = sum(list(db[2].values()))
    VictoryPrint = f"""Game over!
                    Group 1 typed in {score_group_1} characters. Group 2 typed in {score_group_2} characters."""
    if score_group_1 > score_group_2:
        winner = 1
    elif score_group_1 < score_group_2:
        winner = 2
    if winner == 0:
        VictoryPrint += """
                        It's a Tie!
                        """
    else:
        VictoryPrint += f"""   
                        Group {winner} wins!
                        Congratulations to the winners:
                        =="""
        for name in db[winner].keys():
            VictoryPrint += f"\n{name}"
    clients_wait.set()
    logging.debug('Release clients to send Victory print')


def send_UDP_Broadcast(start_time, SUBNET, udp_port, tcp_port):
    global num_of_clients, b_startgame
    addr = (SUBNET, udp_port)
    feedbeef = int('0xfeedbeef', 16)
    space = int('0x2', 16)
    port_tcp = int(hex(tcp_port), 16)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pack = struct.pack('!III', feedbeef, space, port_tcp)
    print("send udp pack  time: " +"  num: " + str(num_of_clients))
    while (time.time() - start_time < 10 and num_of_clients < 4):
        if b_startgame:
            break
        client_socket.sendto(pack, addr)
    print("stop Udp")
    client_socket.close()


def RunServerSocket(tcp_port, SUBNET,udp_port):
    global b_startgame, num_of_clients
    socket_pool =[]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((socket.gethostbyname(socket.gethostname()), tcp_port))
        #socket.setdefaulttimeout(10)
        start_time = time.time()   
        s.listen(4)  # added 4 -> clients
        Udp_thread = threading.Thread(target=send_UDP_Broadcast, args=(start_time, SUBNET, udp_port, tcp_port))
        Udp_thread.start()
        db = {1: {}, 2: {}}
        while num_of_clients < 1:
            s.settimeout(10-(time.time()-start_time))
            #print(10-(time.time()-start_time))
            #print("before connection")
            #time.sleep(6)
            #print(time.time()-start_time)
            conn, addr = s.accept()
            num_of_clients += 1
            conn.settimeout(10-(time.time()-start_time)) 
            print(f"New connection : [{addr}]")
            #logging.debug(f"New connection : [{add} ,{conn}]")
            #print("after recv")
            if len(db[1].keys()) < 2:
                group = 1
            elif len(db[2].keys()) < 2:
                group = 2
            if(num_of_clients < 4):
                threading.Thread(name="client_thread", target=RunClientSocket, args=(
                    conn, db, group, addr)).start()    
                socket_pool.append(conn)
        b_startgame = True
        s.settimeout(5000)
        for i in range(num_of_clients):
            waiting_semaphore.acquire()
        num_of_clients = 0
        start_game(db)
    except socket.timeout:
        print('server time out!')
        for t_socket in socket_pool:
            print(t_socket.fileno)
            if t_socket.fileno == -1:
                continue
            t_socket.sendall(b'break')  
    print('Main TCP thread closed.')


def wait():
    global clients_wait
    waiting_semaphore.release()
    clients_wait.wait()
    #print("awake...")


def RunClientSocket(__socket, db, group_num, address):
    """
    param: database = {group_num : {client_id : score} }
    """
    counter = 0
    global num_of_clients ,WelcomePrint ,VictoryPrint
    client_name = None
    try:
        data = __socket.recv(1024)
        #print(data)
        #time.sleep(2)
        client_name = data.decode("utf-8")
        db[group_num][client_name] = 0
        print(client_name)
        # while TCP connection should be open.
        # wait for all clients to connect - main thread wakes them up.
        wait()
        __socket.settimeout(5000)
        __socket.sendall(bytes(WelcomePrint,"utf-8"))
         #check!!!
        # while game is on
        start_time = time.time()
        while b_startgame:
            #print("in while")
            try:
                __socket.settimeout(10-(time.time()-start_time))
                data = __socket.recv(1)  # check size
                #print("wait recv while")
                char = data.decode("utf-8")
                print(f'{client_name} || {char}')
                if data:
                    counter += 1
            except socket.timeout:
                pass
            except ValueError:
                pass
        __socket.shutdown(socket.SHUT_RD)
        __socket.settimeout(5000)
        __socket.sendall(b'stop')
        # game is over, update database
        db[group_num][client_name] = counter
        # wait for all threads to update the db - main thread wakes them up.
        num_of_clients += 1
        wait()
        # get final score from main thread, send it to client
        __socket.sendall(bytes(VictoryPrint,"utf-8"))
        __socket.shutdown(socket.SHUT_WR)
        #print(f'{__socket} sended Victory print')
    except socket.timeout:
        traceback.print_exc()
        print(f'disconnect: timeout {client_name}')
    except:
        traceback.print_exc()
        print(f'disconnect: else {client_name}')  
    # end connection with client
    if client_name is None:
        return
    num_of_clients -= 1
    db[group_num].pop(client_name)
    #print(f"{client_name} as disconnected. closing socket {__socket}.")
    __socket.close()


# def wait_for_clients():
#     stop_client.wait()

while True:
    num_of_clients = 0
    VictoryPrint = ""
    WelcomePrint = ""
    b_startgame = False
    RunServerSocket(TCP_PORT, SUBNET,UDP_PORT)
