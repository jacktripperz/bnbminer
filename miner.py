import json
import time
import contract as c
import cyclemanager as cmanager
from datetime import datetime,timedelta
import time
import json

dm_contract_addr = "0xce93F9827813761665CE348e33768Cb1875a9704"
loop_sleep_seconds = 2
start_polling_threshold_in_seconds = 0

# load private key
wallet_private_key = open('key.txt', "r").readline().strip().strip('\'').strip('\"').strip()

# load public address
wallet_public_addr = open('pa.txt', "r").readline().strip().strip('\'').strip('\"').strip()

# load abi
f = open('bnbminer_abi.json')
dm_abi = json.load(f)

# create contract
dm_contract = c.connect_to_contract(dm_contract_addr, dm_abi)

# create cycle
cycle = cmanager.build_cycle_from_config()

# methods
def compound():
    txn = dm_contract.functions.hatchEggs(wallet_public_addr).buildTransaction(c.get_tx_options(wallet_public_addr, 500000))
    return c.send_txn(txn, wallet_private_key)

def withdraw():
    txn = dm_contract.functions.sellEggs().buildTransaction(c.get_tx_options(wallet_public_addr, 500000))
    return c.send_txn(txn, wallet_private_key)

def my_miners():
    total = dm_contract.functions.hatcheryMiners(wallet_public_addr).call()
    return total

def payout_to_compound():
    eggs = dm_contract.functions.getEggsSinceLastHatch(wallet_public_addr).call()
    sellAmount = dm_contract.functions.calculateEggSell(eggs).call()
    fee = dm_contract.functions.devFee(sellAmount).call()
    return (sellAmount - fee)/1000000000000000000

def buildTimer(t):
    mins, secs = divmod(int(t), 60)
    hours, mins = divmod(int(mins), 60)
    timer = '{:02d} hours, {:02d} minutes, {:02d} seconds'.format(hours, mins, secs)
    return timer

def countdown(t):
    while t:
        print(f"Next poll in: {buildTimer(t)}", end="\r")
        time.sleep(1)
        t -= 1

def findCycleMinimumBnb(cycleId):
    for x in cycle:
        if x.id == cycleId:
            return x.minimumBnb
            break
        else:
            x = None

def findCycleType(cycleId):
    for x in cycle:
        if x.id == cycleId:
            return x.type
            break
        else:
            x = None

def findCycleEndTimerAt(cycleId):
    for x in cycle:
        if x.id == cycleId:
            return x.endTimerAt
            break
        else:
            x = None

def calcNextCycleId(currentCycleId):
    cycleLength = len(cycle)
    if currentCycleId == cycleLength:
        return 1
    else:
        newCycleId = currentCycleId + 1
        return newCycleId

def seconds_until_cycle(endTimerAt):
    time_delta = datetime.combine(
        datetime.now().date(), datetime.strptime(endTimerAt, "%H:%M").time()
    ) - datetime.now()
    return time_delta.seconds

# create infinate loop that checks contract every set sleep time
nextCycleId = cmanager.getNextCycleId()
nextCycleType = findCycleType(nextCycleId)
retryCount = 0

def itterate():
    global nextCycleId
    global nextCycleType
    cycleMinimumBnb = findCycleMinimumBnb(nextCycleId)
    nextCycleTime = findCycleEndTimerAt(nextCycleId)
    secondsUntilCycle = seconds_until_cycle(nextCycleTime)
    myMiners = my_miners()
    payoutToCompound = payout_to_compound()

    dateTimeObj = datetime.now()
    timestampStr = dateTimeObj.strftime("[%d-%b-%Y (%H:%M:%S)]")

    sleep = loop_sleep_seconds 
    
    print("********** BNB miner *******")
    print(f"{timestampStr} Next cycle id: {nextCycleId}")
    print(f"{timestampStr} Next cycle type: {nextCycleType}")
    print(f"{timestampStr} Next cycle time: {nextCycleTime}")
    print(f"{timestampStr} My miners: {myMiners}")
    print(f"{timestampStr} Estimated daily miners: {myMiners*0.08:.3f}")
    print(f"{timestampStr} Payout available for compound/withdraw: {payoutToCompound:.8f} BNB")
    print(f"{timestampStr} Minimum set for compound/withdraw: {cycleMinimumBnb:.8f} BNB")
    print("******************************")

    if secondsUntilCycle > start_polling_threshold_in_seconds:
        sleep = secondsUntilCycle - start_polling_threshold_in_seconds

    countdown(int(sleep))

    payoutToCompound = payout_to_compound()

    if payoutToCompound >= cycleMinimumBnb:
        if nextCycleType == "compound":
            compound()
        if nextCycleType == "withdraw":
            withdraw()
        
        if nextCycleType == "compound":
            print("********** COMPOUNDED *******")
            print(f"{timestampStr} Compounded {payoutToCompound:.8f} BNB to the pool!")
        if nextCycleType == "withdraw":
            print("********** WITHDREW ***********")
            print(f"{timestampStr} Withdrew {payoutToCompound:.8f} BNB!")

        print("**************************")
        print(f"{timestampStr} Sleeping for 1 min until next cycle starts..")
        countdown(60)

    print("********** IDLE ***********")
    calculatedNextCycleId = calcNextCycleId(nextCycleId)
    cmanager.updateNextCycleId(calculatedNextCycleId)
    nextCycleId = cmanager.getNextCycleId()
    nextCycleType = findCycleType(nextCycleId)
    print(f"{timestampStr} Available compund/withdraw did not meet the minimum requirements")
    print(f"{timestampStr} Moving on to next cycle")
    print(f"{timestampStr} Next cycleId is: {nextCycleId}")
    print(f"{timestampStr} Next cycle type will be: {nextCycleType}")
    print("**************************")
 
def run(): 
    global retryCount
    try: 
        itterate()
        run()
    except Exception as e:
        retryCount = retryCount + 1
        print("********* EXCEPTION *****************")
        print("Something went wrong! Message:")
        print(f"{e}")
        if retryCount < 5:
            print(f"[EXCEPTION] Retrying! (retryCount: {retryCount})")
            print("*************************************")
            run()
        else:
            print("********* TERMINATING *****************")
            print("Exception occurred 5 times. Terminating!")

run()
