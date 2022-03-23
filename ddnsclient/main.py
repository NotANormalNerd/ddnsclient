import requests
import time
import click
import click_config_file

@click.command()
@click.option("-s", "--ddns-server", required=True)
@click.option("-u", "--login")
@click.option("-p", "--password")
@click.option("-d", "--delay", type=int)
@click.option("-w", "--web", required=True)
@click.option("-w6", "--web-v6")
@click_config_file.configuration_option()
def command(ddns_server, login, password, delay, web, web_v6=None):
    print(locals())
    while True:
        # find out my ipv4
        myipv4 = requests.get(web).text

        # find out my ipv6
        if web_v6:
            myipv6 = requests.get(web_v6).text

        # call api for DynDNS update
        url = f"https://{login}:{password}@{ddns_server}/nic/update"
        ipv4 = f"myip={myipv4}"
        ipv6 = None
        if web_v6:
            ipv6 = f"myipv6={myipv6}"

        try:
            result = requests.get(f"{url}?{ipv4}&{ipv6 or ''}")
            print(f"Request sucessfully sent: {result.request.url}")
            result.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Encountered a problem setting the new IP: {e}")

        time.sleep(delay)


if __name__ == '__main__':
    command()
