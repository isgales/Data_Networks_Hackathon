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

def acquireSemaphore(db):
    global waiting_semaphore
    real_num_of_client = len(list(db[1].keys())) + len(list(db[2].keys()))
    for i in range(real_num_of_client):
        waiting_semaphore.acquire()
    waiting_semaphore._value = 0

def setWelcomeMsg(db):
    global WelcomePrint
    WelcomePrint = "Welcome to Keyboard Spamming Battle Royale.\n"
    for group_id in db.keys():
        WelcomePrint += f"Group{group_id}:\n==\n"
        for name in db[group_id].keys():
            WelcomePrint += f"{name}"
    WelcomePrint += "\nStart pressing keys on your keyboard as fast as you can!!"
    
def setVictoryMsg(score_group_1, score_group_2, db):
    global VictoryPrint
    VictoryPrint = f"Game over!\nGroup 1 typed in {score_group_1} characters. Group 2 typed in {score_group_2} characters.\n"
    winner = 0
    if score_group_1 > score_group_2:
        winner = 1
    elif score_group_1 < score_group_2:
        winner = 2
    if winner == 0:
        VictoryPrint += "It's a Tie!\n"
    else:
        VictoryPrint += f"Group {winner} wins!\nCongratulations to the winners:\n==\n"
        for name in db[winner].keys():
            VictoryPrint += f"{name}"

def checkForClients(db):
    real_num_of_client = len(db[1].keys()) + len(db[2].keys())
    return not real_num_of_client == 0 
    
def start_game(db):
    global WelcomePrint, b_startgame, VictoryPrint, clients_wait, waiting_semaphore
    setWelcomeMsg(db)
    # print(WelcomePrint)
    # notify all client threads to start the game
    clients_wait.set()
    # main thread sleeps for 10 seconds while clients threads play
    if not checkForClients(db):
        return
    time.sleep(10)
    clients_wait.clear()
    b_startgame = False
    # game is finished, calculate results
    real_num_of_client = len(db[1].keys()) + len(db[2].keys())
    # print('num of clients: ', num_of_clients)
    # print('real num of clients: ', real_num_of_client)
    # while num_of_clients != real_num_of_client:
    #     check_change = len(db[1].keys()) + len(db[2].keys())
    #     if real_num_of_client != check_change:
    #         real_num_of_client = check_change
    # waiting_semaphore = threading.Semaphore(0)
    acquireSemaphore(db)
    score_group_1 = sum(list(db[1].values()))
    score_group_2 = sum(list(db[2].values()))
    setVictoryMsg(score_group_1, score_group_2, db)
    clients_wait.set()


def send_UDP_Broadcast(start_time, SUBNET, udp_port, tcp_port):
    global num_of_clients, b_startgame
    # build the packet to be sent.
    addr = (SUBNET, udp_port)
    feedbeef = int('0xfeedbeef', 16)
    space = int('0x2', 16)
    port_tcp = int(hex(tcp_port), 16)
    pack = struct.pack('!III', feedbeef, space, port_tcp)
    # set the broadcast socket.
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # print("send udp pack  time: " +"  num: " + str(num_of_clients))
    # broadcast for 10 seconds, once each second.
    while (time.time() - start_time < 10):
        client_socket.sendto(pack, addr)
        time.sleep(1)
    client_socket.close()


def acceptClients(start_time, db, accepting_socket, socket_pool):
    global num_of_clients
    # run until 10 seconds pass from the moment the server started
    while (time.time()-start_time) < 10:
        # there is still available spot for new client
        if(num_of_clients < 2):
            # accept client
            accepting_socket.settimeout(10-(time.time()-start_time))
            conn, addr = accepting_socket.accept()
            num_of_clients += 1
            conn.settimeout(10-(time.time()-start_time)) 
            print(f"New connection : [{addr}]")
            # assign group
            if len(db[1].keys()) < 1:
                group = 1
            elif len(db[2].keys()) < 1:
                group = 2
            threading.Thread(name="client_thread", target=RunClientSocket, args=(
                conn, db, group, addr)).start()    
            socket_pool.append(conn)

def RunServerSocket(tcp_port, SUBNET,udp_port):
    global b_startgame, num_of_clients, waiting_semaphore
    socket_pool =[]
    db = {1: {}, 2: {}}
    try:
        # Set the TCP socket to accept the clients
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = socket.gethostbyname(socket.gethostname())
        s.bind((ip_address, tcp_port))  
        s.listen(2)  # added 4 -> clients
        print(f'Server started, listening on IP address {ip_address}')
        start_time = time.time() 
        # start sending UDP broadcast
        Udp_thread = threading.Thread(target=send_UDP_Broadcast, args=(start_time, SUBNET, udp_port, tcp_port))
        Udp_thread.start()
        # accept clients
        acceptClients(start_time, db, s, socket_pool)
        b_startgame = True
        # print ('before semaphore - serversocket: ', db)
        acquireSemaphore(db)
        num_of_clients = 0
        # all client are ready to play (resigitered in db) - still waiting
        # print ('before start game - serversocket: ', db)
        start_game(db)
        # print('before shutdown server socket')
        # s.shutdown(socket.SHUT_RDWR)   
    except socket.timeout:
        print('server time out!')
    acquireSemaphore(db)
    for t_socket in socket_pool:
        if t_socket.fileno != -1:
            t_socket.close()
    s.close()
    print('Game over, sending out offer requests...')


def wait():
    global clients_wait, waiting_semaphore
    waiting_semaphore.release()
    clients_wait.wait()
    #print("awake...")

def registerClient(__socket, db, group_num):
    data = __socket.recv(1024)
    #print(data)
    #time.sleep(2)
    client_name = data.decode("utf-8")
    db[group_num][client_name] = 0
    print(f'{client_name} is registered to db in {group_num}')
    return client_name

def RunClientSocket(__socket, db, group_num, address):
    """
    param: database = {group_num : {client_id : score} }
    """
    counter = 0
    global num_of_clients ,WelcomePrint ,VictoryPrint, waiting_semaphore
    client_name = None
    try:
        # print ('before register - clientsocket: ', db)
        client_name = registerClient(__socket, db, group_num)
        # print ('after register - clientsocket: ', db)
        # while TCP connection should be open.
        # wait for all clients to connect - main thread wakes them up.
        wait()

        __socket.sendall(bytes(WelcomePrint,"utf-8"))
        # while game is on
        start_time = time.time()
        while b_startgame:
            #print("in while")
            try:
                __socket.settimeout(10-(time.time()-start_time))
                data = __socket.recv(1)  # check size
                #print("wait recv while")
                char = data.decode("utf-8")
               # print(f'{client_name} || {char}')
                if data:
                    counter += 1
            except socket.timeout:
                pass
            except ValueError:
                pass
        # print('before client socket shutdown after game')
        # __socket.shutdown(socket.SHUT_WR)
        # game is over, update database
        db[group_num][client_name] = counter
        # wait for all threads to update the db - main thread wakes them up.
        num_of_clients += 1
        wait()
        # get final score from main thread, send it to client
        # print('before send victory: server side', __socket, VictoryPrint)
        __socket.sendall(bytes(VictoryPrint,"utf-8"))  
        # print('before closing: server side')
       # __socket.shutdown(socket.SHUT_RD)
        __socket.close()
        waiting_semaphore.release()
        #print(f'{__socket} sended Victory print')
    except socket.timeout:
        __socket.close()
        print(f'disconnect: timeout {client_name}')
    except:
        __socket.close()
        traceback.print_exc()
        print(f'disconnect: else {client_name}')  
    # end connection with client
    if client_name is None:
        return
    num_of_clients -= 1
    db[group_num].pop(client_name)
    # waiting_semaphore.release()
    #print(f"{client_name} as disconnected. closing socket {__socket}.")
   


# def wait_for_clients():
#     stop_client.wait()

while True:
    num_of_clients = 0
    VictoryPrint = ""
    WelcomePrint = ""
    b_startgame = False
    RunServerSocket(TCP_PORT, SUBNET,UDP_PORT)
    clients_wait.clear()