#!/usr/bin/env python3
import struct
import socket
import threading
import time
import logging
from multiprocessing.pool import Pool

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
num_of_clients1 = 0
VictoryPrint = ""
WelcomePrint = ""
b_startgame = True
clients_wait = threading.Event()


def start_game(db):
    logging.debug('Starting game !')
    global WelcomePrint, b_startgame, VictoryPrint, clients_wait
    winner= 0
    WelcomePrint = "Welcome to Keyboard Spamming Battle Royale.\n"
    for group_id in db.keys():
        WelcomePrint += "Group{group_id}:\n==\n"
        for name in db[group_id].keys():
            WelcomePrint += "{name}\n"
    clients_wait.set()
    time.sleep(10)
    clients_wait.clear()
    b_startgame = False
    real_num_of_client = len(db[1].values()) + len(db[2].values())
    while num_of_clients1 != real_num_of_client :
        check_change = len(db[1].values()) + len(db[2].values())
        if real_num_of_client != check_change:
            real_num_of_client = check_change
    logging.debug('game finished. calculating results')
    score_group_1 = sum(db[1].values()[0])
    score_group_2 = sum(db[2].values())
    VictoryPrint = """Game over!
                    Group 1 typed in {score_group_1} characters. Group 2 typed in {score_group_2} characters."""
    if score_group_1 > score_group_2:
        winner = 1
    elif score_group_1 < score_group_2:
        winner = 2
    if winner == 0:
        VictoryPrint +="""
                        It's a Tie!
                        """
    else:
        VictoryPrint += """   
                        Group {winner} wins!
                        Congratulations to the winners:
                        =="""
        for name in db[winner].keys():
            VictoryPrint +="\n{name}"
    clients_wait.set()
    logging.debug('Release clients to send Victory print')

def RunServerSocket(port, pool):
    global b_startgame, num_of_clients1
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((socket.gethostbyname(), port))
        s.settimeout(10000)
        s.listen(4)             ## added 4 -> clients
        db = {1:{},2:{}}
        while num_of_clients1 < 4:
            conn, addr = s.accept()
            logging.debug("New connection : [{add} ,{conn}]")
            data = conn.recv(1024)
            client_name = data.decode("utf-8")
            if len(db[1].keys()) < 2:
                group = 1
                db[group][client_name] = [0] 
            elif len(db[2].keys()) < 2:
                group = 2
                db[group][client_name] = [0]         
            if(num_of_clients1 < 4):
                db[group][client_name].append(threading.Thread(name="client_thread", target=RunClientSocket, args=(conn, db , num_of_clients1%2, client_name)).start())
        s.settimeout()
        num_of_clients1 = 0
        start_game(db)
    except TimeoutError:
        for group in db.keys():
            for client in db[group].keys():
                db[group][client][1]._stop().set()
            
            

    logging.debug('Main TCP thread closed.')

def wait():
    global num_of_clients1 
    num_of_clients1 += 1
    clients_wait.wait()

def RunClientSocket(__socket, db, group_num, client_name): 
    """
    param: database = {group_num : {client_id : score} }
    """
    counter = 0
    global num_of_clients1
    with __socket:
        # while TCP connection should be open.
        # wait for all clients to connect - main thread wakes them up.
        wait()
        # while game is on
        while b_startgame:
            data = __socket.recv(1) ### check size
            if data:
                counter += 1
        # game is over, update database
        db[group_num][client_name][0] = counter
        # wait for all threads to update the db - main thread wakes them up.
        wait()
        # get final score from main thread, send it to client
        __socket.sendall(VictoryPrint)
        logging.debug('{__socket} sended Victory print')
    #end connection with client
    num_of_clients1 -= 1
    db[group_num].pop(client_name)
    logging.debug("{client_name} as disconnected. closing socket {__sicket}.")



# def wait_for_clients():
#     stop_client.wait()


while True:
    num_of_clients1 = 0
    VictoryPrint = ""
    WelcomePrint = ""
    b_startgame = True
    pool = Pool(processes=4)
    RunServerSocket(PORT, pool)