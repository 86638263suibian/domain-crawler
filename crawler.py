import argparse

from tqdm import tqdm
from sys import argv
from pprint import pformat

from twisted.internet.task import react
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
from twisted.internet.task import cooperate
from twisted.internet.defer import gatherResults

import lxml.html

from geoip import geolite2
import pycountry

from tld import get_tld
import json
import socket

poweredby = ""
server = ""
ip = ""


def cbRequest(response, url):
    global poweredby, server, ip
    # print 'Response version:', response.version
    # print 'Response code:', response.code
    # print 'Response phrase:', response.phrase
    # print 'Response headers:'
    # print pformat(list(response.headers.getAllRawHeaders()))
    poweredby = response.headers.getRawHeaders("X-Powered-By")[0]
    server = response.headers.getRawHeaders("Server")[0]

    #print poweredby
    #print server

    d = readBody(response)
    d.addCallback(cbBody, url)
    return d


def cbBody(body, ourl):
    global poweredby, server,ip

    #print body
    html_element = lxml.html.fromstring(body)
    generator = html_element.xpath("//meta[@name='generator']/@content")

    ip = socket.gethostbyname(ourl)

    try:
        match = geolite2.lookup(ip)
        if match is not None:
            country = match.country
            try:

                c = pycountry.countries.lookup(country)
                country = c.name
            except:
                country = ""

    except:
        country = ""
    try:
        res = get_tld("http://www" + ourl, as_object=True)
        tld = res.suffix
    except:
        tld = ""

    try:
        match = re.search(r'[\w\.-]+@[\w\.-]+', body)
        email = match.group(0)
    except:
        email = ""

    permalink=ourl.rstrip().replace(".","-")

    try:
        item = generator[0]
        val = "{ \"Domain\":" + json.dumps(
            "http://" + ourl.rstrip()) + ",\"IP\":\"" + ip + "\",\"Server\":" + json.dumps(
            str(server)) + ",\"PoweredBy\":" + json.dumps(
                str(poweredby)) + ",\"MetaGenerator\":" + json.dumps(item) + ",\"Email\":" + json.dumps(
                    email) + ",\"Suffix\":\"" + tld + "\",\"CountryHosted\":\"" + country+"\",\"permalink\":\""+permalink+"\" }"
    except:
        val = "{ \"Domain\":" + json.dumps(
            "http://" + ourl.rstrip()) + ",\"IP\":\"" + ip + "\"," + "\"Server\":" + json.dumps(
            str(server)) + ",\"PoweredBy\":" + json.dumps(
                str(poweredby)) + ",\"MetaGenerator\":\"\",\"Email\":" + json.dumps(
                    email) + ",\"Suffix\":\"" + tld + "\",\"CountryHosted\":\"" + country+"\",\"permalink\":\""+permalink+"\" }"


    print val


def main(reactor, url_path):
    urls = open(url_path)
    return mainjob(reactor, (url.strip() for url in urls))

def mainjob(reactor, urls=argv[2:]):
    #for url in urls:
    #  print url
    agent = Agent(reactor)
    work = (process(agent, url) for url in tqdm(urls))
    tasks = list(cooperate(work) for i in range(100))
    return gatherResults(list(task.whenDone() for task in tasks))



def process(agent, url):
    d = agent.request(
        'GET', "http://" + url,
        Headers({'User-Agent': ['bot']}),
        None)
    d.addCallback(cbRequest, url)
    d.addErrback(lambda x: None)  # ignore errors
    return d

react(main, ["./domain-list.txt"])

