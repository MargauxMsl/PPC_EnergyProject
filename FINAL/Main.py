import time
from prompt_toolkit import prompt
import sysv_ipc
import os
import select
import signal
import random
import signal
import socket
#import matplotlib.pyplot as plt
import threading
import multiprocessing
import concurrent.futures
from multiprocessing import Process, Value, Array, Lock, Barrier

# CONSTANTS -----------------------------------------------------

NB_THREADS=10
HOST=""
PORT=8787
ATTENUATION = 0.99
INT_COEFF = [ 0.2, 0.04]
EXT_COEFF = [1.006, 1.5]
mutex = multiprocessing.Lock()

# MESSAGE QUEUES-------------------------------------------------

key1 =int(random.random()*1000)
key2 =int(random.random()*1000)
mq_ask = sysv_ipc.MessageQueue(key1, sysv_ipc.IPC_CREAT)
mq_give = sysv_ipc.MessageQueue(key2, sysv_ipc.IPC_CREAT)

# GLOBAL---------------------------------------------------------

externalFactor=[0 for k in range(0,6)]
banque=1000
marketStock=100
price=0.14
run = True


# MARKET --------------------------------------------------------

def market(barrier_sock):

    # Opening Signals
    signal.signal(signal.SIGUSR1, externalHandler)
    signal.signal(signal.SIGUSR2, externalHandler)
    signal.signal(signal.SIGRTMIN, externalHandler)
    signal.signal(signal.SIGRTMIN+1, externalHandler)
    signal.signal(signal.SIGRTMIN+2, externalHandler)
    signal.signal(signal.SIGRTMIN+3, externalHandler)


    #Open connection with houses
    houseSocketThread=threading.Thread(target=houseSocket)
    houseSocketThread.start()

    #External events
    external=Process(target=externalFactorsProcess)
    external.start()

    day=1

    while day<=nbDays:
        print("----------------- DAY ", day, "---------------" )
        global price
        price=priceEvolve()
        print("The price of the energy today: ", price)
        print("Market stock :", marketStock, "Market banque: ", banque)
        day += 1
        barrier_sock.wait()
        
    # os.kill(os.getpid(), signal.SIGKILL)

# EXTERNAL SIGNAL HANDLERS 

def externalHandler(signum, frame):
    if signum == signal.SIGUSR1:
        event="war"
        if externalFactor[0]==0:
            externalFactor[0]=1
        else:
            externalFactor[0]=0
    elif signum == signal.SIGUSR2:
        event = "nuclear accident"
        if externalFactor[1]==0:
            externalFactor[1]=1
        else:
            externalFactor[1]=0
    elif signum == 35:
        event= "Elon musk posts a meme"
        if externalFactor[2]==0:
            externalFactor[2]=1
        else:
            externalFactor[1]=1
    elif signum == 36:
        event="drought"
        if externalFactor[3]==0:
            externalFactor[3]=1
        else:
            externalFactor[3]=0
    elif signum == 37:
        event="finally a break"
        if externalFactor[4]==0:
            externalFactor[4]=1
        else:
            externalFactor[4]=1
    elif signum == 38: 
        event = "no more lithium"
        if externalFactor[5]==0:
            externalFactor[5]=1
        else:
            externalFactor[5]=0
    print("------- ALARME EVENT ----", event)

# HOUSE SOCKET CONNECTION

def houseSocket():

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as market_socket:
        market_socket.setblocking(False)
        market_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        market_socket.bind((HOST, PORT))
        market_socket.listen(NB_THREADS)

        #création d'une pool de threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=NB_THREADS) as threadPool:
            while run :
                readable, writable, error = select.select([market_socket], [], [], 1)
                if market_socket in readable:
                    house_socket, address = market_socket.accept()
                    threadPool.submit(house_handler, house_socket, address,)


# HOUSE CONNEXION HANDLER

def house_handler(socket, address):
    with socket as home:
        received=False
        while not received:
            try:
                dataReceived=home.recv(1024).decode('utf-8')
                received=True
            except:
                time.sleep(1)
                pass
        request=dataReceived.split(",")
        while True:
            if request[0]=="SELL":
                mutex.acquire()
                feedback=marketBuyFromHouse(float(request[1]))
                mutex.release()
                break
            if request[0]=="BUY":
                mutex.acquire()
                feedback=marketSellToHouse(float(request[1]))
                mutex.release()
                break
            else:
                time.wait()
        home.send(feedback.encode('utf-8'))
        home.close()


# MARKET FUNCTIONS

def marketSellToHouse(request):
    global marketStock, banque
    if request <= marketStock:
        quantity = request
        cost = quantity * price
        marketStock -= quantity
        banque += cost 
    else:
        quantity = marketStock
        marketStock = 0
        banque += quantity * price 
    return (str(price) + "," + str(quantity))

def marketBuyFromHouse(request):
    global marketStock, banque
    cost=request*price
    if cost <= banque:
        quantity=request
        banque-=cost
    else:
        quantity=banque//price
        banque=0
    marketStock += quantity
    return (str(price)+","+str(quantity))

def priceEvolve():
    global price
    price=ATTENUATION*price+sum([a*f for a,f in zip(INT_COEFF, internal_factor )])+sum([b*u for b,u in zip(EXT_COEFF,externalFactor)])
    return price


# EXTERNAL FACTORS CHILD PROCESS----------------------------------------------------------------------------------

def externalFactorsProcess():
    while True:
        event = random.choice(["war", "nuclear accident", "Elon musk posts a meme", "drought", "", "lithium depletion"])
        if event =="war":
            signalType=signal.SIGUSR1
        elif event == "nuclear accident":
            signalType=signal.SIGUSR2
        elif event == "Elon Musk posts a meme":
            signalType=signal.SIGRTMIN+1
        elif event == "drought":
            signalType=signal.SIGRTMIN+2
        elif event == "" :
            signalType=signal.SIGRTMIN+3
        elif event == "lithium depletion":
            signalType=signal.SIGRTMIN+4
        else:
            signalType=signal.SIGRTMIN+3
        os.kill(os.getppid(), signalType)
        breakTime = random.uniform(5, 10)
        time.sleep(breakTime)


# HOME -------------------------------------------------------------------------------------------------------
startClock = time.time()
dayTime = 3
initIncome = 100
initStock = 10

def home(index,barrier,barrier_sock):
    global startClock
    global initIncome
    global initStock

    pid = os.getpid()
    income = initIncome
    energy_trade_policy=random.randint(1,3) # 1 : always give; 2 : always sell; 3 : mix
    consumption_rate=random.uniform(9.0,15.0)
    production_rate=random.uniform(4.0,17.0)
    stock = random.uniform(1.0, 7.0)
    asset = random.choice(["Solar panel", "Generator", "Wind turbine", "Votes for Trump"])
    # The asset implies a given advantage (or misadvantage)
    if asset == "Solar panel":
        production_rate += 0.7
    if asset == "Generator":
        production_rate += 0.5
    if asset == "Wind turbine":
        production_rate += 1
    if asset == "Votes for Trump":
        production_rate -= 0.1

    while True:

        homeDisplay(index,production_rate, consumption_rate, stock, energy_trade_policy, income, asset)

        # The stock is decremented everyday due to the consumption of energy
        stock -= 0.1 * consumption_rate

        # At the end of the day, the energy variables are updated 
        consumption_rate = 1.1 * consumption_rate
        stock = production_rate - consumption_rate
        startClock=time.time()
        endClock=time.time()

        # Actions of a day
        while endClock-startClock<dayTime:
            if stock < 0 :
                ask_for_energy(-stock,index, pid)
                result=str(receive_energy(index,pid,stock))
                amountSent=float(result.split(",")[1])
                actualPrice=float(result.split(",")[0])
                stock += amountSent
                income -= amountSent*actualPrice

            time.sleep(1)

            if stock > 0 :
                result=str(send_energy(energy_trade_policy, index,stock))
                amountSent=float(result.split(",")[1])
                actualPrice=float(result.split(",")[0])
                stock -= amountSent
                income += amountSent*actualPrice
            

            if stock==0:
                endClock=time.time()
                while endClock-startClock<dayTime:
                    time.sleep(1)
                    endClock=time.time()
                    pass

            endClock=time.time()

        if stock<0:
            result=buy_to_market(index, -stock)
            amountSent=float(result.split(",")[1])
            actualPrice=float(result.split(",")[0])
            stock += amountSent
            income -= amountSent*actualPrice

        barrier.wait()
        barrier_sock.wait()
    

def homeDisplay(index,production_rate, consumption_rate, stock, energy_trade_policy, income, asset):
    print(f'Home {index} :\n Production rate : {production_rate} kwH\n Consumption rate : {consumption_rate} kwH \n Stock : {stock}\n Energy trade policy : {energy_trade_policy}\nCurrent balance : {income}\nAsset :', asset,'\n')

# Function that allows homes to ask for energy in case of shortage

def ask_for_energy(amount_needed,index,pid):
    request = str(amount_needed)
    request += " "
    request += str(pid)
    mq_ask.send(request, type = 1)


# Function that allows homes to receive energy after asking for it 

def receive_energy(index,pid,stock):

    global startClock
    endClock = time.time()
    received = False
    energy_received=0
    while (endClock-startClock<dayTime and not received):
        try:
            energy,t = mq_give.receive(block=False,type = int(pid))
            energy_received = float(energy.decode())
            received = True
        except sysv_ipc.BusyError:
            time.sleep(1)
            pass
        endClock = time.time()
    return (str(0)+","+str(energy_received))
# Function that allows homes that have more energy to give it away to needing homes

def give_energy(index, stock):
    energy_available=0
    endClock = time.time()
    given = False
    while (endClock-startClock<dayTime and not given):
        try:
            msg,t = mq_ask.receive(block=False,type=1)
            request=str(msg.decode())
            requestMessage = request.split(" ")
            amount = float(requestMessage[0])
            house_pid = int(requestMessage[1])

            if amount <= stock :
                energy_available = amount
            else :
                energy_available = stock

            mq_give.send(str(energy_available), type=house_pid)
            given = True 
        except sysv_ipc.BusyError:
            pass
        endClock = time.time()

    result = ("0"+","+str(energy_available))
    return result #result of form "price amount"

def send_energy(energy_trade_policy, index, stock):
    if energy_trade_policy == 1: 
        result=give_energy(index,stock)
    if energy_trade_policy == 2:
        result=sell_to_market(stock,index)
    if energy_trade_policy == 3:
        endClock=time.time()
        while endClock - startClock < dayTime and stock>0:
            give_energy(index,stock)
            endClock=time.time()
        if stock>0:
            result=sell_to_market(stock,index)
    return result #result of form "price amount"


def buy_to_market(index, amount):
    message=("BUY,"+str(amount))
    feedback=connectToMarket(message, index)
    return feedback #feedback of form "price amount"
        

        

def sell_to_market(amount, index):
    message= ("SELL,"+str(amount))
    feedback=connectToMarket(message, index)
    return feedback #feedback of form "price amount"

def connectToMarket(message, index):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as house_socket:
        connect=False
        while not connect:
            try :
                house_socket.connect((HOST, PORT))
                connect=True
            except:
                time.sleep(1)
                pass
        sent=False
        while not sent:
            try :
                house_socket.send(message.encode())
                sent = True
            except:
                time.sleep(1)
                pass

        feedback=[""]
        
        while feedback==[""]:
            try :
                feedback=house_socket.recv(1024).decode('utf-8')
                break
            except :
                time.sleep(1)
                pass
        house_socket.close()
        return feedback # feedback of form : "price amount"


# WEATHER FACTOR----------------------------------------------------------------------------------------
def weather(temp, list):
    while True:
        clock = random.randint(0,10)
        for i in range(clock):
            time.sleep(1)
            temp_variation = random.randint(-2,2)
            #print(f'The current temperature is {temp.value} degrees')
            temp.value = temp.value + temp_variation
            for j in range(len(list)):
                list[j] = temp.value

#CLOSING CONNECTION-------------------------------------------------------------------------------------
 
def handler(signum, frame):
    res = input("Ctrl-c was pressed. Do you really want to exit? y/n ")
    if res == 'y':
        exit(1)
 
#signal.signal(signal.SIGINT, handler)


if __name__== '__main__':

    #starter
    houseNb=int(prompt("How many houses do you want? (int expected)"))
    nbDays=int(prompt("How many days should the simulation run ? (int expected)"))

    NB_THREADS = houseNb

    barrier=Barrier(NB_THREADS)
    barrier_sock=Barrier(NB_THREADS+1)

    internal_factor = Array ('d', range (0))
    internal_coeff = [0.1 for i in range(len(internal_factor))]
    temperature = Value ('i', 20 )   

    child = Process(target=weather, args=(temperature, internal_factor))
    child.start()

    market_process = Process(target=market,args=(barrier_sock,))
    market_process.start()
    # home1 = Process(target=home, args=(1,barrier))
    # home2 = Process(target=home, args=(2,barrier))
    # home3 = Process(target=home, args=(3,barrier))
    # home4 = Process(target=home, args=(4,barrier))
    for i in range(0, houseNb):
        Process(target=home, args=(i,barrier,barrier_sock,)).start()
    # home1.start()
    # home2.start()
    # home3.start()
    # home4.start()
    # home1.join()
    # home2.join()
    # home3.join()
    # home4.join()

    child.join()
    market_process.join()