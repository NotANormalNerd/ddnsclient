import logging
import signal
import sys
from threading import Event

import click
import click_config_file
import daemon
import requests

import ddnsclient

killswitch = Event()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger()


def terminate(signal, stack_frame):
    logger.info(f"Shutting down: {signal}")
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
@click.option("-v", "--debug", is_flag=True)
@click_config_file.configuration_option()
def command(ddns_server, login, password, delay, web, web_v6=None, debug=False):
    if debug:
        logger.setLevel(logging.DEBUG)
    logger.info(f"Starting ddnsclient version {ddnsclient.VERSION}")
    logger.debug(f"Config: {locals()}")

    last_ipv4 = None
    last_ipv6 = None

    with daemon.DaemonContext(stdout=sys.stdout, stderr=sys.stderr, signal_map=SIGNAL_MAP, detach_process=False):
        logger.info("Switched into daemon context")
        while not killswitch.is_set():
            # find out my ipv4
            try:
                myip_v4 = requests.get(web).text
                logger.info(f"Successfully received a response from web: {myip_v4}")

                if myip_v4 != last_ipv4:
                    logger.info(f"IPv4 changed {last_ipv4} -> {myip_v4}")
                    last_ipv4 = myip_v4

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Could no access {web}: {e}")
                terminate(None, None)

            # find out my ipv6
            if web_v6:
                try:
                    myip_v6 = requests.get(web_v6).text
                    logger.info(f"Successfully received a response from web: {myip_v6}")

                    if myip_v6 != last_ipv6:
                        logger.info(f"IPv6 changed {last_ipv6} -> {myip_v6}")
                        last_ipv6 = myip_v6

                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"Could no access {web_v6}: {e}")
                    terminate(None, None)

            if myip_v4 == last_ipv4 or myip_v6 == last_ipv6:
                logger.info(f"IPv4 {myip_v4} and IPv6 {myip_v6} did not change. Not updating the DYNDNS Endpoint")
            else:
                # build the url and the params
                url = f"https://{ddns_server}/nic/update"
                ipv4 = f"myip={myip_v4}"
                last_ipv4 = myip_v4
                ipv6 = f"myipv6={myip_v6}" if web_v6 else None
                last_ipv6 = myip_v6

                try:
                    result = requests.get(f"{url}?{ipv4}&{ipv6 or ''}", auth=(login, password))
                    logger.info(f"Request successfully sent: {result.request.url}")
                    result.raise_for_status()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Encountered a problem setting the new IP: {e}")

            killswitch.wait(delay)


if __name__ == '__main__':
    command()
