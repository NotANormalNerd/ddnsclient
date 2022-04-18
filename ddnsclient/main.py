import logging
import signal
import sys
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, AddressValueError
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


@dataclass
class IPRegistry:
    ipv4: IPv4Address = IPv4Address("0.0.0.0")
    ipv4_changed: bool = False

    ipv6: IPv6Address = IPv6Address("::")
    ipv6_changed: bool = False

    def set_ipv4(self, ipv4):
        ipv4 = IPv4Address(ipv4)
        self.ipv4_changed = self.ipv4 != ipv4
        logger.info(f"IPv4 has {'' if self.ipv4_changed else 'not'} changed: {self.ipv4} -> {ipv4}")
        self.ipv4 = ipv4

    def set_ipv6(self, ipv6):
        ipv6 = IPv6Address(ipv6)
        self.ipv6_changed = self.ipv6 != ipv6
        logger.info(f"IPv6 has {'' if self.ipv6_changed else 'not'} changed: {self.ipv6} -> {ipv6}")
        self.ipv6 = ipv6


@click.command()
@click.option("-s", "--ddns-server")
@click.option("-u", "--login")
@click.option("-p", "--password")
@click.option("-d", "--delay", type=int, default=600, show_default=True)
@click.option("-w", "--web")
@click.option("-w6", "--web-v6")
@click.option("-n", "--dry-run", is_flag=True)
@click.option("-v", "--debug", is_flag=True)
@click_config_file.configuration_option()
def command(ddns_server, login, password, delay, web, web_v6=None, dry_run=False, debug=False):
    if debug:
        logger.setLevel(logging.DEBUG)
    logger.info(f"Starting ddnsclient version {ddnsclient.VERSION}")
    logger.debug(f"Config: {locals()}")

    registry = IPRegistry()

    with daemon.DaemonContext(stdout=sys.stdout, stderr=sys.stderr, signal_map=SIGNAL_MAP, detach_process=False):
        logger.info("Switched into daemon context")
        while not killswitch.is_set():
            # find out my ipv4
            try:
                registry.set_ipv4(requests.get(web).text)
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Could no access {web}: {e}")
                terminate(None, None)
            except AddressValueError as e:
                logger.warning(f"Returned malformed IPv4 {e}")
                terminate(None, None)

            # find out my ipv6
            if web_v6:
                try:
                    registry.set_ipv6(requests.get(web_v6).text)
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"Could no access {web_v6}: {e}")
                    terminate(None, None)
                except AddressValueError as e:
                    logger.warning(f"Returned malformed IPv4 {e}")
                    terminate(None, None)

            if registry.ipv4_changed or registry.ipv6_changed:
                # build the url and the params
                url = f"https://{ddns_server}/nic/update"

                ipv4_query = f"myip={registry.ipv4}"
                ipv6_query = f"myipv6={registry.ipv6}" if registry.ipv6_changed else ""

                try:
                    if not dry_run:
                        result = requests.get(f"{url}?{ipv4_query}&{ipv6_query}", auth=(login, password))
                    logger.info(f"Request successfully sent: {result.request.url}")
                    result.raise_for_status()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Encountered a problem setting the new IP: {e}")
            else:
                logger.info(
                    f"IPv4 {registry.ipv4} and IPv6 {registry.ipv6} did not change. Not updating the DYNDNS Endpoint")

            killswitch.wait(delay)


if __name__ == '__main__':
    command()
