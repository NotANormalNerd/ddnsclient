import logging
import signal
import sys
from threading import Event

import click
import click_config_file
import daemon
import requests

killswitch = Event()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger()


def terminate(signal, stack_frame):
    logger.info("Shutting down")
    killswitch.set()


SIGNAL_MAP = {
    signal.SIGTERM: terminate,
    signal.SIGINT: terminate
}


@click.command()
@click.option("-s", "--ddns-server")
@click.option("-u", "--login")
@click.option("-p", "--password")
@click.option("-d", "--delay", type=int, default=600, show_default=True)
@click.option("-w", "--web")
@click.option("-w6", "--web-v6")
@click_config_file.configuration_option()
def command(ddns_server, login, password, delay, web, web_v6=None):
    logger.info(f"Starting ddnsclient with {locals()}")
    with daemon.DaemonContext(stdin=sys.stdin, stderr=sys.stderr, signal_map=SIGNAL_MAP):
        logger.info("Switched into daemon context")
        while not killswitch.is_set():
            # find out my ipv4
            myip_v4 = requests.get(web).text

            # find out my ipv6
            if web_v6:
                try:
                    myip_v6 = requests.get(web_v6).text
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Could no access {web_v6}")

            # build the url and the params
            url = f"https://{ddns_server}/nic/update"
            ipv4 = f"myip={myip_v4}"
            ipv6 = f"myipv6={myip_v6}" if web_v6 else None

            try:
                result = requests.get(f"{url}?{ipv4}&{ipv6 or ''}", auth=(login, password))
                logger.info(f"Request sucessfully sent: {result.request.url}")
                result.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"Encountered a problem setting the new IP: {e}")

            killswitch.wait(delay)


if __name__ == '__main__':
    command()
