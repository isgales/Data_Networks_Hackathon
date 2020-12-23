#!/usr/bin/env python3
import struct
import socket
import threading

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
# global stop_game = True
# global stop_client = True
# global update_db = False
global num_of_clients = 0
stop_game = threading.Event()
stop_client = threading.Event()
update_db = threading.Event()


        print('Connected by', addr)
        while True:
            data = conn.recv(1024)
            if data:
                counter += 1
            conn.sendall(data)
    update_db.set()

def start_game():
    stop_game

def RunServerSocket():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.settimeout(10000)
        s.listen()
        client_names = []
        while num_of_clients < 4:
            conn, addr = s.accept()
            client_name = conn.recv(1024)
            client_names.append(client_name)
            threading.Thread(name="client_thread", target=RunClientSocket, args=(conn, database, num_of_clients%2, client_name))
            num_of_clients += 1
        start_game()

def RunClientSocket(__socket, database, group_num, client_name): 
    """
    param: database = {group_num : {client_id : score} }
    """
    counter = 0
    with __socket:
        # while TCP connection should be open.
        # wait for all clients to connect - main thread wakes them up.
        wait_for_clients()
        # while game is on
        while stop_game:
            data = __socket.recv(1024)
            if data:
                counter += 1
        # game is over, update database
        database[group_num][client_id] = counter
        # wait for all threads to update the db - main thread wakes them up.
        wait_update_db()
        # get final score from main thread, send it to client
        __socket.sendall(String)
    #end connection with client

def wait_update_db():
    num_of_clients += 1
    update_db.wait()

def wait_for_clients():
    stop_client.wait()