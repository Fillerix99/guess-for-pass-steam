from twisted.internet import reactor, defer, threads
from twisted.logger import Logger, textFileLogObserver, globalLogPublisher
import time, sys, requests, random

log = Logger()
reactor.suggestThreadPoolSize(20)
fread=open("proxy.txt").readline().rstrip()
proxies = {'http' : fread}
def try_password(password, app, real):
    try:
        r = requests.get(
                "http://store.steampowered.com/actions/clues",
				proxies=proxies,
                params={
                    "key": password,
                    "_": "%s%s" % (time.time(), random.randint(0, 1000000))
                },
                headers={
                    'Referer': "http://store.steampowered.com/app/%d/" % app
                }
            )
        try:
            result = r.json()
            if result:
                if real:
                    if "url" in result:
                        log.info("Got a result! Password {password} on {app} told me to go to url {url}", password=password, app=app, url=result["url"])
                    elif "response" in result:
                        log.info("Got a result! Password {password} on {app} told me a clue: {clue}", password=password, app=app, clue=result["response"])
                    else:
                        log.info("Got a result! Password {password} on {app} gave me result: {result}", password=password, app=app, result=result)
                    reactor.stop()
                return result
            else:
                return None
        except ValueError:
            log.failure("Weird response trying {password} on app {app}: {response}", password=password, app=app, response=r.text)
            return None
    except requests.exceptions.RequestException:
        log.failure("Couldn't try password {password} on app {app}", password=password, app=app)
        return None

def ensure_valid():
    if not reactor.running:
        return False
    result = try_password("94050999014715", 6900, False)
    if result and 'response' in result and result['response'] == 'ic/4f21ca7':
        log.info("Still not ratelimited...")
        return True
    else:
        log.error("Got weird response checking hitman password: {response}", response=result)
        reactor.stop()
        return False

def scan_apps(password, apps, amount, first=False):
    if not first:
        if not ensure_valid():
            return
        time.sleep(5)
    amount = min(amount, len(apps))
    chunk = apps[0:amount]
    del apps[0:amount]
    if not chunk:
        reactor.stop()
        return
    log.info("Trying {password} on {apps} apps ({total} to go)...", password=password, apps=len(chunk), total=len(apps))

    defers = []
    for app in chunk:
        defers.append(threads.deferToThread(try_password, password, app, True))
    dl = defer.DeferredList(defers)
    dl.addCallback(lambda results: scan_apps(password, apps, amount))
    dl.addErrback(lambda error: log.failure("Couldn't scan apps", failure=error))

if __name__ == '__main__':
    if len(sys.argv) < 3 or len(sys.argv) > 4 or len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Usage: %s <list_file> <password> [chunk_size]" % sys.argv[0])
        sys.exit(1)
    list_file = sys.argv[1]
    password = sys.argv[2]
    chunk_size = 1500
    if len(sys.argv) > 3:
        chunk_size = int(sys.argv[3])

    with open(list_file, 'r') as app_file:
        apps = [int(line.strip()) for line in app_file]

    globalLogPublisher.addObserver(textFileLogObserver(sys.stdout))
    scan_apps(password, apps, chunk_size, first=True)
    reactor.run()
