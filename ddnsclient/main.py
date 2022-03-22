import requests
import time
import click

@click.command()
@click.option("-s", "--server")
@click.option("-u", "--login")
@click.option("-p", "--password")
@click.option("-s", "--delay")
@click.option("-w", "--web")
@click.option("-w6", "--web-v6")
def command(server, login, password, delay, web, web_6):
    while True:
        # find out my ipv4
        print(requests.get("https://ipv4.nsupdate.info/myip").text)
        # find out my ipv6
        # print(requests.get("https://ipv6.nsupdate.info/myip").text)
        # call api for DynDNS update
        requests.get("https://dyndns.inwx.com/nic/update?myip=<ipaddr>&myipv6=<ip6addr>")

        time.sleep(delay)

if __name__ == '__main__':
    command()