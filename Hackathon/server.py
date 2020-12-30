#!/usr/bin/env python3
import struct
import socket
import threading
import time
import logging
import traceback


SUBNET = '10.0.0.255'
UDP_PORT = 13117
TCP_PORT = 65432 # Port to listen on (non-privileged ports are > 1023)

# Global variables.
num_of_clients = 0
waiting_semaphore = threading.Semaphore(0) 
VictoryPrint = ""
WelcomePrint = ""
b_startgame = False
clients_wait = threading.Event()
num_of_clients_limit = 4

def acquireSemaphoreByDB(db):
    """
    Function acquire the global semaphore the number of times as the number of clients at the moment
    in the DB.
    param: db - the DB that holds the registered clients.
    """
    global waiting_semaphore
    real_num_of_client = len(list(db[1].keys())) + len(list(db[2].keys()))
    for i in range(real_num_of_client):
        waiting_semaphore.acquire()
    waiting_semaphore._value = 0

def acquireSemaphoreBySockets(socket_pool):
    """
    Function acquire the global semaphore the number of times as the number of -open- client sockets at the moment
    in the socket pool.
    param: socket_pool - list of all client sockets in the program.
    """
    global waiting_semaphore
    for t_socket in socket_pool:
        # if client socket is open
        if t_socket.fileno() != -1: 
            waiting_semaphore.acquire()
    waiting_semaphore._value = 0

def setWelcomeMsg(db):
    """
    Function assembel the welcome message to be sent to the clients.
    param: db - the DB that holds the registered clients.
    """
    global WelcomePrint
    WelcomePrint  = r"""
       ____    _    ______   __
      | __ )  / \  | __ ) \ / /
      |  _ \ / _ \ |  _ \\ V / 
      | |_) / ___ \| |_) || |  
      |____/_/   \_\____/ |_|  
           ____  ___ _____     
          / ___|/ _ \_   _|    
         | |  _| | | || |      
         | |_| | |_| || |      
          \____|\___/ |_|      
               _    ____ _  __ 
              / \  / ___| |/ / 
             / _ \| |   | ' /  
            / ___ \ |___| . \  
           /_/   \_\____|_|\_\ 
    

https://www.youtube.com/watch?v=X53ZSxkQ3Ho&ab_channel=SirMixALotVEVO"""
    WelcomePrint += "\n\nWelcome to Keyboard Spamming Battle Royale.\n"
    # for each group
    for group_id in db.keys():
        WelcomePrint += f"Group{group_id}:\n==\n"
        # for each client
        for ID in db[group_id].keys():
            name = db[group_id][ID][0]
            WelcomePrint += f"{name}"
    WelcomePrint += "\nStart pressing keys on your keyboard as fast as you can!!"
    
def setVictoryMsg(score_group_1, score_group_2, db):
    """
    Function assembel the victory message to be sent to the clients.
    param: score_group_1 - Group 1 score.
    param: score_group_2 - Group 2 score.
    param: db - the DB that holds the registered clients.
    """
    global VictoryPrint
    VictoryPrint = f"Game over!\nGroup 1 typed in {score_group_1} characters. Group 2 typed in {score_group_2} characters.\n"
    winner = 0
    # set the winning group
    if score_group_1 > score_group_2:
        winner = 1
    elif score_group_1 < score_group_2:
        winner = 2
    if winner == 0:
        VictoryPrint += "It's a Tie!\n"
    else:
        VictoryPrint += f"Group {winner} wins!\nCongratulations to the winners:\n==\n"
        for ID in db[winner].keys():
            name = db[winner][ID][0]
            VictoryPrint += f"{name}"

def checkForClients(db):
    """
    Function check if there are any registered clients in the DB at the moment.
    param: db - the DB that holds the registered clients.
    return: boolean - are there any registered clients.
    """
    real_num_of_client = len(db[1].keys()) + len(db[2].keys())
    return not real_num_of_client == 0 
    
def start_game(db):
    """
    Function simulates the game from the server side.
    Set the welcome msg and send it.
    Wait for 10 seconds for client to play.
    Calculate the results and assembel victory msg. send it to all clients.
    param: db - the DB that holds the registered clients.
    """
    global WelcomePrint, b_startgame, VictoryPrint, clients_wait, waiting_semaphore
    setWelcomeMsg(db)
    # notify all client threads to start the game
    clients_wait.set()
    # if there are no clients, stop the game.
    if not checkForClients(db):
        return
    # main thread sleeps for 10 seconds while clients threads play
    time.sleep(10)
    clients_wait.clear()
    b_startgame = False
    acquireSemaphoreByDB(db)
    # game is finished, calculate results and send to all clients.
    score_group_1 = sum([id[1] for id in db[1].values()])
    score_group_2 = sum([id[1] for id in db[2].values()])
    setVictoryMsg(score_group_1, score_group_2, db)
    clients_wait.set()


def send_UDP_Broadcast(start_time, SUBNET, udp_port, tcp_port):
    """
    Function create UDP socket, assembel offer packet, and broadcast offers to all clients in the SUBNET.
    param: start_time - the moment the counting of 10 seconds started.
    param: SUBNET - the ip address to broadcast.
    param: udp_port - the port which the server listens at.
    param: tcp_port - the port which the server will open TCP connection with the future clients.
    """
    global num_of_clients, b_startgame
    addr = (SUBNET, udp_port)
    # Format of the msg: I - 4 bytes, b - 1 byte, H - 2 bytes.
    # Message components: Magic cookie, space, tcp port.
    pack = struct.pack('>IbH', 0xfeedbeef, 0x2, tcp_port)
    # set the broadcast socket.
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    # broadcast for 10 seconds, once each second.
    while (time.time() - start_time < 10):
        client_socket.sendto(pack, addr)
        time.sleep(1)
    client_socket.close()


def acceptClients(start_time, db, accepting_socket, socket_pool):
    """
    Function responsible for accepting clients in the TCP port.
    Once connection is established, the function sets a thread to handle the client and start it.
    param: start_time - the moment the counting of 10 seconds started.
    param: db - the DB that holds the registered clients.
    param: accepting_socket - the main TCP socket which accepts clients.
    param: socket_pool - the list which holds all sockets in program.
    """
    global num_of_clients, num_of_clients_limit
    ID = 0 # each client owns unique ID which will be used in the DB.
    # run until 10 seconds pass from the moment the server started
    while (time.time()-start_time) < 10:
        # there is still available spot for new client
        if num_of_clients < num_of_clients_limit:
            # sync the timeout of socket with the 10 seconds deadline.
            accepting_socket.settimeout(10-(time.time()-start_time))
            try:
                # accept client
                conn, addr = accepting_socket.accept()
            except socket.timeout:
                break
            try:
                # sync the timeout of new client socket with the 10 seconds deadline.
                conn.settimeout(9.9-(time.time()-start_time)) 
            except ValueError:
                conn.close()
                break
            num_of_clients += 1
            # print new connection, with address of new client.
            print(f"New connection : [{addr}]")
            # assign group
            if num_of_clients%2 == 1:
                group = 1
            else:
                group = 2
            # set client thread and start it.
            threading.Thread(name="client_thread", target=RunClientSocket, args=(
                conn, db, group, ID, addr)).start()   
            ID += 1 
            socket_pool.append(conn)

def RunServerSocket(tcp_port, SUBNET,udp_port):
    """
    Function responsible for all the server socket actions during the program.
    param: tcp_port - the port which the server will open TCP connection with the future clients.
    param: SUBNET - the ip address to broadcast.
    param: udp_port - the port which the server listens at while broadcasting offers..
    """
    global b_startgame, waiting_semaphore
    socket_pool =[]
    db = {1: {}, 2: {}}
    try:
        # Set the TCP socket to accept the clients
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        ip_address = socket.gethostbyname(socket.gethostname())
        s.bind((ip_address, tcp_port))  
        s.listen(1)  
        print(f'Server started, listening on IP address {ip_address}')
        start_time = time.time() 
        # start sending UDP broadcast
        Udp_thread = threading.Thread(target=send_UDP_Broadcast, args=(start_time, SUBNET, udp_port, tcp_port))
        Udp_thread.start()
        # accept clients
        acceptClients(start_time, db, s, socket_pool)
        b_startgame = True
        acquireSemaphoreBySockets(socket_pool)
        # All clients are registered and ready to play, start game.
        start_game(db)
    except socket.timeout:
        print('server time out!')
    # Game is finished, close all sockets that should be closed.
    s.close()    
    acquireSemaphoreBySockets(socket_pool)
    for t_socket in socket_pool:
        if t_socket.fileno() != -1:
            t_socket.close()
    if s.fileno() != -1:
        s.close()
    print('Game over, sending out offer requests...')


def wait():
    """
    Function is responsible to sync all client threads with the main server thread during the program.
    Each client which enters the function do 2 things:
    1. Release the semaphore - let the server know the client finished its current part.
    2. Wait - wait for all other clients to finish as well.
    """
    global clients_wait, waiting_semaphore
    waiting_semaphore.release()
    clients_wait.wait()

def registerClient(__socket, db, group_num, ID):
    """
    Function registers new client to the DB.
    param: __socket - the client's socket.
    param: db - the DB that holds the registered clients.
    param: group_num - the client's group number.
    param: ID - the client's ID.
    return: client's name as was given from the client.
    """
    data = __socket.recv(1024)
    client_name = data.decode("utf-8")
    db[group_num][ID] = [client_name,0]
    return client_name

def RunClientSocket(__socket, db, group_num, ID, address):
    """
    Function responsible for all client actions during the game.
    param: __socket - the client's socket.
    param: database = {group_num : { ID : [client_id, score] } }. Holds all registered clients.
    param: group_num - the client's group number.
    param: ID - the client's ID.
    param: address - the client's ip address.
    """
    counter = 0
    global num_of_clients ,WelcomePrint ,VictoryPrint, waiting_semaphore, b_startgame
    client_name = None
    try:
        # try register the client while queue.
        try:
            client_name = registerClient(__socket, db, group_num, ID)
            data = __socket.recv(1024)
        except socket.timeout:
            pass
        except:
            __socket.close()
            if b_startgame:
                # Client disconnected after his registration. The server will consider it when acquiring the
                # semaphore, so it should release it before finish the thread.
                waiting_semaphore.release()
            # pop out from DB - client didn't even play.
            db[group_num].pop(ID)
            return
        # wait for all clients to connect - main thread wakes them up.
        wait()
        # while TCP connection should be open.
        __socket.settimeout(12)
        __socket.sendall(bytes(WelcomePrint,"utf-8"))
        # while game is on
        start_time = time.time()
        while b_startgame:
            try:
                # get the client messages and count them.
                data = __socket.recv(1)  
                if data:
                    counter += 1
            except socket.timeout:
                pass
            except:
                # if client disconnected during the game, keep it's score in the DB.
                db[group_num][ID][1] = counter
                __socket.close()
                wait()
                return
        # game is over, update database
        db[group_num][ID][1] = counter
        # wait for all threads to update the db - main thread wakes them up.
        wait()
        # get final score from main thread, send it to client
        __socket.sendall(bytes(VictoryPrint,"utf-8"))  
        # Waiting for FIN flag from the client, so we know it finished the connection.
        while True:
            data = __socket.recv(1024)
            if data == b'':
                break
        __socket.close()
        wait()
    except:
        wait()
    # if client disconnected before registration, return.
    if client_name is None:
        return
  
"""
Main run of the server. 'While True' because of the demand that the server runs until the user stops the program.
Initialize the keyboard game every cycle.
"""
while True:
    num_of_clients = 0
    VictoryPrint = ""
    WelcomePrint = ""
    b_startgame = False
    RunServerSocket(TCP_PORT, SUBNET,UDP_PORT)
    clients_wait.clear()